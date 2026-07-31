from functools import cache
from typing import Any

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrockConverse

from src.agent.config.settings import settings
from src.agent.core.exceptions import AgentDomainError
from src.agent.core.logger import get_logger

logger = get_logger(__name__)


@cache
def _get_bedrock_runtime_client(region_name: str) -> Any:
    """
    Returns a cached boto3 bedrock-runtime client per region.

    get_evaluator_llm() is called fresh on every validate_dq_node execution
    (see src/agent/nodes.py), so without caching, every DQ validation paid for
    a brand new client/connection pool. See _get_athena_client in
    aws_athena.py for the same rationale. The retry Config only depends on
    region, so it's safe to bake into this cached factory.
    """
    retry_config = Config(
        region_name=region_name,
        retries={
            "max_attempts": 5,
            "mode": "adaptive"
        }
    )
    return boto3.client("bedrock-runtime", config=retry_config)


class BedrockEngineFactory:
    """
    Factory for instantiating production-ready Bedrock connections with
    enforced retry geometries and deterministic temperature controls.
    """

    @staticmethod
    def get_evaluator_llm() -> ChatBedrockConverse:
        """
        Returns a ChatBedrockConverse instance configured strictly for analytical
        evaluation tasks (zero temperature, high token limit, aggressive retries).
        """
        logger.info("initializing_bedrock_engine", model_id=settings.BEDROCK_MODEL_ID)

        try:
            bedrock_client = _get_bedrock_runtime_client(settings.AWS_REGION)

            # Instantiate the LangChain interface using the hardened, shared client
            llm = ChatBedrockConverse(
                client=bedrock_client,
                model=settings.BEDROCK_MODEL_ID,
                temperature=0.0, # Deterministic outputs required for DQ validation
                max_tokens=4096,
                region_name=settings.AWS_REGION,
                # LangChain level retries for transient HTTP failures
                max_retries=3
            )

            return llm

        except Exception as e:
            logger.critical("bedrock_initialization_failure", error=str(e), exc_info=True)
            raise AgentDomainError(f"Failed to initialize AWS Bedrock runtime: {str(e)}") from e
