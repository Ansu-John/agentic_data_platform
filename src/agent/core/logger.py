import logging
import logging.config
from collections.abc import MutableMapping
from contextvars import ContextVar
from typing import Any, cast

import structlog
from structlog.typing import Processor

# Thread-safe context variable to track execution trace boundaries across async calls
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="system-startup")



def inject_execution_context(
    _logger: logging.Logger, _log_method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Injects distributed tracing IDs and operational environment metadata into every log."""
    event_dict["correlation_id"] = correlation_id.get()
    event_dict["service"] = "ai-dq-agent"
    return event_dict

def configure_enterprise_logging(log_level: str = "INFO") -> None:
    """
    Configures structural logging and hijacks standard python logging
    to ensure external libraries (boto3, langchain) conform to the JSON schema.
    """
    shared_processors: list[Processor]  = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        inject_execution_context,
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[structlog.processors.JSONRenderer()],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    # Quiet down overly verbose AWS SDK and HTTP libraries
    for noisy_logger in ("botocore", "urllib3", "httpx", "boto3"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Returns a bound logger instance for domain-specific logging."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))

