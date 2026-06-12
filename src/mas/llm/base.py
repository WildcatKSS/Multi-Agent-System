"""BaseProvider: a reusable LLMProvider base with timeout, retry, and logging.

Concrete providers (Ollama, HuggingFace, OpenAI, Anthropic, ...) subclass
:class:`BaseProvider` and implement only the provider-specific bits -- ``name``,
``default_model``, ``validate_config`` and the actual API call ``_invoke``. The
cross-cutting concerns are handled here once:

- **Config validation** at construction time (raises :class:`ConfigError`).
- **Timeout enforcement** per attempt via :func:`asyncio.timeout`.
- **Retry with exponential backoff** for transient failures (``2**n`` seconds).
- **Error classification** using the :class:`LLMError` ``transient`` flag.
- **Structured JSON logging** with correlation IDs, token, latency and cost
  metrics -- never logging message contents or provider credentials.

The retry/timeout template lives in :meth:`BaseProvider.call`; subclasses do the
network I/O in :meth:`BaseProvider._invoke`.
"""

import asyncio
import logging
import time
from abc import abstractmethod
from typing import Any

from mas.llm.contracts import (
    APIError,
    ConfigError,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    ValidationError,
)
from mas.llm.contracts import (
    TimeoutError as ProviderTimeoutError,
)
from mas.observability.correlation import get_correlation_id

#: Default per-attempt timeout, in seconds.
DEFAULT_TIMEOUT_SECONDS = 30.0

#: Default maximum number of retries for transient failures.
DEFAULT_MAX_RETRIES = 3

_logger = logging.getLogger("mas.llm.base")


