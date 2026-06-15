"""Domain contracts for workflow execution."""

from mas.domain.annotation import Annotation, AnnotationType
from mas.domain.evaluation import Evaluation, EvaluationCriteria
from mas.domain.plan import Plan, Step
from mas.domain.task import Task

__all__ = [
    "Task",
    "Plan",
    "Step",
    "Evaluation",
    "EvaluationCriteria",
    "Annotation",
    "AnnotationType",
]
