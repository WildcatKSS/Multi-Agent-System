"""Tests for Annotation domain contract."""

import pytest

from mas.domain.annotation import Annotation, AnnotationType


class TestAnnotation:
    """Tests for Annotation dataclass."""

    def test_annotation_creation(self) -> None:
        """Can create an annotation."""
        annotation = Annotation(
            key="priority",
            value="high",
        )
        assert annotation.key == "priority"
        assert annotation.value == "high"
        assert annotation.annotation_type == AnnotationType.METADATA
        assert annotation.confidence == 1.0

    def test_annotation_with_type(self) -> None:
        """Annotation can have a specific type."""
        annotation = Annotation(
            key="sentiment",
            value="positive",
            annotation_type=AnnotationType.INTENT,
        )
        assert annotation.annotation_type == AnnotationType.INTENT

    def test_annotation_with_source(self) -> None:
        """Annotation can track its source."""
        annotation = Annotation(
            key="language",
            value="en",
            source="nlp-model",
        )
        assert annotation.source == "nlp-model"

    def test_annotation_with_confidence(self) -> None:
        """Annotation can have a confidence score."""
        annotation = Annotation(
            key="entity_type",
            value="person",
            confidence=0.95,
        )
        assert annotation.confidence == 0.95

    def test_annotation_validation_empty_key(self) -> None:
        """Annotation creation fails with empty key."""
        with pytest.raises(ValueError, match="key cannot be empty"):
            Annotation(key="", value="test")

    def test_annotation_validation_invalid_confidence(self) -> None:
        """Annotation creation fails with invalid confidence."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            Annotation(key="test", value="test", confidence=1.5)

        with pytest.raises(ValueError, match="Confidence must be between"):
            Annotation(key="test", value="test", confidence=-0.1)

    def test_annotation_is_high_confidence(self) -> None:
        """is_high_confidence() checks against threshold."""
        annotation = Annotation(
            key="test",
            value="value",
            confidence=0.9,
        )
        assert annotation.is_high_confidence(0.8)
        assert not annotation.is_high_confidence(0.95)

    def test_annotation_is_low_confidence(self) -> None:
        """is_low_confidence() checks against threshold."""
        annotation = Annotation(
            key="test",
            value="value",
            confidence=0.4,
        )
        assert annotation.is_low_confidence(0.5)
        assert not annotation.is_low_confidence(0.3)

    def test_annotation_repr(self) -> None:
        """Annotation has meaningful string representation."""
        annotation = Annotation(
            key="priority",
            value="high",
            annotation_type=AnnotationType.TAG,
            confidence=0.95,
        )
        repr_str = repr(annotation)
        assert "priority" in repr_str
        assert "high" in repr_str
        assert "0.95" in repr_str

    def test_annotation_various_value_types(self) -> None:
        """Annotation can store various value types."""
        # String
        ann_str = Annotation(key="type", value="text")
        assert ann_str.value == "text"

        # Number
        ann_num = Annotation(key="count", value=42)
        assert ann_num.value == 42

        # List
        ann_list = Annotation(key="tags", value=["tag1", "tag2"])
        assert ann_list.value == ["tag1", "tag2"]

        # Dict
        ann_dict = Annotation(key="metadata", value={"nested": "value"})
        assert ann_dict.value == {"nested": "value"}
