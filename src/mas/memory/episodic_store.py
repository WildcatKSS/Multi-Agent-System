"""Episodic memory storage interface and in-memory implementation."""

from abc import ABC, abstractmethod

from mas.memory.contracts import EpisodicRecord


class EpisodicStore(ABC):
    """Abstract interface for episodic memory storage.

    Episodic memory stores records of completed task executions so the system
    can learn over time. Implementations can range from in-memory to persistent
    stores (JSON, SQLite, PostgreSQL, etc.).
    """

    @abstractmethod
    def store(self, record: EpisodicRecord) -> None:
        """Store an episodic record.

        Args:
            record: The episodic record to store.

        Raises:
            ValueError: If a record with the same ID already exists.
        """
        ...

    @abstractmethod
    def get(self, record_id: str) -> EpisodicRecord | None:
        """Retrieve a record by ID.

        Args:
            record_id: The record ID to look up.

        Returns:
            The record if found, None otherwise.
        """
        ...

    @abstractmethod
    def query_by_task(self, task_id: str) -> list[EpisodicRecord]:
        """Query all records for a specific task.

        Args:
            task_id: The task ID to query.

        Returns:
            List of records for this task (empty if none found).
        """
        ...

    @abstractmethod
    def all_records(self) -> list[EpisodicRecord]:
        """Get all stored records.

        Returns:
            List of all records.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored records."""
        ...


class InMemoryEpisodicStore(EpisodicStore):
    """In-memory episodic store (MVP default).

    Stores records in a dict. Suitable for development and testing.
    For production, consider swapping with a persistent store.
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory store."""
        self._records: dict[str, EpisodicRecord] = {}

    def store(self, record: EpisodicRecord) -> None:
        """Store an episodic record.

        Args:
            record: The record to store.

        Raises:
            ValueError: If a record with this ID already exists.
        """
        if record.id in self._records:
            raise ValueError(f"Record with id '{record.id}' already exists")
        self._records[record.id] = record

    def get(self, record_id: str) -> EpisodicRecord | None:
        """Retrieve a record by ID.

        Args:
            record_id: The record ID.

        Returns:
            The record if found, None otherwise.
        """
        return self._records.get(record_id)

    def query_by_task(self, task_id: str) -> list[EpisodicRecord]:
        """Query all records for a task.

        Args:
            task_id: The task ID.

        Returns:
            List of records for this task.
        """
        return [r for r in self._records.values() if r.task_id == task_id]

    def all_records(self) -> list[EpisodicRecord]:
        """Get all stored records.

        Returns:
            List of all records (a copy of the values).
        """
        return list(self._records.values())

    def clear(self) -> None:
        """Clear all stored records."""
        self._records.clear()
