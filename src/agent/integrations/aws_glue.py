
from datetime import datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.agent.core.exceptions import GlueCatalogUpdateError
from src.agent.core.logger import get_logger

logger = get_logger(__name__)

# The strict whitelist of keys allowed in TableInput for update_table/create_table
ALLOWED_TABLE_INPUT_KEYS = {
    "Name",
    "Description",
    "Owner",
    "LastAccessTime",
    "LastAnalyzedTime",
    "Retention",
    "StorageDescriptor",
    "PartitionKeys",
    "ViewOriginalText",
    "ViewExpandedText",
    "TableType",
    "Parameters",
    "TargetTable",
    "ViewDefinition",
}

class GlueCatalogRepository:
    """Handles operational mutations against Data Catalog schemas."""

    def __init__(self, region_name: str):
        self.client = boto3.client("glue", region_name=region_name)

    def enrich_table_metadata(self, database: str, table_name: str, metrics: dict[str, Any],
                              status: str) -> None:
        """Applies transaction-safe state changes and
        performance metrics back to the Data Catalog."""
        try:
            # 1. Fetch the raw table representation from Glue
            response = self.client.get_table(DatabaseName=database, Name=table_name)
            raw_table = response["Table"]

            # 2. Safely capture the UpdateTime from the raw table *before* filtering.
            # Note: boto3 returns UpdateTime as a native Python datetime object.
            update_time = raw_table.get("UpdateTime")
            if isinstance(update_time, datetime):
                last_dq_timestamp = str(int(update_time.timestamp()))
            else:
                last_dq_timestamp = "0"

            # 3. Filter raw table down to ONLY allowed TableInput fields (whitelist approach)
            table_input = {k: v for k, v in raw_table.items() if k in ALLOWED_TABLE_INPUT_KEYS}

            # 4. Standardize platform properties safely
            parameters = table_input.setdefault("Parameters", {})
            parameters["governance_compliance_status"] = status
            parameters["last_dq_scan_timestamp"] = last_dq_timestamp

            for metric_key, val in metrics.items():
                parameters[f"dq_metric_{metric_key}"] = str(val)

            table_input["Parameters"] = parameters

            # 5. Commit the sanitized TableInput
            self.client.update_table(
                DatabaseName=database,
                TableInput=table_input
            )
            logger.info("glue_catalog_mutation_committed", database=database, table=table_name,
                        status=status)
        except ClientError as e:
            logger.error("glue_catalog_mutation_failed", table=table_name, error=str(e))
            raise GlueCatalogUpdateError(f"Failed to patch catalog entry for table "
                                         f"{table_name}: {str(e)}") from e
