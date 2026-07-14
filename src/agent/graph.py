from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agent.core.logger import get_logger
from src.agent.nodes import (
    enhance_catalog_node,
    profile_data_node,
    quarantine_data_node,
    validate_dq_node,
)
from src.agent.state import AgentState

logger = get_logger(__name__)

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

def build_governance_graph()-> CompiledStateGraph[Any, Any, Any, Any]:
    """
    Assembles and compiles the definitive multi-agent processing topology
    with structural schema assertions.
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

    # Compile the graph without persistent checkpointers here
    # (Fargate tasks execute statelessly per event)
    compiled_workflow = builder.compile()
    return compiled_workflow
