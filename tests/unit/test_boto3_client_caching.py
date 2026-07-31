"""
Tests for the module-scope boto3 client caching introduced in Batch 2
(src/agent/integrations/aws_athena.py, aws_glue.py, llm_bedrock.py).

Before this batch, AthenaRepository, GlueCatalogRepository, and
BedrockEngineFactory each constructed a brand new boto3 client on every
instantiation -- and each of those classes is instantiated fresh on every
single LangGraph node execution (see src/agent/nodes.py). That meant every
governance decision paid for a new client, new connection pool, and new
credential resolution. The fix wraps client construction in an
`lru_cache(maxsize=None)`-decorated module-level factory keyed by region, so
repeated instantiations for the same region reuse the same underlying client.

These tests confirm: (1) two instantiations for the same region return the
*same* underlying client object (proving the cache is actually hit, not just
present), and (2) two instantiations for different regions do NOT share a
client (proving the cache key includes region and won't leak an EU client's
config into a US call, say).
"""

from __future__ import annotations

from moto import mock_aws

from src.agent.integrations.aws_athena import AthenaRepository, _get_athena_client
from src.agent.integrations.aws_glue import GlueCatalogRepository, _get_glue_client
from src.agent.integrations.llm_bedrock import _get_bedrock_runtime_client


@mock_aws
def test_athena_client_is_cached_and_reused_for_same_region() -> None:
    _get_athena_client.cache_clear()

    repo_a = AthenaRepository(
        region_name="ap-south-1", database="db_a", output_bucket="bucket-a"
    )
    repo_b = AthenaRepository(
        region_name="ap-south-1", database="db_b", output_bucket="bucket-b"
    )

    assert repo_a.client is repo_b.client


@mock_aws
def test_athena_client_is_distinct_per_region() -> None:
    _get_athena_client.cache_clear()

    repo_us = AthenaRepository(
        region_name="us-east-1", database="db_a", output_bucket="bucket-a"
    )
    repo_ap = AthenaRepository(
        region_name="ap-south-1", database="db_a", output_bucket="bucket-a"
    )

    assert repo_us.client is not repo_ap.client


@mock_aws
def test_glue_client_is_cached_and_reused_for_same_region() -> None:
    _get_glue_client.cache_clear()

    repo_a = GlueCatalogRepository(region_name="ap-south-1")
    repo_b = GlueCatalogRepository(region_name="ap-south-1")

    assert repo_a.client is repo_b.client


@mock_aws
def test_glue_client_is_distinct_per_region() -> None:
    _get_glue_client.cache_clear()

    repo_us = GlueCatalogRepository(region_name="us-east-1")
    repo_ap = GlueCatalogRepository(region_name="ap-south-1")

    assert repo_us.client is not repo_ap.client


@mock_aws
def test_bedrock_runtime_client_is_cached_and_reused_for_same_region() -> None:
    _get_bedrock_runtime_client.cache_clear()

    client_a = _get_bedrock_runtime_client("ap-south-1")
    client_b = _get_bedrock_runtime_client("ap-south-1")

    assert client_a is client_b


@mock_aws
def test_bedrock_runtime_client_is_distinct_per_region() -> None:
    _get_bedrock_runtime_client.cache_clear()

    client_us = _get_bedrock_runtime_client("us-east-1")
    client_ap = _get_bedrock_runtime_client("ap-south-1")

    assert client_us is not client_ap
