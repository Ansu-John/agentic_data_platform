import time
from typing import Any

import boto3
from botocore.exceptions import ClientError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.agent.core.exceptions import AthenaQueryExecutionError
from src.agent.core.logger import get_logger

logger = get_logger(__name__)

class AthenaRepository:
    """Manages high-throughput analytical query compilation against Iceberg tables."""

    def __init__(self, region_name: str, database: str, workgroup: str = "primary"):
        self.client = boto3.client("athena", region_name=region_name)
        self.database = database
        self.workgroup = workgroup

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(4),
        retry=retry_if_exception_type(ClientError),
        reraise=True
    )
    def execute_query_async(self, query: str, output_location: str) -> str:
        """Launches an asynchronous query execution thread with automatic retries on throttling."""
        try:
            response = self.client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={"Database": self.database},
                ResultConfiguration={"OutputLocation": output_location},
                WorkGroup=self.workgroup
            )
            execution_id: str = response["QueryExecutionId"]
            logger.info("athena_query_submitted", query_execution_id=execution_id)
            return execution_id
        except ClientError as e:
            logger.error("athena_submission_failed", error=str(e), query=query)
            raise

    def poll_query_results(self, execution_id: str, max_wait_seconds: int = 180
                           ) -> list[dict[str, Any]]:
        """Blocks and polls until results are ready, parsing rows into standard dictionary maps."""
        start_time = time.time()
        sleep_interval = 2.0

        while time.time() - start_time < max_wait_seconds:
            try:
                response = self.client.get_query_execution(QueryExecutionId=execution_id)
                state = response["QueryExecution"]["Status"]["State"]

                if state == "SUCCEEDED":
                    logger.info("athena_query_success", query_execution_id=execution_id)
                    return self._parse_results(execution_id)

                if state in ("FAILED", "CANCELLED"):
                    reason = response["QueryExecution"]["Status"].get("StateChangeReason",
                                                                      "Unknown")
                    raise AthenaQueryExecutionError(f"Athena query {execution_id} terminated "
                                                    f"in state {state}: {reason}")

                time.sleep(sleep_interval)
                sleep_interval = min(sleep_interval * 1.5, 10) # Progressive backoff
            except ClientError as e:
                logger.error("athena_polling_error", query_execution_id=execution_id, error=str(e))
                raise

        raise AthenaQueryExecutionError(f"Athena query {execution_id} timed out after "
                                        f"{max_wait_seconds} seconds.")

    def _parse_results(self, execution_id: str) -> list[dict[str, Any]]:
        """Parses raw Athena tabular data structures into standard Python primitives."""
        paginator = self.client.get_paginator("get_query_results")
        parsed_rows: list[dict[str, Any]] = []
        is_header = True
        headers: list[str] = []

        for page in paginator.paginate(QueryExecutionId=execution_id):
            for row in page["ResultSet"]["Rows"]:
                cells = [cell.get("VarCharValue", "") for cell in row["Data"]]
                if is_header:
                    headers = cells
                    is_header = False
                    continue
                parsed_rows.append(dict(zip(headers, cells, strict=False)))

        return parsed_rows
