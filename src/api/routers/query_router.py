import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from src.api.agents.nlq_agent.graph import nlq_agent_graph
from src.api.agents.nlq_agent.state import NLQAgentState
from src.api.utils.auth import get_current_user

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["Analytics Execution Platform"])

class QueryInboundRequest(BaseModel):
    query: str = Field(..., examples=["Show total transactional throughput "
    "aggregated by user last week."])


class QueryOutboundResponse(BaseModel):
    answer: str
    generated_sql: str | None
    execution_success: bool

@router.post("/ask", response_model=QueryOutboundResponse)
async def process_natural_language_query(
    payload: QueryInboundRequest,
    _current_user: dict[str, Any] = Depends(get_current_user)
)->QueryOutboundResponse:

    # thread_id addresses this request's checkpoint chain in DynamoDB. Each
    # request gets its own thread today (no multi-turn conversation memory
    # yet -- QueryInboundRequest carries no conversation/session id); this
    # still gives per-request resumability and an auditable execution trail.
    #
    # Prefixed with "nlq-agent:" so this app's threads stay isolated from the
    # DQ agent's on the shared DynamoDB table. This prefix is what actually
    # provides that isolation -- NOT config["configurable"]["checkpoint_ns"],
    # which an earlier version of this code set to "nlq-agent". Testing
    # showed langgraph-checkpoint-aws doesn't honor a caller-supplied
    # checkpoint_ns for a top-level invoke (LangGraph's Pregel runtime treats
    # it as an internal subgraph-nesting field and recomputes it per task, so
    # it's always "" at the root); see src/agent/main.py for the full
    # writeup of the repro. thread_id is the identifier LangGraph actually
    # respects, so the prefix lives there instead.
    thread_id = f"nlq-agent:{uuid.uuid4()}"
    logger.info("received_inbound_nlq_request", client_query=payload.query, thread_id=thread_id)

    initial_state: NLQAgentState= {
        "user_query": payload.query,
        "messages": [],
        "target_tables": [],
        "catalog_context": "",
        "generated_sql": None,
        "sql_is_valid": False,
        "security_error": None,
        "athena_query_execution_id": None,
        "query_results_json": None,
        "final_answer": None,
        "error_trace": None
    }

    try:
        # Run synchronous step graph state evaluation loop
        execution_output = nlq_agent_graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
        )

        success_flag = (
            execution_output.get("error_trace") is None and
            execution_output.get("security_error") is None
        )

        return QueryOutboundResponse(
            answer=execution_output.get("final_answer") or "Could not process request.",
            generated_sql=execution_output.get("generated_sql"),
            execution_success=success_flag
        )

    except Exception as e:
        logger.error("router_endpoint_crash", error=str(e))
        raise HTTPException(status_code=500,
                            detail=f"Internal agent execution crash: {str(e)}") from e
