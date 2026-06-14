"""HuggingFace Inference API LLM provider.

Calls the HuggingFace Inference API (``api-inference.huggingface.co``) for
text-generation and text2text tasks. Requires an API key.

No extra dependencies are required: HTTP is handled via stdlib ``urllib`` on a
thread-pool executor so ``asyncio.timeout`` (enforced by
:class:`~mas.llm.base.BaseProvider`) can cancel the call cleanly.

Usage::

    from mas.llm.providers.huggingface import HuggingFaceProvider
    from mas.llm.config import HuggingFaceConfig
    from mas.llm.contracts import LLMMessage

    provider = HuggingFaceProvider(
        HuggingFaceConfig(model="gpt2", api_key="hf-...")
    )
    response = await provider.call([LLMMessage(role="user", content="Hello")])
"""

import asyncio
import contextlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable
from typing import Any

from mas.llm.base import BaseProvider
from mas.llm.config import HuggingFaceConfig
from mas.llm.contracts import LLMMessage, LLMResponse
from mas.llm.errors import APIError, AuthenticationError, RateLimitError

#: Type of the injectable HTTP transport.
_Transport = Callable[[str, dict[str, Any]], Awaitable[Any]]

#: HuggingFace Inference API base URL.
_HF_API_BASE = "https://api-inference.huggingface.co/models"


def _build_headers(api_key: str) -> dict[str, str]:
    """Return request headers with ``Authorization: Bearer`` for the given API key."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def _format_prompt(messages: list[LLMMessage]) -> str:
    """Convert a message list to a plain-text prompt string for the Inference API."""
    return "\n".join(f"{m.role}: {m.content}" for m in messages)


def _map_http_error(
    exc: urllib.error.HTTPError,
    body: dict[str, Any] | None = None,
) -> APIError | RateLimitError | AuthenticationError:
    """Map an HTTP status code to the appropriate :class:`~mas.llm.errors.LLMError`.

    Args:
        exc: The ``urllib`` HTTP error.
        body: Optional parsed JSON body from the error response, used to extract
            model-loading metadata from 503 responses.
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
            f"HuggingFace rate limit: {reason}",
            original_exception=exc,
            retry_after_seconds=retry_after,
        )
    if status in (401, 403):
        return AuthenticationError(
            f"HuggingFace authentication failed ({status}): {reason}",
            original_exception=exc,
        )
    if status == 503:
        loading_info = ""
        if body and "estimated_time" in body:
            loading_info = f" (estimated_time={body['estimated_time']}s)"
        return APIError(
            f"HuggingFace model loading{loading_info}: {reason}",
            original_exception=exc,
            transient=True,
        )
    transient = status >= 500
    return APIError(
        f"HuggingFace HTTP {status}: {reason}",
        original_exception=exc,
        transient=transient,
    )


def _make_urllib_transport(timeout_seconds: float, api_key: str) -> _Transport:  # pragma: no cover
    """Return an async HTTP transport using stdlib urllib on a thread-pool executor."""
    headers = _build_headers(api_key)

    async def _post(url: str, payload: dict[str, Any]) -> Any:
        loop = asyncio.get_running_loop()
        data = json.dumps(payload).encode()
        request = urllib.request.Request(url, data=data, headers=headers)

        def _do_request() -> Any:
            try:
                with urllib.request.urlopen(request, timeout=timeout_seconds) as resp:  # noqa: S310
                    return json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                error_body: dict[str, Any] | None = None
                with contextlib.suppress(Exception):
                    error_body = json.loads(exc.read())
                raise _map_http_error(exc, error_body) from exc
            except urllib.error.URLError as exc:
                raise APIError(
                    f"HuggingFace connection error: {exc.reason}",
                    original_exception=exc,
                    transient=True,
                ) from exc

        return await loop.run_in_executor(None, _do_request)

    return _post


