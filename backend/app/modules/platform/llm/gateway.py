"""LLM Gateway with rate limiting, daily request cap, bounded repair, and caching."""

import asyncio
import hashlib
import json
import logging
from typing import Any, TypeVar

from app.config import settings
from app.modules.platform.llm.client import (
    FakeLLMClient,
    GeminiLLMClient,
    LLMClient,
    LLMMessage,
    LLMResponse,
)
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class DailyCapExceededError(Exception):
    """Raised when daily LLM budget or request cap is reached."""

    pass


class StructuredOutputValidationError(Exception):
    """Raised when LLM output violates Pydantic schema and bounded repair fails."""

    pass


class LLMGateway:
    """Enterprise Gateway encapsulating safety, cost control, retries, and bounded repair."""

    def __init__(self, client: LLMClient | None = None) -> None:
        if client is not None:
            self.client = client
        elif settings.llm_provider == "gemini" and settings.llm_api_key:
            self.client = GeminiLLMClient(
                api_key=settings.llm_api_key, model_name=settings.llm_model
            )
        else:
            self.client = FakeLLMClient(default_model=settings.llm_model)

        self.requests_today = 0
        self.total_tokens_today = 0
        self.total_cost_usd_today = 0.0
        self._cache: dict[str, LLMResponse] = {}

    def _hash_messages(self, messages: list[LLMMessage], temperature: float) -> str:
        serialized = "|".join(f"{m.role}:{m.content}" for m in messages) + f"|temp:{temperature}"
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        response_schema: type[T] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Invokes LLM with daily cap check, dev caching, and retry with backoff."""
        if self.requests_today >= settings.llm_daily_request_cap:
            raise DailyCapExceededError(
                f"Daily LLM request cap of {settings.llm_daily_request_cap} exceeded."
            )

        # Check in-memory dev cache
        cache_key = self._hash_messages(messages, temperature)
        if settings.llm_cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]

        # Retry with exponential backoff
        last_exc: Exception | None = None
        for attempt in range(1, settings.llm_max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    self.client.generate(
                        messages=messages,
                        temperature=temperature,
                        response_schema=response_schema,
                        tools=tools,
                    ),
                    timeout=float(settings.llm_request_timeout_seconds),
                )
                self.requests_today += 1
                self.total_tokens_today += response.total_tokens
                self.total_cost_usd_today += response.cost_estimate

                if settings.llm_cache_enabled:
                    self._cache[cache_key] = response

                return response
            except TimeoutError as exc:
                last_exc = exc
                logger.warning(f"LLM request timed out on attempt {attempt}")
            except Exception as exc:
                last_exc = exc
                logger.warning(f"LLM generation failed on attempt {attempt}: {exc}")

            if attempt < settings.llm_max_retries:
                await asyncio.sleep(0.1 * (2 ** (attempt - 1)))

        raise RuntimeError(
            f"LLM request failed after {settings.llm_max_retries} attempts: {last_exc}"
        ) from last_exc

    async def generate_structured(
        self,
        messages: list[LLMMessage],
        response_schema: type[T],
        temperature: float = 0.0,
    ) -> T:
        """
        Generates and parses structured output with at most ONE bounded repair attempt.
        Never crashes or guesses on failure; raises StructuredOutputValidationError.
        """
        response = await self.generate(
            messages=messages,
            temperature=temperature,
            response_schema=response_schema,
        )

        try:
            parsed = json.loads(response.content)
            return response_schema.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as initial_err:
            logger.warning(
                f"Initial structured output parsing failed: {initial_err}. Attempting bounded repair..."
            )

            # Bounded Repair: Append validation error and instruct LLM to produce valid JSON
            repair_messages = list(messages) + [
                LLMMessage(role="assistant", content=response.content),
                LLMMessage(
                    role="user",
                    content=(
                        f"Your output failed JSON/schema validation with error:\n{initial_err}\n"
                        f"Please output ONLY valid JSON matching schema '{response_schema.__name__}'."
                    ),
                ),
            ]

            repair_resp = await self.generate(
                messages=repair_messages,
                temperature=0.0,
                response_schema=response_schema,
            )

            try:
                repair_parsed = json.loads(repair_resp.content)
                return response_schema.model_validate(repair_parsed)
            except Exception as final_err:
                raise StructuredOutputValidationError(
                    f"Structured output validation failed after repair attempt: {final_err}"
                ) from final_err


# Global gateway singleton
gateway = LLMGateway()
