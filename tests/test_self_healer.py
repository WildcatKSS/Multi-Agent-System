"""Tests for Self-Healing Agent."""


from mas.agents.recovery.escalation import EscalationReason
from mas.agents.recovery.failures import FailureType, StepFailure
from mas.agents.recovery.retry_policy import RetryConfig
from mas.agents.self_healer import SelfHealingAgent


class TestSelfHealingAgent:
    """Tests for SelfHealingAgent."""

    def test_default_agent(self) -> None:
        """SelfHealingAgent uses default config if none provided."""
        agent = SelfHealingAgent()

        assert agent.retry_policy.config.max_retries == 3

    def test_custom_agent(self) -> None:
        """SelfHealingAgent uses custom config if provided."""
        config = RetryConfig(max_retries=5)
        agent = SelfHealingAgent(config)

        assert agent.retry_policy.config.max_retries == 5

    def test_should_retry_recoverable_within_limit(self) -> None:
        """should_retry returns True for recoverable failures within limit."""
        agent = SelfHealingAgent(RetryConfig(max_retries=3))

        failure = StepFailure(
            step_id="step-01",
            failure_type=FailureType.TIMEOUT,
            message="Timeout",
            attempt_number=1,
        )

        assert agent.should_retry(failure)

    def test_should_retry_recoverable_at_limit(self) -> None:
        """should_retry returns False for recoverable failures at limit."""
        agent = SelfHealingAgent(RetryConfig(max_retries=3))

        failure = StepFailure(
            step_id="step-01",
            failure_type=FailureType.TIMEOUT,
            message="Timeout",
            attempt_number=4,
        )

        assert not agent.should_retry(failure)

    def test_should_retry_permanent_always_false(self) -> None:
        """should_retry returns False for permanent failures."""
        agent = SelfHealingAgent(RetryConfig(max_retries=3))

        failure = StepFailure(
            step_id="step-01",
            failure_type=FailureType.INVALID_INPUT,
            message="Invalid input",
            attempt_number=1,
        )

        assert not agent.should_retry(failure)

    def test_escalate_permanent_error(self) -> None:
        """escalate_failure handles permanent errors."""
        agent = SelfHealingAgent()

        failure = StepFailure(
            step_id="step-01",
            failure_type=FailureType.INVALID_INPUT,
            message="Invalid input format",
            attempt_number=1,
        )

        outcome = agent.escalate_failure(failure)

        assert outcome.reason == EscalationReason.PERMANENT_ERROR
        assert outcome.should_fail is True
        assert "Invalid input format" in outcome.message

    def test_escalate_retries_exhausted(self) -> None:
        """escalate_failure handles exhausted retries."""
        agent = SelfHealingAgent(RetryConfig(max_retries=3))

        failure = StepFailure(
            step_id="step-01",
            failure_type=FailureType.TIMEOUT,
            message="Timeout after 3 retries",
            attempt_number=4,
        )

        outcome = agent.escalate_failure(failure)

        assert outcome.reason == EscalationReason.RETRIES_EXHAUSTED
        assert outcome.should_fail is True
        assert "3" in outcome.message

    def test_handle_step_failure_should_retry(self) -> None:
        """handle_step_failure returns retry=True for recoverable within limit."""
        agent = SelfHealingAgent(RetryConfig(max_retries=3))

        failure = StepFailure(
            step_id="step-01",
            failure_type=FailureType.TOOL_UNAVAILABLE,
            message="Tool unavailable",
            attempt_number=1,
        )

        should_retry, outcome = agent.handle_step_failure(failure)

        assert should_retry is True
        assert outcome is None

    def test_handle_step_failure_escalate_permanent(self) -> None:
        """handle_step_failure escalates permanent errors."""
        agent = SelfHealingAgent()

        failure = StepFailure(
            step_id="step-01",
            failure_type=FailureType.HANDLER_ERROR,
            message="Handler crashed",
            attempt_number=1,
        )

        should_retry, outcome = agent.handle_step_failure(failure)

        assert should_retry is False
        assert outcome is not None
        assert outcome.reason == EscalationReason.PERMANENT_ERROR
        assert outcome.should_fail is True

    def test_handle_step_failure_escalate_exhausted_retries(self) -> None:
        """handle_step_failure escalates when retries exhausted."""
        agent = SelfHealingAgent(RetryConfig(max_retries=3))

        failure = StepFailure(
            step_id="step-01",
            failure_type=FailureType.TIMEOUT,
            message="Timeout",
            attempt_number=4,
        )

        should_retry, outcome = agent.handle_step_failure(failure)

        assert should_retry is False
        assert outcome is not None
        assert outcome.reason == EscalationReason.RETRIES_EXHAUSTED
        assert outcome.should_fail is True

    def test_retry_boundary_3_retries(self) -> None:
        """Verify retry boundary with 3 max retries."""
        agent = SelfHealingAgent(RetryConfig(max_retries=3))

        # Attempt 1, 2, 3 should retry
        for attempt in [1, 2, 3]:
            failure = StepFailure(
                step_id="step-01",
                failure_type=FailureType.TIMEOUT,
                message="Timeout",
                attempt_number=attempt,
            )
            should_retry, _ = agent.handle_step_failure(failure)
            assert should_retry, f"Attempt {attempt} should retry"

        # Attempt 4 should escalate
        failure = StepFailure(
            step_id="step-01",
            failure_type=FailureType.TIMEOUT,
            message="Timeout",
            attempt_number=4,
        )
        should_retry, outcome = agent.handle_step_failure(failure)
        assert not should_retry
        assert outcome.reason == EscalationReason.RETRIES_EXHAUSTED

    def test_all_recoverable_failure_types(self) -> None:
        """Test retry behavior for all recoverable failure types."""
        agent = SelfHealingAgent(RetryConfig(max_retries=1))

        recoverable_types = [
            FailureType.TIMEOUT,
            FailureType.TOOL_UNAVAILABLE,
            FailureType.RESOURCE_EXHAUSTED,
            FailureType.EXTERNAL_SERVICE_ERROR,
        ]

        for failure_type in recoverable_types:
            failure = StepFailure(
                step_id="step-01",
                failure_type=failure_type,
                message="Test failure",
                attempt_number=1,
            )

            should_retry, outcome = agent.handle_step_failure(failure)
            assert should_retry, (
                f"{failure_type} should be retried at attempt 1"
            )
            assert outcome is None

    def test_all_permanent_failure_types(self) -> None:
        """Test escalation behavior for all permanent failure types."""
        agent = SelfHealingAgent(RetryConfig(max_retries=3))

        permanent_types = [
            FailureType.HANDLER_ERROR,
            FailureType.INVALID_INPUT,
        ]

        for failure_type in permanent_types:
            failure = StepFailure(
                step_id="step-01",
                failure_type=failure_type,
                message="Test failure",
                attempt_number=1,
            )

            should_retry, outcome = agent.handle_step_failure(failure)
            assert not should_retry, (
                f"{failure_type} should not be retried"
            )
            assert outcome is not None
            assert outcome.reason == EscalationReason.PERMANENT_ERROR
