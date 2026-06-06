"""Memory layer for the multi-agent system.

Provides episodic memory (long-term storage of task outcomes) and
working memory (short-lived Redis-backed key/value store) with a
unified MemoryAgent interface.
"""

from mas.memory.contracts import (
    EpisodicRecord,
    MemoryEntry,
    MemoryType,
)
from mas.memory.episodic_store import (
    EpisodicStore,
    InMemoryEpisodicStore,
)
from mas.memory.memory_agent import MemoryAgent
from mas.memory.working_memory import (
    RedisWorkingMemory,
    WorkingMemoryConfig,
)

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
