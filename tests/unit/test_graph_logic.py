from typing import Any
from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from src.agent.graph import evaluate_compliance_route
from src.agent.nodes import validate_dq_node
from src.agent.state import DataProfilingMetrics, ValidationStatus


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


# ---------------------------------------------------------------------------
# Fail-closed governance tests (Batch 2).
#
# Before this batch, an exception raised while calling the Bedrock LLM inside
# validate_dq_node (timeout, throttling, malformed response, etc.) was caught
# and silently treated as a compliance PASS -- fail-open. That's exactly
# backwards for a governance gate: an evaluator that can't run should never
# be interpreted as an evaluator that said yes. These tests lock in the fixed
# fail-closed behavior: every LLM-failure path below must route to
# NON_COMPLIANT, while a genuine LLM COMPLIANT response must still pass.
# ---------------------------------------------------------------------------

def _compliant_profile_state() -> dict[str, Any]:
    """A profile that passes both hard-threshold checks, so the only thing
    left to determine the outcome is the LLM evaluation path."""
    return {
        "execution_arn": "arn:aws:states:ap-south-1:000000000000:execution:Test:001",
        "target_database": "test_db",
        "target_table": "test_table",
        "profiling_results": DataProfilingMetrics(
            total_record_count=1000,
            null_primary_keys=2,
            null_timestamps=1,
            distinct_id_estimate=998,
            calculated_null_ratio=0.002,
        ),
        "validation_status": "PENDING",
        "failure_reasoning": "None",
        "quarantine_manifest_uri": "None",
        "logs": [],
    }


class _RaisingLLM:
    """Stand-in for a Bedrock client that fails outright (timeout, throttling,
    connection reset, etc.) -- `.invoke()` raises before any content exists."""

    def invoke(self, *_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("simulated Bedrock throttling / connection failure")


def test_validate_dq_node_fails_closed_on_llm_exception() -> None:
    """An LLM call that raises must NOT be interpreted as compliant."""
    with patch(
        "src.agent.nodes.BedrockEngineFactory.get_evaluator_llm",
        return_value=_RaisingLLM(),
    ):
        result = validate_dq_node(_compliant_profile_state())

    assert result["validation_status"] == ValidationStatus.NON_COMPLIANT
    assert "Fail-closed" in result["failure_reasoning"]
    assert "RuntimeError" in result["failure_reasoning"]


def test_validate_dq_node_fails_closed_on_malformed_json_response() -> None:
    """An LLM that responds with non-JSON garbage (not an exception, but a
    response json.loads can't parse) must also fail closed."""
    fake_llm = FakeMessagesListChatModel(
        responses=[AIMessage(content="I cannot comply with this request.")]
    )
    with patch(
        "src.agent.nodes.BedrockEngineFactory.get_evaluator_llm",
        return_value=fake_llm,
    ):
        result = validate_dq_node(_compliant_profile_state())

    assert result["validation_status"] == ValidationStatus.NON_COMPLIANT
    assert "Fail-closed" in result["failure_reasoning"]


def test_validate_dq_node_fails_closed_on_missing_status_key() -> None:
    """A syntactically valid JSON response that omits the 'status' key must
    not default to compliant (nodes.py defaults a missing 'status' key to
    NON_COMPLIANT via .get("status", "NON_COMPLIANT") -- this locks that in)."""
    fake_llm = FakeMessagesListChatModel(
        responses=[AIMessage(content='{"reasoning": "no status field provided"}')]
    )
    with patch(
        "src.agent.nodes.BedrockEngineFactory.get_evaluator_llm",
        return_value=fake_llm,
    ):
        result = validate_dq_node(_compliant_profile_state())

    assert result["validation_status"] == ValidationStatus.NON_COMPLIANT


def test_validate_dq_node_passes_through_genuine_compliant_response() -> None:
    """Control case: a well-formed COMPLIANT LLM response must still result in
    COMPLIANT. Guards against a naive fail-closed fix that routes every path
    to NON_COMPLIANT regardless of what the LLM actually says."""
    fake_llm = FakeMessagesListChatModel(
        responses=[AIMessage(content='{"status": "COMPLIANT", "reasoning": "Looks good."}')]
    )
    with patch(
        "src.agent.nodes.BedrockEngineFactory.get_evaluator_llm",
        return_value=fake_llm,
    ):
        result = validate_dq_node(_compliant_profile_state())

    assert result["validation_status"] == ValidationStatus.COMPLIANT
    assert result["failure_reasoning"] == "None"


def test_validate_dq_node_short_circuits_on_hard_null_threshold_before_calling_llm() -> None:
    """Hard deterministic threshold breaches must reject before ever invoking
    the LLM -- confirms the fail-closed exception handling didn't accidentally
    make the hard-threshold gate LLM-dependent."""
    state = _compliant_profile_state()
    state["profiling_results"] = DataProfilingMetrics(
        total_record_count=1000,
        null_primary_keys=950,
        null_timestamps=1,
        distinct_id_estimate=998,
        calculated_null_ratio=0.95,
    )

    with patch("src.agent.nodes.BedrockEngineFactory.get_evaluator_llm") as mock_factory:
        result = validate_dq_node(state)

    mock_factory.assert_not_called()
    assert result["validation_status"] == ValidationStatus.NON_COMPLIANT
    assert "Hard barrier breach" in result["failure_reasoning"]


def test_validate_dq_node_short_circuits_on_zero_records_before_calling_llm() -> None:
    """Same short-circuit guarantee for the zero-records hard check."""
    state = _compliant_profile_state()
    state["profiling_results"] = DataProfilingMetrics(
        total_record_count=0,
        null_primary_keys=0,
        null_timestamps=0,
        distinct_id_estimate=0,
        calculated_null_ratio=0.0,
    )

    with patch("src.agent.nodes.BedrockEngineFactory.get_evaluator_llm") as mock_factory:
        result = validate_dq_node(state)

    mock_factory.assert_not_called()
    assert result["validation_status"] == ValidationStatus.NON_COMPLIANT
    assert "zero active records" in result["failure_reasoning"]


@pytest.mark.parametrize("llm_status", ["NON_COMPLIANT", "UNKNOWN", ""])
def test_validate_dq_node_only_treats_exact_compliant_string_as_passing(llm_status: str) -> None:
    """Anything other than the exact string 'COMPLIANT' from the LLM must be
    treated as non-compliant -- no silent truthy/partial-match acceptance."""
    fake_llm = FakeMessagesListChatModel(
        responses=[AIMessage(content=f'{{"status": "{llm_status}", "reasoning": "test"}}')]
    )
    with patch(
        "src.agent.nodes.BedrockEngineFactory.get_evaluator_llm",
        return_value=fake_llm,
    ):
        result = validate_dq_node(_compliant_profile_state())

    assert result["validation_status"] == ValidationStatus.NON_COMPLIANT

