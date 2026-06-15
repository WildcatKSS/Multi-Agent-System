"""Tests for mas.llm.streaming."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest

from mas.llm.contracts import LLMMessage
from mas.llm.errors import APIError, TimeoutError as ProviderTimeoutError
from mas.llm.streaming import (
    StreamBuffer,
    StreamChunk,
    StreamCollector,
    _StreamTransport,
    build_chat_payload,
    make_error_transport,
    make_sse_transport,
    make_token_transport,
    parse_sse_line,
    stream_with_timeout,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _msg(content: str) -> LLMMessage:
    return LLMMessage(role="user", content=content)


async def _collect_gen(gen: AsyncGenerator[str, None]) -> list[str]:
    return [item async for item in gen]


# ---------------------------------------------------------------------------
# StreamChunk
# ---------------------------------------------------------------------------


class TestStreamChunk:
    def test_defaults(self) -> None:
        c = StreamChunk(token="hi")
        assert c.token == "hi"
        assert c.is_final is False
        assert c.metadata is None

    def test_final_chunk(self) -> None:
        c = StreamChunk(token="", is_final=True)
        assert c.is_final is True

    def test_metadata(self) -> None:
        c = StreamChunk(token="x", metadata={"finish_reason": "stop"})
        assert c.metadata == {"finish_reason": "stop"}

    def test_frozen(self) -> None:
        c = StreamChunk(token="hi")
        with pytest.raises(Exception):
            c.token = "bye"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# StreamBuffer
# ---------------------------------------------------------------------------


class TestStreamBuffer:
    def test_empty_buffer(self) -> None:
        buf = StreamBuffer()
        assert buf.text == ""
        assert buf.is_complete is False
        assert len(buf) == 0
        assert buf.chunks == []

    def test_append_chunk(self) -> None:
        buf = StreamBuffer()
        buf.append(StreamChunk(token="hello"))
        assert len(buf) == 1
        assert buf.text == "hello"

    def test_text_concatenates_tokens(self) -> None:
        buf = StreamBuffer()
        buf.append(StreamChunk(token="Hello"))
        buf.append(StreamChunk(token=", "))
        buf.append(StreamChunk(token="world"))
        assert buf.text == "Hello, world"

    def test_final_chunk_marks_complete(self) -> None:
        buf = StreamBuffer()
        buf.append(StreamChunk(token="hi"))
        assert buf.is_complete is False
        buf.append(StreamChunk(token="", is_final=True))
        assert buf.is_complete is True

    def test_final_chunk_token_excluded_from_text(self) -> None:
        buf = StreamBuffer()
        buf.append(StreamChunk(token="hi"))
        buf.append(StreamChunk(token="", is_final=True))
        assert buf.text == "hi"

    def test_chunks_returns_copy(self) -> None:
        buf = StreamBuffer()
        buf.append(StreamChunk(token="x"))
        copy = buf.chunks
        copy.clear()
        assert len(buf) == 1

    def test_append_after_final_still_works(self) -> None:
        buf = StreamBuffer()
        buf.append(StreamChunk(token="a", is_final=True))
        buf.append(StreamChunk(token="b"))
        assert len(buf) == 2
        assert buf.is_complete is True


# ---------------------------------------------------------------------------
# parse_sse_line
# ---------------------------------------------------------------------------


class TestParseSSELine:
    def test_valid_data_line(self) -> None:
        assert parse_sse_line('data: {"token":"hi"}') == '{"token":"hi"}'

    def test_done_sentinel_returns_none(self) -> None:
        assert parse_sse_line("data: [DONE]") is None

    def test_empty_line_returns_none(self) -> None:
        assert parse_sse_line("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert parse_sse_line("   ") is None

    def test_comment_line_returns_none(self) -> None:
        assert parse_sse_line(": keep-alive") is None

    def test_non_data_line_returns_none(self) -> None:
        assert parse_sse_line("event: message") is None

    def test_data_with_leading_space(self) -> None:
        assert parse_sse_line("data:  hello") == "hello"

    def test_data_with_surrounding_whitespace(self) -> None:
        result = parse_sse_line("  data: hello  ")
        assert result == "hello"

    def test_data_colon_only(self) -> None:
        result = parse_sse_line("data:")
        assert result == ""

    def test_plain_string_without_prefix_returns_none(self) -> None:
        assert parse_sse_line("just some text") is None


# ---------------------------------------------------------------------------
# stream_with_timeout
# ---------------------------------------------------------------------------


class TestStreamWithTimeout:
    def test_yields_items_normally(self) -> None:
        async def _gen() -> AsyncGenerator[str, None]:
            for t in ["a", "b", "c"]:
                yield t

        result = _run(_collect_gen(stream_with_timeout(_gen(), timeout_seconds=5.0)))
        assert result == ["a", "b", "c"]

    def test_empty_stream(self) -> None:
        async def _empty() -> AsyncGenerator[str, None]:
            return
            yield  # pragma: no cover

        result = _run(_collect_gen(stream_with_timeout(_empty(), timeout_seconds=5.0)))
        assert result == []

    def test_negative_timeout_raises_value_error(self) -> None:
        async def _gen() -> AsyncGenerator[str, None]:
            yield "x"

        with pytest.raises(ValueError, match="timeout_seconds"):
            _run(_collect_gen(stream_with_timeout(_gen(), timeout_seconds=-1.0)))

    def test_zero_timeout_raises_value_error(self) -> None:
        async def _gen() -> AsyncGenerator[str, None]:
            yield "x"

        with pytest.raises(ValueError, match="timeout_seconds"):
            _run(_collect_gen(stream_with_timeout(_gen(), timeout_seconds=0.0)))

    def test_timeout_raises_provider_timeout_error(self) -> None:
        async def _slow() -> AsyncGenerator[str, None]:
            yield "first"
            await asyncio.sleep(10.0)
            yield "second"  # pragma: no cover

        with pytest.raises(ProviderTimeoutError):
            _run(_collect_gen(stream_with_timeout(_slow(), timeout_seconds=0.001)))


# ---------------------------------------------------------------------------
# make_token_transport / make_sse_transport / make_error_transport
# ---------------------------------------------------------------------------


class TestTransportHelpers:
    def test_make_token_transport_yields_tokens(self) -> None:
        t = make_token_transport(["a", "b", "c"])
        result = _run(_collect_gen(t("url", {})))
        assert result == ["a", "b", "c"]

    def test_make_token_transport_empty(self) -> None:
        t = make_token_transport([])
        result = _run(_collect_gen(t("url", {})))
        assert result == []

    def test_make_sse_transport_wraps_in_data_lines(self) -> None:
        t = make_sse_transport(["hello", "world"])
        result = _run(_collect_gen(t("url", {})))
        assert result[0] == "data: hello"
        assert result[1] == "data: world"
        assert result[-1] == "data: [DONE]"

    def test_make_error_transport_raises(self) -> None:
        t = make_error_transport(APIError("test error", transient=False))
        with pytest.raises(APIError):
            _run(_collect_gen(t("url", {})))


# ---------------------------------------------------------------------------
# StreamCollector
# ---------------------------------------------------------------------------


class TestStreamCollector:
    def test_collects_plain_tokens(self) -> None:
        t = make_token_transport(["Hello", " world"])
        collector = StreamCollector(t, "url", {}, parse_sse=False)
        buffer = _run(collector.collect())
        assert buffer.text == "Hello world"
        assert buffer.is_complete is True

    def test_collects_sse_tokens(self) -> None:
        t = make_sse_transport(["Hello", "world"])
        collector = StreamCollector(t, "url", {}, parse_sse=True)
        buffer = _run(collector.collect())
        assert buffer.text == "Helloworld"
        assert buffer.is_complete is True

    def test_done_sentinel_not_included_in_text(self) -> None:
        t = make_sse_transport(["token"])
        collector = StreamCollector(t, "url", {}, parse_sse=True)
        buffer = _run(collector.collect())
        # [DONE] is filtered by parse_sse_line; only "token" appears
        assert "DONE" not in buffer.text

    def test_empty_stream_results_in_complete_empty_buffer(self) -> None:
        t = make_token_transport([])
        collector = StreamCollector(t, "url", {}, parse_sse=False)
        buffer = _run(collector.collect())
        assert buffer.text == ""
        assert buffer.is_complete is True

    def test_transport_error_raises_api_error(self) -> None:
        t = make_error_transport(RuntimeError("network failure"))
        collector = StreamCollector(t, "url", {}, parse_sse=False)
        with pytest.raises(APIError):
            _run(collector.collect())

    def test_empty_token_lines_skipped_when_parse_sse_false(self) -> None:
        t = make_token_transport(["", "hi", ""])
        collector = StreamCollector(t, "url", {}, parse_sse=False)
        buffer = _run(collector.collect())
        assert buffer.text == "hi"

    def test_timeout_propagated_from_stream(self) -> None:
        async def _slow_transport(url: str, payload: dict[str, Any]) -> AsyncGenerator[str, None]:
            yield "first"
            await asyncio.sleep(10.0)
            yield "never"  # pragma: no cover

        collector = StreamCollector(
            _slow_transport, "url", {}, timeout_seconds=0.001, parse_sse=False
        )
        with pytest.raises(ProviderTimeoutError):
            _run(collector.collect())

    def test_no_timeout_when_none(self) -> None:
        t = make_token_transport(["a", "b"])
        collector = StreamCollector(t, "url", {}, timeout_seconds=None, parse_sse=False)
        buffer = _run(collector.collect())
        assert buffer.text == "ab"


# ---------------------------------------------------------------------------
# build_chat_payload
# ---------------------------------------------------------------------------


class TestBuildChatPayload:
    def test_basic_payload(self) -> None:
        msgs = [_msg("Hello")]
        payload = build_chat_payload(msgs, "gpt-4o")
        assert payload["model"] == "gpt-4o"
        assert payload["stream"] is True
        assert payload["messages"] == [{"role": "user", "content": "Hello"}]

    def test_extra_kwargs_included(self) -> None:
        msgs = [_msg("Hi")]
        payload = build_chat_payload(msgs, "claude-3", temperature=0.7)
        assert payload["temperature"] == 0.7

    def test_multiple_messages(self) -> None:
        msgs = [
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="user", content="Hello"),
        ]
        payload = build_chat_payload(msgs, "gpt-4o")
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
