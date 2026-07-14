import operator
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field


class ValidationStatus(StrEnum):
    """Operational compliance states assigned by the evaluation engine."""
    PENDING = "PENDING"
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"


class DataProfilingMetrics(BaseModel):
    """Strict schema definition for computed columns and structural table analysis."""
    total_record_count: int = Field(default=0, ge=0)
    null_primary_keys: int = Field(default=0, ge=0)
    null_timestamps: int = Field(default=0, ge=0)
    distinct_id_estimate: int = Field(default=0, ge=0)
    calculated_null_ratio: float = Field(default=1.0, ge=0.0, le=1.0)


class SystemLogEntry(BaseModel):
    """Structured tracking element for distributed transaction lineage."""
    node: str = Field(...)
    status: str = Field(...)
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO UTC execution timestamp entry"
    )
    metadata: dict[str, Any] = Field(default_factory=dict,
                                     description="Arbitrary trace debug context attributes")


class AgentState(TypedDict):
    """
    The absolute runtime context object passed through the LangGraph execution topology.
    As a TypedDict, this defines the dictionary keys but does not instantiate default values.
    """
    execution_arn: str
    target_database: str
    target_table: str
    athena_output_s3_prefix: str
    profiling_results: DataProfilingMetrics
    validation_status: ValidationStatus
    failure_reasoning: str
    quarantine_manifest_uri: str

    # Annotated list with custom append operator to aggregate logs
    # statelessly across distributed executions
    logs: Annotated[list[SystemLogEntry], operator.add]
