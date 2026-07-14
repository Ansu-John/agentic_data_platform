from enum import StrEnum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DeploymentEnv(StrEnum):
    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"

class Settings(BaseSettings):
    """
    Validates and stores the immutable environment configuration for the
    AI Data Quality and Governance multi-agent platform.
    """
    ENVIRONMENT: DeploymentEnv = Field(default=DeploymentEnv.DEV)
    AWS_REGION: str = Field(default="ap-south-1")

    # Core Data Lake Infra Parameters
    SILVER_BUCKET_NAME: str = Field(default="dataplatform-dev-s3-ap-south-1-silver")
    QUARANTINE_BUCKET_NAME: str = Field(default="dataplatform-dev-s3-ap-south-1-quarantine")
    CATALOG_DATABASE: str = Field(default="dataplatform_silver_catalog")
    ATHENA_WORKGROUP: str = Field(default="analytics_governance_wg")

    # AI/LLM Orchestration Parameters
    BEDROCK_MODEL_ID: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0")
    DQ_MAX_NULL_THRESHOLD: float = Field(default=0.05)

    # Operational Concurrency and Timeouts
    ATHENA_TIMEOUT_SECONDS: int = Field(default=300)
    MAX_LLM_RETRIES: int = Field(default=3)

    @field_validator("DQ_MAX_NULL_THRESHOLD")
    @classmethod
    def validate_threshold_bounds(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("DQ_MAX_NULL_THRESHOLD must be strictly bounded between 0.0 and 1.0")
        return v

    @field_validator("SILVER_BUCKET_NAME", "QUARANTINE_BUCKET_NAME")
    @classmethod
    def sanitize_s3_bucket(cls, v: str) -> str:
        clean = v.strip().lower().removeprefix("s3://").removesuffix("/")
        if not clean:
            raise ValueError("S3 bucket identifier cannot be empty")
        return clean

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

# Instantiate a process-wide singleton for global access
settings = Settings()
