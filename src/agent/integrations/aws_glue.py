from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.agent.core.exceptions import GlueCatalogUpdateError
from src.agent.core.logger import get_logger

logger = get_logger(__name__)

class GlueCatalogRepository:
    """Handles operational mutations against Data Catalog schemas."""

    def __init__(self, region_name: str):
        self.client = boto3.client("glue", region_name=region_name)

    def enrich_table_metadata(self, database: str, table_name: str, metrics: dict[str, Any]
                              , status: str) -> None:
        """Applies transaction-safe state changes and
        performance metrics back to the Data Catalog."""
        try:
            response = self.client.get_table(DatabaseName=database, Name=table_name)
            table_input = response["Table"]

            # Purge immutable metadata parameters that block catalog updates
            for key in ["DatabaseName", "CreateTime", "UpdateTime", "CreatedBy",
                        "IsRegisteredWithLakeFormation", "CatalogId", "VersionId",
                        "FederatedTable"]:
                table_input.pop(key, None)

            # Standardize platform properties
            parameters = table_input.get("Parameters", {})
            parameters["governance_compliance_status"] = status
            parameters["last_dq_scan_timestamp"] = str(
                int(table_input.get("UpdateTime", {}).get("timestamp", 0)))
            for metric_key, val in metrics.items():
                parameters[f"dq_metric_{metric_key}"] = str(val)

            table_input["Parameters"] = parameters

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
