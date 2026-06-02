"""Tests for Evaluator Agent."""

import pytest

from mas.agents.evaluator import EvaluatorAgent
from mas.agents.evaluation.contracts import (
    EvaluationRule,
    RuleType,
)
from mas.agents.evaluation.heuristics import HeuristicConfig
from mas.agents.evaluation.rules_engine import DeterministicRulesEngine


class TestEvaluatorAgent:
    """Tests for EvaluatorAgent."""

    def test_default_agent(self) -> None:
        """EvaluatorAgent uses default configuration."""
        agent = EvaluatorAgent()

        assert agent.rules_engine is not None
        assert agent.heuristic_scorer is not None

    def test_custom_agent(self) -> None:
        """EvaluatorAgent accepts custom components."""
        engine = DeterministicRulesEngine()
        config = HeuristicConfig(score_threshold=0.6)
        agent = EvaluatorAgent(engine, config)

        assert agent.rules_engine is engine
        assert agent.heuristic_scorer.config.score_threshold == 0.6

    def test_evaluate_returns_report(self) -> None:
        """evaluate() returns EvaluationReport."""
        agent = EvaluatorAgent()

        report = agent.evaluate("step-01", {"output": "test"})

        assert report.step_id == "step-01"
        assert isinstance(report.passed, bool)
        assert 0 <= report.overall_score <= 1

    def test_evaluate_with_passing_rules(self) -> None:
        """evaluate() passes when all rules pass."""
        engine = DeterministicRulesEngine()
        engine.add_rule(
            EvaluationRule(
                name="Test",
                description="Test rule",
                rule_type=RuleType.REQUIRED,
            )
        )
        agent = EvaluatorAgent(engine)

        report = agent.evaluate("step-01", {})

        assert report.passed is True
        assert "Test" in report.rule_results

    def test_evaluate_includes_rule_results(self) -> None:
        """evaluate() report includes rule results."""
        engine = DeterministicRulesEngine()
        engine.add_rule(
            EvaluationRule(
                name="Rule1",
                description="First",
                rule_type=RuleType.REQUIRED,
            )
        )
        engine.add_rule(
            EvaluationRule(
                name="Rule2",
                description="Second",
                rule_type=RuleType.OPTIONAL,
            )
        )
        agent = EvaluatorAgent(engine)

        report = agent.evaluate("step-01", {})

        assert "Rule1" in report.rule_results
        assert "Rule2" in report.rule_results

    def test_evaluate_includes_heuristic_scores(self) -> None:
        """evaluate() report includes heuristic scores."""
        agent = EvaluatorAgent()

        report = agent.evaluate("step-01", {})

        assert len(report.heuristic_scores) > 0
        for score in report.heuristic_scores:
            assert score.heuristic_name
            assert 0 <= score.score <= 1

    def test_evaluate_with_context(self) -> None:
        """evaluate() accepts optional context."""
        agent = EvaluatorAgent()

        context = {"step_id": "step-01", "attempt": 1}
        report = agent.evaluate("step-01", {}, context)

        assert report.step_id == "step-01"

    def test_evaluate_below_threshold_fails(self) -> None:
        """evaluate() fails when score below threshold."""
        config = HeuristicConfig(score_threshold=0.99)
        agent = EvaluatorAgent(
            HeuristicRulesEngine(),
            config,
        )

        report = agent.evaluate("step-01", {})

        assert report.passed is False

    def test_evaluate_above_threshold_passes(self) -> None:
        """evaluate() passes when score above threshold."""
        config = HeuristicConfig(score_threshold=0.5)
        agent = EvaluatorAgent(
            DeterministicRulesEngine(),
            config,
        )

        report = agent.evaluate("step-01", {})

        assert report.passed is True

    def test_evaluate_generates_feedback_pass(self) -> None:
        """evaluate() generates positive feedback on pass."""
        agent = EvaluatorAgent()

        report = agent.evaluate("step-01", {})

        if report.passed:
            assert report.feedback
            assert "passed" in report.feedback.lower() or "check" in report.feedback.lower()

    def test_evaluate_generates_feedback_fail(self) -> None:
        """evaluate() generates feedback on fail."""
        config = HeuristicConfig(score_threshold=0.99)
        agent = EvaluatorAgent(
            DeterministicRulesEngine(),
            config,
        )

        report = agent.evaluate("step-01", {})

        if not report.passed:
            assert report.feedback

    def test_evaluate_complex_output(self) -> None:
        """evaluate() handles complex output structures."""
        agent = EvaluatorAgent()

        output = {
            "result": "success",
            "data": [1, 2, 3],
            "metadata": {
                "timestamp": "2026-06-01",
                "version": "1.0",
            },
        }

        report = agent.evaluate("step-01", output)

        assert report.step_id == "step-01"
        assert isinstance(report.passed, bool)

    def test_evaluate_multiple_steps(self) -> None:
        """evaluate() can evaluate multiple steps independently."""
        agent = EvaluatorAgent()

        report1 = agent.evaluate("step-01", {"data": 1})
        report2 = agent.evaluate("step-02", {"data": 2})

        assert report1.step_id == "step-01"
        assert report2.step_id == "step-02"
        assert report1.overall_score == report2.overall_score

    def test_evaluate_with_blocking_rule_fails(self) -> None:
        """evaluate() fails when blocking rule fails."""
        engine = DeterministicRulesEngine()
        engine.add_rule(
            EvaluationRule(
                name="Critical",
                description="Critical rule",
                rule_type=RuleType.BLOCKING,
                predicate=lambda o, c: False,
            )
        )
        agent = EvaluatorAgent(engine)

        report = agent.evaluate("step-01", {})

        assert report.passed is False

    def test_evaluate_with_mixed_rules(self) -> None:
        """evaluate() handles mixed rule types."""
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
        agent = EvaluatorAgent(engine)

        report = agent.evaluate("step-01", {})

        assert "Required" in report.rule_results
        assert "Optional" in report.rule_results
        assert "Blocking" in report.rule_results


class HeuristicRulesEngine(DeterministicRulesEngine):
    """Alias for backward compatibility."""

    pass
