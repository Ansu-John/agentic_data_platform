import os
from typing import Any, cast

import structlog
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph_checkpoint_aws import DynamoDBSaver  # type: ignore[import-untyped]
from src.api.agents.nlq_agent.nodes.execute_athena import execute_athena

# Individual node files imported cleanly
from src.api.agents.nlq_agent.nodes.fetch_catalog_context import fetch_catalog_context
from src.api.agents.nlq_agent.nodes.generate_sql import generate_sql
from src.api.agents.nlq_agent.nodes.validate_sql import validate_sql
from src.api.agents.nlq_agent.state import NLQAgentState
from src.api.utils.bedrock_client import BedrockClientFactory

logger = structlog.get_logger()


def _build_default_checkpointer() -> BaseCheckpointSaver[Any]:
    """
    Builds the production DynamoDB-backed checkpointer.

    Shares the same table as the Phase 3 DQ agent (see src/agent/graph.py);
    threads are isolated per-app via the "nlq-agent:" thread_id prefix applied
    at invoke time in src/api/routers/query_router.py, not via checkpoint_ns
    -- LangGraph does not honor a caller-supplied checkpoint_ns for a
    top-level invoke (verified against langgraph_checkpoint_aws.DynamoDBSaver
    directly: the persisted item's SK carried an empty namespace segment
    regardless of what was passed in configurable.checkpoint_ns). Constructing
    the client here does not make any network calls.
    """
    table_name = os.getenv("DYNAMODB_CHECKPOINT_TABLE_NAME", "langgraph-checkpoints-dev")
    region = os.getenv("AWS_REGION", "ap-south-1")
    ttl_seconds = int(os.getenv("CHECKPOINT_TTL_SECONDS", str(30 * 24 * 60 * 60)))
    saver =DynamoDBSaver(table_name=table_name, region_name=region, ttl_seconds=ttl_seconds)
    return cast(BaseCheckpointSaver[Any], saver)

def format_final_answer(state: NLQAgentState) -> dict[str, Any]:
    """Generates the natural language analytical synthesis for the business application."""
    if state.get("error_trace"):
        return {"final_answer": f"System Error Encountered: {state['error_trace']}"}
    if state.get("security_error"):
        return {"final_answer": f"Request Rejected: {state['security_error']}"}

    logger.info("synthesizing_final_business_response")

    system_prompt = (
        "You are an expert senior business data analyst. Synthesize the raw JSON query results "
        "into an accurate, highly professional, and natural response that perfectly answers the "
        "user's prompt.\n"
        "Provide direct metrics, key figures, and logical observations cleanly."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "User Query: {query}\n\nExecuted SQL: {sql}\n\nRaw Result Payload:\n{results}")
    ])

    try:
        llm = BedrockClientFactory.get_llm()
        chain = prompt | llm
        response = chain.invoke({
            "query": state["user_query"],
            "sql": state["generated_sql"],
            "results": state["query_results_json"]
        })
        return {"final_answer": str(response.content).strip()}
    except Exception as e:
        logger.error("final_synthesis_failed", error=str(e))
        return {"final_answer": "Error generating textual analysis payload."}

def route_post_validation(state: NLQAgentState) -> str:
    """Evaluates security gates to determine branching routing strategies."""
    if not state["sql_is_valid"]:
        return "terminate"
    if state.get("error_trace"):
        return "terminate"
    return "continue"

def build_nlq_agent_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """
    Assembles and compiles the Text-to-SQL NLQ agent graph.

    Args:
        checkpointer: Checkpoint saver to compile with. Defaults to a real
            DynamoDB-backed saver; tests should inject an in-memory or
            moto-backed saver instead.
    """
    workflow = StateGraph(NLQAgentState)

    workflow.add_node("fetch_catalog_context", fetch_catalog_context)
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("validate_sql", validate_sql)
    workflow.add_node("execute_athena", execute_athena)
    workflow.add_node("format_final_answer", format_final_answer)

    workflow.set_entry_point("fetch_catalog_context")
    workflow.add_edge("fetch_catalog_context", "generate_sql")
    workflow.add_edge("generate_sql", "validate_sql")

    workflow.add_conditional_edges(
        "validate_sql",
        route_post_validation,
        {
            "continue": "execute_athena",
            "terminate": "format_final_answer"
        }
    )

    workflow.add_edge("execute_athena", "format_final_answer")
    workflow.add_edge("format_final_answer", END)

    resolved_checkpointer = (
        checkpointer if checkpointer is not None else _build_default_checkpointer()
    )
    return workflow.compile(checkpointer=resolved_checkpointer)


# Final engine asset export -- production entrypoint used by
# src/api/routers/query_router.py. Built once at process/module load (cold
# start), reused across requests, matching the same client-reuse pattern used
# for the DynamoDB/Athena/Glue/Bedrock clients elsewhere in this platform.
nlq_agent_graph = build_nlq_agent_graph()
