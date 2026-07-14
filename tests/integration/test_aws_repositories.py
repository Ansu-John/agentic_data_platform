import pytest
from src.agent.integrations.aws_glue import GlueCatalogRepository
from botocore.exceptions import ClientError

def test_enrich_table_metadata_success(mock_glue_catalog, glue_client):
    """Verifies that the agent correctly patches Glue Catalog metadata without wiping existing tags."""
    db_name, table_name = mock_glue_catalog.split(".")
    
    repo = GlueCatalogRepository(region_name="ap-south-1")
    metrics = {"total_record_count": 5000, "calculated_null_ratio": 0.01}
    
    # Execute the mutation
    repo.enrich_table_metadata(db_name, table_name, metrics, "COMPLIANT")
    
    # Assert the state mutated correctly in the mocked AWS environment
    response = glue_client.get_table(DatabaseName=db_name, Name=table_name)
    parameters = response["Table"]["Parameters"]
    
    assert parameters["governance_compliance_status"] == "COMPLIANT"
    assert parameters["dq_metric_total_record_count"] == "5000"
    assert parameters["classification"] == "parquet" # Validates pre-existing tags weren't destroyed

def test_enrich_table_metadata_table_not_found(glue_client):
    """Verifies custom error propagation when target resources are missing."""
    repo = GlueCatalogRepository(region_name="ap-south-1")
    
    with pytest.raises(Exception) as exc_info:
        repo.enrich_table_metadata("invalid_db", "invalid_table", {}, "COMPLIANT")
        
    assert "Failed to patch catalog entry" in str(exc_info.value)