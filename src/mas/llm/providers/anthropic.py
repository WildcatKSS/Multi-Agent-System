"""Anthropic Messages API LLM provider.

Calls the Anthropic ``/v1/messages`` endpoint using stdlib ``urllib`` — no
``anthropic`` package required.  Retry, timeout, and backoff are handled by
:class:`~mas.llm.base.BaseProvider`.

Usage::

    from mas.llm.providers.anthropic import AnthropicProvider
    from mas.llm.config import AnthropicConfig
    from mas.llm.contracts import LLMMessage

    provider = AnthropicProvider(
        AnthropicConfig(model="claude-3-5-sonnet-20241022", api_key="sk-ant-...")
    )
    response = await provider.call([LLMMessage(role="user", content="Hello")])
"""

import asyncio
import json
import time
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable
from typing import Any

from mas.llm.base import BaseProvider
from mas.llm.config import AnthropicConfig
from mas.llm.contracts import LLMMessage, LLMResponse
from mas.llm.errors import APIError, AuthenticationError, RateLimitError

#: Type of the injectable HTTP transport.
_Transport = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

#: Anthropic Messages API endpoint.
_ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"

#: Default max_tokens when the caller does not supply one.
#: The Anthropic API requires this field; 1024 is a safe default.
_DEFAULT_MAX_TOKENS = 1024


def _build_headers(api_key: str, version: str) -> dict[str, str]:
    """Return request headers for the Anthropic API.

    Args:
        api_key: Anthropic API key.
        version: Value for the ``anthropic-version`` header.
    """
    return {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": version,
    }


def _map_http_error(exc: urllib.error.HTTPError) -> APIError | RateLimitError | AuthenticationError:
    """Map an HTTP status code to the appropriate :class:`~mas.llm.errors.LLMError`.

    HTTP 529 (Anthropic ``overloaded_error``) is treated as transient alongside
    standard 5xx codes.
    """
    status = exc.code
    reason = exc.reason or str(status)
    if status == 429:
        retry_after: int | None = None
        try:
            raw = exc.headers.get("Retry-After")
            if raw is not None:
                retry_after = int(raw)
        except (ValueError, AttributeError):
            pass
        return RateLimitError(
            f"Anthropic rate limit: {reason}",
            original_exception=exc,
            retry_after_seconds=retry_after,
        )
    if status in (401, 403):
        return AuthenticationError(
            f"Anthropic authentication failed ({status}): {reason}",
            original_exception=exc,
        )
    transient = status >= 500
    return APIError(f"Anthropic HTTP {status}: {reason}", original_exception=exc, transient=transient)


def _make_urllib_transport(  # pragma: no cover
    timeout_seconds: float, api_key: str, version: str
) -> _Transport:
    """Return an async HTTP transport using stdlib urllib on a thread-pool executor."""
    headers = _build_headers(api_key, version)

    async def _post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        data = json.dumps(payload).encode()
        request = urllib.request.Request(url, data=data, headers=headers)

        def _do_request() -> dict[str, Any]:
            try:
                with urllib.request.urlopen(request, timeout=timeout_seconds) as resp:  # noqa: S310
                    return json.loads(resp.read())  # type: ignore[no-any-return]
            except urllib.error.HTTPError as exc:
                raise _map_http_error(exc) from exc
            except urllib.error.URLError as exc:
                raise APIError(
                    f"Anthropic connection error: {exc.reason}",
                    original_exception=exc,
                    transient=True,
                ) from exc

        return await loop.run_in_executor(None, _do_request)

    return _post


