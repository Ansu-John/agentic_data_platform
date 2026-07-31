"""
Unit tests for src/lambda/ingest_trigger/lambda_function.py.

The Lambda source lives under a directory literally named `lambda`, which is a
reserved Python keyword and therefore cannot appear in a dotted `import`
statement -- `from src.lambda.ingest_trigger import lambda_function` is a
SyntaxError, not an ImportError. That is almost certainly why this handler
had zero test coverage. We work around it by loading the module directly
from its file path via `importlib`.

Coverage: S3 event parsing (happy path + malformed payloads), the successful
hand-off to Step Functions, and the three error-handling branches
(ValueError -> 400, ClientError -> 502, unexpected Exception -> 500).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
from collections.abc import Generator
from pathlib import Path
from typing import Any

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

# Required cold-start environment variables must exist BEFORE the module is
# imported: the module raises RuntimeError at import time if they're absent.
os.environ.setdefault(
    "STEP_FUNCTION_ARN",
    "arn:aws:states:ap-south-1:123456789012:stateMachine:test-ingestion-pipeline",
)
os.environ.setdefault("SILVER_BUCKET", "test-silver-bucket")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("PROJECT", "dataplatform")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _REPO_ROOT / "src" / "lambda" / "ingest_trigger" / "lambda_function.py"


def _load_lambda_module() -> types.ModuleType:
    """Imports lambda_function.py by file path, bypassing the 'lambda' keyword."""
    spec = importlib.util.spec_from_file_location("ingest_trigger_lambda_function", _MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lambda_function = _load_lambda_module()


class _FakeLambdaContext:
    """Minimal stand-in for the AWS Lambda runtime's context object."""

    aws_request_id = "11111111-2222-3333-4444-555555555555"


def _s3_put_event(bucket: str, key: str) -> dict[str, Any]:
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key},
                }
            }
        ]
    }


@pytest.fixture
def mocked_state_machine_arn() -> Generator[str, None, None]:
    """Creates a real, moto-mocked Step Function so start_execution succeeds end-to-end."""
    with mock_aws():
        sfn = boto3.client("stepfunctions", region_name="ap-south-1")
        definition = json.dumps(
            {"StartAt": "Pass", "States": {"Pass": {"Type": "Pass", "End": True}}}
        )
        response = sfn.create_state_machine(
            name="test-ingestion-pipeline",
            definition=definition,
            roleArn="arn:aws:iam::123456789012:role/test-sfn-role",
        )
        yield response["stateMachineArn"]


# ---------------------------------------------------------------------------
# parse_s3_event
# ---------------------------------------------------------------------------

def test_parse_s3_event_extracts_bucket_key_entity() -> None:
    event = _s3_put_event("dataplatform-dev-bronze", "raw/orders/2026-07-30.json")

    bucket, key, entity = lambda_function.parse_s3_event(event)

    assert bucket == "dataplatform-dev-bronze"
    assert key == "raw/orders/2026-07-30.json"
    assert entity == "orders"


def test_parse_s3_event_rejects_key_without_entity_folder() -> None:
    event = _s3_put_event("dataplatform-dev-bronze", "orders-2026-07-30.json")

    with pytest.raises(ValueError, match="does not match expected folder structure"):
        lambda_function.parse_s3_event(event)


def test_parse_s3_event_rejects_malformed_payload() -> None:
    with pytest.raises(ValueError, match="Malformed S3 event payload"):
        lambda_function.parse_s3_event({"Records": [{}]})


# ---------------------------------------------------------------------------
# lambda_handler: success path
# ---------------------------------------------------------------------------

def test_lambda_handler_success_starts_step_function_execution(
    monkeypatch: pytest.MonkeyPatch, mocked_state_machine_arn: str
) -> None:
    monkeypatch.setattr(lambda_function, "SFN_ARN", mocked_state_machine_arn)
    monkeypatch.setattr(
        lambda_function, "sfn_client", boto3.client("stepfunctions", region_name="ap-south-1")
    )

    event = _s3_put_event("dataplatform-dev-bronze", "raw/orders/2026-07-30.json")
    result = lambda_function.lambda_handler(event, _FakeLambdaContext())

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["message"] == "Ingestion pipeline triggered successfully"
    assert "execution_arn" in body


# ---------------------------------------------------------------------------
# lambda_handler: error branches
# ---------------------------------------------------------------------------

def test_lambda_handler_returns_400_on_malformed_event() -> None:
    result = lambda_function.lambda_handler({"Records": [{}]}, _FakeLambdaContext())

    assert result["statusCode"] == 400
    assert "Bad Request" in json.loads(result["body"])


def test_lambda_handler_returns_502_on_aws_client_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _RaisingSfnClient:
        def start_execution(self, **_kwargs: Any) -> dict[str, Any]:
            raise ClientError(
                error_response={
                    "Error": {"Code": "StateMachineDoesNotExist", "Message": "not found"}
                },
                operation_name="StartExecution",
            )

    monkeypatch.setattr(lambda_function, "sfn_client", _RaisingSfnClient())

    event = _s3_put_event("dataplatform-dev-bronze", "raw/orders/2026-07-30.json")
    result = lambda_function.lambda_handler(event, _FakeLambdaContext())

    assert result["statusCode"] == 502
    assert "StateMachineDoesNotExist" in json.loads(result["body"])


def test_lambda_handler_returns_500_on_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ExplodingSfnClient:
        def start_execution(self, **_kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("unexpected boom")

    monkeypatch.setattr(lambda_function, "sfn_client", _ExplodingSfnClient())

    event = _s3_put_event("dataplatform-dev-bronze", "raw/orders/2026-07-30.json")
    result = lambda_function.lambda_handler(event, _FakeLambdaContext())

    assert result["statusCode"] == 500
    assert "Internal Server Error" in json.loads(result["body"])
