"""Streaming support for LLM providers.

Defines the building blocks for streaming token-by-token output from LLM
providers:

- :class:`StreamChunk` — a single streamed token or final-message signal.
- :class:`StreamBuffer` — accumulates chunks into a complete text.
- :func:`parse_sse_line` — pure function that extracts the payload from a
  Server-Sent Events ``data:`` line (testable without I/O).
- :func:`stream_with_timeout` — wraps an async generator with a per-chunk
  deadline.
- :class:`StreamCollector` — async context manager that collects a stream
  transport into a :class:`StreamBuffer`.

The injectable :data:`_StreamTransport` type is the seam for testing: in
production it wraps a real HTTP SSE connection; in tests it yields pre-baked
strings directly.

No provider is wired up here — this module is provider-agnostic plumbing.
Provider-specific adapters (hooking ``_stream_transport`` into the actual
HTTP endpoints) belong in the individual provider modules.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any

from mas.llm.contracts import LLMMessage
from mas.llm.errors import APIError
from mas.llm.errors import TimeoutError as ProviderTimeoutError

#: Transport callable: takes (url, payload) and yields raw SSE lines or tokens.
_StreamTransport = Callable[[str, dict[str, Any]], AsyncGenerator[str, None]]


# ---------------------------------------------------------------------------
# StreamChunk
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StreamChunk:
    """A single unit of streamed output from an LLM provider.

    Attributes:
        token: The text fragment delivered in this chunk.
        is_final: ``True`` for the last chunk in a stream (may carry an empty
            ``token``).
        metadata: Optional provider-specific metadata (e.g. finish reason).
    """

    token: str
    is_final: bool = False
    metadata: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# StreamBuffer
# ---------------------------------------------------------------------------


class StreamBuffer:
    """Accumulates :class:`StreamChunk` objects into a complete text response.

    Thread-safety: not thread-safe. Designed for single-task async use.
    """

    def __init__(self) -> None:
        self._chunks: list[StreamChunk] = []
        self._is_complete: bool = False

    def append(self, chunk: StreamChunk) -> None:
        """Add a chunk to the buffer.

        Once a chunk with ``is_final=True`` is received the buffer is marked
        complete; subsequent appends are accepted but ignored in the
        completeness check.

        Args:
            chunk: The :class:`StreamChunk` to add.
        """
        self._chunks.append(chunk)
        if chunk.is_final:
            self._is_complete = True

    @property
    def chunks(self) -> list[StreamChunk]:
        """All chunks received so far, in order."""
        return list(self._chunks)

    @property
    def text(self) -> str:
        """Concatenation of all non-final chunk tokens."""
        return "".join(c.token for c in self._chunks if not c.is_final)

    @property
    def is_complete(self) -> bool:
        """Whether a final chunk has been received."""
        return self._is_complete

    def __len__(self) -> int:
        return len(self._chunks)


# ---------------------------------------------------------------------------
# SSE parsing
# ---------------------------------------------------------------------------


def parse_sse_line(line: str) -> str | None:
    """Extract the payload from a Server-Sent Events ``data:`` line.

    Handles the ``data: <payload>`` format used by OpenAI and Anthropic
    streaming APIs. Returns ``None`` for comment lines, keep-alive pings,
    and ``data: [DONE]`` sentinels.

    Args:
        line: A raw SSE line from the HTTP response body.

    Returns:
        The extracted payload string, or ``None`` if the line should be
        skipped.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith(":"):
        return None
    if not stripped.startswith("data:"):
        return None
    payload = stripped[len("data:"):].strip()
    if payload == "[DONE]":
        return None
    return payload


# ---------------------------------------------------------------------------
# stream_with_timeout
# ---------------------------------------------------------------------------


async def stream_with_timeout(
    stream: AsyncGenerator[str, None],
    timeout_seconds: float,
) -> AsyncGenerator[str, None]:
    """Wrap an async generator with a per-chunk timeout.

    Raises :class:`~mas.llm.errors.TimeoutError` if any single chunk takes
    longer than ``timeout_seconds`` to arrive.

    Args:
        stream: The source async generator.
        timeout_seconds: Maximum seconds to wait for each chunk.

    Yields:
        Each string item from ``stream``.

    Raises:
        ProviderTimeoutError: If any chunk exceeds the timeout.
        StopAsyncIteration: When ``stream`` is exhausted normally.
    """
    if timeout_seconds <= 0:
        raise ValueError(f"timeout_seconds must be > 0, got {timeout_seconds}")

    async def _inner() -> AsyncGenerator[str, None]:
        async for item in stream:
            yield item

    gen = _inner()
    try:
        while True:
            try:
                async with asyncio.timeout(timeout_seconds):
                    try:
                        item = await gen.__anext__()
                    except StopAsyncIteration:
                        return
                yield item
            except TimeoutError as exc:
                raise ProviderTimeoutError(
                    f"stream chunk timed out after {timeout_seconds}s",
                    original_exception=exc,
                ) from exc
    finally:
        await gen.aclose()


