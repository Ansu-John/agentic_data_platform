import pytest
from src.agent.graph import evaluate_compliance_route
from src.agent.nodes import validate_dq_node
from src.agent.state import ValidationStatus, DataProfilingMetrics

def test_evaluate_compliance_route_success():
    """Ensures the router correctly points to catalog enhancement on success."""
    state = {"validation_status": ValidationStatus.COMPLIANT}
    target_node = evaluate_compliance_route(state)
    assert target_node == "enhance_catalog_node"

def test_evaluate_compliance_route_failure():
    """Ensures the router correctly diverts to quarantine upon failure."""
    state = {"validation_status": ValidationStatus.NON_COMPLIANT}
    target_node = evaluate_compliance_route(state)
    assert target_node == "quarantine_data_node"

def test_validate_dq_node_hard_threshold_breach():
    """Tests that deterministic physical data boundaries override LLM checks."""
    state = {
        "profiling_results": DataProfilingMetrics(
            total_record_count=100,
            null_primary_keys=10,
            null_timestamps=0,
            distinct_id_estimate=90,
            calculated_null_ratio=0.10  # 10%, exceeds our 5% default
        )
    }
    
    result = validate_dq_node(state)
    
    assert result["validation_status"] == ValidationStatus.NON_COMPLIANT
    assert "Hard barrier breach" in result["failure_reasoning"]

