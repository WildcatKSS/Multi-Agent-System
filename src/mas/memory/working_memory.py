"""Redis-backed working memory implementation."""

import json
import logging
from typing import Any

from mas.memory.contracts import MemoryEntry, MemoryKey, WorkingMemoryStore

logger = logging.getLogger(__name__)


class RedisWorkingMemory(WorkingMemoryStore):
    """Fast, session-scoped working memory backed by Redis."""

    def __init__(self, redis_client: Any | None = None) -> None:
        """Initialize Redis working memory.

        Args:
            redis_client: Redis client instance. If None, uses lazy connection.
        """
        self.redis = redis_client
        self._connected = redis_client is not None

        logger.debug(
            "RedisWorkingMemory initialized",
            extra={"connected": self._connected},
        )

    async def get(self, key: MemoryKey) -> Any:
        """Get value from Redis working memory.

        Args:
            key: Memory key to retrieve.

        Returns:
            Value if key exists, None otherwise.
        """
        if not self._connected:
            logger.debug(
                "Redis not connected, returning None",
                extra={"key": key.full_key()},
            )
            return None

        try:
            full_key = key.full_key()
            value = await self.redis.get(full_key)

            if value is None:
                logger.debug(
                    f"Cache miss: {full_key}",
                    extra={"key": full_key},
                )
                return None

            deserialized = json.loads(value)
            logger.debug(
                f"Cache hit: {full_key}",
                extra={"key": full_key},
            )
            return deserialized

        except Exception as e:
            logger.error(
                f"Error retrieving from working memory: {e}",
                extra={"key": key.full_key()},
            )
            return None

    async def set(self, entry: MemoryEntry) -> None:
        """Set value in Redis working memory.

        Args:
            entry: Memory entry to store.
        """
        if not self._connected:
            logger.debug(
                "Redis not connected, skipping set",
                extra={"key": entry.key.full_key()},
            )
            return

        try:
            full_key = entry.key.full_key()
            serialized = json.dumps(entry.value)

            await self.redis.setex(
                full_key,
                entry.ttl_seconds,
                serialized,
            )

            logger.debug(
                f"Set in working memory: {full_key}",
                extra={"key": full_key, "ttl": entry.ttl_seconds},
            )

        except Exception as e:
            logger.error(
                f"Error setting in working memory: {e}",
                extra={"key": entry.key.full_key()},
            )

    async def delete(self, key: MemoryKey) -> None:
        """Delete value from Redis working memory.

        Args:
            key: Memory key to delete.
        """
        if not self._connected:
            logger.debug(
                "Redis not connected, skipping delete",
                extra={"key": key.full_key()},
            )
            return

        try:
            full_key = key.full_key()
            await self.redis.delete(full_key)

            logger.debug(
                f"Deleted from working memory: {full_key}",
                extra={"key": full_key},
            )

        except Exception as e:
            logger.error(
                f"Error deleting from working memory: {e}",
                extra={"key": key.full_key()},
            )

    async def exists(self, key: MemoryKey) -> bool:
        """Check if key exists in Redis working memory.

        Args:
            key: Memory key to check.

        Returns:
            True if key exists, False otherwise.
        """
        if not self._connected:
            return False

        try:
            full_key = key.full_key()
            exists = await self.redis.exists(full_key)

            logger.debug(
                f"Existence check: {full_key} = {bool(exists)}",
                extra={"key": full_key, "exists": bool(exists)},
            )
            return bool(exists)

        except Exception as e:
            logger.error(
                f"Error checking existence in working memory: {e}",
                extra={"key": key.full_key()},
            )
            return False
