"""Annotation contract: metadata attached to domain objects."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AnnotationType(Enum):
    """Type of annotation."""

    TAG = "tag"
    METADATA = "metadata"
    INTENT = "intent"
    CONFIDENCE = "confidence"
    SOURCE = "source"
    TIMESTAMP = "timestamp"
    CUSTOM = "custom"


@dataclass
class Annotation:
    """Metadata annotation attached to domain objects.

    Annotations allow attaching arbitrary key-value metadata to tasks,
    plans, steps, and evaluations without modifying their core structure.
    """

    key: str
    value: Any
    annotation_type: AnnotationType = AnnotationType.METADATA
    source: str = ""
    confidence: float = 1.0

    def __post_init__(self) -> None:
        """Validate annotation on creation."""
        if not self.key:
            raise ValueError("Annotation key cannot be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if annotation confidence meets threshold."""
        return self.confidence >= threshold

    def is_low_confidence(self, threshold: float = 0.5) -> bool:
        """Check if annotation confidence is below threshold."""
        return self.confidence < threshold

    def __repr__(self) -> str:
        """String representation showing key, type, and confidence."""
        return f"Annotation({self.key}={self.value!r}, type={self.annotation_type.value}, confidence={self.confidence})"