class BaseProvider(LLMProvider):
    """Reusable base class for LLM providers.

    Wraps the provider-specific :meth:`_invoke` with timeout enforcement, retry
    with exponential backoff, error classification, and structured logging.

    Args:
        config: Provider configuration. Validated via :meth:`validate_config`
            during construction; an invalid config raises :class:`ConfigError`.
        timeout_seconds: Per-attempt timeout. Must be > 0. Defaults to 30s.
        max_retries: Maximum retries for transient failures. Must be >= 0.
            Defaults to 3 (so up to 4 attempts total).

    Raises:
        ValueError: If ``timeout_seconds`` <= 0 or ``max_retries`` < 0.
        ConfigError: If ``validate_config`` rejects ``config``.
    """

    def __init__(
        self,
        config: Any = None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be > 0, got {timeout_seconds}")
        if max_retries < 0:
            raise ValueError(f"max_retries cannot be negative, got {max_retries}")

        self.config = config
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        # Validate config up front so misconfiguration fails fast, before any
        # network I/O. validate_config may raise ConfigError itself, or signal
        # invalidity by returning False (normalised to ConfigError here).
        if not self.validate_config(config):
            raise ConfigError(f"{self.name} received an invalid configuration")

    # ------------------------------------------------------------------ #
    # Defaults that concrete providers may override.
    # ------------------------------------------------------------------ #

    @property
    def supports_streaming(self) -> bool:
        """Whether this provider streams responses. ``False`` by default."""
        return False

    def estimate_tokens(self, text: str) -> int:
        """Roughly estimate token count using a ~4-chars-per-token heuristic.

        Providers with a real tokenizer should override this. The estimate is
        always non-negative (empty text yields 0).

        Args:
            text: The text to estimate.

        Returns:
            A non-negative estimated token count.
        """
        return (len(text) + 3) // 4

    def estimate_cost_usd(self, tokens_used: int, model: str) -> float:
        """Estimate the USD cost of a call. ``0.0`` by default (e.g. local models).

        Providers backed by paid APIs should override this with real pricing.

        Args:
            tokens_used: Total tokens consumed by the call.
            model: The model identifier used.

        Returns:
            A non-negative estimated cost in USD.
        """
        return 0.0

    # ------------------------------------------------------------------ #
    # Provider-specific hooks (abstract).
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
        """Perform the actual provider API call (no retry/timeout wrapping).

        Implementations should raise an appropriate :class:`LLMError` subclass on
        failure so :meth:`call` can classify and retry correctly.

        Args:
            messages: The conversation to send.
            model: The resolved model identifier.
            **kwargs: Provider-specific options.

        Returns:
            The model's response.
        """

    # ------------------------------------------------------------------ #
    # Public template method.
    # ------------------------------------------------------------------ #

    async def call(self, messages: list[LLMMessage], model: str = "", **kwargs: Any) -> LLMResponse:
        """Invoke the model with timeout, retry, and structured logging.

        Args:
            messages: The conversation history. Must be non-empty.
            model: Model identifier. Falls back to :attr:`default_model` if empty.
            **kwargs: Provider-specific options forwarded to :meth:`_invoke`.

        Returns:
            The model's response.

        Raises:
            ValidationError: If ``messages`` is empty.
            LLMError: The last error if all attempts fail (its ``transient`` flag
                reflects whether the failure was retryable).
        """
        if not messages:
            raise ValidationError("messages cannot be empty")

        target_model = model or self.default_model
        attempt = 0
        while True:
            try:
                return await self._attempt(messages, target_model, attempt, **kwargs)
            except LLMError as err:
                if err.transient and attempt < self.max_retries:
                    delay = (
                        err.retry_after_seconds
                        if err.retry_after_seconds is not None
                        else 2**attempt
                    )
                    self._log("llm_call_retry", target_model, attempt=attempt, error=err, delay=delay)
                    await self._sleep(delay)
                    attempt += 1
                    continue
                self._log("llm_call_failed", target_model, attempt=attempt, error=err)
                raise

    # ------------------------------------------------------------------ #
    # Internals.
    # ------------------------------------------------------------------ #

    async def _attempt(
        self, messages: list[LLMMessage], model: str, attempt: int, **kwargs: Any
    ) -> LLMResponse:
        """Run a single attempt under the timeout, normalising errors."""
        start = time.monotonic()
        try:
            async with asyncio.timeout(self.timeout_seconds):
                response = await self._invoke(messages, model, **kwargs)
        except TimeoutError as exc:
            # Builtin TimeoutError (raised by asyncio.timeout) -> our transient
            # provider TimeoutError. The contracts TimeoutError is imported as
            # ProviderTimeoutError, so the bare name here is the builtin.
            raise ProviderTimeoutError(
                f"{self.name} call timed out after {self.timeout_seconds}s",
                original_exception=exc,
            ) from exc
        except LLMError:
            # Already classified by the provider; let call() decide on retry.
            raise
        except Exception as exc:
            # Unexpected error: wrap as a permanent APIError so it is not retried
            # blindly, while preserving the original for diagnostics.
            raise APIError(
                f"{self.name} call failed: {exc}",
                original_exception=exc,
                transient=False,
            ) from exc

        latency_ms = (time.monotonic() - start) * 1000.0
        self._log("llm_call_succeeded", model, attempt=attempt, response=response, latency_ms=latency_ms)
        return response

    async def _sleep(self, seconds: float) -> None:
        """Sleep between retries. Isolated so tests can override it."""
        await asyncio.sleep(seconds)

    def _log(
        self,
        event: str,
        model: str,
        *,
        attempt: int,
        response: LLMResponse | None = None,
        latency_ms: float | None = None,
        error: LLMError | None = None,
        delay: float | None = None,
    ) -> None:
        """Emit a structured log record for a provider operation.

        Logs only operational metadata (provider, model, tokens, latency, cost,
        retry/error classification). Message contents and provider credentials
        are never logged.
        """
        extra: dict[str, Any] = {
            "provider": self.name,
            "model": model,
            "attempt": attempt,
            "correlation_id": get_correlation_id(),
        }
        if response is not None:
            extra["tokens_used"] = response.tokens_used
            extra["cost_usd"] = self.estimate_cost_usd(response.tokens_used, model)
        if latency_ms is not None:
            extra["latency_ms"] = latency_ms
        if error is not None:
            extra["error_type"] = type(error).__name__
            extra["transient"] = error.transient
        if delay is not None:
            extra["retry_delay_seconds"] = delay

        if error is not None and event == "llm_call_failed":
            _logger.error(event, extra=extra)
        elif error is not None:
            _logger.warning(event, extra=extra)
        else:
            _logger.info(event, extra=extra)
