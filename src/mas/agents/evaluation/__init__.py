"""Evaluation module for quality assessment in the multi-agent system.

Provides deterministic and heuristic-based evaluation of step outputs
before final annotation, with configurable thresholds for pass/fail decisions.
"""

from mas.agents.evaluation.contracts import (
    EvaluationRule,
    HeuristicScore,
    EvaluationReport,
)
from mas.agents.evaluation.rules_engine import DeterministicRulesEngine
from mas.agents.evaluation.heuristics import HeuristicScorer

__all__ = [
    "EvaluationRule",
    "HeuristicScore",
    "EvaluationReport",
    "DeterministicRulesEngine",
    "HeuristicScorer",
]
