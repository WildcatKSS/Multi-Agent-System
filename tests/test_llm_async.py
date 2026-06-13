"""Tests for the async LLM provider layer: concurrent calls, timeout, and runtime async variant."""

import asyncio
import time
from typing import Any

import pytest

from mas.domain.plan import Plan, Step
from mas.domain.task import Task
from mas.llm.base import BaseProvider
from mas.llm.contracts import (
    APIError,
    LLMMessage,
    LLMResponse,
)
from mas.llm.contracts import TimeoutError as ProviderTimeoutError
from mas.runtime import Runtime, StepExecutorRegistry, StepResult
from mas.workflow.state import WorkflowState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TIMEOUT = "timeout"  # sentinel: _invoke blocks past the timeout budget


def _msg(content: str = "hello") -> list[LLMMessage]:
    return [LLMMessage(role="user", content=content)]


def _response(content: str = "ok", model: str = "test-model") -> LLMResponse:
    return LLMResponse(
        message=LLMMessage(role="assistant", content=content),
        tokens_used=10,
        model=model,
        latency_ms=1.0,
    )


class _AsyncTestProvider(BaseProvider):
    """Configurable async provider for exercising the BaseProvider template."""

    def __init__(self, *, effects: list[Any] | None = None, **kwargs: Any) -> None:
        self._effects = effects if effects is not None else [_response()]
        self.invoke_calls = 0
        self.slept: list[float] = []
        self.last_model: str = ""
        super().__init__(**kwargs)

    @property
    def name(self) -> str:
        return "async-test"

    @property
    def default_model(self) -> str:
        return "async-model"

    def validate_config(self, config: Any) -> bool:
        return True

    async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
        self.invoke_calls += 1
        self.last_model = model
        effect = self._effects[min(self.invoke_calls - 1, len(self._effects) - 1)]
        if effect == _TIMEOUT:
            await asyncio.sleep(5)  # cancelled by asyncio.timeout inside _attempt
            raise AssertionError("sleep should have been cancelled by timeout")
        if isinstance(effect, BaseException):
            raise effect
        return effect

    async def _sleep(self, seconds: float) -> None:
        self.slept.append(seconds)


class _LatentProvider(BaseProvider):
    """Provider that simulates network latency via asyncio.sleep in _invoke."""

    def __init__(self, *, latency_seconds: float = 0.05, **kwargs: Any) -> None:
        self._latency = latency_seconds
        super().__init__(**kwargs)

    @property
    def name(self) -> str:
        return "latent"

    @property
    def default_model(self) -> str:
        return "latent-model"

    def validate_config(self, config: Any) -> bool:
        return True

    async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
        await asyncio.sleep(self._latency)
        return _response(model=model or self.default_model)


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# TestAsyncCallBasic
# ---------------------------------------------------------------------------


class TestAsyncCallBasic:
    """The async call() method works for the happy path and common error paths."""

    def test_async_call_returns_response(self) -> None:
        provider = _AsyncTestProvider(effects=[_response(content="pong")])
        resp = _run(provider.call(_msg()))
        assert isinstance(resp, LLMResponse)
        assert resp.message.content == "pong"

    def test_async_call_uses_default_model_when_empty(self) -> None:
        provider = _AsyncTestProvider()
        _run(provider.call(_msg(), model=""))
        assert provider.last_model == "async-model"

    def test_async_call_raises_api_error(self) -> None:
        provider = _AsyncTestProvider(
            effects=[APIError("backend unavailable", transient=False)],
            max_retries=0,
        )
        with pytest.raises(APIError, match="backend unavailable"):
            _run(provider.call(_msg()))


# ---------------------------------------------------------------------------
# TestConcurrentCalls
# ---------------------------------------------------------------------------


class TestConcurrentCalls:
    """asyncio.gather works correctly over async call() coroutines."""

    def test_gather_two_calls_both_succeed(self) -> None:
        p1 = _AsyncTestProvider(effects=[_response("a")])
        p2 = _AsyncTestProvider(effects=[_response("b")])

        async def _go() -> list[Any]:
            return list(
                await asyncio.gather(
                    p1.call(_msg()),
                    p2.call(_msg()),
                    return_exceptions=True,
                )
            )

        results = _run(_go())
        assert isinstance(results[0], LLMResponse)
        assert isinstance(results[1], LLMResponse)
        assert results[0].message.content == "a"
        assert results[1].message.content == "b"

    def test_gather_preserves_call_order(self) -> None:
        providers = [_AsyncTestProvider(effects=[_response(str(i))]) for i in range(3)]

        async def _go() -> list[Any]:
            return list(
                await asyncio.gather(
                    *(p.call(_msg()) for p in providers),
                    return_exceptions=True,
                )
            )

        results = _run(_go())
        for i, res in enumerate(results):
            assert isinstance(res, LLMResponse)
            assert res.message.content == str(i)

    def test_gather_one_error_does_not_prevent_others(self) -> None:
        p_ok1 = _AsyncTestProvider(effects=[_response("first")])
        p_err = _AsyncTestProvider(effects=[APIError("boom", transient=False)], max_retries=0)
        p_ok2 = _AsyncTestProvider(effects=[_response("third")])

        async def _go() -> list[Any]:
            return list(
                await asyncio.gather(
                    p_ok1.call(_msg()),
                    p_err.call(_msg()),
                    p_ok2.call(_msg()),
                    return_exceptions=True,
                )
            )

        results = _run(_go())
        assert isinstance(results[0], LLMResponse)
        assert isinstance(results[1], APIError)
        assert isinstance(results[2], LLMResponse)
        assert results[0].message.content == "first"
        assert results[2].message.content == "third"

    def test_gather_without_return_exceptions_raises_on_first_error(self) -> None:
        p_err = _AsyncTestProvider(effects=[APIError("fail", transient=False)], max_retries=0)

        async def _go() -> None:
            await asyncio.gather(p_err.call(_msg()))

        with pytest.raises(APIError, match="fail"):
            _run(_go())


