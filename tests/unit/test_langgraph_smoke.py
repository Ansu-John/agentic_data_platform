import pytest
from unittest.mock import patch
from langchain_core.messages import AIMessage
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from src.agent.graph import build_governance_graph
from src.agent.state import ValidationStatus, AgentState, DataProfilingMetrics

def test_langgraph_state_machine_execution_flow():
    """
    Validates the end-to-end topological execution layout of the LangGraph state engine,
    ensuring standard nodes pass Pydantic structures correctly under local mock execution.
    """
    # 1. Prepare deterministic mock behaviors for the integration layer boundaries
    mock_profile_data = {
        "profiling_results": {
            "total_record_count": 1000,
            "null_primary_keys": 2,
            "null_timestamps": 1,
            "distinct_id_estimate": 998,
            "calculated_null_ratio": 0.002 # Well within compliant ranges
        }
    }

    # Set up a structured fake LLM response string mimicking the exact production payload format
    simulated_llm_json = '{"status": "COMPLIANT", "reasoning": "Local semantic check passed."}'
    fake_llm = FakeMessagesListChatModel(responses=[AIMessage(content=simulated_llm_json)])

    # Initialize standard base context parameters matching the AgentState schema
    initial_context = {
        "execution_arn": "arn:aws:states:ap-south-1:000000000000:execution:LocalTest:001",
        "target_database": "test_db",
        "target_table": "test_table",
        "athena_output_s3_prefix": "s3://mock-local-bucket/_athena_temp/",
        "profiling_results": DataProfilingMetrics(
            total_record_count=0,
            null_primary_keys=0,
            null_timestamps=0,
            distinct_id_estimate=0,
            calculated_null_ratio=1.0
        ),
        "validation_status": ValidationStatus.PENDING,
        "failure_reasoning": "None",
        "quarantine_manifest_uri": "None",
        "logs": []
    }
    
    # 2. Patch out the destructive real-world resource integrations during structural graph runs
    with patch("src.agent.nodes.AthenaRepository") as mock_athena, \
         patch("src.agent.nodes.GlueCatalogRepository") as mock_glue, \
         patch("src.agent.integrations.llm_bedrock.BedrockEngineFactory.get_evaluator_llm", return_value=fake_llm):
         
        # Configure mocked Athena instance to return our static matrix coordinates safely
        mock_athena_instance = mock_athena.return_value
        mock_athena_instance.execute_query_async.return_value = "query_exec_id_999"
        mock_athena_instance.poll_query_results.return_value = [{
            "total_record_count": "1000",
            "null_primary_keys": "2",
            "null_timestamps": "1",
            "distinct_id_estimate": "998"
        }]

        # 3. Assemble and invoke the workflow topology
        workflow = build_governance_graph()
        final_state = workflow.invoke(initial_context)

        # 4. Rigorous architectural assertions
        assert final_state["validation_status"] == ValidationStatus.COMPLIANT
        assert final_state["profiling_results"].total_record_count == 1000
        assert final_state["profiling_results"].calculated_null_ratio == 0.002
        
        # Verify that catalog enhancement was chosen over the isolation path
        mock_glue.return_value.enrich_table_metadata.assert_called_once_with(
            "test_db", "test_table", final_state["profiling_results"].model_dump(), "COMPLIANT"
        )