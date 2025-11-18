import os
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig


class ModelConfig(BaseModel):
    """Configuration for a specific language model."""

    model_provider: str = Field(
        default="openai",
        description="The provider of the language model, e.g., 'openai', 'google', etc."
    )

    model: str = Field(
        default="openai:gpt-4.1-nano",
        description="The name of the language model to use."
    )
    temperature: float = Field(
        default=0.7,
        description="The temperature setting for the language model."
    )
    max_retries: int = Field(
        default=2,
        description="The maximum number of retries for the language model."
    )
    api_key: Optional[str] = Field(
        default=None,
        description="The API key for the language model provider, if required."
    )
    base_url: Optional[str] = Field(
        default=None,
        description="The base URL for the language model provider, if required."
    )

class Configuration(BaseModel):
    """The configuration for the agent."""
    xlangguage_agent_model: ModelConfig = Field(
        default=ModelConfig(
            model="qwen-max",
            model_provider="openai",
            temperature=0.1,
            base_url=os.environ["QWEN_BASE_URL"],
            api_key=os.environ["QWEN_API_KEY"],
        )
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        # Get raw values from environment or config
        raw_values: dict[str, Any] = {
            name: os.environ.get(name.upper(), configurable.get(name))
            for name in cls.model_fields.keys()
        }

        # Filter out None values
        values = {k: v for k, v in raw_values.items() if v is not None}

        return cls(**values)