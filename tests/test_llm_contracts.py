"""Tests for the LLM contracts: messages, responses, provider ABC, and errors."""

import asyncio
import dataclasses
from typing import Any, get_args

import pytest

from mas.llm.contracts import (
    _VALID_ROLES,
    APIError,
    AuthenticationError,
    ConfigError,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    RateLimitError,
    Role,
    TimeoutError,
    ValidationError,
)


class TestLLMMessage:
    """Tests for the LLMMessage frozen dataclass."""

    def test_valid_creation(self) -> None:
        """Can create a message with a valid role and content."""
        msg = LLMMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert msg.metadata is None

    def test_creation_with_metadata(self) -> None:
        """Metadata is stored when provided."""
        msg = LLMMessage(role="system", content="be helpful", metadata={"k": "v"})
        assert msg.metadata == {"k": "v"}

    @pytest.mark.parametrize("role", ["system", "user", "assistant"])
    def test_all_valid_roles(self, role: str) -> None:
        """Each documented role is accepted."""
        msg = LLMMessage(role=role, content="x")  # type: ignore[arg-type]
        assert msg.role == role

    def test_invalid_role_rejected(self) -> None:
        """An unknown role raises ValueError."""
        with pytest.raises(ValueError, match="role must be one of"):
            LLMMessage(role="robot", content="x")  # type: ignore[arg-type]

    def test_empty_content_rejected(self) -> None:
        """Empty content raises ValueError."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            LLMMessage(role="user", content="")

    @pytest.mark.parametrize("content", [" ", "\t", "\n", "  \n\t "])
    def test_whitespace_only_content_rejected(self, content: str) -> None:
        """Whitespace-only content raises ValueError."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            LLMMessage(role="user", content=content)

    def test_valid_roles_derived_from_literal(self) -> None:
        """The runtime role set matches the Role literal (no drift)."""
        assert frozenset(get_args(Role)) == _VALID_ROLES

    def test_metadata_dict_makes_instance_unhashable(self) -> None:
        """A message carrying a metadata dict is not hashable (documented caveat)."""
        msg = LLMMessage(role="user", content="hi", metadata={"k": "v"})
        with pytest.raises(TypeError):
            hash(msg)

    def test_is_frozen(self) -> None:
        """Messages are immutable."""
        msg = LLMMessage(role="user", content="hello")
        with pytest.raises(dataclasses.FrozenInstanceError):
            msg.content = "changed"  # type: ignore[misc]

    def test_frozen_role_assignment(self) -> None:
        """Reassigning the role also fails on a frozen instance."""
        msg = LLMMessage(role="user", content="hello")
        with pytest.raises(dataclasses.FrozenInstanceError):
            msg.role = "assistant"  # type: ignore[misc]

    def test_equality(self) -> None:
        """Equal field values produce equal messages."""
        a = LLMMessage(role="user", content="hi")
        b = LLMMessage(role="user", content="hi")
        assert a == b


