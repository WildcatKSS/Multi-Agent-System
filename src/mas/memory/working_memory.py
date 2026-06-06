"""Redis-backed working memory implementation."""

import json
import logging
from dataclasses import dataclass
from typing import Any

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

    password: str | None = None
    """Redis password (use environment variable for production)."""

    username: str | None = None
    """Redis username for ACL (Redis 6+)."""

    ssl: bool = False
    """Enable SSL/TLS for Redis connection."""

    ssl_certfile: str | None = None
    """Path to SSL certificate file for Redis."""

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if self.port <= 0:
            raise ValueError("port must be positive")
        if self.ssl_certfile and not self.ssl:
            raise ValueError("ssl_certfile requires ssl=True")


class RedisWorkingMemory:
    """Redis-backed working memory for short-lived task state.

    Provides a simple key/value interface backed by Redis with automatic TTL.
    """

    def __init__(
        self,
        config: WorkingMemoryConfig | None = None,
        _client: Any = None,
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

    def _connect(self) -> Any:
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
            username=self.config.username,
            password=self.config.password,
            ssl=self.config.ssl,
            ssl_certfile=self.config.ssl_certfile,
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

    def set(self, key: str, value: dict[str, Any]) -> None:
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

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve a value.

        Args:
            key: The key.

        Returns:
            The value if found, None otherwise.

        Raises:
            ValueError: If retrieved data is invalid JSON or not a dict.
        """
        raw = self._client.get(self._full_key(key))
        if raw is None:
            return None

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to deserialize value for key {key}: invalid JSON")
            raise ValueError(f"Invalid JSON stored for key {key}") from exc

        if not isinstance(data, dict):
            logger.error(f"Retrieved value for key {key} is not a dict: {type(data)}")
            raise ValueError(f"Retrieved value for key {key} must be a dict, got {type(data)}")

        return data

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
