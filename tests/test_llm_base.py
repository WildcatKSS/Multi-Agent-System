"""Tests for BaseProvider: config validation, timeout, retry, and logging."""

import asyncio
import logging
from typing import Any

import pytest

from mas.llm.base import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    BaseProvider,
)
from mas.llm.contracts import (
    APIError,
    ConfigError,
    LLMMessage,
    LLMResponse,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from mas.observability.correlation import reset_correlation_id, set_correlation_id

# A sentinel effect meaning "block long enough to trigger the timeout".
_TIMEOUT = "timeout"


def _response(content: str = "ok", tokens: int = 10, model: str = "test-model") -> LLMResponse:
    return LLMResponse(
        message=LLMMessage(role="assistant", content=content),
        tokens_used=tokens,
        model=model,
        latency_ms=1.0,
    )


class _TestProvider(BaseProvider):
    """Configurable provider for exercising the BaseProvider template."""

    def __init__(
        self,
        *,
        effects: list[Any] | None = None,
        valid: bool = True,
        validate_raises: bool = False,
        **kwargs: Any,
    ) -> None:
        # Set behaviour before super().__init__ -- it calls validate_config().
        self._effects = effects if effects is not None else [_response()]
        self._valid = valid
        self._validate_raises = validate_raises
        self.invoke_calls = 0
        self.slept: list[float] = []
        super().__init__(**kwargs)

    @property
    def name(self) -> str:
        return "test"

    @property
    def default_model(self) -> str:
        return "test-model"

    def validate_config(self, config: Any) -> bool:
        if self._validate_raises:
            raise ConfigError("explicit config rejection")
        return self._valid

    async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
        self.invoke_calls += 1
        effect = self._effects[min(self.invoke_calls - 1, len(self._effects) - 1)]
        if effect == _TIMEOUT:
            await asyncio.sleep(5)
            raise AssertionError("sleep should have been cancelled by timeout")
        if isinstance(effect, BaseException):
            raise effect
        return effect

    async def _sleep(self, seconds: float) -> None:
        # Record backoff delays without actually waiting.
        self.slept.append(seconds)


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


class TestConfigValidation:
    def test_valid_config_constructs(self) -> None:
        provider = _TestProvider(valid=True)
        assert provider.config is None
        assert provider.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
        assert provider.max_retries == DEFAULT_MAX_RETRIES

    def test_invalid_config_raises_config_error(self) -> None:
        with pytest.raises(ConfigError, match="invalid configuration"):
            _TestProvider(valid=False)

    def test_validate_config_may_raise_config_error(self) -> None:
        with pytest.raises(ConfigError, match="explicit config rejection"):
            _TestProvider(validate_raises=True)

    def test_config_is_stored(self) -> None:
        cfg = {"api_key": "x"}
        provider = _TestProvider(config=cfg)
        assert provider.config is cfg


class TestConstructorValidation:
    def test_zero_timeout_rejected(self) -> None:
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            _TestProvider(timeout_seconds=0)

    def test_negative_timeout_rejected(self) -> None:
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            _TestProvider(timeout_seconds=-1.0)

    def test_negative_max_retries_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_retries cannot be negative"):
            _TestProvider(max_retries=-1)


class TestDefaults:
    def test_supports_streaming_default_false(self) -> None:
        assert _TestProvider().supports_streaming is False

    @pytest.mark.parametrize(
        ("text", "expected"),
        [("", 0), ("a", 1), ("abcd", 1), ("abcde", 2), ("12345678", 2)],
    )
    def test_estimate_tokens_heuristic(self, text: str, expected: int) -> None:
        assert _TestProvider().estimate_tokens(text) == expected

    def test_estimate_cost_default_zero(self) -> None:
        assert _TestProvider().estimate_cost_usd(1000, "test-model") == 0.0


class TestCallSuccess:
    def test_returns_invoke_response(self) -> None:
        resp = _response(content="hello")
        provider = _TestProvider(effects=[resp])
        result = _run(provider.call([LLMMessage(role="user", content="hi")]))
        assert result is resp
        assert provider.invoke_calls == 1

    def test_empty_model_falls_back_to_default(self) -> None:
        captured: dict[str, str] = {}

        class _P(_TestProvider):
            async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
                captured["model"] = model
                return _response()

        provider = _P()
        _run(provider.call([LLMMessage(role="user", content="hi")], model=""))
        assert captured["model"] == "test-model"

    def test_explicit_model_used(self) -> None:
        captured: dict[str, str] = {}

        class _P(_TestProvider):
            async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
                captured["model"] = model
                return _response()

        provider = _P()
        _run(provider.call([LLMMessage(role="user", content="hi")], model="custom-model"))
        assert captured["model"] == "custom-model"

    def test_empty_messages_rejected(self) -> None:
        provider = _TestProvider()
        with pytest.raises(ValidationError, match="messages cannot be empty"):
            _run(provider.call([]))
        assert provider.invoke_calls == 0


class TestRetryLogic:
    def test_transient_error_is_retried_then_succeeds(self) -> None:
        ok = _response()
        provider = _TestProvider(effects=[RateLimitError("slow down"), ok])
        result = _run(provider.call([LLMMessage(role="user", content="hi")]))
        assert result is ok
        assert provider.invoke_calls == 2
        assert provider.slept == [1]  # 2**0

    def test_permanent_error_is_not_retried(self) -> None:
        provider = _TestProvider(effects=[ConfigError("bad")])
        with pytest.raises(ConfigError):
            _run(provider.call([LLMMessage(role="user", content="hi")]))
        assert provider.invoke_calls == 1
        assert provider.slept == []

    def test_max_retries_exhausted_raises_last_error(self) -> None:
        provider = _TestProvider(effects=[RateLimitError("nope")], max_retries=3)
        with pytest.raises(RateLimitError):
            _run(provider.call([LLMMessage(role="user", content="hi")]))
        assert provider.invoke_calls == 4  # 1 initial + 3 retries
        assert provider.slept == [1, 2, 4]  # exponential backoff

    def test_retry_after_seconds_overrides_backoff(self) -> None:
        provider = _TestProvider(
            effects=[RateLimitError("wait", retry_after_seconds=30), _response()]
        )
        _run(provider.call([LLMMessage(role="user", content="hi")]))
        assert provider.slept == [30]

    def test_zero_max_retries_means_single_attempt(self) -> None:
        provider = _TestProvider(effects=[RateLimitError("nope")], max_retries=0)
        with pytest.raises(RateLimitError):
            _run(provider.call([LLMMessage(role="user", content="hi")]))
        assert provider.invoke_calls == 1
        assert provider.slept == []

    def test_real_sleep_is_awaitable(self) -> None:
        """The default _sleep (not overridden) awaits without error."""

        class _RealSleepProvider(BaseProvider):
            @property
            def name(self) -> str:
                return "real"

            @property
            def default_model(self) -> str:
                return "m"

            def validate_config(self, config: Any) -> bool:
                return True

            async def _invoke(
                self, messages: list[LLMMessage], model: str, **kwargs: Any
            ) -> LLMResponse:
                return _response()

        provider = _RealSleepProvider()
        _run(provider._sleep(0))


class TestTimeout:
    def test_timeout_raises_provider_timeout_error(self) -> None:
        provider = _TestProvider(effects=[_TIMEOUT], timeout_seconds=0.01, max_retries=0)
        with pytest.raises(TimeoutError, match="timed out after"):
            _run(provider.call([LLMMessage(role="user", content="hi")]))

    def test_timeout_is_transient_and_retried(self) -> None:
        provider = _TestProvider(effects=[_TIMEOUT], timeout_seconds=0.01, max_retries=1)
        with pytest.raises(TimeoutError):
            _run(provider.call([LLMMessage(role="user", content="hi")]))
        assert provider.invoke_calls == 2
        assert provider.slept == [1]

    def test_timeout_then_success(self) -> None:
        ok = _response()
        provider = _TestProvider(effects=[_TIMEOUT, ok], timeout_seconds=0.01, max_retries=1)
        result = _run(provider.call([LLMMessage(role="user", content="hi")]))
        assert result is ok
        assert provider.invoke_calls == 2


class TestErrorClassification:
    def test_unexpected_exception_wrapped_as_permanent_api_error(self) -> None:
        boom = RuntimeError("kaboom")
        provider = _TestProvider(effects=[boom], max_retries=3)
        with pytest.raises(APIError) as exc_info:
            _run(provider.call([LLMMessage(role="user", content="hi")]))
        assert exc_info.value.original_exception is boom
        assert exc_info.value.transient is False
        assert provider.invoke_calls == 1  # not retried
        assert provider.slept == []

    def test_llm_error_subclass_passes_through(self) -> None:
        err = ConfigError("permanent")
        provider = _TestProvider(effects=[err])
        with pytest.raises(ConfigError) as exc_info:
            _run(provider.call([LLMMessage(role="user", content="hi")]))
        assert exc_info.value is err


class TestLogging:
    def test_success_logs_structured_metrics(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.INFO, logger="mas.llm.base")
        provider = _TestProvider(effects=[_response(tokens=42)])
        _run(provider.call([LLMMessage(role="user", content="hi")]))

        records = [r for r in caplog.records if r.message == "llm_call_succeeded"]
        assert len(records) == 1
        rec = records[0]
        assert rec.provider == "test"
        assert rec.model == "test-model"
        assert rec.tokens_used == 42
        assert rec.cost_usd == 0.0
        assert isinstance(rec.latency_ms, float)
        assert rec.attempt == 0

    def test_no_message_content_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.DEBUG, logger="mas.llm.base")
        secret = "TOP_SECRET_PROMPT_CONTENT"
        provider = _TestProvider(effects=[_response()])
        _run(provider.call([LLMMessage(role="user", content=secret)]))

        for rec in caplog.records:
            assert secret not in rec.getMessage()
            for value in rec.__dict__.values():
                assert secret not in str(value)

    def test_failure_logs_error_classification(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.DEBUG, logger="mas.llm.base")
        provider = _TestProvider(effects=[ConfigError("bad")])
        with pytest.raises(ConfigError):
            _run(provider.call([LLMMessage(role="user", content="hi")]))

        failed = [r for r in caplog.records if r.message == "llm_call_failed"]
        assert len(failed) == 1
        assert failed[0].error_type == "ConfigError"
        assert failed[0].transient is False
        assert failed[0].levelno == logging.ERROR

    def test_retry_logs_warning_with_delay(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.DEBUG, logger="mas.llm.base")
        provider = _TestProvider(effects=[RateLimitError("slow"), _response()])
        _run(provider.call([LLMMessage(role="user", content="hi")]))

        retries = [r for r in caplog.records if r.message == "llm_call_retry"]
        assert len(retries) == 1
        assert retries[0].error_type == "RateLimitError"
        assert retries[0].transient is True
        assert retries[0].retry_delay_seconds == 1
        assert retries[0].levelno == logging.WARNING


class TestCorrelationId:
    def teardown_method(self) -> None:
        reset_correlation_id()

    def test_correlation_id_propagates_into_logs(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="mas.llm.base")
        set_correlation_id("run-1234")
        provider = _TestProvider(effects=[_response()])
        _run(provider.call([LLMMessage(role="user", content="hi")]))

        records = [r for r in caplog.records if r.message == "llm_call_succeeded"]
        assert records[0].correlation_id == "run-1234"

    def test_correlation_id_none_when_unset(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.INFO, logger="mas.llm.base")
        reset_correlation_id()
        provider = _TestProvider(effects=[_response()])
        _run(provider.call([LLMMessage(role="user", content="hi")]))

        records = [r for r in caplog.records if r.message == "llm_call_succeeded"]
        assert records[0].correlation_id is None
