from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph_checkpoint_aws import DynamoDBSaver  # type: ignore[import-untyped]

from src.agent.config.settings import settings
from src.agent.core.logger import get_logger
from src.agent.nodes import (
    enhance_catalog_node,
    profile_data_node,
    quarantine_data_node,
    validate_dq_node,
)
from src.agent.state import AgentState

logger = get_logger(__name__)


def _build_default_checkpointer() -> BaseCheckpointSaver[Any]:
    """
    Builds the production DynamoDB-backed checkpointer.

    Uses the table provisioned by terraform/modules/dynamodb_state (shared with
    the Phase 4 NLQ agent -- see src/api/agents/nlq_agent/graph.py -- and kept
    isolated per-app via an "ai-dq-agent:" thread_id prefix applied at invoke
    time in src/agent/main.py, not via checkpoint_ns -- LangGraph does not
    honor a caller-supplied checkpoint_ns for a top-level invoke). Constructing
    the client here does not make any network calls, so this is safe to call
    at import/module-load time.
    """
    saver =DynamoDBSaver(
        table_name=settings.DYNAMODB_CHECKPOINT_TABLE_NAME,
        region_name=settings.AWS_REGION,
        ttl_seconds=settings.CHECKPOINT_TTL_SECONDS,
    )
    return cast(BaseCheckpointSaver[Any], saver)


def evaluate_compliance_route(state: AgentState) -> str:
    """
    Inspects runtime state conditions to direct execution towards
    quarantine isolation or open catalog enhancement.
    """
    status = state.get("validation_status", "NON_COMPLIANT")
    logger.info("evaluating_graph_routing_decision", current_status=status)

    if status == "NON_COMPLIANT":
        return "quarantine_data_node"
    return "enhance_catalog_node"

def build_governance_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """
    Assembles and compiles the definitive multi-agent processing topology
    with structural schema assertions.

    Args:
        checkpointer: Checkpoint saver to compile the graph with. Defaults to
            a real DynamoDB-backed saver (see `_build_default_checkpointer`).
            Tests should inject an in-memory or moto-backed saver instead of
            relying on this default.
    """
    logger.info("compiling_langgraph_governance_topology")

    # Initialize stateful DAG with the explicit state definition schema
    builder = StateGraph(AgentState)

    # Map execution steps to specific operational functions
    builder.add_node("profile_data_node", profile_data_node)
    builder.add_node("validate_dq_node", validate_dq_node)
    builder.add_node("quarantine_data_node", quarantine_data_node)
    builder.add_node("enhance_catalog_node", enhance_catalog_node)

    # Bind linear workflow steps
    builder.add_edge(START, "profile_data_node")
    builder.add_edge("profile_data_node", "validate_dq_node")

    # Attach conditional routing logic to evaluate the output of the compliance engine
    builder.add_conditional_edges(
        "validate_dq_node",
        evaluate_compliance_route,
        {
            "quarantine_data_node": "quarantine_data_node",
            "enhance_catalog_node": "enhance_catalog_node"
        }
    )

    # Connect terminal steps to the end of the state machine runtime
    builder.add_edge("quarantine_data_node", END)
    builder.add_edge("enhance_catalog_node", END)

    # Persist state to DynamoDB so a Fargate task that dies mid-graph can be
    # resumed (same thread_id), and so intermediate node state is auditable
    # after the fact -- see src/agent/main.py for the thread_id
    # ("ai-dq-agent:{execution_arn}") passed at invoke time.
    resolved_checkpointer = (
        checkpointer if checkpointer is not None else _build_default_checkpointer()
    )
    compiled_workflow = builder.compile(checkpointer=resolved_checkpointer)
    return compiled_workflow
