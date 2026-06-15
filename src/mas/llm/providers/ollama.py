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

#: Ollama ``/api/chat`` top-level fields; everything else belongs in ``options``.
_TOP_LEVEL_FIELDS = frozenset({"format", "keep_alive", "tools", "options", "stream"})


def _build_headers(api_key: str | None) -> dict[str, str]:
    """Return request headers, adding ``Authorization`` when an API key is configured."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
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
            f"Ollama rate limit: {reason}",
            original_exception=exc,
            retry_after_seconds=retry_after,
        )
    if status in (401, 403):
        return AuthenticationError(f"Ollama authentication failed ({status}): {reason}", original_exception=exc)
    transient = status >= 500
    return APIError(f"Ollama HTTP {status}: {reason}", original_exception=exc, transient=transient)


def _make_urllib_transport(timeout_seconds: float, api_key: str | None = None) -> _Transport:  # pragma: no cover
    """Return an async HTTP transport using stdlib urllib on a thread-pool executor."""
    headers = _build_headers(api_key)

    async def _post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        body = json.dumps(payload).encode()
        request = urllib.request.Request(url, data=body, headers=headers)

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
        super().__init__(
            config,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        assert isinstance(self.config, OllamaConfig)
        self._transport: _Transport = (
            _transport
            if _transport is not None
            else _make_urllib_transport(self.timeout_seconds, api_key=self.config.api_key)
        )

    # ------------------------------------------------------------------ #
    # LLMProvider abstract properties
    # ------------------------------------------------------------------ #

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return str(self.config.model)

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
            **kwargs: Generation parameters (``temperature``, ``top_p``, …) are
                nested under ``options`` as the Ollama API requires; the reserved
                top-level fields (``format``, ``keep_alive``, ``tools``,
                ``options``) are forwarded as-is.

        Returns:
            The model's response as an :class:`~mas.llm.contracts.LLMResponse`.

        Raises:
            APIError: On HTTP errors or an empty response from the API.
            RateLimitError: On HTTP 429.
            AuthenticationError: On HTTP 401/403.
        """
        config = self.config
        assert isinstance(config, OllamaConfig)

        # Merge caller-supplied options dict and route remaining kwargs:
        # known top-level fields stay at the top level; everything else is a
        # generation parameter and belongs inside the Ollama ``options`` object.
        options: dict[str, Any] = dict(kwargs.get("options") or {})
        top_level: dict[str, Any] = {}
        for key, val in kwargs.items():
            if key == "options":
                continue
            if key in _TOP_LEVEL_FIELDS:
                top_level[key] = val
            else:
                options[key] = val

        url = f"{config.base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            **top_level,
        }
        if options:
            payload["options"] = options

        start = time.monotonic()
        data = await self._transport(url, payload)
        latency_ms = (time.monotonic() - start) * 1000.0

        raw_msg = data.get("message") or {}
        raw_content: str = raw_msg.get("content") or ""
        if not raw_content.strip():
            raise APIError(
                f"Ollama returned empty content for model {model!r}",
                transient=True,
            )
        tokens_used = (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0)
        returned_model: str = data.get("model") or model

        return LLMResponse(
            message=LLMMessage(role="assistant", content=raw_content),
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
