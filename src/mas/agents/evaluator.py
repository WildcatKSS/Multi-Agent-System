"""Evaluator Agent for quality gating of step outputs."""

import logging

from mas.agents.evaluation.contracts import EvaluationReport, RuleType
from mas.agents.evaluation.heuristics import (
    HeuristicConfig,
    HeuristicScorer,
)
from mas.agents.evaluation.rules_engine import DeterministicRulesEngine

logger = logging.getLogger(__name__)


class EvaluatorAgent:
    """Evaluates step outputs for quality before final annotation."""

    def __init__(
        self,
        rules_engine: DeterministicRulesEngine | None = None,
        heuristic_config: HeuristicConfig | None = None,
    ) -> None:
        """Initialize the evaluator agent.

        Args:
            rules_engine: Rules engine instance. Creates default if None.
            heuristic_config: Heuristic configuration. Uses defaults if None.
        """
        self.rules_engine = rules_engine or DeterministicRulesEngine()
        self.heuristic_scorer = HeuristicScorer(heuristic_config)

    def evaluate(
        self, step_id: str, output: dict, context: dict | None = None
    ) -> EvaluationReport:
        """Evaluate step output.

        Args:
            step_id: ID of step being evaluated.
            output: Step output to evaluate.
            context: Optional evaluation context.

        Returns:
            EvaluationReport with pass/fail decision and detailed feedback.
        """
        logger.debug(
            f"Evaluating step {step_id}",
            extra={"step_id": step_id},
        )

        rules_passed, rule_results = self.rules_engine.evaluate(
            output, context or {}
        )

        heuristic_scores = self.heuristic_scorer.score(output, context)
        overall_score = self.heuristic_scorer.calculate_overall_score(
            heuristic_scores
        )

        passed = (
            rules_passed
            and overall_score >= self.heuristic_scorer.config.score_threshold
        )

        feedback = self._generate_feedback(
            rules_passed, rule_results, heuristic_scores, overall_score
        )

        report = EvaluationReport(
            step_id=step_id,
            passed=passed,
            overall_score=overall_score,
            rule_results=rule_results,
            heuristic_scores=heuristic_scores,
            feedback=feedback,
        )

        logger.debug(
            f"Evaluation complete: passed={passed}, score={overall_score}",
            extra={"step_id": step_id, "passed": passed},
        )

        return report

    def _generate_feedback(
        self,
        rules_passed: bool,
        rule_results: dict[str, bool],
        heuristic_scores: list,
        overall_score: float,
    ) -> str:
        """Generate human-readable feedback from evaluation.

        Args:
            rules_passed: Whether all required rules passed.
            rule_results: Results of individual rules.
            heuristic_scores: List of heuristic scores.
            overall_score: Overall score value.

        Returns:
            Feedback string.
        """
        if not rules_passed:
            failed_rules = [
                name for name, result in rule_results.items()
                if not result
            ]
            return f"Failed rules: {', '.join(failed_rules)}"

        if overall_score < self.heuristic_scorer.config.score_threshold:
            return (
                f"Quality score {overall_score:.2f} below threshold "
                f"{self.heuristic_scorer.config.score_threshold}"
            )

        return "Output passed all evaluation checks"
