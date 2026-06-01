"""Deterministic rules engine for evaluation."""

from mas.agents.evaluation.contracts import EvaluationRule, RuleType


class DeterministicRulesEngine:
    """Engine for evaluating deterministic rules against step output."""

    def __init__(self) -> None:
        """Initialize the rules engine."""
        self.rules: list[EvaluationRule] = []

    def add_rule(self, rule: EvaluationRule) -> None:
        """Add a rule to the engine.

        Args:
            rule: Rule to add.
        """
        self.rules.append(rule)

    def evaluate(
        self, output: dict, context: dict | None = None
    ) -> tuple[bool, dict]:
        """Evaluate all rules against step output.

        Args:
            output: Step output to evaluate.
            context: Optional evaluation context.

        Returns:
            Tuple of (passed, results_dict).
            Passed is True only if all required rules pass.
            Results dict maps rule names to boolean pass/fail.
        """
        results = {}
        for rule in self.rules:
            passed = self._evaluate_rule(rule, output, context or {})
            results[rule.name] = passed

        blocking_rules = [
            r for r in self.rules if r.rule_type == RuleType.BLOCKING
        ]
        required_rules = [
            r for r in self.rules if r.rule_type == RuleType.REQUIRED
        ]

        blocking_failed = any(
            not results[r.name] for r in blocking_rules
        )
        required_failed = any(
            not results[r.name] for r in required_rules
        )

        passed = not (blocking_failed or required_failed)

        return passed, results

    def _evaluate_rule(
        self, rule: EvaluationRule, output: dict, context: dict
    ) -> bool:
        """Evaluate a single rule.

        Placeholder for MVP - always returns True.
        Future: Implement rule-specific logic.

        Args:
            rule: Rule to evaluate.
            output: Step output to evaluate against.
            context: Evaluation context.

        Returns:
            True if rule passes, False otherwise.
        """
        return True
