"""Tests for Redis working memory."""

import builtins

import pytest

from mas.memory.working_memory import (
    RedisWorkingMemory,
    WorkingMemoryConfig,
)

try:
    import fakeredis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

pytestmark = pytest.mark.skipif(not HAS_REDIS, reason="fakeredis not installed")


def _make_memory(prefix: str = "mas:") -> RedisWorkingMemory:
    """Helper to create a working memory with fake Redis."""
    config = WorkingMemoryConfig(key_prefix=prefix)
    client = fakeredis.FakeRedis(decode_responses=True)
    return RedisWorkingMemory(config=config, _client=client)


class TestWorkingMemory:
    """Tests for RedisWorkingMemory."""

    def test_set_and_get(self) -> None:
        """Can set and get values."""
        mem = _make_memory()
        mem.set("mykey", {"x": 1})
        assert mem.get("mykey") == {"x": 1}

    def test_get_missing_returns_none(self) -> None:
        """Get returns None for missing key."""
        mem = _make_memory()
        assert mem.get("nope") is None

    def test_delete(self) -> None:
        """Can delete a key."""
        mem = _make_memory()
        mem.set("k", {"v": 1})
        mem.delete("k")
        assert mem.get("k") is None

    def test_exists_true(self) -> None:
        """Exists returns True for existing key."""
        mem = _make_memory()
        mem.set("k", {})
        assert mem.exists("k") is True

    def test_exists_false(self) -> None:
        """Exists returns False for missing key."""
        mem = _make_memory()
        assert mem.exists("missing") is False

    def test_clear_prefix(self) -> None:
        """Can clear keys matching a prefix."""
        mem = _make_memory()
        mem.set("session:a", {"x": 1})
        mem.set("session:b", {"y": 2})
        mem.set("other:c", {"z": 3})

        mem.clear_prefix("session:")

        assert mem.get("session:a") is None
        assert mem.get("session:b") is None
        assert mem.get("other:c") == {"z": 3}

    def test_key_prefix_isolation(self) -> None:
        """Different prefixes don't collide."""
        # Create two memories with different prefixes
        mem_a = _make_memory(prefix="ns_a:")
        # Need to create mem_b with its own FakeRedis instance for true isolation
        config_b = WorkingMemoryConfig(key_prefix="ns_b:")
        client_b = fakeredis.FakeRedis(decode_responses=True)
        mem_b = RedisWorkingMemory(config=config_b, _client=client_b)

        mem_a.set("key", {"owner": "a"})
        mem_b.set("key", {"owner": "b"})

        assert mem_a.get("key") == {"owner": "a"}
        assert mem_b.get("key") == {"owner": "b"}


class TestRedisImportError:
    """Tests for missing redis import error handling."""

    def test_missing_redis_gives_helpful_error(self, monkeypatch) -> None:
        """Missing redis-py raises helpful error."""
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "redis":
                raise ImportError("No module named 'redis'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with pytest.raises(ImportError, match="pip install mas\\[redis\\]"):
            RedisWorkingMemory()
