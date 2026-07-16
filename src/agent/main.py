import json
import sys
from typing import Any

from src.agent.config.settings import settings
from src.agent.core.logger import configure_enterprise_logging, correlation_id, get_logger
from src.agent.graph import build_governance_graph

# Initialize root logging maps during initial container bootstrap
configure_enterprise_logging(log_level="INFO")
logger = get_logger(__name__)

def handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    """
    AWS EventBridge target entry point. Parses upstream orchestration event data,
    maps trace contexts, and runs the LangGraph state machine.
    """
    logger.info("container_task_triggered", raw_event_payload=event)

    try:
        # Extract metadata from upstream pipeline events
        detail = event.get("detail", {})
        execution_arn = detail.get("executionArn")

        if not execution_arn:
            raise KeyError("""Inbound EventBridge payload missing required
                            'detail.executionArn' coordinate.""")

        # Bind the trace identifier across thread context lines
        correlation_id.set(execution_arn)

        upstream_output = detail.get("output", {})
        target_table = upstream_output.get("table_name")

        if not target_table:
            raise KeyError("Inbound operational payload missing "+
                           "'detail.output.table_name' metadata target.")

        logger.info("processing_governance_layer_execution",
                    target_table=target_table, step_function_arn=execution_arn)

        # Build the initial execution state matching the AgentState contract
        initial_context: dict[str, Any] = {
            "execution_arn": execution_arn,
            "target_database": settings.CATALOG_DATABASE,
            "target_table": target_table,
            "athena_output_s3_prefix": f"s3://{settings.SILVER_BUCKET_NAME}/_athena_temp_results/",
            "profiling_results": {},
            "validation_status": "PENDING",
            "failure_reasoning": "None",
            "quarantine_manifest_uri": "None",
            "logs": [{"handler": "bootstrap", "status": "INITIALIZED"}]
        }

        # Invoke the active graph
        workflow = build_governance_graph()
        runtime_outcome = workflow.invoke(initial_context)

        compliance_result = runtime_outcome.get("validation_status")
        logger.info("agent_workflow_terminated_normally", compliance_outcome=compliance_result)

        return {
            "statusCode": 200,
            "executionStatus": "SUCCESS",
            "body": {
                "database": settings.CATALOG_DATABASE,
                "table": target_table,
                "compliance": compliance_result,
                "quarantine_manifest": runtime_outcome.get("quarantine_manifest_uri")
            }
        }

    except KeyError as ke:
        logger.error("payload_schema_validation_failed", error=str(ke))
        sys.exit(2)  # Return dedicated exit code for configuration issues
    except Exception as e:
        logger.critical("fatal_unhandled_agent_engine_exception", error=str(e), exc_info=True)
        sys.exit(1)  # Signal failure to the Fargate ECS container orchestration plane

if __name__ == "__main__":
    # Allows developers to execute local simulation pipelines by running the module directly
    try:
        with open("events/mock_upstream_success.json") as f:
            local_event = json.load(f)
    except FileNotFoundError:
        local_event = {
            "detail": {
                "executionArn": "arn:aws:states:ap-south-1:${{ secrets.AWS_ACCOUNT_ID }}:"
                "execution:DataPipelineSFN:run-8821B",
                "output": {"table_name": "silver_events"}
            }
        }

    handler(local_event)
