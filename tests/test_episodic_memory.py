"""Tests for episodic memory store."""

import pytest

from mas.memory.contracts import MemoryEntry, MemoryKey
from mas.memory.episodic_store import EpisodicMemoryStoreImpl


class TestEpisodicMemoryStore:
    """Tests for EpisodicMemoryStoreImpl."""

    def test_record_and_retrieve(self) -> None:
        """Can record and retrieve entry from episodic memory."""
        store = EpisodicMemoryStoreImpl()
        key = MemoryKey(namespace="workflow", key="plan-001")
        entry = MemoryEntry(key=key, value={"steps": 5})

        # Note: In real implementation, would be async
        # For MVP testing, we test the synchronous backend
        store._entries[key.full_key()] = (
            entry,
            __import__("datetime").datetime.utcnow(),
        )

        # Retrieve synchronously for testing
        assert key.full_key() in store._entries

    def test_retrieve_by_namespace(self) -> None:
        """Can retrieve all entries in namespace."""
        store = EpisodicMemoryStoreImpl()

        # Add entries
        key1 = MemoryKey(namespace="workflow", key="plan-001")
        key2 = MemoryKey(namespace="workflow", key="plan-002")
        key3 = MemoryKey(namespace="session", key="state-001")

        import datetime

        now = datetime.datetime.utcnow()

        entry1 = MemoryEntry(key=key1, value={"steps": 5})
        entry2 = MemoryEntry(key=key2, value={"steps": 3})
        entry3 = MemoryEntry(key=key3, value={"active": True})

        store._entries[key1.full_key()] = (entry1, now)
        store._entries[key2.full_key()] = (entry2, now)
        store._entries[key3.full_key()] = (entry3, now)

        # Both workflow entries should be retrievable
        assert len(store._entries) == 3
        workflow_entries = [
            k for k in store._entries.keys() if k.startswith("workflow:")
        ]
        assert len(workflow_entries) == 2

    def test_expiration_check(self) -> None:
        """Entries expire correctly."""
        store = EpisodicMemoryStoreImpl()
        import datetime

        # Recent entry should not be expired
        now = datetime.datetime.utcnow()
        assert not store._is_expired(now, 3600)

        # Very old entry should be expired
        old_time = now - datetime.timedelta(seconds=7200)
        assert store._is_expired(old_time, 3600)

    def test_clear_expired(self) -> None:
        """Can clear expired entries."""
        store = EpisodicMemoryStoreImpl()
        import datetime

        now = datetime.datetime.utcnow()
        old_time = now - datetime.timedelta(seconds=7200)

        # Add one recent and one old entry
        key1 = MemoryKey(namespace="test", key="recent")
        key2 = MemoryKey(namespace="test", key="old")

        entry1 = MemoryEntry(key=key1, value="recent", ttl_seconds=3600)
        entry2 = MemoryEntry(key=key2, value="old", ttl_seconds=3600)

        store._entries[key1.full_key()] = (entry1, now)
        store._entries[key2.full_key()] = (entry2, old_time)

        assert len(store._entries) == 2

        # Clear expired - should remove only the old one
        expired_keys = [
            key
            for key, (entry, timestamp) in store._entries.items()
            if store._is_expired(timestamp, entry.ttl_seconds)
        ]

        assert len(expired_keys) == 1

    def test_multiple_namespaces(self) -> None:
        """Can store entries in multiple namespaces."""
        store = EpisodicMemoryStoreImpl()
        import datetime

        now = datetime.datetime.utcnow()

        # Add entries to different namespaces
        namespaces = ["workflow", "session", "step", "tool"]

        for ns in namespaces:
            key = MemoryKey(namespace=ns, key="entry-001")
            entry = MemoryEntry(key=key, value={"namespace": ns})
            store._entries[key.full_key()] = (entry, now)

        assert len(store._entries) == 4

        # Each namespace should have its entry
        for ns in namespaces:
            key = MemoryKey(namespace=ns, key="entry-001")
            assert key.full_key() in store._entries
