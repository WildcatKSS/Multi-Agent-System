"""Tests for memory layer contracts."""

import pytest

from mas.memory.contracts import (
    EpisodicRecord,
    MemoryEntry,
    MemoryType,
)


class TestMemoryType:
    """Tests for MemoryType enum."""

    def test_working(self) -> None:
        """MemoryType.WORKING has correct value."""
        assert MemoryType.WORKING == "working"

    def test_episodic(self) -> None:
        """MemoryType.EPISODIC has correct value."""
        assert MemoryType.EPISODIC == "episodic"


class TestMemoryEntry:
    """Tests for MemoryEntry dataclass."""

    def test_create(self) -> None:
        """Can create a memory entry."""
        entry = MemoryEntry(
            id="mem-1",
            content={"data": "test"},
            memory_type=MemoryType.WORKING,
            task_id="task-1",
            step_id="step-1",
            timestamp="2026-06-02T23:00:00Z",
        )
        assert entry.id == "mem-1"
        assert entry.task_id == "task-1"

    def test_default_metadata(self) -> None:
        """Metadata defaults to empty dict."""
        entry = MemoryEntry(
            id="mem-1",
            content={},
            memory_type=MemoryType.WORKING,
            task_id="task-1",
            step_id="step-1",
            timestamp="2026-06-02T23:00:00Z",
        )
        assert entry.metadata == {}

    def test_reject_empty_id(self) -> None:
        """Reject empty id."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            MemoryEntry(
                id="",
                content={},
                memory_type=MemoryType.WORKING,
                task_id="task-1",
                step_id="step-1",
                timestamp="2026-06-02T23:00:00Z",
            )

    def test_reject_empty_task_id(self) -> None:
        """Reject empty task_id."""
        with pytest.raises(ValueError, match="task_id cannot be empty"):
            MemoryEntry(
                id="mem-1",
                content={},
                memory_type=MemoryType.WORKING,
                task_id="",
                step_id="step-1",
                timestamp="2026-06-02T23:00:00Z",
            )

    def test_reject_none_content(self) -> None:
        """Reject None content."""
        with pytest.raises(ValueError, match="content cannot be None"):
            MemoryEntry(
                id="mem-1",
                content=None,  # type: ignore
                memory_type=MemoryType.WORKING,
                task_id="task-1",
                step_id="step-1",
                timestamp="2026-06-02T23:00:00Z",
            )

    def test_immutable(self) -> None:
        """MemoryEntry is immutable."""
        entry = MemoryEntry(
            id="mem-1",
            content={},
            memory_type=MemoryType.WORKING,
            task_id="task-1",
            step_id="step-1",
            timestamp="2026-06-02T23:00:00Z",
        )
        with pytest.raises(AttributeError):
            entry.id = "mem-2"  # type: ignore


class TestEpisodicRecord:
    """Tests for EpisodicRecord dataclass."""

    def test_create(self) -> None:
        """Can create an episodic record."""
        record = EpisodicRecord(
            id="rec-1",
            task_id="task-1",
            plan_id="plan-1",
            steps_executed=3,
            outcome="success",
            score=0.85,
            duration_seconds=10.5,
        )
        assert record.id == "rec-1"
        assert record.score == 0.85

    def test_default_lessons(self) -> None:
        """Lessons defaults to empty list."""
        record = EpisodicRecord(
            id="rec-1",
            task_id="task-1",
            plan_id="plan-1",
            steps_executed=1,
            outcome="success",
            score=0.9,
            duration_seconds=5.0,
        )
        assert record.lessons == []

    def test_boundary_score_zero(self) -> None:
        """Score of 0.0 is valid."""
        record = EpisodicRecord(
            id="rec-1",
            task_id="task-1",
            plan_id="plan-1",
            steps_executed=1,
            outcome="failed",
            score=0.0,
            duration_seconds=1.0,
        )
        assert record.score == 0.0

    def test_boundary_score_one(self) -> None:
        """Score of 1.0 is valid."""
        record = EpisodicRecord(
            id="rec-1",
            task_id="task-1",
            plan_id="plan-1",
            steps_executed=5,
            outcome="success",
            score=1.0,
            duration_seconds=20.0,
        )
        assert record.score == 1.0

    def test_reject_empty_id(self) -> None:
        """Reject empty id."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            EpisodicRecord(
                id="",
                task_id="task-1",
                plan_id="plan-1",
                steps_executed=1,
                outcome="success",
                score=0.5,
                duration_seconds=1.0,
            )

    def test_reject_empty_task_id(self) -> None:
        """Reject empty task_id."""
        with pytest.raises(ValueError, match="task_id cannot be empty"):
            EpisodicRecord(
                id="rec-1",
                task_id="",
                plan_id="plan-1",
                steps_executed=1,
                outcome="success",
                score=0.5,
                duration_seconds=1.0,
            )

    def test_reject_score_above_one(self) -> None:
        """Reject score > 1.0."""
        with pytest.raises(ValueError, match="score must be between 0 and 1"):
            EpisodicRecord(
                id="rec-1",
                task_id="task-1",
                plan_id="plan-1",
                steps_executed=1,
                outcome="success",
                score=1.001,
                duration_seconds=1.0,
            )

    def test_reject_score_below_zero(self) -> None:
        """Reject score < 0.0."""
        with pytest.raises(ValueError, match="score must be between 0 and 1"):
            EpisodicRecord(
                id="rec-1",
                task_id="task-1",
                plan_id="plan-1",
                steps_executed=1,
                outcome="failed",
                score=-0.001,
                duration_seconds=1.0,
            )

    def test_immutable(self) -> None:
        """EpisodicRecord is immutable."""
        record = EpisodicRecord(
            id="rec-1",
            task_id="task-1",
            plan_id="plan-1",
            steps_executed=1,
            outcome="success",
            score=0.8,
            duration_seconds=5.0,
        )
        with pytest.raises(AttributeError):
            record.score = 0.9  # type: ignore
