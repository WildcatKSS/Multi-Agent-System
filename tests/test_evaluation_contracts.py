"""Tests for evaluation contracts."""

import pytest

from mas.agents.evaluation.contracts import (
    RuleType,
    EvaluationRule,
    HeuristicScore,
    EvaluationReport,
)


class TestRuleType:
    """Tests for RuleType enum."""

    def test_required_rule_type(self) -> None:
        """RuleType.REQUIRED is defined."""
        assert RuleType.REQUIRED == "required"

    def test_optional_rule_type(self) -> None:
        """RuleType.OPTIONAL is defined."""
        assert RuleType.OPTIONAL == "optional"

    def test_blocking_rule_type(self) -> None:
        """RuleType.BLOCKING is defined."""
        assert RuleType.BLOCKING == "blocking"


class TestEvaluationRule:
    """Tests for EvaluationRule."""

    def test_create_required_rule(self) -> None:
        """Can create a required evaluation rule."""
        rule = EvaluationRule(
            name="HasOutput",
            description="Output must not be empty",
            rule_type=RuleType.REQUIRED,
        )

        assert rule.name == "HasOutput"
        assert rule.description == "Output must not be empty"
        assert rule.rule_type == RuleType.REQUIRED
        assert rule.weight == 1.0

    def test_create_optional_rule_with_weight(self) -> None:
        """Can create an optional rule with custom weight."""
        rule = EvaluationRule(
            name="Format",
            description="Output is well-formatted",
            rule_type=RuleType.OPTIONAL,
            weight=0.5,
        )

        assert rule.weight == 0.5

    def test_reject_empty_name(self) -> None:
        """Cannot create rule with empty name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            EvaluationRule(
                name="",
                description="Test",
                rule_type=RuleType.REQUIRED,
            )

    def test_reject_empty_description(self) -> None:
        """Cannot create rule with empty description."""
        with pytest.raises(
            ValueError, match="description cannot be empty"
        ):
            EvaluationRule(
                name="Test",
                description="",
                rule_type=RuleType.REQUIRED,
            )

    def test_reject_invalid_weight(self) -> None:
        """Cannot create rule with weight outside 0-1."""
        with pytest.raises(ValueError, match="weight must be between"):
            EvaluationRule(
                name="Test",
                description="Test",
                rule_type=RuleType.REQUIRED,
                weight=1.5,
            )

        with pytest.raises(ValueError, match="weight must be between"):
            EvaluationRule(
                name="Test",
                description="Test",
                rule_type=RuleType.REQUIRED,
                weight=-0.1,
            )

    def test_immutable(self) -> None:
        """EvaluationRule is immutable (frozen dataclass)."""
        rule = EvaluationRule(
            name="Test",
            description="Test",
            rule_type=RuleType.REQUIRED,
        )

        with pytest.raises(AttributeError):
            rule.name = "Modified"  # type: ignore


class TestHeuristicScore:
    """Tests for HeuristicScore."""

    def test_create_score(self) -> None:
        """Can create a heuristic score."""
        score = HeuristicScore(
            heuristic_name="Completeness",
            score=0.8,
            rationale="All required fields present",
        )

        assert score.heuristic_name == "Completeness"
        assert score.score == 0.8
        assert score.rationale == "All required fields present"

    def test_reject_empty_name(self) -> None:
        """Cannot create score with empty heuristic_name."""
        with pytest.raises(
            ValueError, match="heuristic_name cannot be empty"
        ):
            HeuristicScore(
                heuristic_name="",
                score=0.8,
                rationale="Test",
            )

    def test_reject_invalid_score(self) -> None:
        """Cannot create score outside 0-1 range."""
        with pytest.raises(ValueError, match="score must be between"):
            HeuristicScore(
                heuristic_name="Test",
                score=1.5,
                rationale="Test",
            )

        with pytest.raises(ValueError, match="score must be between"):
            HeuristicScore(
                heuristic_name="Test",
                score=-0.1,
                rationale="Test",
            )

    def test_reject_empty_rationale(self) -> None:
        """Cannot create score with empty rationale."""
        with pytest.raises(ValueError, match="rationale cannot be empty"):
            HeuristicScore(
                heuristic_name="Test",
                score=0.8,
                rationale="",
            )

    def test_immutable(self) -> None:
        """HeuristicScore is immutable (frozen dataclass)."""
        score = HeuristicScore(
            heuristic_name="Test",
            score=0.8,
            rationale="Test",
        )

        with pytest.raises(AttributeError):
            score.score = 0.5  # type: ignore


class TestEvaluationReport:
    """Tests for EvaluationReport."""

    def test_create_passing_report(self) -> None:
        """Can create a passing evaluation report."""
        report = EvaluationReport(
            step_id="step-01",
            passed=True,
            overall_score=0.85,
        )

        assert report.step_id == "step-01"
        assert report.passed is True
        assert report.overall_score == 0.85

    def test_create_failing_report_with_feedback(self) -> None:
        """Can create a failing report with feedback."""
        report = EvaluationReport(
            step_id="step-02",
            passed=False,
            overall_score=0.4,
            feedback="Quality score below threshold",
        )

        assert report.passed is False
        assert report.feedback == "Quality score below threshold"

    def test_create_with_rule_results(self) -> None:
        """Can create report with rule results."""
        rule_results = {"HasOutput": True, "IsValid": False}
        report = EvaluationReport(
            step_id="step-01",
            passed=False,
            overall_score=0.5,
            rule_results=rule_results,
        )

        assert report.rule_results == rule_results

    def test_reject_empty_step_id(self) -> None:
        """Cannot create report with empty step_id."""
        with pytest.raises(ValueError, match="step_id cannot be empty"):
            EvaluationReport(
                step_id="",
                passed=True,
                overall_score=0.8,
            )

    def test_reject_invalid_score(self) -> None:
        """Cannot create report with score outside 0-1."""
        with pytest.raises(ValueError, match="overall_score must be between"):
            EvaluationReport(
                step_id="step-01",
                passed=True,
                overall_score=1.5,
            )

    def test_immutable(self) -> None:
        """EvaluationReport is immutable (frozen dataclass)."""
        report = EvaluationReport(
            step_id="step-01",
            passed=True,
            overall_score=0.8,
        )

        with pytest.raises(AttributeError):
            report.passed = False  # type: ignore