# ---------------------------------------------------------------------------
# StreamCollector
# ---------------------------------------------------------------------------


class StreamCollector:
    """Collect a :data:`_StreamTransport` stream into a :class:`StreamBuffer`.

    Usage::

        collector = StreamCollector(transport, url, payload)
        buffer = await collector.collect()
        print(buffer.text)

    The collector applies optional SSE line parsing when ``parse_sse=True``
    (the default). Set ``parse_sse=False`` for transports that already yield
    plain token strings.

    Args:
        transport: Async generator factory ``(url, payload) -> AsyncGen[str]``.
        url: URL to pass to the transport.
        payload: Request payload to pass to the transport.
        timeout_seconds: Per-chunk timeout. ``None`` disables per-chunk timeout.
        parse_sse: If ``True``, each yielded string is passed through
            :func:`parse_sse_line` before being treated as a token. Lines that
            return ``None`` are skipped.
    """

    def __init__(
        self,
        transport: _StreamTransport,
        url: str,
        payload: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
        parse_sse: bool = True,
    ) -> None:
        self._transport = transport
        self._url = url
        self._payload = payload
        self._timeout_seconds = timeout_seconds
        self._parse_sse = parse_sse

    async def collect(self) -> StreamBuffer:
        """Stream all chunks into a :class:`StreamBuffer` and return it.

        Returns:
            A :class:`StreamBuffer` containing all received chunks, with
            ``is_complete=True`` if the transport ended normally.

        Raises:
            APIError: If the transport raises an unexpected exception.
            ProviderTimeoutError: If a per-chunk timeout fires.
        """
        buffer = StreamBuffer()
        raw: AsyncGenerator[str, None] = self._transport(self._url, self._payload)
        source: AsyncGenerator[str, None] = (
            stream_with_timeout(raw, self._timeout_seconds)
            if self._timeout_seconds is not None
            else raw
        )

        try:
            async for line in source:
                token = self._extract(line)
                if token is not None:
                    buffer.append(StreamChunk(token=token))
        except ProviderTimeoutError:
            raise
        except Exception as exc:
            raise APIError(
                f"stream error: {exc}",
                original_exception=exc,
                transient=True,
            ) from exc
        buffer.append(StreamChunk(token="", is_final=True))
        return buffer

    def _extract(self, line: str) -> str | None:
        """Return the token from a raw transport line, or None to skip."""
        if self._parse_sse:
            return parse_sse_line(line)
        return line if line else None


# ---------------------------------------------------------------------------
# Helpers for building mock transports in tests
# ---------------------------------------------------------------------------


def make_token_transport(tokens: list[str]) -> _StreamTransport:
    """Return a mock :data:`_StreamTransport` that yields ``tokens`` directly.

    Useful in tests to verify streaming logic without real HTTP.

    Args:
        tokens: The token strings to yield, in order.

    Returns:
        A :data:`_StreamTransport` callable.
    """

    async def _t(url: str, payload: dict[str, Any]) -> AsyncGenerator[str, None]:
        for token in tokens:
            yield token

    return _t


def make_sse_transport(payloads: list[str]) -> _StreamTransport:
    """Return a mock :data:`_StreamTransport` that yields SSE-formatted lines.

    Each item in ``payloads`` is wrapped as ``data: <item>\\n``. A ``[DONE]``
    sentinel is appended automatically.

    Args:
        payloads: The raw payload strings to wrap in SSE format.

    Returns:
        A :data:`_StreamTransport` callable.
    """

    async def _t(url: str, payload: dict[str, Any]) -> AsyncGenerator[str, None]:
        for p in payloads:
            yield f"data: {p}"
        yield "data: [DONE]"

    return _t


def make_error_transport(error: Exception) -> _StreamTransport:
    """Return a mock :data:`_StreamTransport` that raises ``error`` immediately.

    Args:
        error: The exception to raise.

    Returns:
        A :data:`_StreamTransport` callable.
    """

    async def _t(url: str, payload: dict[str, Any]) -> AsyncGenerator[str, None]:
        raise error
        yield  # pragma: no cover — makes this an async generator

    return _t


def build_chat_payload(
    messages: list[LLMMessage],
    model: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Construct a streaming chat payload dict from messages and model.

    Args:
        messages: The conversation to include.
        model: The model identifier.
        **kwargs: Additional provider-specific fields (e.g. ``temperature``).

    Returns:
        A payload dict with ``model``, ``messages``, and ``stream: True``.
    """
    return {
        "model": model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "stream": True,
        **kwargs,
    }
