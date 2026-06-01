"""Tests for memory contracts."""

import pytest

from mas.memory.contracts import MemoryEntry, MemoryKey


class TestMemoryKey:
    """Tests for MemoryKey."""

    def test_create_key(self) -> None:
        """Can create memory key."""
        key = MemoryKey(namespace="session", key="workflow-01")

        assert key.namespace == "session"
        assert key.key == "workflow-01"

    def test_full_key(self) -> None:
        """full_key() returns qualified key."""
        key = MemoryKey(namespace="session", key="workflow-01")

        assert key.full_key() == "session:workflow-01"

    def test_reject_empty_namespace(self) -> None:
        """Cannot create key with empty namespace."""
        with pytest.raises(ValueError, match="namespace cannot be empty"):
            MemoryKey(namespace="", key="test")

    def test_reject_empty_key(self) -> None:
        """Cannot create key with empty key."""
        with pytest.raises(ValueError, match="key cannot be empty"):
            MemoryKey(namespace="session", key="")

    def test_immutable(self) -> None:
        """MemoryKey is immutable (frozen dataclass)."""
        key = MemoryKey(namespace="session", key="test")

        with pytest.raises(AttributeError):
            key.namespace = "other"  # type: ignore


class TestMemoryEntry:
    """Tests for MemoryEntry."""

    def test_create_entry(self) -> None:
        """Can create memory entry."""
        key = MemoryKey(namespace="session", key="state")
        entry = MemoryEntry(key=key, value={"step": 1})

        assert entry.key.key == "state"
        assert entry.value == {"step": 1}
        assert entry.ttl_seconds == 3600

    def test_create_entry_with_ttl(self) -> None:
        """Can create entry with custom TTL."""
        key = MemoryKey(namespace="temp", key="cache")
        entry = MemoryEntry(key=key, value="data", ttl_seconds=600)

        assert entry.ttl_seconds == 600

    def test_create_entry_with_metadata(self) -> None:
        """Can create entry with metadata."""
        key = MemoryKey(namespace="workflow", key="plan")
        entry = MemoryEntry(
            key=key,
            value={"steps": []},
            metadata={"source": "planner", "version": 1},
        )

        assert entry.metadata["source"] == "planner"

    def test_reject_negative_ttl(self) -> None:
        """Cannot create entry with negative TTL."""
        key = MemoryKey(namespace="session", key="test")

        with pytest.raises(ValueError, match="ttl_seconds cannot be negative"):
            MemoryEntry(key=key, value="test", ttl_seconds=-1)

    def test_immutable(self) -> None:
        """MemoryEntry is immutable (frozen dataclass)."""
        key = MemoryKey(namespace="session", key="test")
        entry = MemoryEntry(key=key, value="test")

        with pytest.raises(AttributeError):
            entry.value = "modified"  # type: ignore
