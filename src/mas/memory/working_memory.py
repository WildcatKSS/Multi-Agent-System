"""Redis-backed working memory implementation."""

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkingMemoryConfig:
    """Configuration for Redis working memory."""

    host: str = "localhost"
    """Redis server hostname."""

    port: int = 6379
    """Redis server port."""

    db: int = 0
    """Redis database number."""

    ttl_seconds: int = 3600
    """Default TTL for keys (in seconds)."""

    key_prefix: str = "mas:"
    """Prefix for all keys to avoid collisions."""

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if self.port <= 0:
            raise ValueError("port must be positive")


class RedisWorkingMemory:
    """Redis-backed working memory for short-lived task state.

    Provides a simple key/value interface backed by Redis with automatic TTL.
    """

    def __init__(
        self,
        config: WorkingMemoryConfig | None = None,
        _client=None,
    ) -> None:
        """Initialize Redis working memory.

        Args:
            config: Configuration (defaults to localhost:6379).
            _client: For testing only — inject a fake Redis client.

        Raises:
            ImportError: If redis-py is not installed and _client is None.
        """
        self.config = config or WorkingMemoryConfig()
        self._client = _client if _client is not None else self._connect()

    def _connect(self):
        """Connect to Redis.

        Raises:
            ImportError: If redis-py is not installed.
        """
        try:
            import redis
        except ImportError as exc:
            raise ImportError(
                "redis-py is required for RedisWorkingMemory. "
                "Install it with: pip install mas[redis]"
            ) from exc

        return redis.Redis(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            decode_responses=True,
        )

    def _full_key(self, key: str) -> str:
        """Get the full Redis key with prefix.

        Args:
            key: The logical key.

        Returns:
            The full Redis key.
        """
        return f"{self.config.key_prefix}{key}"

    def set(self, key: str, value: dict) -> None:
        """Store a value with automatic TTL.

        Args:
            key: The key.
            value: The value (dict, will be JSON-serialized).
        """
        self._client.set(
            self._full_key(key),
            json.dumps(value),
            ex=self.config.ttl_seconds,
        )

    def get(self, key: str) -> dict | None:
        """Retrieve a value.

        Args:
            key: The key.

        Returns:
            The value if found, None otherwise.
        """
        raw = self._client.get(self._full_key(key))
        if raw is None:
            return None
        return json.loads(raw)

    def delete(self, key: str) -> None:
        """Delete a key.

        Args:
            key: The key to delete.
        """
        self._client.delete(self._full_key(key))

    def exists(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: The key.

        Returns:
            True if the key exists, False otherwise.
        """
        return bool(self._client.exists(self._full_key(key)))

    def clear_prefix(self, prefix: str) -> None:
        """Clear all keys matching a prefix.

        Args:
            prefix: The prefix to match (without global key_prefix).
        """
        pattern = f"{self.config.key_prefix}{prefix}*"
        keys = self._client.keys(pattern)
        if keys:
            self._client.delete(*keys)
