"""Tests for heuristic scoring."""

import pytest

from mas.agents.evaluation.heuristics import (
    HeuristicConfig,
    HeuristicScorer,
)


class TestHeuristicConfig:
    """Tests for HeuristicConfig."""

    def test_default_config(self) -> None:
        """HeuristicConfig has sensible defaults."""
        config = HeuristicConfig()

        assert config.score_threshold == 0.5
        assert config.weight_completeness == 0.3
        assert config.weight_confidence == 0.4
        assert config.weight_consistency == 0.3

    def test_custom_config(self) -> None:
        """Can create custom HeuristicConfig."""
        config = HeuristicConfig(
            score_threshold=0.7,
            weight_completeness=0.2,
            weight_confidence=0.5,
            weight_consistency=0.3,
        )

        assert config.score_threshold == 0.7
        assert config.weight_completeness == 0.2
        assert config.weight_confidence == 0.5
        assert config.weight_consistency == 0.3

    def test_reject_invalid_threshold(self) -> None:
        """Cannot create config with invalid score_threshold."""
        with pytest.raises(ValueError, match="score_threshold must be between"):
            HeuristicConfig(score_threshold=1.5)

        with pytest.raises(ValueError, match="score_threshold must be between"):
            HeuristicConfig(score_threshold=-0.1)

    def test_reject_invalid_weights(self) -> None:
        """Cannot create config with invalid weights."""
        with pytest.raises(ValueError, match="weight_completeness must be between"):
            HeuristicConfig(weight_completeness=1.5)

        with pytest.raises(ValueError, match="weight_confidence must be between"):
            HeuristicConfig(weight_confidence=-0.1)

        with pytest.raises(ValueError, match="weight_consistency must be between"):
            HeuristicConfig(weight_consistency=2.0)

    def test_reject_weights_not_summing_to_one(self) -> None:
        """Cannot create config with weights not summing to 1."""
        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            HeuristicConfig(
                weight_completeness=0.5,
                weight_confidence=0.3,
                weight_consistency=0.3,
            )

    def test_immutable(self) -> None:
        """HeuristicConfig is immutable (frozen dataclass)."""
        config = HeuristicConfig()

        with pytest.raises(AttributeError):
            config.score_threshold = 0.9  # type: ignore


class TestHeuristicScorer:
    """Tests for HeuristicScorer."""

    def test_default_scorer(self) -> None:
        """HeuristicScorer uses default config if none provided."""
        scorer = HeuristicScorer()

        assert scorer.config.score_threshold == 0.5

    def test_custom_scorer(self) -> None:
        """HeuristicScorer uses custom config if provided."""
        config = HeuristicConfig(score_threshold=0.7)
        scorer = HeuristicScorer(config)

        assert scorer.config.score_threshold == 0.7

    def test_score_returns_three_heuristics(self) -> None:
        """score() returns three heuristic scores."""
        scorer = HeuristicScorer()

        scores = scorer.score({})

        assert len(scores) == 3
        names = {s.heuristic_name for s in scores}
        assert "Completeness" in names
        assert "Confidence" in names
        assert "Consistency" in names

    def test_all_heuristics_valid(self) -> None:
        """All returned heuristics are valid."""
        scorer = HeuristicScorer()

        scores = scorer.score({})

        for score in scores:
            assert 0 <= score.score <= 1
            assert score.heuristic_name
            assert score.rationale

    def test_calculate_overall_score_default(self) -> None:
        """Overall score calculation uses correct weights."""
        config = HeuristicConfig(
            weight_completeness=0.5,
            weight_confidence=0.3,
            weight_consistency=0.2,
        )
        scorer = HeuristicScorer(config)

        from mas.agents.evaluation.contracts import HeuristicScore

        scores = [
            HeuristicScore(
                heuristic_name="Completeness", score=1.0, rationale="Full"
            ),
            HeuristicScore(
                heuristic_name="Confidence", score=0.6, rationale="Medium"
            ),
            HeuristicScore(
                heuristic_name="Consistency", score=0.5, rationale="Half"
            ),
        ]

        overall = scorer.calculate_overall_score(scores)

        expected = (1.0 * 0.5) + (0.6 * 0.3) + (0.5 * 0.2)
        assert abs(overall - round(expected, 2)) < 0.01

    def test_score_with_context(self) -> None:
        """score() accepts optional context parameter."""
        scorer = HeuristicScorer()

        context = {"step_id": "step-01"}
        scores = scorer.score({}, context)

        assert len(scores) == 3

    def test_score_with_empty_output(self) -> None:
        """score() handles empty output dict."""
        scorer = HeuristicScorer()

        scores = scorer.score({})

        assert len(scores) == 3
        for score in scores:
            assert score.score >= 0

    def test_score_with_complex_output(self) -> None:
        """score() handles complex output structure."""
        scorer = HeuristicScorer()

        output = {
            "result": "success",
            "data": {"nested": {"value": 123}},
            "metadata": {"timestamp": "2026-06-01"},
        }

        scores = scorer.score(output)

        assert len(scores) == 3

    def test_overall_score_bounds(self) -> None:
        """Overall score is always between 0 and 1."""
        scorer = HeuristicScorer()

        from mas.agents.evaluation.contracts import HeuristicScore

        for test_scores in [
            [
                HeuristicScore("C", 1.0, "Max"),
                HeuristicScore("Conf", 1.0, "Max"),
                HeuristicScore("Con", 1.0, "Max"),
            ],
            [
                HeuristicScore("C", 0.0, "Min"),
                HeuristicScore("Conf", 0.0, "Min"),
                HeuristicScore("Con", 0.0, "Min"),
            ],
        ]:
            overall = scorer.calculate_overall_score(test_scores)
            assert 0 <= overall <= 1
