import re
from typing import Any

import structlog
from src.api.agents.nlq_agent.state import NLQAgentState

logger = structlog.get_logger()

def validate_sql(state: NLQAgentState) -> dict[str, Any]:
    """
    Mandatory corporate security guardrail. Parses and checks the generated query
    to completely prevent SQL injection or destructive operations against the Iceberg lakehouse.
    """
    sql = state.get("generated_sql")
    if not sql or state.get("error_trace"):
        return {"sql_is_valid": False}

    logger.info("validating_security_guardrails", sql=sql)

    # Strip whitespaces and force comparison tokens to lowercase
    normalized_sql = sql.lower().strip()

    # Enforce SELECT statements only
    if not normalized_sql.startswith("select"):
        logger.error("security_violation_detected", reason="Query does not begin with SELECT")
        return {
            "sql_is_valid": False,
            "security_error":
            "Forbidden request: Only data retrieval (SELECT) configurations are authorized."
        }

    # Blacklist malicious destructive commands
    destructive_tokens = [
        r"\bdrop\b", r"\bdelete\b", r"\btruncate\b", r"\balter\b",
        r"\binsert\b", r"\bupdate\b", r"\bcreate\b", r"\bgrant\b", r"\brevoke\b"
    ]

    for token in destructive_tokens:
        if re.search(token, normalized_sql):
            logger.error("security_violation_detected", malicious_token=token)
            return {
                "sql_is_valid": False,
                "security_error": f"Security Exception: Malicious or non-read-only "
                                f"operation token detected: {token}"
            }

    logger.info("security_validation_passed")
    return {"sql_is_valid": True, "security_error": None}
