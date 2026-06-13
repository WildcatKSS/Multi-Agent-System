"""Integration tests for Phase 1: cross-component flows across ProviderRegistry,
BaseProvider, LLMConfig, and observability.

Each test here exercises a *seam* between two or more components. Single-component
behaviour is covered by the dedicated unit test files.
"""

import asyncio
import logging
from typing import Any

import pytest

from mas.llm.base import BaseProvider
from mas.llm.config import OllamaConfig, OpenAIConfig
from mas.llm.contracts import (
    APIError,
    ConfigError,
    LLMMessage,
    LLMResponse,
    RateLimitError,
)
from mas.llm.provider_registry import ProviderRegistry
from mas.observability.correlation import (
    reset_correlation_id,
    set_correlation_id,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _msg(text: str = "hello") -> list[LLMMessage]:
    return [LLMMessage(role="user", content=text)]


def _response(
    tokens: int = 10, model: str = "int-model", content: str = "integrated"
) -> LLMResponse:
    return LLMResponse(
        message=LLMMessage(role="assistant", content=content),
        tokens_used=tokens,
        model=model,
        latency_ms=1.0,
    )


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Provider implementations for integration tests
# ---------------------------------------------------------------------------


class _FixedProvider(BaseProvider):
    """BaseProvider subclass with a fixed success response.

    Safe to register in ProviderRegistry because it needs no injected effects —
    instantiated with only a config argument, like a real provider.
    """

    def __init__(self, config: Any = None) -> None:
        self.invoke_calls = 0
        self.slept: list[float] = []
        super().__init__(config)

    @property
    def name(self) -> str:
        return "fixed-provider"

    @property
    def default_model(self) -> str:
        config_model: str = getattr(self.config, "model", "")
        return config_model or "int-model"

    def validate_config(self, config: Any) -> bool:
        return True

    async def _invoke(
        self, messages: list[LLMMessage], model: str, **kwargs: Any
    ) -> LLMResponse:
        self.invoke_calls += 1
        return _response(model=model)

    async def _sleep(self, seconds: float) -> None:
        self.slept.append(seconds)


class _FailingProvider(BaseProvider):
    """BaseProvider subclass whose config validator always rejects."""

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)

    @property
    def name(self) -> str:
        return "failing-provider"

    @property
    def default_model(self) -> str:
        return "fail-model"

    def validate_config(self, config: Any) -> bool:
        return False

    async def _invoke(
        self, messages: list[LLMMessage], model: str, **kwargs: Any
    ) -> LLMResponse:  # pragma: no cover — never reached
        raise RuntimeError("should not be called")

    async def _sleep(self, seconds: float) -> None:  # pragma: no cover
        pass


class _EffectsProvider(BaseProvider):
    """BaseProvider subclass accepting injected effects for retry and error tests."""

    def __init__(
        self,
        effects: list[Any] | None = None,
        *,
        cost_per_token: float = 0.0,
        **kwargs: Any,
    ) -> None:
        self._effects = effects if effects is not None else [_response()]
        self._cost_per_token = cost_per_token
        self.invoke_calls = 0
        self.slept: list[float] = []
        super().__init__(**kwargs)

    @property
    def name(self) -> str:
        return "effects-provider"

    @property
    def default_model(self) -> str:
        return "int-model"

    def validate_config(self, config: Any) -> bool:
        return True

    def estimate_cost_usd(self, tokens_used: int, model: str) -> float:
        return tokens_used * self._cost_per_token

    async def _invoke(
        self, messages: list[LLMMessage], model: str, **kwargs: Any
    ) -> LLMResponse:
        self.invoke_calls += 1
        effect = self._effects[min(self.invoke_calls - 1, len(self._effects) - 1)]
        if isinstance(effect, BaseException):
            raise effect
        return effect

    async def _sleep(self, seconds: float) -> None:
        self.slept.append(seconds)


# ---------------------------------------------------------------------------
# TestRegistryToProvider  (seam: ProviderRegistry ↔ BaseProvider)
# ---------------------------------------------------------------------------


class TestRegistryToProvider:
    """ProviderRegistry builds a BaseProvider subclass and the call path works."""

    @pytest.fixture()
    def registry(self) -> ProviderRegistry:
        r = ProviderRegistry()
        r.register("fixed", _FixedProvider, OllamaConfig)
        return r

    def test_registry_create_returns_base_provider(
        self, registry: ProviderRegistry
    ) -> None:
        provider = registry.create("fixed", OllamaConfig(model="llama3"))
        assert isinstance(provider, BaseProvider)
        assert isinstance(provider, _FixedProvider)

    def test_registry_create_provider_can_call_successfully(
        self, registry: ProviderRegistry
    ) -> None:
        provider = registry.create("fixed", OllamaConfig(model="llama3"))
        resp = _run(provider.call(_msg()))
        assert isinstance(resp, LLMResponse)
        assert resp.message.role == "assistant"

    def test_from_config_dispatch_builds_callable_provider(
        self, registry: ProviderRegistry
    ) -> None:
        provider = registry.from_config(OllamaConfig(model="mistral"))
        resp = _run(provider.call(_msg()))
        assert resp.model == "mistral"

    def test_registry_provider_uses_config_model_as_default(
        self, registry: ProviderRegistry
    ) -> None:
        provider = registry.create("fixed", OllamaConfig(model="codellama"))
        resp = _run(provider.call(_msg()))
        assert resp.model == "codellama"

    def test_invalid_config_raises_at_construction_not_call_time(self) -> None:
        r = ProviderRegistry()
        r.register("bad", _FailingProvider, OllamaConfig)
        with pytest.raises(ConfigError):
            r.create("bad", OllamaConfig(model="llama3"))

    def test_two_different_providers_in_same_registry(self) -> None:
        r = ProviderRegistry()
        r.register("fixed", _FixedProvider, OllamaConfig)
        r.register("openai-fixed", _FixedProvider, OpenAIConfig)

        p1 = r.create("fixed", OllamaConfig(model="llama3"))
        p2 = r.create("openai-fixed", OpenAIConfig(model="gpt-4", api_key="sk-x"))

        r1 = _run(p1.call(_msg()))
        r2 = _run(p2.call(_msg()))
        assert r1.message.content == r2.message.content == "integrated"


