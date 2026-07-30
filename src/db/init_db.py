import json
import logging
import os
import time
from typing import Any, cast

import boto3
from botocore.exceptions import ClientError
from pg8000.native import Connection  # type: ignore

# Configure structured enterprise logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration Constants
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 10

def get_db_credentials(secret_arn: str) -> dict[str, str]:
    """Securely fetches database credentials from AWS Secrets Manager."""
    logger.info(f"Fetching credentials from Secrets Manager: {secret_arn}")
    try:
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId=secret_arn)
        parsed_secret = json.loads(response['SecretString'])
        return cast(dict[str, str], parsed_secret)
    except ClientError as e:
        logger.error(f"Failed to retrieve secrets: {e}")
        raise e

def get_db_connection(db_host: str, db_name: str,
                      secret_dict: dict[str, str]) -> Connection:
    """Attempts to connect to Aurora PostgreSQL with exponential backoff."""
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            logger.info(f"Attempting database connection to {db_host} "
                        f"(Attempt {attempt + 1}/{MAX_RETRIES})...")
            conn = Connection(
                host=db_host,
                database=db_name,
                user=secret_dict['username'],
                password=secret_dict['password'],
                timeout=10
            )
            # DDL commands like CREATE EXTENSION cannot run in a transaction block
            conn.autocommit = True
            logger.info("Database connection established successfully.")
            return conn
        except Exception as e:
            attempt += 1
            logger.warning(f"Connection failed. Aurora may still be initializing. "
                           f"Retrying in {RETRY_DELAY_SECONDS}s... Error: {e}")
            if attempt >= MAX_RETRIES:
                logger.error("Maximum connection retries exceeded.")
                raise e
            time.sleep(RETRY_DELAY_SECONDS)
    raise RuntimeError("Failed to connect to the database: Maximum retries exceeded.")

def initialize_schema(conn: Any) -> None:
    """Executes the DDL statements to establish the AI Vector schema."""
    ddl_statements = [
        "CREATE EXTENSION IF NOT EXISTS vector;",
        "CREATE SCHEMA IF NOT EXISTS catalog;",
        """
        CREATE TABLE IF NOT EXISTS catalog.data_assets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            table_name VARCHAR(255) NOT NULL,
            description TEXT,
            compliance_status VARCHAR(50),
            total_record_count INT,
            embedding vector(1536),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS data_assets_embedding_idx
        ON catalog.data_assets USING hnsw (embedding vector_cosine_ops);
        """
    ]

    for statement in ddl_statements:
        logger.info(f"Executing DDL: {statement.strip().splitlines()[0]}...")
        conn.run(statement)
    logger.info("All DDL statements executed successfully.")

def lambda_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """AWS Lambda entry point."""
    logger.info("Starting Database Initialization sequence.")

    # Environment variables injected by Terraform
    db_host = os.environ.get('DB_HOST')
    db_name = os.environ.get('DB_NAME')
    secret_arn = os.environ.get('SECRET_ARN')

    if not all([db_host, db_name, secret_arn]):
        logger.error("Missing required environment variables.")
        raise ValueError("DB_HOST, DB_NAME, and SECRET_ARN must be set.")

    conn = None
    try:
        secret_dict = get_db_credentials(secret_arn) # type: ignore
        conn = get_db_connection(db_host, db_name, secret_dict) # type: ignore
        initialize_schema(conn)

        return {
            "statusCode": 200,
            "body": json.dumps("Enterprise Database initialization completed successfully.")
        }
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise e
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")
