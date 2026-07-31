"""
Unit tests for src/spark/raw_to_iceberg.py.

These tests exercise the Iceberg MERGE INTO / UPSERT idempotency logic that is
central to Phase 2 of the platform. Two testing strategies are combined:

1. A real, local (non-Iceberg) SparkSession is used to validate the parts of
   the pipeline that only need plain Spark SQL DataFrame semantics: reading
   raw JSON, applying audit transformations, and the `run()` control flow.
2. The MERGE INTO / CREATE branch of `write_to_iceberg` is validated against a
   mocked `SparkSession` + mocked `DataFrame`, asserting on the exact SQL text
   and API calls produced. This sandbox/CI environment has no network access
   to Maven Central, so the real `iceberg-spark-runtime` JAR cannot be
   fetched -- mocking at the `spark.sql(...)` / `df.writeTo(...)` boundary
   lets us assert the MERGE logic is correct without requiring a live Iceberg
   catalog.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Spark's local discovery of the driver's hostname fails inside this sandbox
# (no DNS entry for the container hostname). Pinning the driver to the
# loopback address must happen before any SparkSession is created.
os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")

from pyspark.sql import Row, SparkSession  # noqa: E402, I001

from src.spark import raw_to_iceberg  # noqa: E402
from src.spark.raw_to_iceberg import IcebergIngestionPipeline  # noqa: E402


@pytest.fixture(scope="module")
def local_spark() -> Generator[SparkSession, None, None]:
    """A real, plain local SparkSession (no Iceberg catalog configured).

    The test suite's conftest.py sets fake AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY
    env vars (for moto). Their mere presence makes Spark's driver bootstrap try to
    propagate them into Hadoop's S3A config via a code path that calls
    `InetAddress.getLocalHost()`, which fails with UnknownHostException in
    sandboxes without a resolvable hostname and crashes the JVM before the py4j
    gateway can start. This session doesn't touch S3, so we simply hide those
    env vars from the driver process for the moment of session creation and
    restore them immediately afterward for the rest of the test session (moto
    fixtures elsewhere still need them).
    """
    aws_env_keys = (
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SECURITY_TOKEN", "AWS_SESSION_TOKEN",
    )
    saved_env = {key: os.environ.pop(key, None) for key in aws_env_keys}
    try:
        spark = (
            SparkSession.builder
            .master("local[1]")
            .appName("raw-to-iceberg-tests")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "1")
            .getOrCreate()
        )
    finally:
        for key, value in saved_env.items():
            if value is not None:
                os.environ[key] = value

    yield spark
    spark.stop()


@pytest.fixture
def pipeline(local_spark: SparkSession) -> IcebergIngestionPipeline:
    """A pipeline instance wired to the shared local SparkSession (not Iceberg-backed)."""
    return IcebergIngestionPipeline(
        source_path="s3://test-bronze/raw/orders/file.json",
        db_name="dataplatform_test_ai_catalog",
        table_name="silver_orders",
        silver_bucket="test-silver-bucket",
        merge_key="event_id",
        spark_session=local_spark,
    )


def _mocked_pipeline(*, table_exists: bool) -> tuple[IcebergIngestionPipeline, MagicMock]:
    """Builds a pipeline whose Spark session is fully mocked, for MERGE-SQL assertions."""
    spark_mock = MagicMock(name="spark_session")
    spark_mock.catalog.tableExists.return_value = table_exists

    pipeline = IcebergIngestionPipeline(
        source_path="s3://test-bronze/raw/orders/file.json",
        db_name="dataplatform_test_ai_catalog",
        table_name="silver_orders",
        silver_bucket="test-silver-bucket",
        merge_key="event_id",
        spark_session=spark_mock,
    )
    return pipeline, spark_mock


# ---------------------------------------------------------------------------
# _initialize_spark_session: verifies the parameterized catalog_name wiring
# ---------------------------------------------------------------------------

def test_initialize_spark_session_configures_parameterized_catalog(mocker: Any) -> None:
    """The Iceberg catalog conf keys must be derived from `catalog_name`, not hardcoded."""
    mock_builder = MagicMock(name="spark_builder")
    mock_builder.appName.return_value = mock_builder
    mock_builder.config.return_value = mock_builder
    sentinel_session = MagicMock(name="created_spark_session")
    mock_builder.getOrCreate.return_value = sentinel_session

    mock_spark_session_cls = mocker.patch.object(raw_to_iceberg, "SparkSession")
    mock_spark_session_cls.builder = mock_builder

    pipeline = IcebergIngestionPipeline(
        source_path="s3://test-bronze/raw/orders/file.json",
        db_name="test_db",
        table_name="orders",
        silver_bucket="test-silver-bucket",
        merge_key="event_id",
        catalog_name="local_catalog",
    )

    assert pipeline.spark is sentinel_session
    assert pipeline._owns_spark_session is True

    config_calls = {call.args[0]: call.args[1] for call in mock_builder.config.call_args_list}
    assert (
        config_calls["spark.sql.catalog.local_catalog"]
        == "org.apache.iceberg.spark.SparkCatalog"
    )
    assert (
        config_calls["spark.sql.catalog.local_catalog.catalog-impl"]
        == "org.apache.iceberg.aws.glue.GlueCatalog"
    )
    assert (
        config_calls["spark.sql.catalog.local_catalog.io-impl"]
        == "org.apache.iceberg.aws.s3.S3FileIO"
    )


def test_injected_spark_session_is_reused_not_recreated(
    mocker: Any, local_spark: SparkSession
) -> None:
    """Passing an existing SparkSession must skip _initialize_spark_session entirely."""
    spy = mocker.spy(IcebergIngestionPipeline, "_initialize_spark_session")

    pipeline = IcebergIngestionPipeline(
        source_path="s3://test-bronze/raw/orders/file.json",
        db_name="test_db",
        table_name="orders",
        silver_bucket="test-silver-bucket",
        merge_key="event_id",
        spark_session=local_spark,
    )

    assert pipeline.spark is local_spark
    assert pipeline._owns_spark_session is False
    spy.assert_not_called()


# ---------------------------------------------------------------------------
# read_source_data / apply_transformations: real local Spark, no Iceberg needed
# ---------------------------------------------------------------------------

def test_read_source_data_returns_dataframe_for_valid_json(
    pipeline: IcebergIngestionPipeline, tmp_path: Path
) -> None:
    source_file = tmp_path / "orders.json"
    source_file.write_text(
        '[{"event_id": "e1", "amount": 10}, {"event_id": "e2", "amount": 20}]'
    )
    pipeline.source_path = str(source_file)

    df = pipeline.read_source_data()

    assert df is not None
    assert df.count() == 2
    assert set(df.columns) == {"event_id", "amount"}


def test_read_source_data_returns_none_for_empty_source(
    pipeline: IcebergIngestionPipeline, tmp_path: Path
) -> None:
    source_file = tmp_path / "empty.json"
    source_file.write_text("[]")
    pipeline.source_path = str(source_file)

    assert pipeline.read_source_data() is None


def test_apply_transformations_adds_audit_columns(
    pipeline: IcebergIngestionPipeline, local_spark: SparkSession
) -> None:
    df = local_spark.createDataFrame([Row(event_id="e1", amount=10)])

    transformed = pipeline.apply_transformations(df)

    assert "_ingest_timestamp" in transformed.columns
    assert "_source_file" in transformed.columns
    row = transformed.collect()[0]
    assert row["_source_file"] == pipeline.source_path
    assert row["_ingest_timestamp"] is not None


# ---------------------------------------------------------------------------
# run(): control-flow branches
# ---------------------------------------------------------------------------

def test_run_short_circuits_when_source_is_empty(
    pipeline: IcebergIngestionPipeline, mocker: Any
) -> None:
    mocker.patch.object(pipeline, "read_source_data", return_value=None)
    write_spy = mocker.patch.object(pipeline, "write_to_iceberg")

    pipeline.run()

    write_spy.assert_not_called()


def test_run_raises_when_merge_key_missing(
    pipeline: IcebergIngestionPipeline, local_spark: SparkSession, mocker: Any
) -> None:
    df_missing_key = local_spark.createDataFrame([Row(not_the_merge_key="e1")])
    mocker.patch.object(pipeline, "read_source_data", return_value=df_missing_key)
    write_spy = mocker.patch.object(pipeline, "write_to_iceberg")

    with pytest.raises(ValueError, match="Primary merge key 'event_id' not found"):
        pipeline.run()

    write_spy.assert_not_called()


def test_run_does_not_stop_an_injected_shared_session(
    pipeline: IcebergIngestionPipeline, mocker: Any
) -> None:
    """A pipeline built with an externally-owned session must never call spark.stop()."""
    mocker.patch.object(pipeline, "read_source_data", return_value=None)
    stop_spy = mocker.patch.object(pipeline.spark, "stop")

    pipeline.run()

    stop_spy.assert_not_called()


# ---------------------------------------------------------------------------
# write_to_iceberg: the idempotent MERGE INTO / CREATE branch logic
# ---------------------------------------------------------------------------

def test_write_to_iceberg_creates_table_when_absent() -> None:
    pipeline, spark_mock = _mocked_pipeline(table_exists=False)

    write_builder = MagicMock(name="write_builder")
    write_builder.tableProperty.return_value = write_builder
    df_mock = MagicMock(name="dataframe")
    df_mock.writeTo.return_value = write_builder

    pipeline.write_to_iceberg(df_mock)

    df_mock.writeTo.assert_called_once_with(pipeline.iceberg_table_identifier)
    assert write_builder.tableProperty.call_args_list == [
        (("location", pipeline.s3_location),),
        (("format-version", "2"),),
        (("write.merge.mode", "merge-on-read"),),
    ]
    write_builder.createOrReplace.assert_called_once()
    spark_mock.sql.assert_not_called()


def test_write_to_iceberg_executes_merge_when_table_exists() -> None:
    pipeline, spark_mock = _mocked_pipeline(table_exists=True)
    df_mock = MagicMock(name="dataframe")

    pipeline.write_to_iceberg(df_mock)

    df_mock.createOrReplaceTempView.assert_called_once_with("updates")
    df_mock.writeTo.assert_not_called()

    spark_mock.sql.assert_called_once()
    merge_sql = spark_mock.sql.call_args[0][0]
    assert f"MERGE INTO {pipeline.iceberg_table_identifier} t" in merge_sql
    assert "USING updates s" in merge_sql
    assert f"ON t.{pipeline.merge_key} = s.{pipeline.merge_key}" in merge_sql
    assert "WHEN MATCHED THEN UPDATE SET *" in merge_sql
    assert "WHEN NOT MATCHED THEN INSERT *" in merge_sql


def test_write_to_iceberg_propagates_merge_failures() -> None:
    pipeline, spark_mock = _mocked_pipeline(table_exists=True)
    spark_mock.sql.side_effect = RuntimeError("simulated MERGE failure")
    df_mock = MagicMock(name="dataframe")

    with pytest.raises(RuntimeError, match="simulated MERGE failure"):
        pipeline.write_to_iceberg(df_mock)
