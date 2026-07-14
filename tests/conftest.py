import os
import pytest
from typing import Any, Generator
from moto import mock_aws
import boto3

# 1. Force strict mocked environment variables BEFORE app imports occur
os.environ["DEPLOYMENT_ENV"] = "test"
os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"
os.environ["PLATFORM_SILVER_BUCKET"] = "test-silver-bucket"
os.environ["PLATFORM_QUARANTINE_BUCKET"] = "test-quarantine-bucket"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"

@pytest.fixture(scope="function")
def aws_credentials() -> None:
    """Mocked AWS Credentials for moto."""
    pass

@pytest.fixture(scope="function")
def glue_client(aws_credentials) -> Generator[Any, None, None]:
    """Yields a mocked AWS Glue client."""
    with mock_aws():
        client = boto3.client("glue", region_name="ap-south-1")
        yield client

@pytest.fixture(scope="function")
def mock_glue_catalog(glue_client) -> str:
    """Sets up a simulated Glue database and table structure for integration tests."""
    db_name = "dataplatform_silver_catalog"
    table_name = "silver_events"
    
    glue_client.create_database(DatabaseInput={"Name": db_name})
    glue_client.create_table(
        DatabaseName=db_name,
        TableInput={
            "Name": table_name,
            "Parameters": {"classification": "parquet"}
        }
    )
    return f"{db_name}.{table_name}"