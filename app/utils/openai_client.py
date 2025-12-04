import os
from typing import Any

import openai
import structlog

logger = structlog.get_logger(__name__)


class OpenAIClientWrapper:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        self.client = openai.Client(api_key=self.api_key)

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Wrapper for client.chat.completions.create that logs token usage.
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
                **kwargs,
            )
        except Exception as e:
            logger.error("openai_api_error", error=str(e))
            raise e

        # Log usage
        if response.usage:
            logger.info(
                "openai_usage",
                model=response.model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
        else:
            logger.warning("openai_usage_missing", model=model)

        return response
