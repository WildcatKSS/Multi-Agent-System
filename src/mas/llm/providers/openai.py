"""OpenAI Chat Completions LLM provider.

Calls the OpenAI ``/v1/chat/completions`` endpoint using stdlib ``urllib`` — no
``openai`` package required.  Retry, timeout, and backoff are handled by
:class:`~mas.llm.base.BaseProvider`.

Usage::

    from mas.llm.providers.openai import OpenAIProvider
    from mas.llm.config import OpenAIConfig
    from mas.llm.contracts import LLMMessage

    provider = OpenAIProvider(OpenAIConfig(model="gpt-4o", api_key="sk-..."))
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
from mas.llm.config import OpenAIConfig
from mas.llm.contracts import LLMMessage, LLMResponse
from mas.llm.errors import APIError, AuthenticationError, RateLimitError

#: Type of the injectable HTTP transport.
_Transport = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

#: OpenAI Chat Completions endpoint.
_OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def _build_headers(api_key: str, organization: str | None = None) -> dict[str, str]:
    """Return request headers for the OpenAI API.

    Args:
        api_key: OpenAI API key.
        organization: Optional organization identifier.  When present, adds the
            ``OpenAI-Organization`` header.
    """
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if organization:
        headers["OpenAI-Organization"] = organization
    return headers


def _map_http_error(exc: urllib.error.HTTPError) -> APIError | RateLimitError | AuthenticationError:
    """Map an HTTP status code to the appropriate :class:`~mas.llm.errors.LLMError`."""
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
            f"OpenAI rate limit: {reason}",
            original_exception=exc,
            retry_after_seconds=retry_after,
        )
    if status in (401, 403):
        return AuthenticationError(
            f"OpenAI authentication failed ({status}): {reason}",
            original_exception=exc,
        )
    transient = status >= 500
    return APIError(f"OpenAI HTTP {status}: {reason}", original_exception=exc, transient=transient)


def _make_urllib_transport(  # pragma: no cover
    timeout_seconds: float, api_key: str, organization: str | None = None
) -> _Transport:
    """Return an async HTTP transport using stdlib urllib on a thread-pool executor."""
    headers = _build_headers(api_key, organization)

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
                    f"OpenAI connection error: {exc.reason}",
                    original_exception=exc,
                    transient=True,
                ) from exc

        return await loop.run_in_executor(None, _do_request)

    return _post


class OpenAIProvider(BaseProvider):
    """LLM provider that calls the OpenAI Chat Completions API.

    Inherits timeout enforcement, retry with exponential backoff, and structured
    logging from :class:`~mas.llm.base.BaseProvider`.  Streaming is deferred to
    Phase 2 Issue 08.

    Generation parameters (``temperature``, ``top_p``, ``max_tokens``, …) are
    passed at the **top level** of the request body as the OpenAI API requires —
    not nested under an ``options`` or ``parameters`` sub-object.

    Args:
        config: OpenAI configuration. Must be an
            :class:`~mas.llm.config.OpenAIConfig` instance.
        _transport: Injectable async HTTP transport for testing.  When ``None``
            (default), a stdlib urllib transport is created automatically.

    Raises:
        ConfigError: If ``config`` is not an :class:`~mas.llm.config.OpenAIConfig`.
    """

    def __init__(
        self,
        config: OpenAIConfig,
        *,
        _transport: _Transport | None = None,
    ) -> None:
        self._injected_transport = _transport
        super().__init__(
            config,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        assert isinstance(self.config, OpenAIConfig)
        api_key = self.config.api_key
        assert api_key is not None
        self._transport: _Transport = (
            _transport
            if _transport is not None
            else _make_urllib_transport(
                self.timeout_seconds,
                api_key=api_key,
                organization=self.config.organization,
            )
        )

    # ------------------------------------------------------------------ #
    # LLMProvider abstract properties
    # ------------------------------------------------------------------ #

    @property
    def name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        assert isinstance(self.config, OpenAIConfig)
        return self.config.model

    # ------------------------------------------------------------------ #
    # BaseProvider abstract method
    # ------------------------------------------------------------------ #

    def validate_config(self, config: Any) -> bool:
        """Accept only :class:`~mas.llm.config.OpenAIConfig` instances."""
        return isinstance(config, OpenAIConfig)

    # ------------------------------------------------------------------ #
    # Provider-specific implementation
    # ------------------------------------------------------------------ #

    async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
        """POST to the OpenAI Chat Completions endpoint and return a response.

        Args:
            messages: Conversation history to send.
            model: Model identifier (e.g. ``"gpt-4o"``).
            **kwargs: Generation parameters (``temperature``, ``top_p``,
                ``max_tokens``, …) are forwarded at the **top level** of the
                request body as the OpenAI API requires.

        Returns:
            The model's response as an :class:`~mas.llm.contracts.LLMResponse`.

        Raises:
            APIError: On HTTP errors or unexpected response shapes.
            RateLimitError: On HTTP 429.
            AuthenticationError: On HTTP 401/403.
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            **kwargs,
        }

        start = time.monotonic()
        data = await self._transport(_OPENAI_CHAT_URL, payload)
        latency_ms = (time.monotonic() - start) * 1000.0

        choices = data.get("choices") or []
        if not choices:
            raise APIError(
                f"OpenAI returned no choices for model {model!r}",
                transient=False,
            )
        raw_content: str = (choices[0].get("message") or {}).get("content") or ""
        if not raw_content.strip():
            raise APIError(
                f"OpenAI returned empty content for model {model!r}",
                transient=False,
            )

        usage = data.get("usage") or {}
        tokens_used: int = usage.get("total_tokens") or 0
        returned_model: str = data.get("model") or model

        return LLMResponse(
            message=LLMMessage(role="assistant", content=raw_content),
            tokens_used=tokens_used,
            model=returned_model,
            latency_ms=latency_ms,
            metadata={
                "finish_reason": (choices[0].get("finish_reason")),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
            },
        )


# Self-register with the process-wide default registry so callers can use
# ``default_registry.from_config(OpenAIConfig(...))`` without manual setup.
from mas.llm.provider_registry import default_registry  # noqa: E402

default_registry.register("openai", OpenAIProvider, OpenAIConfig)
