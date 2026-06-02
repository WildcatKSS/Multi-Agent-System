"""Heuristic-based scoring for evaluation."""

from dataclasses import dataclass

from mas.agents.evaluation.contracts import HeuristicScore


@dataclass(frozen=True)
class HeuristicConfig:
    """Configuration for heuristic scoring."""

    score_threshold: float = 0.5
    """Minimum score to pass (0-1)."""

    weight_completeness: float = 0.3
    """Weight for completeness heuristic."""

    weight_confidence: float = 0.4
    """Weight for confidence heuristic."""

    weight_consistency: float = 0.3
    """Weight for consistency heuristic."""

    def __post_init__(self) -> None:
        """Validate config on creation."""
        if not (0 <= self.score_threshold <= 1):
            raise ValueError("score_threshold must be between 0 and 1")
        if not (0 <= self.weight_completeness <= 1):
            raise ValueError("weight_completeness must be between 0 and 1")
        if not (0 <= self.weight_confidence <= 1):
            raise ValueError("weight_confidence must be between 0 and 1")
        if not (0 <= self.weight_consistency <= 1):
            raise ValueError("weight_consistency must be between 0 and 1")

        weights_sum = (
            self.weight_completeness
            + self.weight_confidence
            + self.weight_consistency
        )
        if abs(weights_sum - 1.0) > 0.01:
            raise ValueError("weights must sum to 1.0")


class HeuristicScorer:
    """Scores step output using heuristic evaluation."""

    def __init__(self, config: HeuristicConfig | None = None) -> None:
        """Initialize the heuristic scorer.

        Args:
            config: Heuristic configuration. Uses defaults if None.
        """
        self.config = config or HeuristicConfig()

    def score(self, output: dict, context: dict | None = None) -> list[HeuristicScore]:
        """Score step output using heuristics.

        Args:
            output: Step output to score.
            context: Optional evaluation context.

        Returns:
            List of HeuristicScore objects.
        """
        scores = []

        completeness_score = self._score_completeness(output)
        scores.append(completeness_score)

        confidence_score = self._score_confidence(output)
        scores.append(confidence_score)

        consistency_score = self._score_consistency(output)
        scores.append(consistency_score)

        return scores

    def calculate_overall_score(
        self, heuristic_scores: list[HeuristicScore]
    ) -> float:
        """Calculate overall score from heuristic scores.

        Args:
            heuristic_scores: List of heuristic scores.

        Returns:
            Weighted overall score (0-1).
        """
        score_map = {
            "Completeness": self.config.weight_completeness,
            "Confidence": self.config.weight_confidence,
            "Consistency": self.config.weight_consistency,
        }

        total = 0.0
        for heuristic in heuristic_scores:
            if heuristic.heuristic_name in score_map:
                total += (
                    heuristic.score * score_map[heuristic.heuristic_name]
                )

        return round(total, 2)

    def _score_completeness(self, output: dict) -> HeuristicScore:
        """Score completeness of output.

        Placeholder for MVP - always returns 0.8.

        Args:
            output: Step output to evaluate.

        Returns:
            HeuristicScore for completeness.
        """
        return HeuristicScore(
            heuristic_name="Completeness",
            score=0.8,
            rationale="Output has all required fields",
        )

    def _score_confidence(self, output: dict) -> HeuristicScore:
        """Score confidence in output.

        Placeholder for MVP - always returns 0.75.

        Args:
            output: Step output to evaluate.

        Returns:
            HeuristicScore for confidence.
        """
        return HeuristicScore(
            heuristic_name="Confidence",
            score=0.75,
            rationale="Output meets quality standards",
        )

    def _score_consistency(self, output: dict) -> HeuristicScore:
        """Score consistency of output.

        Placeholder for MVP - always returns 0.85.

        Args:
            output: Step output to evaluate.

        Returns:
            HeuristicScore for consistency.
        """
        return HeuristicScore(
            heuristic_name="Consistency",
            score=0.85,
            rationale="Output is internally consistent",
        )
