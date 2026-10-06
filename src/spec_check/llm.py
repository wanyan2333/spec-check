"""A small LLM interface so the checker can swap models and tests can mock it."""

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import openai
from dotenv import find_dotenv, load_dotenv

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

log = logging.getLogger(__name__)

# Errors worth retrying: rate limits (free tier!), transient server errors, network blips.
RETRYABLE_ERRORS = (
    openai.RateLimitError,
    openai.InternalServerError,
    openai.APIConnectionError,
)


@dataclass
class LLMResponse:
    text: str
    model: str
    latency_s: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    retries: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMClient(Protocol):
    model: str

    def complete(self, messages: list[dict]) -> LLMResponse:
        """Send chat messages, return the assistant text plus timing and token usage."""
        ...


class OpenAICompatClient:
    """Chat client for any OpenAI-compatible endpoint (default: Gemini)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = GEMINI_BASE_URL,
        max_retries: int = 5,
        base_delay_s: float = 4.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.model = model
        self.max_retries = max_retries
        self.base_delay_s = base_delay_s
        self._sleep = sleep
        # We do our own backoff so it is visible in logs and testable.
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url, max_retries=0)

    def complete(self, messages: list[dict]) -> LLMResponse:
        for attempt in range(self.max_retries + 1):
            start = time.perf_counter()
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0,
                    response_format={"type": "json_object"},
                )
            except RETRYABLE_ERRORS as exc:
                if attempt == self.max_retries:
                    raise
                delay = min(self.base_delay_s * 2**attempt, 60.0)
                log.warning(
                    "LLM call failed (%s), retry %d/%d in %.0fs",
                    type(exc).__name__,
                    attempt + 1,
                    self.max_retries,
                    delay,
                )
                self._sleep(delay)
                continue

            latency = time.perf_counter() - start
            usage = resp.usage
            result = LLMResponse(
                text=resp.choices[0].message.content or "",
                model=self.model,
                latency_s=latency,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                retries=attempt,
            )
            log.info(
                "LLM call: model=%s latency=%.2fs tokens=%d (prompt %d, completion %d)",
                self.model,
                latency,
                result.total_tokens,
                result.prompt_tokens,
                result.completion_tokens,
            )
            return result
        raise AssertionError("unreachable")


def client_from_env(model: str | None = None) -> OpenAICompatClient:
    """Build the default client from GEMINI_API_KEY / SPEC_CHECK_MODEL (.env is loaded)."""
    load_dotenv(find_dotenv(usecwd=True))
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in.")
    model = model or os.environ.get("SPEC_CHECK_MODEL")
    if not model:
        raise RuntimeError("SPEC_CHECK_MODEL is not set. Run scripts/list_models.py and pick one.")
    return OpenAICompatClient(api_key=api_key, model=model)
