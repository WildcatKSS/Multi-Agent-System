"""Evaluation contracts and data structures."""

from dataclasses import dataclass, field
from enum import Enum


class RuleType(str, Enum):
    """Type of evaluation rule."""

    REQUIRED = "required"
    """Rule must pass for evaluation to succeed."""

    OPTIONAL = "optional"
    """Rule is optional, but contributes to score."""

    BLOCKING = "blocking"
    """Rule failure immediately blocks output."""


@dataclass(frozen=True)
class EvaluationRule:
    """Definition of an evaluation rule."""

    name: str
    """Name of the rule."""

    description: str
    """Description of what this rule checks."""

    rule_type: RuleType
    """Type of rule (required, optional, blocking)."""

    weight: float = 1.0
    """Weight in scoring (0-1)."""

    def __post_init__(self) -> None:
        """Validate rule on creation."""
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")
        if not (0 <= self.weight <= 1):
            raise ValueError("weight must be between 0 and 1")


@dataclass(frozen=True)
class HeuristicScore:
    """Score from a heuristic evaluation."""

    heuristic_name: str
    """Name of the heuristic."""

    score: float
    """Score value (0-1)."""

    rationale: str
    """Explanation of the score."""

    def __post_init__(self) -> None:
        """Validate score on creation."""
        if not self.heuristic_name:
            raise ValueError("heuristic_name cannot be empty")
        if not (0 <= self.score <= 1):
            raise ValueError("score must be between 0 and 1")
        if not self.rationale:
            raise ValueError("rationale cannot be empty")


@dataclass(frozen=True)
class EvaluationReport:
    """Report from evaluation of step output."""

    step_id: str
    """ID of the step evaluated."""

    passed: bool
    """Whether evaluation passed."""

    overall_score: float
    """Overall score (0-1)."""

    rule_results: dict[str, bool] = field(default_factory=dict)
    """Results of individual rules (name -> bool)."""

    heuristic_scores: list["HeuristicScore"] = field(default_factory=list)
    """Scores from heuristics."""

    feedback: str = ""
    """Human-readable feedback."""

    def __post_init__(self) -> None:
        """Validate report on creation."""
        if not self.step_id:
            raise ValueError("step_id cannot be empty")
        if not (0 <= self.overall_score <= 1):
            raise ValueError("overall_score must be between 0 and 1")
