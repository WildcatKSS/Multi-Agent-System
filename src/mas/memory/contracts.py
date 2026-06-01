"""Memory contracts and abstract base classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryKey:
    """Key for accessing memory entries."""

    namespace: str
    """Memory namespace (e.g., 'session', 'workflow', 'step')."""

    key: str
    """Unique key within namespace."""

    def __post_init__(self) -> None:
        """Validate key on creation."""
        if not self.namespace:
            raise ValueError("namespace cannot be empty")
        if not self.key:
            raise ValueError("key cannot be empty")

    def full_key(self) -> str:
        """Return fully qualified key."""
        return f"{self.namespace}:{self.key}"


@dataclass(frozen=True)
class MemoryEntry:
    """Single memory entry with metadata."""

    key: MemoryKey
    """Key for this entry."""

    value: Any
    """Entry value (any JSON-serializable data)."""

    ttl_seconds: int = 3600
    """Time-to-live in seconds (default 1 hour)."""

    metadata: dict = field(default_factory=dict)
    """Optional metadata about the entry."""

    def __post_init__(self) -> None:
        """Validate entry on creation."""
        if self.ttl_seconds < 0:
            raise ValueError("ttl_seconds cannot be negative")


class WorkingMemoryStore(ABC):
    """Abstract base for working memory (fast, session-scoped)."""

    @abstractmethod
    async def get(self, key: MemoryKey) -> Any:
        """Get value from working memory."""
        pass

    @abstractmethod
    async def set(self, entry: MemoryEntry) -> None:
        """Set value in working memory."""
        pass

    @abstractmethod
    async def delete(self, key: MemoryKey) -> None:
        """Delete value from working memory."""
        pass

    @abstractmethod
    async def exists(self, key: MemoryKey) -> bool:
        """Check if key exists in working memory."""
        pass


class EpisodicMemoryStore(ABC):
    """Abstract base for episodic memory (historical records)."""

    @abstractmethod
    async def record(self, entry: MemoryEntry) -> None:
        """Record entry in episodic memory."""
        pass

    @abstractmethod
    async def retrieve(self, key: MemoryKey) -> MemoryEntry | None:
        """Retrieve entry from episodic memory."""
        pass

    @abstractmethod
    async def retrieve_by_namespace(self, namespace: str) -> list[MemoryEntry]:
        """Retrieve all entries in a namespace."""
        pass

    @abstractmethod
    async def clear_expired(self) -> int:
        """Clear expired entries. Returns count deleted."""
        pass
