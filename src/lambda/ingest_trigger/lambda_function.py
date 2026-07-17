import json
import logging
import os
import uuid
from typing import Any

import boto3
from botocore.exceptions import ClientError


# ==============================================================================
# 1. ENTERPRISE OBSERVABILITY SETUP
# ==============================================================================
class JSONFormatter(logging.Formatter):
    """Custom formatter to output structured JSON logs for Datadog/Splunk indexing."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "custom_fields"):
            log_entry.update(record.custom_fields)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Clear default AWS handlers to prevent duplicate logging
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)

json_handler = logging.StreamHandler()
json_handler.setFormatter(JSONFormatter())
logger.addHandler(json_handler)


# ==============================================================================
# 2. COLD-START INITIALIZATION & VALIDATION (Fail-Fast)
# ==============================================================================
try:
    SFN_ARN = os.environ['STEP_FUNCTION_ARN']
    SILVER_BUCKET = os.environ['SILVER_BUCKET']
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
    PROJECT = os.environ.get('PROJECT', 'dataplatform')
except KeyError as e:
    logger.critical("Fatal: Missing required environment variable",
                    extra={"custom_fields": {"missing_var": str(e)}})
    raise RuntimeError(f"Initialization failed due to missing environment variable: {e}") from e

# Initialize boto3 clients globally to reuse connection pools across warm invocations
sfn_client = boto3.client('stepfunctions')


# ==============================================================================
# 3. DOMAIN LOGIC
# ==============================================================================
def parse_s3_event(event: dict[str, Any]) -> tuple[str, str, str]:
    """
    Extracts and validates S3 bucket, key, and logical entity name from the event.
    """
    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        # Expected pattern: raw/{entity}/{filename}.json
        parts = key.split('/')
        if len(parts) < 2:
            raise ValueError(f"S3 Key '{key}' does not match expected folder structure "
                             f"'raw/entity/file'")

        entity = parts[1]
        return bucket, key, entity
    except KeyError as e:
        raise ValueError(f"Malformed S3 event payload. Missing key: {e}") from e


# ==============================================================================
# 4. MAIN HANDLER
# ==============================================================================
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    AWS Lambda entry point. Orchestrates the transition from S3 event to Step Function.
    """
    request_id = context.aws_request_id

    logger.info("Lambda invoked", extra={"custom_fields": {
        "aws_request_id": request_id,
        "event_source": "s3_trigger"
    }})

    try:
        # 1. Parse Event
        bucket, key, entity = parse_s3_event(event)

        logger.info("S3 event parsed successfully", extra={"custom_fields": {
            "bucket": bucket,
            "key": key,
            "entity": entity,
            "aws_request_id": request_id
        }})

        # 2. Construct Step Function Payload
        job_name = f"ingest-{entity}-{uuid.uuid4().hex[:8]}"
        table_name = f"silver_{entity}"

        sfn_input = {
            "job_name": job_name,
            "source_path": f"s3://{bucket}/{key}",
            "db_name": f"{PROJECT}_{ENVIRONMENT}_ai_catalog",
            "table_name": table_name,
            "silver_bucket": SILVER_BUCKET,
            "merge_key": "event_id",
            "trigger_request_id": request_id  # Tracing lineage
        }

        # 3. Execute Orchestrator
        logger.info("Triggering Step Function", extra={"custom_fields": {
            "step_function_arn": SFN_ARN,
            "payload": sfn_input
        }})

        response = sfn_client.start_execution(
            stateMachineArn=SFN_ARN,
            name=job_name,
            input=json.dumps(sfn_input)
        )

        execution_arn = response['executionArn']
        logger.info("Step Function execution started successfully", extra={"custom_fields": {
            "execution_arn": execution_arn,
            "aws_request_id": request_id
        }})

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Ingestion pipeline triggered successfully',
                'execution_arn': execution_arn
            })
        }

    except ValueError as ve:
        # Client-side / Payload errors
        logger.error("Validation error processing event", extra={"custom_fields": {
            "aws_request_id": request_id,
            "error_type": "ValueError"
        }}, exc_info=True)
        return {'statusCode': 400, 'body': json.dumps(f"Bad Request: {str(ve)}")}

    except ClientError as ce:
        # AWS API / Permission errors
        error_code = ce.response['Error']['Code']
        logger.error(f"AWS API Error: {error_code}", extra={"custom_fields": {
            "aws_request_id": request_id,
            "aws_error_code": error_code
        }}, exc_info=True)
        return {'statusCode': 502, 'body': json.dumps(f"Upstream AWS Error: {error_code}")}

    except Exception as e:
        # Unhandled execution errors
        logger.error("Unhandled exception during execution", extra={"custom_fields": {
            "aws_request_id": request_id,
            "error_type": type(e).__name__
        }}, exc_info=True)
        return {'statusCode': 500, 'body': json.dumps("Internal Server Error")}