class HuggingFaceProvider(BaseProvider):
    """LLM provider that calls the HuggingFace Inference API.

    Supports ``text-generation`` and ``text2text`` tasks via the classic
    ``api-inference.huggingface.co`` endpoint. Requires an API key.

    Generation parameters (``temperature``, ``max_new_tokens``, …) are passed
    under the ``parameters`` sub-object as the Inference API requires. A caller
    may supply a ``parameters`` dict in ``kwargs``; any remaining keyword
    arguments are merged into it.

    Args:
        config: HuggingFace configuration. Must be a
            :class:`~mas.llm.config.HuggingFaceConfig` instance.
        _transport: Injectable async HTTP transport for testing. When ``None``
            (default), a stdlib urllib transport is created automatically.

    Raises:
        ConfigError: If ``config`` is not a
            :class:`~mas.llm.config.HuggingFaceConfig`.
    """

    def __init__(
        self,
        config: HuggingFaceConfig,
        *,
        _transport: _Transport | None = None,
    ) -> None:
        self._injected_transport = _transport
        super().__init__(
            config,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        assert isinstance(self.config, HuggingFaceConfig)
        api_key = self.config.api_key
        assert api_key is not None
        self._transport: _Transport = (
            _transport
            if _transport is not None
            else _make_urllib_transport(self.timeout_seconds, api_key=api_key)
        )

    # ------------------------------------------------------------------ #
    # LLMProvider abstract properties
    # ------------------------------------------------------------------ #

    @property
    def name(self) -> str:
        return "huggingface"

    @property
    def default_model(self) -> str:
        assert isinstance(self.config, HuggingFaceConfig)
        return self.config.model

    # ------------------------------------------------------------------ #
    # BaseProvider abstract method
    # ------------------------------------------------------------------ #

    def validate_config(self, config: Any) -> bool:
        """Accept only :class:`~mas.llm.config.HuggingFaceConfig` instances."""
        return isinstance(config, HuggingFaceConfig)

    # ------------------------------------------------------------------ #
    # Provider-specific implementation
    # ------------------------------------------------------------------ #

    async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
        """POST to the HuggingFace Inference API and return a response.

        Args:
            messages: Conversation history, formatted as a plain-text prompt.
            model: Model identifier (e.g. ``"gpt2"``).
            **kwargs: Generation parameters (``temperature``, ``max_new_tokens``,
                …) are nested under ``parameters`` as the Inference API requires.
                A caller-supplied ``parameters`` dict is merged with remaining
                keyword arguments.

        Returns:
            The model's response as an :class:`~mas.llm.contracts.LLMResponse`.

        Raises:
            APIError: On HTTP errors, unexpected response shapes, or empty content.
            RateLimitError: On HTTP 429.
            AuthenticationError: On HTTP 401/403.
        """
        config = self.config
        assert isinstance(config, HuggingFaceConfig)

        # Merge caller-supplied parameters dict with remaining kwargs.
        parameters: dict[str, Any] = dict(kwargs.get("parameters") or {})
        for key, val in kwargs.items():
            if key != "parameters":
                parameters[key] = val

        # text-generation models echo the prompt unless told otherwise.
        if config.task == "text-generation":
            parameters.setdefault("return_full_text", False)

        url = f"{_HF_API_BASE}/{model}"
        payload: dict[str, Any] = {"inputs": _format_prompt(messages)}
        if parameters:
            payload["parameters"] = parameters

        start = time.monotonic()
        data = await self._transport(url, payload)
        latency_ms = (time.monotonic() - start) * 1000.0

        if not isinstance(data, list) or not data:
            raise APIError(
                f"HuggingFace returned unexpected response format for model {model!r}",
                transient=False,
            )
        raw_content: str = data[0].get("generated_text") or ""
        if not raw_content.strip():
            raise APIError(
                f"HuggingFace returned empty content for model {model!r}",
                transient=False,
            )
        content = raw_content

        return LLMResponse(
            message=LLMMessage(role="assistant", content=content),
            tokens_used=0,
            model=model,
            latency_ms=latency_ms,
            metadata={"task": config.task},
        )


# Self-register with the process-wide default registry so callers can use
# ``default_registry.from_config(HuggingFaceConfig(...))`` without manual setup.
from mas.llm.provider_registry import default_registry  # noqa: E402

default_registry.register("huggingface", HuggingFaceProvider, HuggingFaceConfig)
