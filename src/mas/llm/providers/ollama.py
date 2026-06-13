"""Ollama LLM provider — calls the local Ollama REST API.

Ollama runs models locally and exposes a simple HTTP interface. This provider
calls the ``/api/chat`` endpoint (non-streaming) and maps HTTP errors to the
:class:`~mas.llm.errors.LLMError` hierarchy.

No extra dependencies are required: HTTP is handled via stdlib ``urllib`` on a
thread-pool executor so ``asyncio.timeout`` (enforced by
:class:`~mas.llm.base.BaseProvider`) can cancel the call cleanly.

Usage::

    from mas.llm.providers.ollama import OllamaProvider
    from mas.llm.config import OllamaConfig
    from mas.llm.contracts import LLMMessage

    provider = OllamaProvider(OllamaConfig(model="llama2"))
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
from mas.llm.config import OllamaConfig
from mas.llm.contracts import LLMMessage, LLMResponse
from mas.llm.errors import APIError, AuthenticationError, RateLimitError

#: Type of the injectable HTTP transport.
_Transport = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


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
            f"Ollama rate limit: {reason}",
            original_exception=exc,
            retry_after_seconds=retry_after,
        )
    if status in (401, 403):
        return AuthenticationError(f"Ollama authentication failed ({status}): {reason}", original_exception=exc)
    transient = status >= 500
    return APIError(f"Ollama HTTP {status}: {reason}", original_exception=exc, transient=transient)


def _make_urllib_transport(timeout_seconds: float) -> _Transport:  # pragma: no cover
    """Return an async HTTP transport using stdlib urllib on a thread-pool executor."""

    async def _post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        body = json.dumps(payload).encode()
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
        )

        def _do_request() -> dict[str, Any]:
            try:
                with urllib.request.urlopen(request, timeout=timeout_seconds) as resp:  # noqa: S310
                    return json.loads(resp.read())  # type: ignore[no-any-return]
            except urllib.error.HTTPError as exc:
                raise _map_http_error(exc) from exc
            except urllib.error.URLError as exc:
                raise APIError(
                    f"Ollama connection error: {exc.reason}",
                    original_exception=exc,
                    transient=True,
                ) from exc

        return await loop.run_in_executor(None, _do_request)

    return _post


class OllamaProvider(BaseProvider):
    """LLM provider that calls a local Ollama server via its REST API.

    Inherits timeout enforcement, retry with exponential backoff, and structured
    logging from :class:`~mas.llm.base.BaseProvider`. Only non-streaming calls
    are supported; streaming is added in Phase 2 Issue 08.

    Args:
        config: Ollama configuration. Must be an :class:`~mas.llm.config.OllamaConfig`
            instance.
        _transport: Injectable async HTTP transport for testing. When ``None``
            (default), a stdlib urllib transport is created automatically after
            ``super().__init__()`` has set :attr:`~mas.llm.base.BaseProvider.timeout_seconds`.

    Raises:
        ConfigError: If ``config`` is not an :class:`~mas.llm.config.OllamaConfig`.
    """

    def __init__(
        self,
        config: OllamaConfig,
        *,
        _transport: _Transport | None = None,
    ) -> None:
        self._injected_transport = _transport
        super().__init__(config)
        self._transport: _Transport = (
            _transport if _transport is not None else _make_urllib_transport(self.timeout_seconds)
        )

    # ------------------------------------------------------------------ #
    # LLMProvider abstract properties
    # ------------------------------------------------------------------ #

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        assert isinstance(self.config, OllamaConfig)
        return self.config.model

    # ------------------------------------------------------------------ #
    # BaseProvider abstract method
    # ------------------------------------------------------------------ #

    def validate_config(self, config: Any) -> bool:
        """Accept only :class:`~mas.llm.config.OllamaConfig` instances."""
        return isinstance(config, OllamaConfig)

    # ------------------------------------------------------------------ #
    # Provider-specific implementation
    # ------------------------------------------------------------------ #

    async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
        """POST to the Ollama ``/api/chat`` endpoint and return a response.

        Args:
            messages: Conversation history to send.
            model: Model identifier (e.g. ``"llama2"``).
            **kwargs: Extra fields forwarded to the Ollama API payload.

        Returns:
            The model's response as an :class:`~mas.llm.contracts.LLMResponse`.

        Raises:
            APIError: On HTTP errors or an empty response from the API.
            RateLimitError: On HTTP 429.
            AuthenticationError: On HTTP 401/403.
        """
        config = self.config
        assert isinstance(config, OllamaConfig)

        url = f"{config.base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            **kwargs,
        }

        start = time.monotonic()
        data = await self._transport(url, payload)
        latency_ms = (time.monotonic() - start) * 1000.0

        raw_msg = data.get("message") or {}
        content: str = (raw_msg.get("content") or "").strip()
        if not content:
            raise APIError(
                f"Ollama returned empty content for model {model!r}",
                transient=False,
            )

        tokens_used = (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0)
        returned_model: str = data.get("model") or model

        return LLMResponse(
            message=LLMMessage(role="assistant", content=content),
            tokens_used=tokens_used,
            model=returned_model,
            latency_ms=latency_ms,
            metadata={
                "done": data.get("done", True),
                "total_duration": data.get("total_duration"),
            },
        )


# Self-register with the process-wide default registry so callers can use
# ``default_registry.from_config(OllamaConfig(...))`` without manual setup.
from mas.llm.provider_registry import default_registry  # noqa: E402

default_registry.register("ollama", OllamaProvider, OllamaConfig)