# ---------------------------------------------------------------------------
# TestRetryThroughBase  (seam: BaseProvider retry ↔ error taxonomy)
# ---------------------------------------------------------------------------


class TestRetryThroughBase:
    """BaseProvider's retry/backoff wires correctly to the error hierarchy."""

    def test_transient_error_triggers_retry_and_succeeds(self) -> None:
        provider = _EffectsProvider(
            effects=[RateLimitError("busy"), _response()],
            max_retries=1,
        )
        resp = _run(provider.call(_msg()))
        assert resp.message.content == "integrated"
        assert provider.invoke_calls == 2

    def test_permanent_error_not_retried(self) -> None:
        provider = _EffectsProvider(
            effects=[APIError("gone", transient=False)],
            max_retries=3,
        )
        with pytest.raises(APIError):
            _run(provider.call(_msg()))
        assert provider.invoke_calls == 1

    def test_retry_cap_is_strictly_enforced(self) -> None:
        provider = _EffectsProvider(
            effects=[RateLimitError("always")] * 5,
            max_retries=2,
        )
        with pytest.raises(RateLimitError):
            _run(provider.call(_msg()))
        assert provider.invoke_calls == 3  # 1 initial + 2 retries

    def test_exponential_backoff_delays_increase(self) -> None:
        provider = _EffectsProvider(
            effects=[
                RateLimitError("s1"),
                RateLimitError("s2"),
                _response(),
            ],
            max_retries=2,
        )
        _run(provider.call(_msg()))
        assert len(provider.slept) == 2
        assert provider.slept[1] >= provider.slept[0]


# ---------------------------------------------------------------------------
# TestObservabilityAcrossComponents
# (seam: BaseProvider logging ↔ correlation context ↔ ProviderRegistry)
# ---------------------------------------------------------------------------


class TestObservabilityAcrossComponents:
    """Correlation ID and structured logs work end-to-end from registry call."""

    def teardown_method(self) -> None:
        reset_correlation_id()

    def test_correlation_id_set_before_registry_call_appears_in_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="mas.llm.base")
        set_correlation_id("int-run-42")

        r = ProviderRegistry()
        r.register("fixed", _FixedProvider, OllamaConfig)
        provider = r.create("fixed", OllamaConfig(model="llama3"))
        _run(provider.call(_msg()))

        success_records = [
            rec for rec in caplog.records if rec.message == "llm_call_succeeded"
        ]
        assert len(success_records) == 1
        assert success_records[0].correlation_id == "int-run-42"  # type: ignore[attr-defined]

    def test_cost_estimate_flows_from_provider_to_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="mas.llm.base")
        provider = _EffectsProvider(
            effects=[_response(tokens=50)], cost_per_token=0.01
        )
        _run(provider.call(_msg()))

        rec = next(r for r in caplog.records if r.message == "llm_call_succeeded")
        assert rec.cost_usd == pytest.approx(0.5)  # type: ignore[attr-defined]

    def test_retry_log_and_success_log_share_correlation_id(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG, logger="mas.llm.base")
        set_correlation_id("sticky-id")
        provider = _EffectsProvider(
            effects=[RateLimitError("slow"), _response()],
            max_retries=1,
        )
        _run(provider.call(_msg()))

        ids = {
            rec.correlation_id  # type: ignore[attr-defined]
            for rec in caplog.records
        }
        assert ids == {"sticky-id"}


# ---------------------------------------------------------------------------
# TestAsyncIntegration  (seam: BaseProvider ↔ async runtime)
# ---------------------------------------------------------------------------


class TestAsyncIntegration:
    """Concurrent provider calls via asyncio.gather work through BaseProvider."""

    def test_concurrent_calls_to_same_provider_all_succeed(self) -> None:
        provider = _EffectsProvider(effects=[_response(tokens=5)] * 5)

        async def _gather() -> list[LLMResponse]:
            return await asyncio.gather(*[provider.call(_msg()) for _ in range(5)])

        results = _run(_gather())
        assert len(results) == 5
        assert all(r.tokens_used == 5 for r in results)

    def test_concurrent_calls_to_different_registry_providers(self) -> None:
        r = ProviderRegistry()
        r.register("fixed", _FixedProvider, OllamaConfig)
        p1 = r.create("fixed", OllamaConfig(model="llama3"))
        p2 = r.create("fixed", OllamaConfig(model="mistral"))

        async def _gather() -> list[LLMResponse]:
            return list(await asyncio.gather(p1.call(_msg()), p2.call(_msg())))

        results = _run(_gather())
        models = {r.model for r in results}
        assert models == {"llama3", "mistral"}
