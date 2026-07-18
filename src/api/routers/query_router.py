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

    logger.info("received_inbound_nlq_request", client_query=payload.query)

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
        execution_output = nlq_agent_graph.invoke(initial_state)

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
