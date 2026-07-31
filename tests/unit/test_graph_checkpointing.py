"""
Tests for DynamoDB-backed LangGraph state persistence (Batch 2).

Before this batch, both `build_governance_graph()` (src/agent/graph.py) and the
NLQ agent graph (src/api/agents/nlq_agent/graph.py) were compiled with no
checkpointer at all -- `builder.compile()` with no arguments -- even though a
DynamoDB table was already provisioned in Terraform specifically for this
purpose (terraform/modules/dynamodb_state). These tests prove the DynamoDB
checkpointer is genuinely wired in now, not just that `invoke()` doesn't
crash: they independently re-open the same moto-mocked table after invoke()
returns and confirm a real checkpoint is retrievable, and they confirm the
compiled graphs actually require a thread_id (a stateless/no-op compile would
never care about one).
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import boto3
import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langgraph_checkpoint_aws import DynamoDBSaver
from moto import mock_aws

from src.agent.graph import _build_default_checkpointer, build_governance_graph
from src.agent.state import DataProfilingMetrics, ValidationStatus


@pytest.fixture
def dynamodb_checkpoint_table() -> Generator[str, None, None]:
    """A moto-mocked DynamoDB table matching the Terraform PK/SK schema
    (terraform/modules/dynamodb_state/main.tf) that langgraph-checkpoint-aws's
    DynamoDBSaver expects."""
    table_name = "langgraph-checkpoints-test"
    with mock_aws():
        client = boto3.client("dynamodb", region_name="ap-south-1")
        client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table_name


def _build_dq_agent_context(execution_arn: str) -> dict[str, Any]:
    return {
        "execution_arn": execution_arn,
        "target_database": "test_db",
        "target_table": "test_table",
        "athena_output_s3_prefix": "s3://mock-local-bucket/_athena_temp/",
        "profiling_results": DataProfilingMetrics(
            total_record_count=1000,
            null_primary_keys=2,
            null_timestamps=1,
            distinct_id_estimate=998,
            calculated_null_ratio=0.002,
        ),
        "validation_status": ValidationStatus.PENDING,
        "failure_reasoning": "None",
        "quarantine_manifest_uri": "None",
        "logs": [],
    }


# ---------------------------------------------------------------------------
# DQ Agent graph (src/agent/graph.py)
# ---------------------------------------------------------------------------

def test_governance_graph_persists_checkpoints_to_dynamodb(
    dynamodb_checkpoint_table: str,
) -> None:
    """Checkpoints written during invoke() must be independently retrievable
    from the same table afterward -- proof state actually persists, not just
    that invoke() ran without error."""
    simulated_llm_json = '{"status": "COMPLIANT", "reasoning": "ok"}'
    fake_llm = FakeMessagesListChatModel(responses=[AIMessage(content=simulated_llm_json)])
    checkpointer = DynamoDBSaver(table_name=dynamodb_checkpoint_table, region_name="ap-south-1")

    with patch("src.agent.nodes.AthenaRepository") as mock_athena, \
         patch("src.agent.nodes.GlueCatalogRepository"), \
         patch(
             "src.agent.integrations.llm_bedrock.BedrockEngineFactory.get_evaluator_llm",
             return_value=fake_llm,
         ):
        mock_athena.return_value.execute_query_async.return_value = "exec-id"
        mock_athena.return_value.poll_query_results.return_value = [{
            "total_record_count": "1000",
            "null_primary_keys": "2",
            "null_timestamps": "1",
            "distinct_id_estimate": "998",
        }]

        workflow = build_governance_graph(checkpointer=checkpointer)
        # Prefixed thread_id, matching the production wiring in
        # src/agent/main.py -- NOT checkpoint_ns. LangGraph does not honor a
        # caller-supplied checkpoint_ns for a top-level invoke (confirmed via
        # a standalone repro against DynamoDBSaver directly: the persisted
        # item's SK carried an empty namespace segment regardless of what was
        # passed in configurable.checkpoint_ns), so isolation has to live in
        # thread_id instead.
        thread_id = "ai-dq-agent:arn:aws:states:ap-south-1:000000000000:execution:Test:001"
        config = {"configurable": {"thread_id": thread_id}}

        result = workflow.invoke(_build_dq_agent_context(thread_id), config=config)
        assert result["validation_status"] == ValidationStatus.COMPLIANT

    # Independently reconstruct a saver against the same table + thread_id and
    # confirm a real, retrievable checkpoint was written.
    verifying_checkpointer = DynamoDBSaver(
        table_name=dynamodb_checkpoint_table, region_name="ap-south-1"
    )
    checkpoint_tuple = verifying_checkpointer.get_tuple(config)
    assert checkpoint_tuple is not None
    assert (
        checkpoint_tuple.checkpoint["channel_values"]["validation_status"]
        == ValidationStatus.COMPLIANT
    )


def test_governance_graph_requires_thread_id_when_checkpointer_configured(
    dynamodb_checkpoint_table: str,
) -> None:
    """A checkpointer-compiled graph refuses to run without a thread_id. A
    stateless compile (the pre-fix behavior) would never raise this."""
    checkpointer = DynamoDBSaver(table_name=dynamodb_checkpoint_table, region_name="ap-south-1")
    workflow = build_governance_graph(checkpointer=checkpointer)

    with pytest.raises(ValueError, match="thread_id"):
        workflow.invoke(_build_dq_agent_context("arn:no-thread-id"), config={"configurable": {}})


def test_default_checkpointer_factory_builds_without_network_calls() -> None:
    """_build_default_checkpointer() must construct cleanly with no live AWS
    calls (boto3 clients are lazy) -- main.py relies on this at cold start."""
    saver = _build_default_checkpointer()
    assert saver is not None


# ---------------------------------------------------------------------------
# NLQ Agent graph (src/api/agents/nlq_agent/graph.py)
# ---------------------------------------------------------------------------

def test_nlq_agent_graph_persists_checkpoints_to_dynamodb(
    dynamodb_checkpoint_table: str,
) -> None:
    """Same proof-of-persistence as the DQ agent, for the Phase 4 NLQ graph,
    which shares the same DynamoDB table (isolated via a thread_id prefix,
    not checkpoint_ns -- see the comment in the DQ agent test above)."""
    from src.api.agents.nlq_agent.graph import build_nlq_agent_graph

    fake_sql_llm = FakeMessagesListChatModel(
        responses=[AIMessage(content="SELECT 1 AS total FROM silver_events")]
    )
    fake_answer_llm = FakeMessagesListChatModel(
        responses=[AIMessage(content="There was 1 event.")]
    )

    checkpointer = DynamoDBSaver(table_name=dynamodb_checkpoint_table, region_name="ap-south-1")

    with patch("src.api.agents.nlq_agent.nodes.fetch_catalog_context.boto3") as mock_boto3, \
         patch(
             "src.api.utils.bedrock_client.BedrockClientFactory.get_llm",
             side_effect=[fake_sql_llm, fake_answer_llm],
         ), \
         patch("src.api.agents.nlq_agent.nodes.execute_athena.wr") as mock_wr:
        mock_glue_client = mock_boto3.client.return_value
        mock_glue_client.get_tables.return_value = {"TableList": []}

        mock_df = mock_wr.athena.read_sql_query.return_value
        mock_df.head.return_value.to_json.return_value = "[]"

        graph = build_nlq_agent_graph(checkpointer=checkpointer)
        thread_id = "nlq-agent:test-request-thread-1"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "user_query": "How many events happened?",
            "messages": [],
            "target_tables": [],
            "catalog_context": "",
            "generated_sql": None,
            "sql_is_valid": False,
            "security_error": None,
            "athena_query_execution_id": None,
            "query_results_json": None,
            "final_answer": None,
            "error_trace": None,
        }

        result = graph.invoke(initial_state, config=config)
        assert result["final_answer"]

    verifying_checkpointer = DynamoDBSaver(
        table_name=dynamodb_checkpoint_table, region_name="ap-south-1"
    )
    checkpoint_tuple = verifying_checkpointer.get_tuple(config)
    assert checkpoint_tuple is not None


def test_nlq_agent_graph_requires_thread_id_when_checkpointer_configured(
    dynamodb_checkpoint_table: str,
) -> None:
    from src.api.agents.nlq_agent.graph import build_nlq_agent_graph

    checkpointer = DynamoDBSaver(table_name=dynamodb_checkpoint_table, region_name="ap-south-1")
    graph = build_nlq_agent_graph(checkpointer=checkpointer)

    initial_state = {
        "user_query": "irrelevant",
        "messages": [],
        "target_tables": [],
        "catalog_context": "",
        "generated_sql": None,
        "sql_is_valid": False,
        "security_error": None,
        "athena_query_execution_id": None,
        "query_results_json": None,
        "final_answer": None,
        "error_trace": None,
    }

    with pytest.raises(ValueError, match="thread_id"):
        graph.invoke(initial_state, config={"configurable": {}})