# ---------------------------------------------------------------------------
# TestTimeoutEnforcement
# ---------------------------------------------------------------------------


class TestTimeoutEnforcement:
    """asyncio.timeout inside BaseProvider._attempt is properly enforced."""

    def test_timeout_raises_provider_timeout_error(self) -> None:
        provider = _AsyncTestProvider(
            effects=[_TIMEOUT],
            timeout_seconds=0.05,
            max_retries=0,
        )
        with pytest.raises(ProviderTimeoutError):
            _run(provider.call(_msg()))

    def test_timeout_error_triggers_retry(self) -> None:
        provider = _AsyncTestProvider(
            effects=[_TIMEOUT, _response("retried")],
            timeout_seconds=0.05,
            max_retries=1,
        )
        resp = _run(provider.call(_msg()))
        assert isinstance(resp, LLMResponse)
        assert provider.invoke_calls == 2

    def test_provider_usable_after_timeout(self) -> None:
        provider = _AsyncTestProvider(
            effects=[_TIMEOUT, _response("recovered")],
            timeout_seconds=0.05,
            max_retries=1,
        )
        resp = _run(provider.call(_msg()))
        assert resp.message.content == "recovered"


# ---------------------------------------------------------------------------
# TestBackwardCompatRuntime
# ---------------------------------------------------------------------------


def _simple_run(task_id: str) -> tuple[Task, Plan]:
    task = Task(id=task_id, description="test task", goal="done")
    plan = Plan(
        id="plan-1",
        task_id=task_id,
        steps=[Step(id="s1", action="noop")],
    )
    return task, plan


class TestBackwardCompatRuntime:
    """Runtime.run() still works; run_async() delegates to the same logic."""

    def test_sync_run_still_works(self) -> None:
        registry = StepExecutorRegistry()
        registry.register("noop", lambda _s: StepResult(success=True))
        runtime = Runtime(registry=registry)
        task, plan = _simple_run("task-sync")
        result = runtime.run(task, plan)
        assert result.task_id == "task-sync"
        assert result.final_state == WorkflowState.COMPLETED
        assert result.succeeded is True

    def test_run_async_returns_same_outcome_as_run(self) -> None:
        registry = StepExecutorRegistry()
        registry.register("noop", lambda _s: StepResult(success=True))
        runtime = Runtime(registry=registry)

        task1, plan1 = _simple_run("task-sync-2")
        result_sync = runtime.run(task1, plan1)

        task2, plan2 = _simple_run("task-async-2")
        result_async = _run(runtime.run_async(task2, plan2))

        assert result_async.succeeded is result_sync.succeeded
        assert result_async.final_state == result_sync.final_state


# ---------------------------------------------------------------------------
# TestAsyncIntegration
# ---------------------------------------------------------------------------


class TestAsyncIntegration:
    """End-to-end async behaviour with latency-simulating providers."""

    def test_concurrent_calls_faster_than_sequential(self) -> None:
        latency = 0.08
        n = 3

        async def _sequential() -> float:
            providers = [_LatentProvider(latency_seconds=latency) for _ in range(n)]
            t0 = time.monotonic()
            for p in providers:
                await p.call(_msg())
            return time.monotonic() - t0

        async def _concurrent() -> float:
            providers = [_LatentProvider(latency_seconds=latency) for _ in range(n)]
            t0 = time.monotonic()
            await asyncio.gather(*(p.call(_msg()) for p in providers))
            return time.monotonic() - t0

        sequential_time = _run(_sequential())
        concurrent_time = _run(_concurrent())
        assert concurrent_time < sequential_time / 2

    def test_gather_five_calls_all_succeed(self) -> None:
        providers = [_AsyncTestProvider(effects=[_response(str(i))]) for i in range(5)]

        async def _go() -> list[Any]:
            return list(await asyncio.gather(*(p.call(_msg()) for p in providers)))

        results = _run(_go())
        assert all(isinstance(r, LLMResponse) for r in results)
        assert [r.message.content for r in results] == ["0", "1", "2", "3", "4"]

    def test_mixed_success_and_errors_in_concurrent_batch(self) -> None:
        providers: list[BaseProvider] = [
            _AsyncTestProvider(effects=[_response("ok-a")]),
            _AsyncTestProvider(effects=[APIError("oops", transient=False)], max_retries=0),
            _AsyncTestProvider(effects=[_response("ok-b")]),
        ]

        async def _go() -> list[Any]:
            return list(
                await asyncio.gather(
                    *(p.call(_msg()) for p in providers),
                    return_exceptions=True,
                )
            )

        results = _run(_go())
        successes = [r for r in results if isinstance(r, LLMResponse)]
        errors = [r for r in results if isinstance(r, APIError)]
        assert len(successes) == 2
        assert len(errors) == 1
        assert {r.message.content for r in successes} == {"ok-a", "ok-b"}