class AnthropicProvider(BaseProvider):
    """LLM provider that calls the Anthropic Messages API.

    Inherits timeout enforcement, retry with exponential backoff, and structured
    logging from :class:`~mas.llm.base.BaseProvider`.  Streaming is deferred to
    Phase 2 Issue 08.

    Generation parameters (``temperature``, ``top_p``, ``max_tokens``, …) are
    passed at the **top level** of the request body as the Anthropic API requires.
    ``max_tokens`` defaults to :data:`_DEFAULT_MAX_TOKENS` when not supplied by
    the caller; the Anthropic API requires it and provides no default.

    Args:
        config: Anthropic configuration. Must be an
            :class:`~mas.llm.config.AnthropicConfig` instance.
        _transport: Injectable async HTTP transport for testing.  When ``None``
            (default), a stdlib urllib transport is created automatically.

    Raises:
        ConfigError: If ``config`` is not an :class:`~mas.llm.config.AnthropicConfig`.
    """

    def __init__(
        self,
        config: AnthropicConfig,
        *,
        _transport: _Transport | None = None,
    ) -> None:
        super().__init__(
            config,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        assert isinstance(self.config, AnthropicConfig)
        api_key = self.config.api_key
        assert api_key is not None
        self._transport: _Transport = (
            _transport
            if _transport is not None
            else _make_urllib_transport(
                self.timeout_seconds,
                api_key=api_key,
                version=self.config.version,
            )
        )

    # ------------------------------------------------------------------ #
    # LLMProvider abstract properties
    # ------------------------------------------------------------------ #

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return self.config.model

    # ------------------------------------------------------------------ #
    # BaseProvider abstract method
    # ------------------------------------------------------------------ #

    def validate_config(self, config: Any) -> bool:
        """Accept only :class:`~mas.llm.config.AnthropicConfig` instances."""
        return isinstance(config, AnthropicConfig)

    # ------------------------------------------------------------------ #
    # Provider-specific implementation
    # ------------------------------------------------------------------ #

    async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
        """POST to the Anthropic Messages endpoint and return a response.

        Args:
            messages: Conversation history to send.
            model: Model identifier (e.g. ``"claude-3-5-sonnet-20241022"``).
            **kwargs: Generation parameters (``temperature``, ``top_p``, …) are
                forwarded at the **top level** of the request body.
                ``max_tokens`` defaults to :data:`_DEFAULT_MAX_TOKENS` if not
                supplied — the Anthropic API requires it.

        Returns:
            The model's response as an :class:`~mas.llm.contracts.LLMResponse`.

        Raises:
            APIError: On HTTP errors or unexpected response shapes.
            RateLimitError: On HTTP 429.
            AuthenticationError: On HTTP 401/403.
        """
        max_tokens: int = kwargs.pop("max_tokens", _DEFAULT_MAX_TOKENS)

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            **kwargs,
        }

        start = time.monotonic()
        data = await self._transport(_ANTHROPIC_MESSAGES_URL, payload)
        latency_ms = (time.monotonic() - start) * 1000.0

        content_blocks = data.get("content") or []
        if not content_blocks:
            raise APIError(
                f"Anthropic returned no content blocks for model {model!r}",
                transient=False,
            )
        raw_content: str = next(
            (b.get("text") or "" for b in content_blocks if b.get("type") == "text"), ""
        )
        has_tool_use = any(b.get("type") == "tool_use" for b in content_blocks)
        if not raw_content.strip() and not has_tool_use:
            raise APIError(
                f"Anthropic returned empty content for model {model!r}",
                transient=False,
            )

        usage = data.get("usage") or {}
        tokens_used: int = (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0)
        returned_model: str = data.get("model") or model

        return LLMResponse(
            message=LLMMessage(role="assistant", content=raw_content),
            tokens_used=tokens_used,
            model=returned_model,
            latency_ms=latency_ms,
            metadata={
                "stop_reason": data.get("stop_reason"),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
            },
        )


# Self-register with the process-wide default registry so callers can use
# ``default_registry.from_config(AnthropicConfig(...))`` without manual setup.
from mas.llm.provider_registry import default_registry  # noqa: E402

default_registry.register("anthropic", AnthropicProvider, AnthropicConfig)
