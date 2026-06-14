"""Concrete LLM provider implementations.

Each sub-module implements a :class:`~mas.llm.base.BaseProvider` subclass and
self-registers with :data:`~mas.llm.provider_registry.default_registry` on import.

Import the provider you need explicitly, or import ``mas.llm.providers`` to
register all built-ins at once.
"""

from mas.llm.providers.huggingface import HuggingFaceProvider
from mas.llm.providers.ollama import OllamaProvider
from mas.llm.providers.openai import OpenAIProvider

__all__ = ["HuggingFaceProvider", "OllamaProvider", "OpenAIProvider"]
