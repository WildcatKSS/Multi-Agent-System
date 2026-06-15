"""Self-Healing Agent: recoverable failure handling with retry and escalation logic."""

import logging

from mas.agents.recovery.escalation import EscalationOutcome, EscalationReason
from mas.agents.recovery.failures import StepFailure
from mas.agents.recovery.retry_policy import RetryConfig, RetryPolicy

logger = logging.getLogger(__name__)


class SelfHealingAgent:
    """Agent that handles recoverable failures through retry and escalation.

    v1 characteristics:
    - Deterministic retry logic (no randomization)
    - Max retry enforcement (default 3 retries)
    - Clear failure classification (recoverable vs permanent)
    - Escalation to FAILED state when retries exhausted
    - Fallback hooks for custom recovery logic (future)
    """

    def __init__(self, retry_config: RetryConfig | None = None) -> None:
        """Initialize self-healing agent with optional retry configuration.

        Args:
            retry_config: RetryConfig for retry behavior (defaults to RetryConfig())
        """
        self.retry_policy = RetryPolicy(retry_config)

    def should_retry(self, failure: StepFailure) -> bool:
        """Determine if a failure should trigger a retry.

        Args:
            failure: StepFailure with classification and metadata

        Returns:
            True if failure is recoverable and retries remain, False otherwise
        """
        # Permanent errors never retry
        if not failure.is_recoverable():
            logger.debug(
                f"Step {failure.step_id}: Permanent error {failure.failure_type}, "
                f"no retry"
            )
            return False

        # Check if we have retries left
        can_retry = self.retry_policy.should_retry(failure.attempt_number)

        if can_retry:
            logger.debug(
                f"Step {failure.step_id}: Recoverable error "
                f"(attempt {failure.attempt_number}), will retry"
            )
        else:
            logger.debug(
                f"Step {failure.step_id}: Recoverable error but retries exhausted "
                f"(attempt {failure.attempt_number}), will escalate"
            )

        return can_retry

    def escalate_failure(self, failure: StepFailure) -> EscalationOutcome:
        """Escalate a failure that cannot be recovered.

        Args:
            failure: StepFailure that could not be recovered

        Returns:
            EscalationOutcome describing the escalation action
        """
        if not failure.is_recoverable():
            logger.debug(
                f"Step {failure.step_id}: Escalating permanent error "
                f"{failure.failure_type}"
            )
            return EscalationOutcome.permanent_error(
                failure.step_id, failure.message
            )

        if self.retry_policy.is_exhausted(failure.attempt_number):
            logger.debug(
                f"Step {failure.step_id}: Escalating after exhausting "
                f"{self.retry_policy.config.max_retries} retries"
            )
            return EscalationOutcome.retries_exhausted(
                failure.step_id, self.retry_policy.config.max_retries
            )

        # Should not reach here if should_retry() is used correctly
        return EscalationOutcome(
            reason=EscalationReason.UNKNOWN,
            should_fail=True,
            message=f"Step {failure.step_id}: Unknown escalation reason",
            context={"step_id": failure.step_id},
        )

    def handle_step_failure(
        self, failure: StepFailure
    ) -> tuple[bool, EscalationOutcome | None]:
        """Handle a step failure and determine recovery or escalation.

        This is the main entry point for failure handling.

        Args:
            failure: StepFailure with classification and metadata

        Returns:
            Tuple of (should_retry, escalation_outcome)
            - If should_retry=True: attempt will be retried, escalation=None
            - If should_retry=False: attempt failed, escalation contains action
        """
        if self.should_retry(failure):
            return True, None

        escalation = self.escalate_failure(failure)
        return False, escalation
