"""Tests for memory agent."""

import pytest

from mas.memory.contracts import EpisodicRecord
from mas.memory.episodic_store import InMemoryEpisodicStore
from mas.memory.memory_agent import MemoryAgent
from mas.memory.working_memory import RedisWorkingMemory

try:
    import fakeredis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


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


class TestMemoryAgent:
    """Tests for MemoryAgent."""

    def test_default_agent(self) -> None:
        """Default agent has in-memory episodic store and no working memory."""
        agent = MemoryAgent()
        assert isinstance(agent.episodic_store, InMemoryEpisodicStore)
        assert agent.working_memory is None

    def test_remember_and_recall_episode(self) -> None:
        """Can remember and recall episodes."""
        agent = MemoryAgent()
        record = _record()
        agent.remember_episode(record)
        recalled = agent.recall_episodes("task-1")
        assert len(recalled) == 1
        assert recalled[0].id == "rec-1"

    def test_recall_by_task_id(self) -> None:
        """Can recall episodes by task ID."""
        agent = MemoryAgent()
        agent.remember_episode(_record(id="r1", task_id="task-A"))
        agent.remember_episode(_record(id="r2", task_id="task-B"))
        agent.remember_episode(_record(id="r3", task_id="task-A"))

        results = agent.recall_episodes("task-A")
        assert len(results) == 2
        assert all(r.task_id == "task-A" for r in results)

    def test_recall_unknown_task_returns_empty(self) -> None:
        """Recall returns empty list for unknown task."""
        agent = MemoryAgent()
        assert agent.recall_episodes("unknown") == []

    def test_working_memory_optional(self) -> None:
        """Agent works normally without working memory."""
        agent = MemoryAgent(working_memory=None)

        # These should not raise
        agent.store_working("k", {"x": 1})
        assert agent.retrieve_working("k") is None
        assert agent.has_working("k") is False

    @pytest.mark.skipif(not HAS_REDIS, reason="fakeredis not installed")
    def test_store_and_retrieve_working(self) -> None:
        """Can store and retrieve values in working memory."""
        client = fakeredis.FakeRedis(decode_responses=True)
        wm = RedisWorkingMemory(_client=client)
        agent = MemoryAgent(working_memory=wm)

        agent.store_working("session", {"user": "alice"})
        result = agent.retrieve_working("session")
        assert result == {"user": "alice"}
        assert agent.has_working("session") is True

    @pytest.mark.skipif(not HAS_REDIS, reason="fakeredis not installed")
    def test_working_memory_integration(self) -> None:
        """Full integration test with episodic and working memory."""
        client = fakeredis.FakeRedis(decode_responses=True)
        wm = RedisWorkingMemory(_client=client)
        agent = MemoryAgent(working_memory=wm)

        # Store some working state
        agent.store_working("plan:1", {"status": "running"})

        # Remember an episode
        record = _record()
        agent.remember_episode(record)

        # Retrieve both
        assert agent.retrieve_working("plan:1") == {"status": "running"}
        assert agent.recall_episodes("task-1")[0].id == "rec-1"
