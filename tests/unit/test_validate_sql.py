import pytest
from src.api.agents.nlq_agent.nodes.validate_sql import validate_sql
from src.api.agents.nlq_agent.state import NLQAgentState

def test_validate_sql_allows_safe_select_queries():
    """Ensure standard analytical queries pass security validation."""
    state = NLQAgentState(generated_sql="SELECT user_id, amount FROM silver_events LIMIT 10;")
    result = validate_sql(state)
    
    assert result["sql_is_valid"] is True
    assert result.get("security_error") is None

def test_validate_sql_blocks_destructive_commands():
    """Ensure malicious injection or destructive operations are caught."""
    malicious_queries = [
        "DROP TABLE silver_events;",
        "DELETE FROM silver_events WHERE amount > 0;",
        "ALTER TABLE silver_events ADD COLUMN new_col VARCHAR;",
        "SELECT * FROM silver_events; DROP DATABASE ai_catalog;"
    ]
    
    for query in malicious_queries:
        state = NLQAgentState(generated_sql=query)
        result = validate_sql(state)
        
        assert result["sql_is_valid"] is False
        assert "Security Exception" in result["security_error"] or "Forbidden request" in result["security_error"]

def test_validate_sql_blocks_non_select_start():
    """Ensure queries that do not explicitly begin with SELECT are dropped."""
    state = NLQAgentState(generated_sql="WITH CTE AS (SELECT * FROM table) SELECT * FROM CTE;")
    # While valid SQL, strict constraints for this agent mandate starting with SELECT
    # (Adjust regex in validation logic if CTEs need explicit support)
    result = validate_sql(state)
    
    assert result["sql_is_valid"] is False
    assert "Forbidden request" in result["security_error"]