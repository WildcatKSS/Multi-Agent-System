"""Tests for episodic memory store."""

import pytest

from mas.memory.contracts import EpisodicRecord
from mas.memory.episodic_store import InMemoryEpisodicStore


def _record(
    id: str = "rec-1",
    task_id: str = "task-1",
    plan_id: str = "plan-1",
    score: float = 0.8,
) -> EpisodicRecord:
    """Helper to create an episodic record."""
    return EpisodicRecord(
        id=id,
        task_id=task_id,
        plan_id=plan_id,
        steps_executed=3,
        outcome="success",
        score=score,
        duration_seconds=1.5,
    )


class TestInMemoryEpisodicStore:
    """Tests for InMemoryEpisodicStore."""

    def test_store_and_get(self) -> None:
        """Can store and retrieve a record."""
        store = InMemoryEpisodicStore()
        r = _record()
        store.store(r)
        assert store.get("rec-1") == r

    def test_get_missing_returns_none(self) -> None:
        """Get returns None for missing record."""
        store = InMemoryEpisodicStore()
        assert store.get("nonexistent") is None

    def test_query_by_task(self) -> None:
        """Can query records by task ID."""
        store = InMemoryEpisodicStore()
        store.store(_record(id="r1", task_id="task-A"))
        store.store(_record(id="r2", task_id="task-B"))
        store.store(_record(id="r3", task_id="task-A"))

        results = store.query_by_task("task-A")
        assert len(results) == 2
        assert all(r.task_id == "task-A" for r in results)

    def test_query_missing_task_returns_empty(self) -> None:
        """Query returns empty list for unknown task."""
        store = InMemoryEpisodicStore()
        assert store.query_by_task("unknown") == []

    def test_all_records(self) -> None:
        """Can get all records."""
        store = InMemoryEpisodicStore()
        store.store(_record(id="r1"))
        store.store(_record(id="r2"))
        assert len(store.all_records()) == 2

    def test_clear(self) -> None:
        """Can clear all records."""
        store = InMemoryEpisodicStore()
        store.store(_record())
        store.clear()
        assert store.all_records() == []
        assert store.get("rec-1") is None

    def test_duplicate_raises(self) -> None:
        """Store raises on duplicate ID."""
        store = InMemoryEpisodicStore()
        r = _record()
        store.store(r)
        with pytest.raises(ValueError, match="already exists"):
            store.store(r)
