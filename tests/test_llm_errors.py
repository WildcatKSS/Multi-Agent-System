"""Tests for the LLM error hierarchy defined in mas.llm.errors."""

import pytest

from mas.llm.errors import (
    APIError,
    AuthenticationError,
    ConfigError,
    LLMError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

_ALL_SUBCLASSES: list[type[LLMError]] = [
    ConfigError,
    TimeoutError,
    APIError,
    ValidationError,
    RateLimitError,
    AuthenticationError,
]


class TestLLMErrorBase:
    """Tests for the LLMError base class."""

    def test_inherits_from_exception(self) -> None:
        """LLMError is a standard Python exception."""
        assert issubclass(LLMError, Exception)
        assert isinstance(LLMError("x"), Exception)

    def test_message_propagation(self) -> None:
        """The message is accessible both via .message and str()."""
        err = LLMError("something went wrong")
        assert err.message == "something went wrong"
        assert str(err) == "something went wrong"

    def test_valid_creation_minimal(self) -> None:
        """LLMError can be created with only a message."""
        err = LLMError("minimal")
        assert err.message == "minimal"

    def test_optional_fields_default_to_none(self) -> None:
        """original_exception and retry_after_seconds default to None."""
        err = LLMError("defaults")
        assert err.original_exception is None
        assert err.retry_after_seconds is None

    def test_string_representation(self) -> None:
        """str() returns the message, matching standard Exception behaviour."""
        assert str(LLMError("oops")) == "oops"

    def test_original_exception_stored(self) -> None:
        """original_exception is preserved for root-cause inspection."""
        root = ValueError("root cause")
        err = LLMError("wrapped", original_exception=root)
        assert err.original_exception is root

    def test_retry_after_seconds_stored(self) -> None:
        """retry_after_seconds is preserved when supplied."""
        err = LLMError("wait", retry_after_seconds=42)
        assert err.retry_after_seconds == 42

    def test_default_transient_is_false(self) -> None:
        """LLMError defaults to non-transient (permanent)."""
        assert LLMError("x").transient is False

    def test_transient_override_true(self) -> None:
        """transient=True overrides the class default."""
        err = LLMError("x", transient=True)
        assert err.transient is True

    def test_transient_override_false_on_transient_subclass(self) -> None:
        """Passing transient=False overrides a subclass default of True."""
        err = APIError("permanent 4xx", transient=False)
        assert err.transient is False


class TestTransientClassification:
    """Each subclass has the correct default transient value."""

    @pytest.mark.parametrize(
        "error_cls",
        [ConfigError, ValidationError, AuthenticationError],
    )
    def test_permanent_errors_not_transient(self, error_cls: type[LLMError]) -> None:
        """Configuration, validation, and auth errors are permanent."""
        assert error_cls("x").transient is False

    @pytest.mark.parametrize(
        "error_cls",
        [TimeoutError, APIError, RateLimitError],
    )
    def test_transient_errors_are_transient(self, error_cls: type[LLMError]) -> None:
        """Timeout, API, and rate-limit errors are transient."""
        assert error_cls("x").transient is True

    def test_transient_uses_class_default_when_not_supplied(self) -> None:
        """Omitting the transient kwarg falls back to default_transient."""
        assert ConfigError("x").transient is ConfigError.default_transient
        assert TimeoutError("x").transient is TimeoutError.default_transient


class TestSubclassHierarchy:
    """All six subclasses are proper LLMError subclasses."""

    @pytest.mark.parametrize("error_cls", _ALL_SUBCLASSES)
    def test_inherits_from_llm_error(self, error_cls: type[LLMError]) -> None:
        """Every subclass is an instance of LLMError and Exception."""
        err = error_cls("boom")
        assert isinstance(err, LLMError)
        assert isinstance(err, Exception)

    @pytest.mark.parametrize("error_cls", _ALL_SUBCLASSES)
    def test_subclass_message_propagation(self, error_cls: type[LLMError]) -> None:
        """Message is accessible on every subclass."""
        err = error_cls("sub message")
        assert err.message == "sub message"
        assert str(err) == "sub message"

    def test_rate_limit_retry_after(self) -> None:
        """RateLimitError can carry a retry-after hint and is transient."""
        err = RateLimitError("slow down", retry_after_seconds=30)
        assert err.transient is True
        assert err.retry_after_seconds == 30

    def test_rate_limit_without_retry_after(self) -> None:
        """retry_after_seconds is optional on RateLimitError."""
        err = RateLimitError("slow down")
        assert err.retry_after_seconds is None


class TestBackwardCompatibility:
    """The re-exports in mas.llm.contracts are the same objects."""

    def test_contracts_reexports_are_identical(self) -> None:
        """Importing from contracts yields the same classes as from errors."""
        from mas.llm.contracts import (
            APIError as ContractsAPIError,
        )
        from mas.llm.contracts import (
            AuthenticationError as ContractsAuthenticationError,
        )
        from mas.llm.contracts import (
            ConfigError as ContractsConfigError,
        )
        from mas.llm.contracts import (
            LLMError as ContractsLLMError,
        )
        from mas.llm.contracts import (
            RateLimitError as ContractsRateLimitError,
        )
        from mas.llm.contracts import (
            TimeoutError as ContractsTimeoutError,
        )
        from mas.llm.contracts import (
            ValidationError as ContractsValidationError,
        )

        assert ContractsLLMError is LLMError
        assert ContractsConfigError is ConfigError
        assert ContractsTimeoutError is TimeoutError
        assert ContractsAPIError is APIError
        assert ContractsValidationError is ValidationError
        assert ContractsRateLimitError is RateLimitError
        assert ContractsAuthenticationError is AuthenticationError

    def test_isinstance_works_across_import_paths(self) -> None:
        """isinstance checks pass regardless of which path was used to import."""
        from mas.llm.contracts import LLMError as ContractsLLMError

        err = ConfigError("x")
        assert isinstance(err, ContractsLLMError)
