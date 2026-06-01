"""Tests for Redis working memory."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from mas.memory.contracts import MemoryEntry, MemoryKey
from mas.memory.working_memory import RedisWorkingMemory


class TestRedisWorkingMemory:
    """Tests for RedisWorkingMemory."""

    def test_init_with_redis_client(self) -> None:
        """Can initialize with Redis client."""
        mock_redis = MagicMock()
        memory = RedisWorkingMemory(redis_client=mock_redis)

        assert memory.redis == mock_redis
        assert memory._connected is True

    def test_init_without_redis_client(self) -> None:
        """Can initialize without Redis client (no-op mode)."""
        memory = RedisWorkingMemory()

        assert memory.redis is None
        assert memory._connected is False

    @pytest.mark.asyncio
    async def test_get_with_connected_redis(self) -> None:
        """Get returns deserialized value from Redis."""
        mock_redis = AsyncMock()
        value_json = json.dumps({"step": 1}).encode()
        mock_redis.get.return_value = value_json

        memory = RedisWorkingMemory(redis_client=mock_redis)
        key = MemoryKey(namespace="test", key="state")

        result = await memory.get(key)

        assert result == {"step": 1}
        mock_redis.get.assert_called_once_with("test:state")

    @pytest.mark.asyncio
    async def test_get_with_missing_key(self) -> None:
        """Get returns None for missing key."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        memory = RedisWorkingMemory(redis_client=mock_redis)
        key = MemoryKey(namespace="test", key="missing")

        result = await memory.get(key)

        assert result is None
        mock_redis.get.assert_called_once_with("test:missing")

    @pytest.mark.asyncio
    async def test_get_without_redis(self) -> None:
        """Get returns None when Redis not connected."""
        memory = RedisWorkingMemory()
        key = MemoryKey(namespace="test", key="state")

        result = await memory.get(key)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_handles_redis_error(self) -> None:
        """Get returns None on Redis error."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")

        memory = RedisWorkingMemory(redis_client=mock_redis)
        key = MemoryKey(namespace="test", key="state")

        result = await memory.get(key)

        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_connected_redis(self) -> None:
        """Set stores serialized value in Redis."""
        mock_redis = AsyncMock()
        memory = RedisWorkingMemory(redis_client=mock_redis)

        key = MemoryKey(namespace="test", key="state")
        entry = MemoryEntry(key=key, value={"step": 1}, ttl_seconds=600)

        await memory.set(entry)

        expected_json = json.dumps({"step": 1})
        mock_redis.setex.assert_called_once_with(
            "test:state",
            600,
            expected_json,
        )

    @pytest.mark.asyncio
    async def test_set_with_default_ttl(self) -> None:
        """Set uses entry TTL in Redis."""
        mock_redis = AsyncMock()
        memory = RedisWorkingMemory(redis_client=mock_redis)

        key = MemoryKey(namespace="test", key="state")
        entry = MemoryEntry(key=key, value="data")  # default TTL 3600

        await memory.set(entry)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600

    @pytest.mark.asyncio
    async def test_set_without_redis(self) -> None:
        """Set does nothing when Redis not connected."""
        memory = RedisWorkingMemory()
        key = MemoryKey(namespace="test", key="state")
        entry = MemoryEntry(key=key, value={"step": 1})

        await memory.set(entry)

        # Should not raise error
        assert True

    @pytest.mark.asyncio
    async def test_set_handles_redis_error(self) -> None:
        """Set handles Redis error gracefully."""
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = Exception("Redis error")

        memory = RedisWorkingMemory(redis_client=mock_redis)
        key = MemoryKey(namespace="test", key="state")
        entry = MemoryEntry(key=key, value={"step": 1})

        await memory.set(entry)

        # Should not raise error
        assert True

    @pytest.mark.asyncio
    async def test_delete_with_connected_redis(self) -> None:
        """Delete removes key from Redis."""
        mock_redis = AsyncMock()
        memory = RedisWorkingMemory(redis_client=mock_redis)

        key = MemoryKey(namespace="test", key="state")

        await memory.delete(key)

        mock_redis.delete.assert_called_once_with("test:state")

    @pytest.mark.asyncio
    async def test_delete_without_redis(self) -> None:
        """Delete does nothing when Redis not connected."""
        memory = RedisWorkingMemory()
        key = MemoryKey(namespace="test", key="state")

        await memory.delete(key)

        # Should not raise error
        assert True

    @pytest.mark.asyncio
    async def test_delete_handles_redis_error(self) -> None:
        """Delete handles Redis error gracefully."""
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = Exception("Redis error")

        memory = RedisWorkingMemory(redis_client=mock_redis)
        key = MemoryKey(namespace="test", key="state")

        await memory.delete(key)

        # Should not raise error
        assert True

    @pytest.mark.asyncio
    async def test_exists_with_connected_redis_true(self) -> None:
        """Exists returns True when key exists."""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1

        memory = RedisWorkingMemory(redis_client=mock_redis)
        key = MemoryKey(namespace="test", key="state")

        result = await memory.exists(key)

        assert result is True
        mock_redis.exists.assert_called_once_with("test:state")

    @pytest.mark.asyncio
    async def test_exists_with_connected_redis_false(self) -> None:
        """Exists returns False when key does not exist."""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0

        memory = RedisWorkingMemory(redis_client=mock_redis)
        key = MemoryKey(namespace="test", key="missing")

        result = await memory.exists(key)

        assert result is False
        mock_redis.exists.assert_called_once_with("test:missing")

    @pytest.mark.asyncio
    async def test_exists_without_redis(self) -> None:
        """Exists returns False when Redis not connected."""
        memory = RedisWorkingMemory()
        key = MemoryKey(namespace="test", key="state")

        result = await memory.exists(key)

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_handles_redis_error(self) -> None:
        """Exists returns False on Redis error."""
        mock_redis = AsyncMock()
        mock_redis.exists.side_effect = Exception("Redis error")

        memory = RedisWorkingMemory(redis_client=mock_redis)
        key = MemoryKey(namespace="test", key="state")

        result = await memory.exists(key)

        assert result is False

    @pytest.mark.asyncio
    async def test_json_serialization_complex_types(self) -> None:
        """Set/get handles complex JSON-serializable types."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(
            {
                "list": [1, 2, 3],
                "nested": {"key": "value"},
                "bool": True,
                "null": None,
            }
        ).encode()

        memory = RedisWorkingMemory(redis_client=mock_redis)
        key = MemoryKey(namespace="test", key="complex")

        result = await memory.get(key)

        assert result["list"] == [1, 2, 3]
        assert result["nested"]["key"] == "value"
        assert result["bool"] is True
        assert result["null"] is None

    @pytest.mark.asyncio
    async def test_set_empty_value(self) -> None:
        """Set handles empty/null values."""
        mock_redis = AsyncMock()
        memory = RedisWorkingMemory(redis_client=mock_redis)

        key = MemoryKey(namespace="test", key="empty")
        entry = MemoryEntry(key=key, value=None)

        await memory.set(entry)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][2] == json.dumps(None)

    @pytest.mark.asyncio
    async def test_set_large_value(self) -> None:
        """Set handles large JSON values."""
        mock_redis = AsyncMock()
        memory = RedisWorkingMemory(redis_client=mock_redis)

        key = MemoryKey(namespace="test", key="large")
        large_dict = {"data": "x" * 10000}
        entry = MemoryEntry(key=key, value=large_dict)

        await memory.set(entry)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        serialized = call_args[0][2]
        assert len(serialized) > 10000