class TestLLMResponse:
    """Tests for the LLMResponse frozen dataclass."""

    def _assistant_msg(self) -> LLMMessage:
        return LLMMessage(role="assistant", content="answer")

    def test_valid_response(self) -> None:
        """Can create a response with valid fields."""
        resp = LLMResponse(
            message=self._assistant_msg(),
            tokens_used=42,
            model="test-model",
            latency_ms=12.5,
        )
        assert resp.tokens_used == 42
        assert resp.model == "test-model"
        assert resp.latency_ms == 12.5
        assert resp.metadata is None

    def test_response_with_metadata(self) -> None:
        """Metadata is stored when provided."""
        resp = LLMResponse(
            message=self._assistant_msg(),
            tokens_used=1,
            model="m",
            latency_ms=0.0,
            metadata={"finish_reason": "stop"},
        )
        assert resp.metadata == {"finish_reason": "stop"}

    def test_zero_tokens_and_latency_allowed(self) -> None:
        """Zero is a valid boundary for tokens and latency."""
        resp = LLMResponse(
            message=self._assistant_msg(),
            tokens_used=0,
            model="m",
            latency_ms=0.0,
        )
        assert resp.tokens_used == 0
        assert resp.latency_ms == 0.0

    def test_negative_tokens_rejected(self) -> None:
        """Negative tokens_used raises ValueError."""
        with pytest.raises(ValueError, match="tokens_used cannot be negative"):
            LLMResponse(message=self._assistant_msg(), tokens_used=-1, model="m", latency_ms=0.0)

    def test_negative_latency_rejected(self) -> None:
        """Negative latency_ms raises ValueError."""
        with pytest.raises(ValueError, match="latency_ms cannot be negative"):
            LLMResponse(message=self._assistant_msg(), tokens_used=0, model="m", latency_ms=-0.1)

    def test_nan_latency_rejected(self) -> None:
        """NaN latency_ms raises ValueError (would otherwise slip past the >= 0 check)."""
        with pytest.raises(ValueError, match="latency_ms must be finite"):
            LLMResponse(
                message=self._assistant_msg(),
                tokens_used=0,
                model="m",
                latency_ms=float("nan"),
            )

    @pytest.mark.parametrize("latency", [float("inf"), float("-inf")])
    def test_infinite_latency_rejected(self, latency: float) -> None:
        """Infinite latency_ms raises ValueError."""
        with pytest.raises(ValueError, match="latency_ms must be finite"):
            LLMResponse(
                message=self._assistant_msg(), tokens_used=0, model="m", latency_ms=latency
            )

    def test_empty_model_rejected(self) -> None:
        """Empty model raises ValueError."""
        with pytest.raises(ValueError, match="model cannot be empty"):
            LLMResponse(message=self._assistant_msg(), tokens_used=0, model="", latency_ms=0.0)

    def test_non_assistant_message_rejected(self) -> None:
        """A response message must be authored by the assistant."""
        with pytest.raises(ValueError, match="must have role 'assistant'"):
            LLMResponse(
                message=LLMMessage(role="user", content="x"),
                tokens_used=0,
                model="m",
                latency_ms=0.0,
            )

    def test_is_frozen(self) -> None:
        """Responses are immutable."""
        resp = LLMResponse(message=self._assistant_msg(), tokens_used=1, model="m", latency_ms=1.0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            resp.tokens_used = 2  # type: ignore[misc]


class _DummyProvider(LLMProvider):
    """Minimal concrete provider used to test the ABC contract."""

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def default_model(self) -> str:
        return "dummy-1"

    @property
    def supports_streaming(self) -> bool:
        return False

    async def call(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            message=LLMMessage(role="assistant", content="ok"),
            tokens_used=1,
            model=model,
            latency_ms=1.0,
        )

    def validate_config(self, config: Any) -> bool:
        return True

    def estimate_tokens(self, text: str) -> int:
        return len(text)


class TestLLMProvider:
    """Tests for the LLMProvider abstract base class."""

    def test_cannot_instantiate_abstract(self) -> None:
        """The ABC itself cannot be instantiated."""
        with pytest.raises(TypeError):
            LLMProvider()  # type: ignore[abstract]

    def test_incomplete_subclass_cannot_instantiate(self) -> None:
        """A subclass missing abstract methods cannot be instantiated."""

        class Incomplete(LLMProvider):
            @property
            def name(self) -> str:
                return "x"

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_concrete_subclass_works(self) -> None:
        """A fully implemented subclass instantiates and exposes properties."""
        provider = _DummyProvider()
        assert provider.name == "dummy"
        assert provider.default_model == "dummy-1"
        assert provider.supports_streaming is False
        assert provider.estimate_tokens("abcd") == 4
        assert provider.validate_config(None) is True

    def test_call_returns_response(self) -> None:
        """The async call method returns a well-formed response."""
        provider = _DummyProvider()
        resp = asyncio.run(provider.call([LLMMessage(role="user", content="hi")], "dummy-1"))
        assert isinstance(resp, LLMResponse)
        assert resp.message.role == "assistant"


class TestErrorHierarchy:
    """Tests for the LLM error hierarchy."""

    @pytest.mark.parametrize(
        "error_cls",
        [
            ConfigError,
            TimeoutError,
            APIError,
            ValidationError,
            RateLimitError,
            AuthenticationError,
        ],
    )
    def test_all_inherit_from_base(self, error_cls: type[LLMError]) -> None:
        """Every error type inherits from LLMError (and Exception)."""
        err = error_cls("boom")
        assert isinstance(err, LLMError)
        assert isinstance(err, Exception)

    def test_base_carries_attributes(self) -> None:
        """The base error exposes its documented attributes."""
        original = ValueError("root cause")
        err = LLMError(
            "failed",
            original_exception=original,
            transient=True,
            retry_after_seconds=5,
        )
        assert err.message == "failed"
        assert err.original_exception is original
        assert err.transient is True
        assert err.retry_after_seconds == 5
        assert str(err) == "failed"

    def test_default_attributes(self) -> None:
        """Defaults are applied when optional fields are omitted."""
        err = LLMError("oops")
        assert err.original_exception is None
        assert err.retry_after_seconds is None

    @pytest.mark.parametrize(
        ("error_cls", "expected_transient"),
        [
            (ConfigError, False),
            (TimeoutError, True),
            (APIError, True),
            (ValidationError, False),
            (RateLimitError, True),
            (AuthenticationError, False),
        ],
    )
    def test_transient_classification(
        self, error_cls: type[LLMError], expected_transient: bool
    ) -> None:
        """Each error type defaults to the correct transient classification."""
        assert error_cls("x").transient is expected_transient

    def test_transient_can_be_overridden(self) -> None:
        """An explicit transient flag overrides the class default."""
        err = APIError("permanent 4xx", transient=False)
        assert err.transient is False

    def test_retry_after_on_rate_limit(self) -> None:
        """Rate limit errors can carry a retry-after hint."""
        err = RateLimitError("slow down", retry_after_seconds=30)
        assert err.transient is True
        assert err.retry_after_seconds == 30
