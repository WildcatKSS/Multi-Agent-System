"""Guard violations and results."""

from dataclasses import dataclass
from enum import Enum


class GuardType(str, Enum):
    """Type of guardrail that was violated."""

    COST = "cost"
    TTL = "ttl"
    RETRIES = "retries"
    PLAN_DEPTH = "plan_depth"


@dataclass(frozen=True)
class GuardViolation:
    """A single guardrail violation.

    Attributes:
        guard_type: Type of guard that was violated.
        message: Human-readable violation message.
        limit: The enforced limit.
        actual: The actual value that exceeded the limit.
    """

    guard_type: GuardType
    message: str
    limit: float
    actual: float


@dataclass(frozen=True)
class GuardResult:
    """Result of a guardrail check.

    Attributes:
        passed: True if no violations, False otherwise.
        violation: GuardViolation details if check failed, None if passed.
    """

    passed: bool
    violation: GuardViolation | None = None
