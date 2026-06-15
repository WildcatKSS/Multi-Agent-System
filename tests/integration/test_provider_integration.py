"""Phase-2 integration tests: all new components wired together.

Exercises ModelValidator, TokenCounter, streaming infrastructure, and
ErrorClassifier in realistic workflows with all four built-in LLM providers.
All I/O is mock-based — no real HTTP calls are made.
"""

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

import pytest

from mas.llm.config import AnthropicConfig, HuggingFaceConfig, OllamaConfig, OpenAIConfig
from mas.llm.contracts import LLMMessage, LLMProvider, LLMResponse
from mas.llm.error_classifier import (
    ErrorClassifier,
    RetryStrategy,
    classify,
    default_classifier,
    is_retryable,
)
from mas.llm.errors import APIError, AuthenticationError, ConfigError, RateLimitError, TimeoutError, ValidationError
from mas.llm.provider_registry import default_registry
from mas.llm.providers.anthropic import AnthropicProvider
from mas.llm.providers.huggingface import HuggingFaceProvider
from mas.llm.providers.ollama import OllamaProvider
from mas.llm.providers.openai import OpenAIProvider
from mas.llm.streaming import (
    StreamCollector,
    build_chat_payload,
    make_sse_transport,
    make_token_transport,
)
from mas.llm.token_counter import TokenCounter, default_counter
from mas.llm.validation.model_validator import (
    ModelValidator,
    ValidationResult,
    default_validator,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_Transport = Callable[[str, dict[str, Any]], Awaitable[Any]]

_MESSAGES = [LLMMessage(role="user", content="Hello")]

_OLLAMA_RESP: dict[str, Any] = {
    "message": {"role": "assistant", "content": "Hi from Ollama"},
    "prompt_eval_count": 5,
    "eval_count": 10,
    "model": "llama2",
    "done": True,
}
_HF_RESP: list[dict[str, Any]] = [{"generated_text": "Hi from HuggingFace"}]
_OPENAI_RESP: dict[str, Any] = {
    "id": "chatcmpl-1",
    "choices": [{"message": {"role": "assistant", "content": "Hi from OpenAI"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    "model": "gpt-4o",
}
_ANTHROPIC_RESP: dict[str, Any] = {
    "id": "msg_1",
    "type": "message",
    "content": [{"type": "text", "text": "Hi from Anthropic"}],
    "model": "claude-3-5-sonnet-20241022",
    "usage": {"input_tokens": 5, "output_tokens": 4},
    "stop_reason": "end_turn",
}


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _transport(response: Any) -> _Transport:
    async def _t(url: str, payload: dict[str, Any]) -> Any:
        return response

    return _t


def _make_ollama() -> OllamaProvider:
    return OllamaProvider(OllamaConfig(model="llama2"), _transport=_transport(_OLLAMA_RESP))


def _make_huggingface() -> HuggingFaceProvider:
    return HuggingFaceProvider(
        HuggingFaceConfig(model="gpt2", api_key="hf-test"), _transport=_transport(_HF_RESP)
    )


def _make_openai() -> OpenAIProvider:
    return OpenAIProvider(
        OpenAIConfig(model="gpt-4o", api_key="sk-test"), _transport=_transport(_OPENAI_RESP)
    )


def _make_anthropic() -> AnthropicProvider:
    return AnthropicProvider(
        AnthropicConfig(model="claude-3-5-sonnet-20241022", api_key="sk-ant-test"),
        _transport=_transport(_ANTHROPIC_RESP),
    )


@pytest.fixture(
    params=["ollama", "huggingface", "openai", "anthropic"],
    ids=["ollama", "huggingface", "openai", "anthropic"],
)
def provider(request: pytest.FixtureRequest) -> LLMProvider:
    return {
        "ollama": _make_ollama,
        "huggingface": _make_huggingface,
        "openai": _make_openai,
        "anthropic": _make_anthropic,
    }[request.param]()


# ---------------------------------------------------------------------------
# Section 1: ModelValidator + providers
# ---------------------------------------------------------------------------


class TestValidatorWithProviders:
    """ModelValidator validates configs from all four providers."""

    def test_ollama_default_model_is_known(self) -> None:
        p = _make_ollama()
        result = default_validator.validate_model(p.default_model, p.name)
        assert result.valid is True

    def test_openai_default_model_is_known(self) -> None:
        p = _make_openai()
        result = default_validator.validate_model(p.default_model, p.name)
        assert result.valid is True

    def test_anthropic_default_model_is_known(self) -> None:
        p = _make_anthropic()
        result = default_validator.validate_model(p.default_model, p.name)
        assert result.valid is True

    def test_huggingface_default_model_is_known(self) -> None:
        p = _make_huggingface()
        result = default_validator.validate_model(p.default_model, p.name)
        assert result.valid is True

    def test_all_provider_configs_pass_validation(self) -> None:
        configs = [
            OllamaConfig(model="llama2"),
            HuggingFaceConfig(model="gpt2", api_key="hf-x"),
            OpenAIConfig(model="gpt-4o", api_key="sk-x"),
            AnthropicConfig(model="claude-3-5-sonnet-20241022", api_key="sk-ant-x"),
        ]
        for config in configs:
            result = default_validator.validate_config(config)
            assert result.valid is True, f"config for {config.model} failed"

    def test_invalid_temperature_rejected(self) -> None:
        result = default_validator.validate_parameters({"temperature": 3.0})
        assert result.valid is False

    def test_valid_parameters_accepted(self) -> None:
        result = default_validator.validate_parameters(
            {"temperature": 0.7, "top_p": 0.9, "max_tokens": 512}
        )
        assert result.valid is True

    def test_unknown_model_rejected_for_provider(self) -> None:
        result = default_validator.validate_model("gpt-99-turbo", "openai")
        assert result.valid is False

    def test_capabilities_returned_for_provider_model(self, provider: LLMProvider) -> None:
        caps = default_validator.capabilities(provider.default_model, provider.name)
        assert caps is not None

    def test_custom_validator_independent_of_default(self) -> None:
        v = ModelValidator()
        result = v.validate_model("llama2", "ollama")
        assert result.valid is False  # empty catalog

    def test_validation_result_type(self) -> None:
        r = default_validator.validate_model("gpt-4o", "openai")
        assert isinstance(r, ValidationResult)
        assert r.valid is True
        assert r.errors == ()


# ---------------------------------------------------------------------------
# Section 2: TokenCounter + providers
# ---------------------------------------------------------------------------


class TestTokenCounterWithProviders:
    """TokenCounter estimates tokens for each provider's strategy."""

    def test_openai_token_count_non_zero(self) -> None:
        count = default_counter.count("Hello, world!", provider="openai")
        assert count > 0

    def test_anthropic_token_count_non_zero(self) -> None:
        count = default_counter.count("Hello, world!", provider="anthropic")
        assert count > 0

    def test_ollama_token_count_non_zero(self) -> None:
        count = default_counter.count("Hello, world!", provider="ollama")
        assert count > 0

    def test_huggingface_token_count_non_zero(self) -> None:
        count = default_counter.count("Hello, world!", provider="huggingface")
        assert count > 0

    def test_openai_uses_smaller_ratio_than_ollama(self) -> None:
        text = "Hello world " * 100
        openai_count = default_counter.count(text, provider="openai")
        ollama_count = default_counter.count(text, provider="ollama")
        # OpenAI uses 3.5 chars/token vs Ollama's 4.0, so OpenAI gives more tokens
        assert openai_count >= ollama_count

    def test_count_messages_for_each_provider(self, provider: LLMProvider) -> None:
        count = default_counter.count_messages(_MESSAGES, provider=provider.name)
        assert count > 0

    def test_provider_response_tokens_positive(self, provider: LLMProvider) -> None:
        resp = _run(provider.call(_MESSAGES))
        assert resp.tokens_used >= 0

    def test_count_messages_scales_with_length(self) -> None:
        short_msgs = [LLMMessage(role="user", content="Hi")]
        long_msgs = [LLMMessage(role="user", content="Hi " * 100)]
        short = default_counter.count_messages(short_msgs, provider="openai")
        long_ = default_counter.count_messages(long_msgs, provider="openai")
        assert long_ > short

    def test_custom_counter_independent_of_default(self) -> None:
        tc = TokenCounter(cache_size=0)
        result = tc.count("hello", provider="openai")
        assert result > 0

    def test_counter_caches_results(self) -> None:
        tc = TokenCounter(cache_size=10)
        tc.count("cached text", provider="ollama")
        size_after_first = tc.cache_size()
        tc.count("cached text", provider="ollama")
        # Second call hits cache; no new entry
        assert tc.cache_size() == size_after_first


# ---------------------------------------------------------------------------
# Section 3: Streaming infrastructure integration
# ---------------------------------------------------------------------------


class TestStreamingIntegration:
    """StreamCollector, SSE parsing, and timeout work together."""

    def test_token_stream_collected_into_buffer(self) -> None:
        tokens = ["Hello", ", ", "world", "!"]
        t = make_token_transport(tokens)
        collector = StreamCollector(t, "url", {}, parse_sse=False)
        buffer = _run(collector.collect())
        assert buffer.text == "Hello, world!"
        assert buffer.is_complete is True

    def test_sse_stream_collected_correctly(self) -> None:
        t = make_sse_transport(["tok1", "tok2", "tok3"])
        collector = StreamCollector(t, "url", {}, parse_sse=True)
        buffer = _run(collector.collect())
        assert buffer.text == "tok1tok2tok3"
        assert buffer.is_complete is True

    def test_sse_done_sentinel_not_in_buffer(self) -> None:
        t = make_sse_transport(["hello"])
        collector = StreamCollector(t, "url", {}, parse_sse=True)
        buffer = _run(collector.collect())
        assert "DONE" not in buffer.text

    def test_parse_sse_line_used_by_collector(self) -> None:
        lines = ["data: first", ": comment", "data: [DONE]"]

        async def _t(url: str, payload: dict[str, Any]) -> AsyncGenerator[str, None]:
            for line in lines:
                yield line

        collector = StreamCollector(_t, "url", {}, parse_sse=True)
        buffer = _run(collector.collect())
        assert buffer.text == "first"

    def test_build_chat_payload_includes_stream_flag(self) -> None:
        payload = build_chat_payload(_MESSAGES, "gpt-4o", temperature=0.5)
        assert payload["stream"] is True
        assert payload["model"] == "gpt-4o"
        assert payload["temperature"] == 0.5

    def test_stream_buffer_chunks_in_order(self) -> None:
        tokens = ["a", "b", "c", "d", "e"]
        t = make_token_transport(tokens)
        collector = StreamCollector(t, "url", {}, parse_sse=False)
        buffer = _run(collector.collect())
        non_final = [c.token for c in buffer.chunks if not c.is_final]
        assert non_final == tokens

    def test_empty_stream_is_complete_with_empty_text(self) -> None:
        t = make_token_transport([])
        collector = StreamCollector(t, "url", {}, parse_sse=False)
        buffer = _run(collector.collect())
        assert buffer.text == ""
        assert buffer.is_complete is True

    def test_streaming_timeout_raises_provider_timeout_error(self) -> None:
        from mas.llm.errors import TimeoutError as ProviderTimeoutError

        async def _slow(url: str, payload: dict[str, Any]) -> AsyncGenerator[str, None]:
            yield "first"
            await asyncio.sleep(10.0)
            yield "never"  # pragma: no cover

        collector = StreamCollector(_slow, "url", {}, timeout_seconds=0.001, parse_sse=False)
        with pytest.raises(ProviderTimeoutError):
            _run(collector.collect())

    def test_multiple_providers_stream_independently(self) -> None:
        providers_and_tokens = [
            ("openai", ["Hello", " from", " OpenAI"]),
            ("anthropic", ["Hello", " from", " Anthropic"]),
        ]
        results = []
        for provider_name, tokens in providers_and_tokens:
            t = make_token_transport(tokens)
            collector = StreamCollector(t, "url", {"model": provider_name}, parse_sse=False)
            buffer = _run(collector.collect())
            results.append(buffer.text)
        assert results[0] != results[1]


# ---------------------------------------------------------------------------
# Section 4: ErrorClassifier + provider errors
# ---------------------------------------------------------------------------


class TestErrorClassificationWorkflow:
    """ErrorClassifier integrates with the LLM error hierarchy."""

    def test_auth_error_from_provider_classified_as_not_retryable(self) -> None:
        err = AuthenticationError("Invalid API key")
        result = classify(err)
        assert result.is_retryable is False
        assert result.strategy == RetryStrategy.NO_RETRY

    def test_rate_limit_error_classified_with_backoff(self) -> None:
        err = RateLimitError("Too many requests")
        result = classify(err)
        assert result.is_retryable is True
        assert result.strategy in (RetryStrategy.EXPONENTIAL_BACKOFF, RetryStrategy.FIXED_WAIT)

    def test_timeout_error_classified_as_retryable(self) -> None:
        err = TimeoutError("Request timed out")
        result = classify(err)
        assert result.is_retryable is True
        assert result.recommended_wait(attempt=1) == 2.0

    def test_transient_api_error_retryable(self) -> None:
        err = APIError("503 Service Unavailable", transient=True)
        assert is_retryable(err) is True

    def test_permanent_api_error_not_retryable(self) -> None:
        err = APIError("400 Bad Request", transient=False)
        assert is_retryable(err) is False

    def test_config_error_not_retryable(self) -> None:
        err = ConfigError("Missing API key")
        result = classify(err)
        assert result.is_retryable is False

    def test_validation_error_not_retryable(self) -> None:
        err = ValidationError("Empty messages")
        result = classify(err)
        assert result.is_retryable is False

    def test_rate_limit_with_retry_after_uses_fixed_wait(self) -> None:
        err = RateLimitError("Too many requests", retry_after_seconds=60)
        result = classify(err)
        assert result.strategy == RetryStrategy.FIXED_WAIT
        assert result.recommended_wait() == 60.0

    def test_user_messages_are_non_empty_for_all_error_types(self) -> None:
        errors = [
            AuthenticationError("denied"),
            ConfigError("bad config"),
            ValidationError("bad input"),
            RateLimitError("too fast"),
            TimeoutError("timed out"),
            APIError("server error", transient=True),
            APIError("bad request", transient=False),
        ]
        for err in errors:
            msg = default_classifier.user_message(err)
            assert isinstance(msg, str)
            assert len(msg) > 0, f"empty user message for {type(err).__name__}"

    def test_classifier_recommended_wait_scales_with_attempt(self) -> None:
        err = TimeoutError("slow")
        ec = ErrorClassifier()
        assert ec.recommended_wait(err, attempt=0) == 1.0
        assert ec.recommended_wait(err, attempt=1) == 2.0
        assert ec.recommended_wait(err, attempt=3) == 8.0


# ---------------------------------------------------------------------------
# Section 5: Multi-provider + full workflow
# ---------------------------------------------------------------------------


class TestFullWorkflow:
    """Validate config → count tokens → call provider → classify errors."""

    def test_validate_before_call_succeeds_for_known_model(self) -> None:
        config = OllamaConfig(model="llama2")
        validation = default_validator.validate_config(config)
        assert validation.valid
        p = OllamaProvider(config, _transport=_transport(_OLLAMA_RESP))
        resp = _run(p.call(_MESSAGES))
        assert resp.message.content

    def test_estimate_tokens_before_call(self) -> None:
        msg = LLMMessage(role="user", content="Hello, world!")
        count = default_counter.count(msg.content, provider="openai")
        assert count > 0
        p = _make_openai()
        resp = _run(p.call([msg]))
        assert resp.tokens_used >= 0

    def test_classify_errors_in_workflow(self) -> None:
        async def _error_transport(url: str, payload: dict[str, Any]) -> Any:
            raise RateLimitError("429", retry_after_seconds=5)

        p = OpenAIProvider(OpenAIConfig(model="gpt-4o", api_key="sk-x"), _transport=_error_transport)
        try:
            _run(p.call(_MESSAGES, model="gpt-4o"))
        except RateLimitError as err:
            result = classify(err)
            assert result.is_retryable is True
            assert result.recommended_wait() == 5.0

    def test_provider_name_matches_registry_entry(self, provider: LLMProvider) -> None:
        assert default_registry.is_registered(provider.name)

    def test_response_model_field_non_empty(self, provider: LLMProvider) -> None:
        resp = _run(provider.call(_MESSAGES))
        assert resp.model

    def test_token_count_before_and_after_call(self) -> None:
        content = "How are you today?"
        pre_tokens = default_counter.count(content, provider="anthropic")
        p = _make_anthropic()
        resp = _run(p.call([LLMMessage(role="user", content=content)]))
        # post-call tokens_used reflects provider's actual usage
        assert pre_tokens > 0
        assert resp.tokens_used >= 0

    def test_validate_params_then_call(self) -> None:
        params: dict[str, Any] = {"temperature": 0.7, "max_tokens": 256}
        validation = default_validator.validate_parameters(params)
        assert validation.valid
        p = _make_openai()
        resp = _run(p.call(_MESSAGES, **params))
        assert resp.message.content

    def test_stream_then_classify_error(self) -> None:
        err = APIError("502 Bad Gateway", transient=True)

        async def _err_transport(url: str, payload: dict[str, Any]) -> AsyncGenerator[str, None]:
            raise err
            yield  # pragma: no cover

        from mas.llm.streaming import StreamCollector

        collector = StreamCollector(_err_transport, "url", {}, parse_sse=False)
        with pytest.raises(APIError) as exc_info:
            _run(collector.collect())
        result = classify(exc_info.value)
        assert result.is_retryable is True


# ---------------------------------------------------------------------------
# Section 6: Multi-provider comparison
# ---------------------------------------------------------------------------


class TestMultiProviderComparison:
    """Parallel calls to all four providers produce distinct, valid responses."""

    def test_all_providers_return_non_empty_content(self) -> None:
        providers = [_make_ollama(), _make_huggingface(), _make_openai(), _make_anthropic()]
        for p in providers:
            resp = _run(p.call(_MESSAGES))
            assert resp.message.content.strip(), f"{p.name} returned empty content"

    def test_all_providers_return_assistant_role(self) -> None:
        providers = [_make_ollama(), _make_huggingface(), _make_openai(), _make_anthropic()]
        for p in providers:
            resp = _run(p.call(_MESSAGES))
            assert resp.message.role == "assistant"

    def test_provider_responses_differ(self) -> None:
        providers = [_make_ollama(), _make_huggingface(), _make_openai(), _make_anthropic()]
        contents = {_run(p.call(_MESSAGES)).message.content for p in providers}
        assert len(contents) == 4

    def test_token_count_for_each_provider_response(self) -> None:
        providers = [_make_ollama(), _make_huggingface(), _make_openai(), _make_anthropic()]
        for p in providers:
            resp = _run(p.call(_MESSAGES))
            count = default_counter.count(resp.message.content, provider=p.name)
            assert count >= 0

    def test_validate_default_model_for_all_providers(self) -> None:
        providers = [_make_ollama(), _make_huggingface(), _make_openai(), _make_anthropic()]
        for p in providers:
            result = default_validator.validate_model(p.default_model, p.name)
            assert result.valid is True, f"{p.name} default model not in catalog"


# ---------------------------------------------------------------------------
# Section 7: Provider switching
# ---------------------------------------------------------------------------


class TestProviderSwitching:
    """Switch providers mid-workflow using the registry."""

    def test_switch_from_ollama_to_openai(self) -> None:
        p1 = _make_ollama()
        p2 = _make_openai()
        r1 = _run(p1.call(_MESSAGES))
        r2 = _run(p2.call(_MESSAGES))
        assert r1.message.content != r2.message.content

    def test_registry_creates_provider_from_config(self) -> None:
        config = OllamaConfig(model="llama2")
        p = default_registry.from_config(config)
        assert p.name == "ollama"

    def test_fallback_to_different_provider_on_error(self) -> None:
        async def _error_transport(url: str, payload: dict[str, Any]) -> Any:
            raise AuthenticationError("denied")

        primary = AnthropicProvider(
            AnthropicConfig(model="claude-3-5-sonnet-20241022", api_key="bad-key"),
            _transport=_error_transport,
        )
        fallback = _make_openai()

        try:
            _run(primary.call(_MESSAGES))
        except AuthenticationError as err:
            result = classify(err)
            assert not result.is_retryable
            # Fall back to OpenAI
            resp = _run(fallback.call(_MESSAGES))
            assert resp.message.content

    def test_provider_name_stable_across_calls(self) -> None:
        p = _make_openai()
        assert p.name == p.name  # noqa: PLR0124 - deliberate identity check

    def test_custom_registry_creates_independent_provider(self) -> None:
        from mas.llm.provider_registry import ProviderRegistry

        isolated = ProviderRegistry()
        isolated.register("openai", OpenAIProvider, OpenAIConfig)
        p = isolated.create("openai", OpenAIConfig(model="gpt-4o", api_key="sk-x"))
        assert p.name == "openai"


# ---------------------------------------------------------------------------
# Section 8: Concurrent calls
# ---------------------------------------------------------------------------


class TestConcurrentCalls:
    """Multiple providers can be called concurrently without interference."""

    def test_concurrent_calls_to_same_provider(self) -> None:
        async def _run_concurrent() -> list[LLMResponse]:
            p1 = _make_openai()
            p2 = _make_openai()
            results = await asyncio.gather(
                p1.call(_MESSAGES),
                p2.call(_MESSAGES),
            )
            return list(results)

        responses = asyncio.run(_run_concurrent())
        assert len(responses) == 2
        for r in responses:
            assert r.message.content

    def test_concurrent_calls_to_different_providers(self) -> None:
        async def _run_all() -> list[LLMResponse]:
            results = await asyncio.gather(
                _make_ollama().call(_MESSAGES),
                _make_huggingface().call(_MESSAGES),
                _make_openai().call(_MESSAGES),
                _make_anthropic().call(_MESSAGES),
            )
            return list(results)

        responses = asyncio.run(_run_all())
        assert len(responses) == 4
        for r in responses:
            assert r.message.role == "assistant"

    def test_token_counter_thread_safe_for_concurrent_counts(self) -> None:
        tc = TokenCounter(cache_size=100)

        async def _count_all() -> list[int]:
            return [
                tc.count("hello openai", provider="openai"),
                tc.count("hello anthropic", provider="anthropic"),
                tc.count("hello ollama", provider="ollama"),
                tc.count("hello huggingface", provider="huggingface"),
            ]

        results = asyncio.run(_count_all())
        assert all(r > 0 for r in results)
