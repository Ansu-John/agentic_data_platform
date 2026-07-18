from typing import TypedDict

from langchain_core.messages import BaseMessage


class NLQAgentState(TypedDict):
    """
    Production-grade state schema for the Text-to-SQL execution graph.
    Tracks lineage, security validation status, and raw execution contexts.
    """
    user_query: str
    messages: list[BaseMessage]
    target_tables: list[str]
    catalog_context: str
    generated_sql: str | None
    sql_is_valid: bool
    security_error: str | None
    athena_query_execution_id: str | None
    query_results_json: str | None
    final_answer: str | None
    error_trace: str | None
