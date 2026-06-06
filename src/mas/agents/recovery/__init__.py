"""Recovery and self-healing module for the multi-agent system.

Provides failure classification, retry policies, fallback handlers,
and escalation logic to enable the system to recover from transient failures
while preventing infinite loops and resource exhaustion.
"""

from mas.agents.recovery.escalation import (
    EscalationOutcome,
    EscalationReason,
)
from mas.agents.recovery.failures import (
    FailureType,
    PermanentError,
    RecoverableError,
    StepFailure,
)
from mas.agents.recovery.retry_policy import (
    RetryConfig,
    RetryPolicy,
)

__all__ = [
    "FailureType",
    "StepFailure",
    "RecoverableError",
    "PermanentError",
    "RetryPolicy",
    "RetryConfig",
    "EscalationOutcome",
    "EscalationReason",
]
