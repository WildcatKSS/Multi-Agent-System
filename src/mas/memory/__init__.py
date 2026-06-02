"""Memory layer for the multi-agent system.

Provides episodic memory (long-term storage of task outcomes) and
working memory (short-lived Redis-backed key/value store) with a
unified MemoryAgent interface.
"""

from mas.memory.contracts import (
    MemoryType,
    MemoryEntry,
    EpisodicRecord,
)
from mas.memory.episodic_store import (
    EpisodicStore,
    InMemoryEpisodicStore,
)
from mas.memory.working_memory import (
    WorkingMemoryConfig,
    RedisWorkingMemory,
)
from mas.memory.memory_agent import MemoryAgent

__all__ = [
    "MemoryType",
    "MemoryEntry",
    "EpisodicRecord",
    "EpisodicStore",
    "InMemoryEpisodicStore",
    "WorkingMemoryConfig",
    "RedisWorkingMemory",
    "MemoryAgent",
]
