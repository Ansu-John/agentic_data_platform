import os

import boto3
import structlog
from botocore.config import Config
from langchain_aws import ChatBedrock

logger = structlog.get_logger()

class BedrockClientFactory:
    """Factory to safely initialize authenticated Bedrock clients
    with custom retry configurations."""

    @staticmethod
    def get_llm(model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0") -> ChatBedrock:
        region = os.getenv("AWS_REGION", "us-east-1")
        logger.info("initializing_bedrock_client", model_id=model_id, region=region)

        # Enforce corporate proxy rules, time-outs, and aggressive exponential backoff
        config = Config(
            region_name=region,
            retries={"max_attempts": 5, "mode": "standard"},
            connect_timeout=10,
            read_timeout=60
        )

        boto_session = boto3.Session()
        bedrock_runtime = boto_session.client(
            service_name="bedrock-runtime",
            config=config
        )

        return ChatBedrock(
            client=bedrock_runtime,
            model=model_id,
            model_kwargs={"temperature": 0.0, "max_tokens": 4096}
        )
