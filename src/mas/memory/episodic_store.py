"""In-memory episodic memory store (for MVP)."""

import logging
from datetime import datetime, timedelta

from mas.memory.contracts import EpisodicMemoryStore, MemoryEntry, MemoryKey

logger = logging.getLogger(__name__)


class EpisodicMemoryStoreImpl(EpisodicMemoryStore):
    """In-memory episodic memory for execution history.

    MVP implementation: stores in-process. For v2, replace with
    persistent backend (PostgreSQL, MongoDB, etc).
    """

    def __init__(self) -> None:
        """Initialize episodic memory store."""
        self._entries: dict[str, tuple[MemoryEntry, datetime]] = {}
        logger.debug("EpisodicMemoryStoreImpl initialized")

    async def record(self, entry: MemoryEntry) -> None:
        """Record entry in episodic memory.

        Args:
            entry: Memory entry to record.
        """
        try:
            full_key = entry.key.full_key()
            timestamp = datetime.utcnow()

            self._entries[full_key] = (entry, timestamp)

            logger.debug(
                f"Recorded to episodic memory: {full_key}",
                extra={"key": full_key},
            )

        except Exception as e:
            logger.error(
                f"Error recording to episodic memory: {e}",
                extra={"key": entry.key.full_key()},
            )

    async def retrieve(self, key: MemoryKey) -> MemoryEntry | None:
        """Retrieve entry from episodic memory.

        Args:
            key: Memory key to retrieve.

        Returns:
            Memory entry if exists and not expired, None otherwise.
        """
        try:
            full_key = key.full_key()

            if full_key not in self._entries:
                logger.debug(
                    f"Episodic memory miss: {full_key}",
                    extra={"key": full_key},
                )
                return None

            entry, timestamp = self._entries[full_key]

            # Check expiration
            if self._is_expired(timestamp, entry.ttl_seconds):
                del self._entries[full_key]
                logger.debug(
                    f"Episodic memory expired: {full_key}",
                    extra={"key": full_key},
                )
                return None

            logger.debug(
                f"Episodic memory hit: {full_key}",
                extra={"key": full_key},
            )
            return entry

        except Exception as e:
            logger.error(
                f"Error retrieving from episodic memory: {e}",
                extra={"key": key.full_key()},
            )
            return None

    async def retrieve_by_namespace(self, namespace: str) -> list[MemoryEntry]:
        """Retrieve all entries in a namespace.

        Args:
            namespace: Memory namespace to query.

        Returns:
            List of non-expired entries in namespace.
        """
        try:
            results = []

            for full_key, (entry, timestamp) in self._entries.items():
                if full_key.startswith(f"{namespace}:"):
                    if not self._is_expired(timestamp, entry.ttl_seconds):
                        results.append(entry)

            logger.debug(
                f"Retrieved {len(results)} entries from namespace: {namespace}",
                extra={"namespace": namespace, "count": len(results)},
            )
            return results

        except Exception as e:
            logger.error(
                f"Error retrieving from episodic memory by namespace: {e}",
                extra={"namespace": namespace},
            )
            return []

    async def clear_expired(self) -> int:
        """Clear expired entries from episodic memory.

        Returns:
            Number of entries deleted.
        """
        try:
            expired_keys = [
                key
                for key, (entry, timestamp) in self._entries.items()
                if self._is_expired(timestamp, entry.ttl_seconds)
            ]

            for key in expired_keys:
                del self._entries[key]

            logger.debug(
                f"Cleared {len(expired_keys)} expired entries from episodic memory",
                extra={"count": len(expired_keys)},
            )
            return len(expired_keys)

        except Exception as e:
            logger.error(
                f"Error clearing expired entries: {e}",
            )
            return 0

    def _is_expired(self, timestamp: datetime, ttl_seconds: int) -> bool:
        """Check if entry is expired.

        Args:
            timestamp: When entry was created.
            ttl_seconds: Time-to-live in seconds.

        Returns:
            True if expired, False otherwise.
        """
        expiration = timestamp + timedelta(seconds=ttl_seconds)
        return datetime.utcnow() > expiration
