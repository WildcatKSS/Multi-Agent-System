"""Tests for LLM observability: correlation IDs, structured logging, and metrics.

Covers the observability layer built into BaseProvider._log() and the
correlation ID support in mas.observability.correlation.  Most production-side
logic was implemented in #48; this file validates the observable contract from
the outside.
"""

import asyncio
import logging
from typing import Any

import pytest

from mas.llm.base import BaseProvider
from mas.llm.contracts import (
    APIError,
    LLMMessage,
    LLMResponse,
    RateLimitError,
)
from mas.observability.correlation import (
    generate_run_id,
    get_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)

# ---------------------------------------------------------------------------
# Shared helpers (mirror test_llm_base.py patterns to stay independent)
# ---------------------------------------------------------------------------


def _msg() -> list[LLMMessage]:
    return [LLMMessage(role="user", content="hello")]


def _response(tokens: int = 20, model: str = "obs-model") -> LLMResponse:
    return LLMResponse(
        message=LLMMessage(role="assistant", content="ok"),
        tokens_used=tokens,
        model=model,
        latency_ms=1.0,
    )


class _ObsProvider(BaseProvider):
    """Minimal configurable provider for observability tests."""

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
        return "obs-provider"

    @property
    def default_model(self) -> str:
        return "obs-model"

    def validate_config(self, config: Any) -> bool:
        return True

    def estimate_cost_usd(self, tokens_used: int, model: str) -> float:
        return tokens_used * self._cost_per_token

    async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
        self.invoke_calls += 1
        effect = self._effects[min(self.invoke_calls - 1, len(self._effects) - 1)]
        if isinstance(effect, BaseException):
            raise effect
        return effect

    async def _sleep(self, seconds: float) -> None:
        self.slept.append(seconds)


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# TestCorrelationIdGeneration
# ---------------------------------------------------------------------------


class TestCorrelationIdGeneration:
    """generate_run_id() and set_correlation_id() contract."""

    def teardown_method(self) -> None:
        reset_correlation_id()

    def test_generate_run_id_is_8_char_hex(self) -> None:
        run_id = generate_run_id()
        assert len(run_id) == 8
        int(run_id, 16)  # raises ValueError if not valid hex

    def test_generate_run_id_produces_unique_values(self) -> None:
        ids = {generate_run_id() for _ in range(50)}
        assert len(ids) == 50

    def test_set_correlation_id_stores_all_three_fields(self) -> None:
        ctx = set_correlation_id("abc12345", task_id="task-1", workflow_id="wf-1")
        assert ctx.run_id == "abc12345"
        assert ctx.task_id == "task-1"
        assert ctx.workflow_id == "wf-1"
        assert get_correlation_id() == "abc12345"


# ---------------------------------------------------------------------------
# TestJsonLogging
# ---------------------------------------------------------------------------


class TestJsonLogging:
    """Structured log format: required fields, correct values, no sensitive data."""

    def teardown_method(self) -> None:
        reset_correlation_id()

    def test_success_log_contains_all_required_fields(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="mas.llm.base")
        set_correlation_id("run-obs1")
        provider = _ObsProvider(effects=[_response(tokens=55)])
        _run(provider.call(_msg()))

        rec = next(r for r in caplog.records if r.message == "llm_call_succeeded")
        assert rec.provider == "obs-provider"  # type: ignore[attr-defined]
        assert rec.model == "obs-model"  # type: ignore[attr-defined]
        assert rec.tokens_used == 55  # type: ignore[attr-defined]
        assert rec.attempt == 0  # type: ignore[attr-defined]
        assert isinstance(rec.latency_ms, float)  # type: ignore[attr-defined]
        assert rec.correlation_id == "run-obs1"  # type: ignore[attr-defined]

    def test_retry_log_contains_all_required_fields(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG, logger="mas.llm.base")
        set_correlation_id("run-obs2")
        provider = _ObsProvider(effects=[RateLimitError("slow", retry_after_seconds=5), _response()])
        _run(provider.call(_msg()))

        rec = next(r for r in caplog.records if r.message == "llm_call_retry")
        assert rec.provider == "obs-provider"  # type: ignore[attr-defined]
        assert rec.error_type == "RateLimitError"  # type: ignore[attr-defined]
        assert rec.transient is True  # type: ignore[attr-defined]
        assert rec.retry_delay_seconds == 5  # type: ignore[attr-defined]
        assert isinstance(rec.latency_ms, float)  # type: ignore[attr-defined]
        assert rec.correlation_id == "run-obs2"  # type: ignore[attr-defined]

    def test_no_prompt_content_in_any_log_field(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG, logger="mas.llm.base")
        secret = "CONFIDENTIAL_PROMPT_VALUE_XYZ"
        provider = _ObsProvider(effects=[_response()])
        _run(provider.call([LLMMessage(role="user", content=secret)]))

        for rec in caplog.records:
            for attr_val in rec.__dict__.values():
                assert secret not in str(attr_val)

    def test_no_api_key_patterns_in_log_values(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG, logger="mas.llm.base")
        fake_key = "sk-ant-api03-FAKEKEYVALUE"
        provider = _ObsProvider(effects=[_response()])
        _run(provider.call([LLMMessage(role="user", content=fake_key)]))

        # Only check the fields emitted by _log(), not pytest-internal rec attributes.
        _log_fields = [
            "provider", "model", "tokens_used", "cost_usd", "latency_ms",
            "attempt", "correlation_id", "error_type", "transient",
            "retry_delay_seconds",
        ]
        for rec in caplog.records:
            for field_name in _log_fields:
                assert fake_key not in str(getattr(rec, field_name, ""))


