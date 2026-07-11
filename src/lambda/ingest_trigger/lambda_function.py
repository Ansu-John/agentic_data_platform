import json
import os
import logging
import urllib.parse
from typing import Dict, Any, List

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# -------------------------------------------------------------------
# 1. Initialization & Configuration (Runs on cold start)
# -------------------------------------------------------------------
# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Retrieve and validate environment variables
ENVIRONMENT = os.environ.get("ENVIRONMENT")
if not ENVIRONMENT:
    logger.error("CRITICAL: ENVIRONMENT variable is not set.")
    raise ValueError("Missing required environment variable: ENVIRONMENT")

# Configure Boto3 client with aggressive timeouts and exponential backoff
# Best practice to prevent Lambda from hanging and billing for idle time
BOTO_CONFIG = Config(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=15
)

# Initialize AWS clients outside the handler to reuse connection pools across warm starts
# (e.g., sfn_client = boto3.client('stepfunctions', config=BOTO_CONFIG))

# -------------------------------------------------------------------
# 2. Helper Functions
# -------------------------------------------------------------------
def parse_s3_event(event: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Safely extracts bucket names and object keys from an S3 event payload.
    """
    records = event.get("Records", [])
    if not records:
        logger.warning("Received event with no 'Records' array. Ignoring.")
        return []

    parsed_files = []
    for record in records:
        try:
            bucket = record["s3"]["bucket"]["name"]
            # S3 replaces spaces with '+', so we must unquote it safely
            key = urllib.parse.unquote_plus(record["s3"]["object"]["key"], encoding="utf-8")
            parsed_files.append({"bucket": bucket, "key": key})
        except KeyError as e:
            logger.error(f"Malformed S3 event record. Missing key: {str(e)}", exc_info=True)
            continue
            
    return parsed_files

# -------------------------------------------------------------------
# 3. Main Handler
# -------------------------------------------------------------------
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Triggered by S3 ObjectCreated events. 
    Intercepts raw data drops and orchestrates downstream AI evaluation.
    """
    # Log the exact invocation ID for distributed tracing
    request_id = context.aws_request_id
    logger.info(json.dumps({
        "message": "Lambda invoked",
        "request_id": request_id,
        "environment": ENVIRONMENT
    }))

    try:
        # 1. Parse the incoming payload
        files_to_process = parse_s3_event(event)
        
        if not files_to_process:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No valid S3 records found in event"})
            }

        # 2. Process each file
        for file_data in files_to_process:
            bucket = file_data["bucket"]
            key = file_data["key"]
            
            logger.info(json.dumps({
                "message": "Processing file drop",
                "bucket": bucket,
                "key": key,
                "status": "INITIATED"
            }))
            
            # TODO: Phase 3 Integration
            # Example: Trigger AWS Step Functions to start LangGraph evaluation
            # sfn_client.start_execution(
            #     stateMachineArn=os.environ['STEP_FUNCTION_ARN'],
            #     name=f"Ingest-{request_id}",
            #     input=json.dumps({"bucket": bucket, "key": key})
            # )

        # 3. Return standardized success response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Successfully processed {len(files_to_process)} file(s)",
                "request_id": request_id
            })
        }

    except ClientError as e:
        # Catch specific AWS API errors (e.g., permissions issues, throttling)
        error_code = e.response['Error']['Code']
        logger.error(json.dumps({
            "message": "AWS API Error",
            "error_code": error_code,
            "details": str(e)
        }))
        raise e

    except Exception as e:
        # Catch-all for unexpected runtime errors to ensure they hit the DLQ if configured
        logger.critical(json.dumps({
            "message": "Unexpected runtime error during execution",
            "error_type": type(e).__name__,
            "details": str(e)
        }), exc_info=True)
        raise e