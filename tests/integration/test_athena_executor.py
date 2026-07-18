import os
import json
import pytest
import pandas as pd
from unittest.mock import patch
from src.api.agents.nlq_agent.nodes.execute_athena import execute_athena
from src.api.agents.nlq_agent.state import NLQAgentState

@pytest.fixture
def mock_athena_environment(monkeypatch):
    monkeypatch.setenv("GLUE_DATABASE", "test_db")
    monkeypatch.setenv("ATHENA_WORKGROUP", "test_wg")

@patch("src.api.agents.nlq_agent.nodes.execute_athena.wr.athena.read_sql_query")
def test_execute_athena_successful_query(mock_read_sql, mock_athena_environment):
    """Verifies that executed SQL successfully converts Athena DataFrames to JSON state payloads."""
    # Mock the DataFrame returned by awswrangler
    mock_df = pd.DataFrame({
        "user_id": ["u1", "u2"],
        "transaction_amount": [150.50, 89.99]
    })
    mock_read_sql.return_value = mock_df
    
    state = NLQAgentState(
        sql_is_valid=True,
        generated_sql="SELECT user_id, transaction_amount FROM test_table LIMIT 2;"
    )
    
    result = execute_athena(state)
    
    # Assert awswrangler was called with correct environment parameters
    mock_read_sql.assert_called_once_with(
        sql=state["generated_sql"],
        database="test_db",
        workgroup="test_wg",
        ctas_approach=False
    )
    
    # Verify the JSON payload matches the graph state requirements
    assert result.get("error_trace") is None
    
    parsed_results = json.loads(result["query_results_json"])
    assert len(parsed_results) == 2
    assert parsed_results[0]["user_id"] == "u1"
    assert parsed_results[1]["transaction_amount"] == 89.99

def test_execute_athena_aborts_on_invalid_sql():
    """Verifies that the executor skips network calls if the security validator failed the query."""
    state = NLQAgentState(sql_is_valid=False, generated_sql="DROP TABLE silver_events;")
    result = execute_athena(state)
    
    # Empty dict expected when skipping node execution
    assert result == {}