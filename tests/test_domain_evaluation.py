"""Tests for Evaluation domain contract."""

import pytest

from mas.domain.evaluation import Evaluation, EvaluationCriteria


class TestEvaluation:
    """Tests for Evaluation dataclass."""

    def test_evaluation_creation(self) -> None:
        """Can create an evaluation with required fields."""
        evaluation = Evaluation(
            id="eval-1",
            task_id="task-1",
            plan_id="plan-1",
            score=8.5,
        )
        assert evaluation.id == "eval-1"
        assert evaluation.task_id == "task-1"
        assert evaluation.plan_id == "plan-1"
        assert evaluation.score == 8.5
        assert not evaluation.passed

    def test_evaluation_with_criteria(self) -> None:
        """Evaluation can store criterion scores."""
        criteria = {
            "correctness": 9.0,
            "completeness": 8.5,
            "efficiency": 7.0,
        }
        evaluation = Evaluation(
            id="eval-1",
            task_id="task-1",
            plan_id="plan-1",
            score=8.2,
            criteria=criteria,
        )
        assert evaluation.criteria == criteria

    def test_evaluation_validation_invalid_score(self) -> None:
        """Evaluation creation fails with invalid score."""
        with pytest.raises(ValueError, match="Score must be between"):
            Evaluation(
                id="eval-1",
                task_id="task-1",
                plan_id="plan-1",
                score=10.5,
            )

    def test_evaluation_validation_invalid_criterion_score(self) -> None:
        """Evaluation creation fails with invalid criterion score."""
        criteria = {"correctness": 11.0}
        with pytest.raises(ValueError, match="score must be between"):
            Evaluation(
                id="eval-1",
                task_id="task-1",
                plan_id="plan-1",
                score=9.0,
                criteria=criteria,
            )

    def test_evaluation_from_criteria(self) -> None:
        """Can create evaluation from criterion scores."""
        criteria = {
            "correctness": 10.0,
            "completeness": 8.0,
            "efficiency": 6.0,
        }
        evaluation = Evaluation.from_criteria(
            task_id="task-1",
            plan_id="plan-1",
            criteria_scores=criteria,
            feedback="Good execution",
            passed=True,
        )
        assert evaluation.task_id == "task-1"
        assert evaluation.plan_id == "plan-1"
        assert evaluation.criteria == criteria
        assert evaluation.score == 8.0  # Average of 10, 8, 6
        assert evaluation.feedback == "Good execution"
        assert evaluation.passed

    def test_evaluation_from_criteria_empty(self) -> None:
        """from_criteria handles empty criteria."""
        evaluation = Evaluation.from_criteria(
            task_id="task-1",
            plan_id="plan-1",
            criteria_scores={},
        )
        assert evaluation.score == 0.0
        assert len(evaluation.criteria) == 0

    def test_evaluation_meets_threshold(self) -> None:
        """meets_minimum_threshold() checks score against threshold."""
        evaluation = Evaluation(
            id="eval-1",
            task_id="task-1",
            plan_id="plan-1",
            score=8.5,
        )
        assert evaluation.meets_minimum_threshold(8.0)
        assert not evaluation.meets_minimum_threshold(9.0)

    def test_evaluation_has_issues(self) -> None:
        """has_issues() checks if evaluation found issues."""
        evaluation_no_issues = Evaluation(
            id="eval-1",
            task_id="task-1",
            plan_id="plan-1",
            score=9.0,
            issues=[],
        )
        assert not evaluation_no_issues.has_issues()

        evaluation_with_issues = Evaluation(
            id="eval-2",
            task_id="task-1",
            plan_id="plan-1",
            score=6.0,
            issues=["Response too long", "Missing context"],
        )
        assert evaluation_with_issues.has_issues()

    def test_evaluation_critical_issues(self) -> None:
        """get_critical_issues() filters marked critical issues."""
        evaluation = Evaluation(
            id="eval-1",
            task_id="task-1",
            plan_id="plan-1",
            score=5.0,
            issues=[
                "CRITICAL: Failed to complete task",
                "Warning: Low confidence",
                "CRITICAL: Security violation",
            ],
        )
        critical = evaluation.get_critical_issues()
        assert len(critical) == 2
        assert all(issue.startswith("CRITICAL:") for issue in critical)
