import boto3
from botocore.config import Config
from langchain_aws import ChatBedrockConverse

from src.agent.config.settings import settings
from src.agent.core.exceptions import AgentDomainError
from src.agent.core.logger import get_logger

logger = get_logger(__name__)

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
            # Configure custom boto3 client with aggressive exponential backoff for LLM rate limits
            retry_config = Config(
                region_name=settings.AWS_REGION,
                retries={
                    "max_attempts": 5,
                    "mode": "adaptive"
                }
            )
            bedrock_client = boto3.client("bedrock-runtime", config=retry_config)


            # Instantiate the LangChain interface using the hardened client
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
