"""Memory layer for the multi-agent system.

Provides working memory (Redis) for session state and episodic memory
for historical execution records, enabling agents to learn from past executions.
"""

from mas.memory.contracts import (
    MemoryEntry,
    WorkingMemoryStore,
    EpisodicMemoryStore,
    MemoryKey,
)
from mas.memory.working_memory import RedisWorkingMemory
from mas.memory.episodic_store import EpisodicMemoryStoreImpl

__all__ = [
    "MemoryEntry",
    "WorkingMemoryStore",
    "EpisodicMemoryStore",
    "MemoryKey",
    "RedisWorkingMemory",
    "EpisodicMemoryStoreImpl",
]
