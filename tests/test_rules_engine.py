"""Tests for rules engine."""

import pytest

from mas.agents.evaluation.contracts import (
    EvaluationRule,
    RuleType,
)
from mas.agents.evaluation.rules_engine import (
    DeterministicRulesEngine,
)


class TestDeterministicRulesEngine:
    """Tests for DeterministicRulesEngine."""

    def test_empty_engine(self) -> None:
        """Engine with no rules returns all passed."""
        engine = DeterministicRulesEngine()

        passed, results = engine.evaluate({})

        assert passed is True
        assert results == {}

    def test_single_required_rule(self) -> None:
        """Engine evaluates single required rule."""
        engine = DeterministicRulesEngine()
        rule = EvaluationRule(
            name="HasOutput",
            description="Must have output",
            rule_type=RuleType.REQUIRED,
        )
        engine.add_rule(rule)

        passed, results = engine.evaluate({"output": "test"})

        assert passed is True
        assert results["HasOutput"] is True

    def test_single_optional_rule(self) -> None:
        """Engine evaluates single optional rule."""
        engine = DeterministicRulesEngine()
        rule = EvaluationRule(
            name="Format",
            description="Well formatted",
            rule_type=RuleType.OPTIONAL,
        )
        engine.add_rule(rule)

        passed, results = engine.evaluate({})

        assert passed is True
        assert "Format" in results

    def test_multiple_rules_all_pass(self) -> None:
        """Engine passes when all rules pass."""
        engine = DeterministicRulesEngine()
        rule1 = EvaluationRule(
            name="Rule1",
            description="First rule",
            rule_type=RuleType.REQUIRED,
        )
        rule2 = EvaluationRule(
            name="Rule2",
            description="Second rule",
            rule_type=RuleType.REQUIRED,
        )
        engine.add_rule(rule1)
        engine.add_rule(rule2)

        passed, results = engine.evaluate({})

        assert passed is True
        assert results["Rule1"] is True
        assert results["Rule2"] is True

    def test_blocking_rule_failure(self) -> None:
        """Blocking rule failure prevents pass."""
        engine = DeterministicRulesEngine()
        blocking_rule = EvaluationRule(
            name="MustPass",
            description="Blocking rule",
            rule_type=RuleType.BLOCKING,
        )
        engine.add_rule(blocking_rule)

        passed, results = engine.evaluate({})

        assert passed is False
        assert results["MustPass"] is False

    def test_required_rule_failure(self) -> None:
        """Required rule failure prevents pass."""
        engine = DeterministicRulesEngine()
        required_rule = EvaluationRule(
            name="Essential",
            description="Required rule",
            rule_type=RuleType.REQUIRED,
        )
        engine.add_rule(required_rule)

        passed, results = engine.evaluate({})

        assert passed is False
        assert results["Essential"] is False

    def test_optional_rule_failure_allows_pass(self) -> None:
        """Optional rule failure doesn't prevent pass."""
        engine = DeterministicRulesEngine()
        optional_rule = EvaluationRule(
            name="Optional",
            description="Optional rule",
            rule_type=RuleType.OPTIONAL,
        )
        engine.add_rule(optional_rule)

        passed, results = engine.evaluate({})

        assert passed is True
        assert results["Optional"] is False

    def test_mixed_rule_types_blocking_fails(self) -> None:
        """Mixed rules with blocking failure fails overall."""
        engine = DeterministicRulesEngine()
        engine.add_rule(
            EvaluationRule(
                name="Blocking",
                description="Blocking",
                rule_type=RuleType.BLOCKING,
            )
        )
        engine.add_rule(
            EvaluationRule(
                name="Optional",
                description="Optional",
                rule_type=RuleType.OPTIONAL,
            )
        )

        passed, results = engine.evaluate({})

        assert passed is False
        assert results["Blocking"] is False
        assert results["Optional"] is False

    def test_mixed_rule_types_all_pass(self) -> None:
        """Mixed rules all passing results in overall pass."""
        engine = DeterministicRulesEngine()
        engine.add_rule(
            EvaluationRule(
                name="Required",
                description="Required",
                rule_type=RuleType.REQUIRED,
            )
        )
        engine.add_rule(
            EvaluationRule(
                name="Optional",
                description="Optional",
                rule_type=RuleType.OPTIONAL,
            )
        )
        engine.add_rule(
            EvaluationRule(
                name="Blocking",
                description="Blocking",
                rule_type=RuleType.BLOCKING,
            )
        )

        passed, results = engine.evaluate({})

        assert passed is True
        for rule_name in ["Required", "Optional", "Blocking"]:
            assert results[rule_name] is True

    def test_add_rule_multiple_times(self) -> None:
        """Can add multiple rules to engine."""
        engine = DeterministicRulesEngine()

        for i in range(5):
            rule = EvaluationRule(
                name=f"Rule{i}",
                description=f"Rule {i}",
                rule_type=RuleType.OPTIONAL,
            )
            engine.add_rule(rule)

        passed, results = engine.evaluate({})

        assert len(results) == 5
        for i in range(5):
            assert results[f"Rule{i}"] is True
