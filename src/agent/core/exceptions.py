from __future__ import annotations

from typing import Any


class AgentDomainError(Exception):
    """Base exception for the AI Governance domain layer."""
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class DataQualityThresholdError(AgentDomainError):
    """Raised when data metrics violate strict operational limits."""
    pass

class AthenaQueryExecutionError(AgentDomainError):
    """Raised when an internal Athena query fails or times out during polling."""
    pass

class GlueCatalogUpdateError(AgentDomainError):
    """Raised when catalog schema updates fail concurrency or structural validation."""
    pass

class LLMResponseParsingError(AgentDomainError):
    """Raised when LLM outputs fail to conform to strict JSON schemas."""
    pass