# ---------------------------------------------------------------------------
# TestMetrics
# ---------------------------------------------------------------------------


class TestMetrics:
    """Token, latency, and cost metrics in log records."""

    def test_tokens_used_in_log_matches_response(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="mas.llm.base")
        provider = _ObsProvider(effects=[_response(tokens=99)])
        _run(provider.call(_msg()))

        rec = next(r for r in caplog.records if r.message == "llm_call_succeeded")
        assert rec.tokens_used == 99  # type: ignore[attr-defined]

    def test_latency_ms_is_a_positive_float_on_success(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="mas.llm.base")
        provider = _ObsProvider(effects=[_response()])
        _run(provider.call(_msg()))

        rec = next(r for r in caplog.records if r.message == "llm_call_succeeded")
        assert isinstance(rec.latency_ms, float)  # type: ignore[attr-defined]
        assert rec.latency_ms >= 0.0  # type: ignore[attr-defined]

    def test_cost_usd_nonzero_when_provider_overrides_estimate(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="mas.llm.base")
        provider = _ObsProvider(effects=[_response(tokens=100)], cost_per_token=0.01)
        _run(provider.call(_msg()))

        rec = next(r for r in caplog.records if r.message == "llm_call_succeeded")
        assert rec.cost_usd == pytest.approx(1.0)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# TestErrorLogging
# ---------------------------------------------------------------------------


class TestErrorLogging:
    """Error and retry log records carry the expected context."""

    def test_failure_log_includes_provider_name(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG, logger="mas.llm.base")
        provider = _ObsProvider(effects=[APIError("gone", transient=False)], max_retries=0)
        with pytest.raises(APIError):
            _run(provider.call(_msg()))

        rec = next(r for r in caplog.records if r.message == "llm_call_failed")
        assert rec.provider == "obs-provider"  # type: ignore[attr-defined]
        assert rec.error_type == "APIError"  # type: ignore[attr-defined]

    def test_multiple_retries_each_produce_a_retry_log_record(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG, logger="mas.llm.base")
        provider = _ObsProvider(
            effects=[
                RateLimitError("slow"),
                RateLimitError("still slow"),
                _response(),
            ],
            max_retries=2,
        )
        _run(provider.call(_msg()))

        retry_records = [r for r in caplog.records if r.message == "llm_call_retry"]
        assert len(retry_records) == 2
        assert retry_records[0].attempt == 0  # type: ignore[attr-defined]
        assert retry_records[1].attempt == 1  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# TestIntegration
# ---------------------------------------------------------------------------


class TestIntegration:
    """End-to-end observability checks across providers and call sequences."""

    def teardown_method(self) -> None:
        reset_correlation_id()

    def test_logs_are_emitted_to_mas_llm_base_logger(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="mas.llm.base")
        provider = _ObsProvider(effects=[_response()])
        _run(provider.call(_msg()))

        assert any(r.name == "mas.llm.base" for r in caplog.records)

    def test_retry_then_success_generates_both_event_types(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG, logger="mas.llm.base")
        provider = _ObsProvider(
            effects=[RateLimitError("busy"), _response()],
            max_retries=1,
        )
        _run(provider.call(_msg()))

        events = {r.message for r in caplog.records}
        assert "llm_call_retry" in events
        assert "llm_call_succeeded" in events
        assert "llm_call_failed" not in events

    def test_correlation_id_consistent_across_retry_and_success_logs(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG, logger="mas.llm.base")
        set_correlation_id("run-sticky")
        provider = _ObsProvider(
            effects=[RateLimitError("busy"), _response()],
            max_retries=1,
        )
        _run(provider.call(_msg()))

        ids = {r.correlation_id for r in caplog.records}  # type: ignore[attr-defined]
        assert ids == {"run-sticky"}

    def test_two_providers_log_distinct_provider_names(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        class _AltProvider(_ObsProvider):
            @property
            def name(self) -> str:
                return "alt-provider"

            @property
            def default_model(self) -> str:
                return "alt-model"

        caplog.set_level(logging.INFO, logger="mas.llm.base")
        p1 = _ObsProvider(effects=[_response()])
        p2 = _AltProvider(effects=[_response(model="alt-model")])

        _run(p1.call(_msg()))
        _run(p2.call(_msg()))

        provider_names = {
            r.provider  # type: ignore[attr-defined]
            for r in caplog.records
            if r.message == "llm_call_succeeded"
        }
        assert provider_names == {"obs-provider", "alt-provider"}
