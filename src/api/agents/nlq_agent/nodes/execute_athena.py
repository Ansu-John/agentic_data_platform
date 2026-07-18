import os
from typing import Any

import awswrangler as wr
import structlog
from src.api.agents.nlq_agent.state import NLQAgentState

logger = structlog.get_logger()

def execute_athena(state: NLQAgentState) -> dict[str, Any]:
    """Executes the validated query against AWS Athena within the isolated workgroup container."""
    if not state["sql_is_valid"] or state.get("error_trace"):
        return {}

    sql = state["generated_sql"]
    if not sql:
        return {"error_trace": "Execution failed: No SQL query was provided."}
    database = os.getenv("GLUE_DATABASE", "dataplatform_dev_ai_catalog")
    workgroup = os.getenv("ATHENA_WORKGROUP", "dataplatform_dev_nlq_workgroup")

    logger.info("running_athena_query", sql=sql, workgroup=workgroup, database=database)

    try:
        # awswrangler internally tracks execution IDs, polls the state transitions, and pushes to S3
        df = wr.athena.read_sql_query(
            sql=sql,
            database=database,
            workgroup=workgroup,
            ctas_approach=False # Avoid building temporary tables in the data lake
        )

        # Limit payload sizes passed through the state graph memory
        json_payload = df.head(100).to_json(orient="records")

        return {
            "query_results_json": json_payload,
            "error_trace": None
        }

    except Exception as e:
        logger.error("athena_query_execution_failed", error=str(e))
        return {
            "error_trace": f"Athena Engine execution error: {str(e)}"
        }
