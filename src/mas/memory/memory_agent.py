"""Top-level memory agent coordinating episodic and working memory."""

import logging
from typing import Any

from mas.memory.contracts import EpisodicRecord
from mas.memory.episodic_store import EpisodicStore, InMemoryEpisodicStore
from mas.memory.working_memory import RedisWorkingMemory

logger = logging.getLogger(__name__)


class MemoryAgent:
    """Agent coordinating episodic and working memory.

    - Episodic memory: long-term storage of task outcomes
    - Working memory: short-lived Redis-backed key/value store
    """

    def __init__(
        self,
        episodic_store: EpisodicStore | None = None,
        working_memory: RedisWorkingMemory | None = None,
    ) -> None:
        """Initialize the memory agent.

        Args:
            episodic_store: Episodic store (defaults to in-memory).
            working_memory: Working memory (optional; None if Redis unavailable).
        """
        self.episodic_store = episodic_store or InMemoryEpisodicStore()
        self.working_memory = working_memory

    def remember_episode(self, record: EpisodicRecord) -> None:
        """Store an episodic record.

        Args:
            record: The episodic record to remember.

        Raises:
            ValueError: If record ID already exists.
        """
        self.episodic_store.store(record)

    def recall_episodes(self, task_id: str) -> list[EpisodicRecord]:
        """Recall all episodic records for a task.

        Args:
            task_id: The task ID.

        Returns:
            List of records for this task.
        """
        return self.episodic_store.query_by_task(task_id)

    def store_working(self, key: str, value: dict[str, Any]) -> None:
        """Store a value in working memory.

        Args:
            key: The key.
            value: The value (dict).
        """
        if self.working_memory is None:
            logger.debug("Working memory not available; store_working is a no-op")
            return
        self.working_memory.set(key, value)

    def retrieve_working(self, key: str) -> dict[str, Any] | None:
        """Retrieve a value from working memory.

        Args:
            key: The key.

        Returns:
            The value if found, None otherwise.
        """
        if self.working_memory is None:
            return None
        return self.working_memory.get(key)

    def has_working(self, key: str) -> bool:
        """Check if a key exists in working memory.

        Args:
            key: The key.

        Returns:
            True if the key exists, False otherwise.
        """
        if self.working_memory is None:
            return False
        return self.working_memory.exists(key)
