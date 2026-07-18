import os
from typing import Literal

from pydantic_settings import BaseSettings


class UIConfigurationSettings(BaseSettings):
    """Production runtime settings using environment injection fallback defaults."""
    api_gateway_endpoint: str = os.getenv("API_URL", "http://localhost:8000/api/v1")
    application_title: str = "Enterprise Data Analytics Copilot"
    page_layout: Literal["centered", "wide"]= "wide"

ui_settings = UIConfigurationSettings()
