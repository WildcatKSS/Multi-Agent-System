"""Token counting for LLM providers.

Provides a :class:`TokenCounter` that dispatches to per-provider counting
strategies and caches results for repeated inputs. All strategies use only
the stdlib — no external tokeniser packages are required.

The default strategy is a ``(len(text) + 3) // 4`` heuristic (≈ 4 chars per
token), which matches :meth:`~mas.llm.base.BaseProvider.estimate_tokens`.
Provider-specific strategies can adjust the chars-per-token ratio or apply
a fixed overhead for chat-message framing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from mas.llm.contracts import LLMMessage

# ---------------------------------------------------------------------------
# Counting strategies
# ---------------------------------------------------------------------------


class TokenCountStrategy(ABC):
    """Abstract base for a token-counting strategy.

    Each concrete strategy encapsulates one approach to estimating how many
    tokens a piece of text will consume for a particular provider or model
    family. Strategies are stateless: they perform no I/O and hold no mutable
    state beyond their constructor arguments.
    """

    @abstractmethod
    def count(self, text: str) -> int:
        """Return a non-negative token estimate for ``text``.

        Args:
            text: The raw text to estimate.

        Returns:
            A non-negative integer token count.
        """

    def count_messages(self, messages: list[LLMMessage]) -> int:
        """Return a token estimate for a list of messages.

        The default implementation sums :meth:`count` over each message's
        content and adds a small per-message framing overhead (4 tokens).

        Args:
            messages: The conversation to estimate.

        Returns:
            A non-negative integer token count.
        """
        per_message_overhead = 4
        return sum(self.count(m.content) + per_message_overhead for m in messages)


@dataclass(frozen=True)
class HeuristicStrategy(TokenCountStrategy):
    """Chars-per-token heuristic strategy.

    Estimates ``ceil(len(text) / chars_per_token)`` tokens. The default ratio
    of 4 chars/token matches the ``BaseProvider.estimate_tokens`` heuristic.

    Args:
        chars_per_token: Average characters per token for the target model
            family. Smaller values give higher token estimates (conservative);
            larger values give lower estimates (aggressive).
    """

    chars_per_token: float = 4.0

    def count(self, text: str) -> int:
        """Estimate tokens using the chars-per-token ratio."""
        if not text:
            return 0
        ratio = self.chars_per_token
        return max(1, int((len(text) + ratio - 1) // ratio))


@dataclass(frozen=True)
class OverheadStrategy(TokenCountStrategy):
    """Wraps another strategy and adds a fixed overhead per call.

    Useful for providers that add a fixed number of tokens for prompt
    framing, special tokens, or system-message headers.

    Args:
        base: The underlying counting strategy.
        overhead_tokens: Fixed number of tokens added on top of the base
            strategy's estimate (default 0).
    """

    base: TokenCountStrategy
    overhead_tokens: int = 0

    def count(self, text: str) -> int:
        """Count tokens via ``base``, plus the fixed overhead."""
        return self.base.count(text) + self.overhead_tokens


# ---------------------------------------------------------------------------
# Provider strategy factories
# ---------------------------------------------------------------------------

# OpenAI's cl100k_base tokeniser averages ≈ 3.5 chars/token for English text.
_OPENAI_STRATEGY = HeuristicStrategy(chars_per_token=3.5)

# Anthropic uses a similar BPE tokeniser; ≈ 3.5 chars/token is a good proxy.
_ANTHROPIC_STRATEGY = HeuristicStrategy(chars_per_token=3.5)

# Ollama models (LLaMA family) average ≈ 4 chars/token.
_OLLAMA_STRATEGY = HeuristicStrategy(chars_per_token=4.0)

# HuggingFace GPT-2 style tokenisers average ≈ 4 chars/token.
_HUGGINGFACE_STRATEGY = HeuristicStrategy(chars_per_token=4.0)

#: Default strategy used when no provider-specific one is registered.
DEFAULT_STRATEGY = HeuristicStrategy(chars_per_token=4.0)

#: Built-in provider → strategy mapping.
_BUILTIN_STRATEGIES: dict[str, TokenCountStrategy] = {
    "openai": _OPENAI_STRATEGY,
    "anthropic": _ANTHROPIC_STRATEGY,
    "ollama": _OLLAMA_STRATEGY,
    "huggingface": _HUGGINGFACE_STRATEGY,
}


# ---------------------------------------------------------------------------
# TokenCounter
# ---------------------------------------------------------------------------


class TokenCounter:
    """Counts tokens for LLM provider calls with per-provider strategies and caching.

    Dispatches to a registered :class:`TokenCountStrategy` per provider name.
    Results are cached in an LRU-style dict (up to ``cache_size`` entries) so
    repeated calls with the same ``(provider, text)`` pair are O(1).

    Args:
        cache_size: Maximum number of ``(provider, text)`` pairs to cache.
            ``0`` disables caching. Defaults to 512.
    """

    def __init__(self, cache_size: int = 512) -> None:
        if cache_size < 0:
            raise ValueError(f"cache_size cannot be negative, got {cache_size}")
        self._strategies: dict[str, TokenCountStrategy] = dict(_BUILTIN_STRATEGIES)
        self._cache_size = cache_size
        self._cache: dict[tuple[str, str], int] = {}

    # ------------------------------------------------------------------
    # Strategy management
    # ------------------------------------------------------------------

    def register_strategy(self, provider: str, strategy: TokenCountStrategy) -> None:
        """Register a counting strategy for ``provider``.

        Replaces any existing strategy for that provider (including built-ins).

        Args:
            provider: Provider name (e.g. ``"openai"``).
            strategy: The :class:`TokenCountStrategy` to use.
        """
        self._strategies[provider] = strategy
        self._evict_provider(provider)

    def strategy_for(self, provider: str) -> TokenCountStrategy:
        """Return the strategy registered for ``provider``, or the default.

        Args:
            provider: Provider name.

        Returns:
            The registered :class:`TokenCountStrategy`, or :data:`DEFAULT_STRATEGY`.
        """
        return self._strategies.get(provider, DEFAULT_STRATEGY)

    # ------------------------------------------------------------------
    # Counting
    # ------------------------------------------------------------------

    def count(self, text: str, provider: str = "") -> int:
        """Estimate the token count of ``text`` for the given provider.

        Results are cached by ``(provider, text)`` pair. Pass an empty string
        for ``provider`` to use the default strategy without caching under a
        provider key.

        Args:
            text: The text to estimate.
            provider: Provider name used to select the strategy. Falls back to
                :data:`DEFAULT_STRATEGY` for unknown providers.

        Returns:
            A non-negative integer token count.
        """
        if self._cache_size > 0:
            key = (provider, text)
            if key in self._cache:
                return self._cache[key]
            result = self.strategy_for(provider).count(text)
            self._maybe_cache(key, result)
            return result
        return self.strategy_for(provider).count(text)

    def count_messages(self, messages: list[LLMMessage], provider: str = "") -> int:
        """Estimate the total token count for a list of messages.

        Delegates to the provider's strategy :meth:`TokenCountStrategy.count_messages`.
        Results are NOT cached (message lists are mutable containers).

        Args:
            messages: The conversation to estimate.
            provider: Provider name used to select the strategy.

        Returns:
            A non-negative integer token count.
        """
        return self.strategy_for(provider).count_messages(messages)

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Evict all cached results."""
        self._cache.clear()

    def cache_size(self) -> int:
        """Return the current number of cached entries."""
        return len(self._cache)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _maybe_cache(self, key: tuple[str, str], value: int) -> None:
        """Insert ``value`` into the cache, evicting oldest entry if full."""
        if len(self._cache) >= self._cache_size:
            # Evict the first (oldest) entry — dict preserves insertion order.
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = value

    def _evict_provider(self, provider: str) -> None:
        """Remove all cached entries for ``provider``."""
        keys_to_drop = [k for k in self._cache if k[0] == provider]
        for k in keys_to_drop:
            del self._cache[k]

    def __repr__(self) -> str:
        strategies = list(self._strategies)
        return f"TokenCounter(strategies={strategies!r}, cache_size={self._cache_size})"


# ---------------------------------------------------------------------------
# Module-level default instance
# ---------------------------------------------------------------------------

#: Process-wide :class:`TokenCounter` pre-loaded with built-in provider strategies.
default_counter: TokenCounter = TokenCounter()
