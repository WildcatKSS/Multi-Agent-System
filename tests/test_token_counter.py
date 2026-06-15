"""Tests for mas.llm.token_counter."""

import pytest

from mas.llm.contracts import LLMMessage
from mas.llm.token_counter import (
    DEFAULT_STRATEGY,
    HeuristicStrategy,
    OverheadStrategy,
    TokenCountStrategy,
    TokenCounter,
    _BUILTIN_STRATEGIES,
    default_counter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _msg(content: str, role: str = "user") -> LLMMessage:
    return LLMMessage(role=role, content=content)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# HeuristicStrategy
# ---------------------------------------------------------------------------


class TestHeuristicStrategy:
    def test_empty_string_returns_zero(self) -> None:
        s = HeuristicStrategy()
        assert s.count("") == 0

    def test_short_text_at_least_one(self) -> None:
        s = HeuristicStrategy()
        assert s.count("hi") == 1

    def test_four_chars_one_token(self) -> None:
        s = HeuristicStrategy()
        assert s.count("abcd") == 1

    def test_five_chars_two_tokens(self) -> None:
        s = HeuristicStrategy()
        assert s.count("abcde") == 2

    def test_eight_chars_two_tokens(self) -> None:
        s = HeuristicStrategy()
        assert s.count("abcdefgh") == 2

    def test_custom_ratio(self) -> None:
        s = HeuristicStrategy(chars_per_token=2.0)
        assert s.count("abcd") == 2

    def test_result_is_non_negative(self) -> None:
        s = HeuristicStrategy()
        assert s.count("x" * 1000) > 0

    def test_longer_text_more_tokens(self) -> None:
        s = HeuristicStrategy()
        short = s.count("Hello")
        long_ = s.count("Hello, this is a much longer sentence with more words in it.")
        assert long_ > short

    def test_count_messages_sums_content_plus_overhead(self) -> None:
        s = HeuristicStrategy()
        msgs = [_msg("abcd"), _msg("abcd")]
        # Each: count("abcd")=1, + 4 overhead = 5; total = 10
        assert s.count_messages(msgs) == 10

    def test_count_messages_empty_list(self) -> None:
        s = HeuristicStrategy()
        assert s.count_messages([]) == 0

    def test_frozen(self) -> None:
        s = HeuristicStrategy()
        with pytest.raises(Exception):
            s.chars_per_token = 2.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# OverheadStrategy
# ---------------------------------------------------------------------------


class TestOverheadStrategy:
    def test_zero_overhead(self) -> None:
        base = HeuristicStrategy()
        s = OverheadStrategy(base=base, overhead_tokens=0)
        assert s.count("abcd") == base.count("abcd")

    def test_positive_overhead(self) -> None:
        base = HeuristicStrategy()
        s = OverheadStrategy(base=base, overhead_tokens=3)
        assert s.count("abcd") == base.count("abcd") + 3

    def test_empty_text_with_overhead(self) -> None:
        base = HeuristicStrategy()
        s = OverheadStrategy(base=base, overhead_tokens=10)
        assert s.count("") == 10

    def test_count_messages_uses_base_count_messages(self) -> None:
        base = HeuristicStrategy()
        s = OverheadStrategy(base=base, overhead_tokens=0)
        msgs = [_msg("hello")]
        assert s.count_messages(msgs) == base.count_messages(msgs)

    def test_frozen(self) -> None:
        base = HeuristicStrategy()
        s = OverheadStrategy(base=base)
        with pytest.raises(Exception):
            s.overhead_tokens = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TokenCounter construction
# ---------------------------------------------------------------------------


class TestTokenCounterConstruction:
    def test_default_construction(self) -> None:
        tc = TokenCounter()
        assert tc.cache_size() == 0

    def test_zero_cache_size(self) -> None:
        tc = TokenCounter(cache_size=0)
        assert tc.cache_size() == 0

    def test_negative_cache_size_raises(self) -> None:
        with pytest.raises(ValueError, match="cache_size"):
            TokenCounter(cache_size=-1)

    def test_repr_contains_strategies(self) -> None:
        tc = TokenCounter()
        r = repr(tc)
        assert "TokenCounter" in r
        assert "cache_size" in r


# ---------------------------------------------------------------------------
# TokenCounter — strategy management
# ---------------------------------------------------------------------------


class TestTokenCounterStrategies:
    def test_builtin_strategies_registered(self) -> None:
        tc = TokenCounter()
        for provider in ["openai", "anthropic", "ollama", "huggingface"]:
            assert tc.strategy_for(provider) is not DEFAULT_STRATEGY

    def test_unknown_provider_returns_default(self) -> None:
        tc = TokenCounter()
        assert tc.strategy_for("nonexistent") is DEFAULT_STRATEGY

    def test_register_strategy_replaces_builtin(self) -> None:
        tc = TokenCounter()
        custom = HeuristicStrategy(chars_per_token=1.0)
        tc.register_strategy("openai", custom)
        assert tc.strategy_for("openai") is custom

    def test_register_strategy_evicts_cache(self) -> None:
        tc = TokenCounter(cache_size=10)
        tc.count("hello", provider="openai")
        assert tc.cache_size() == 1
        tc.register_strategy("openai", HeuristicStrategy(chars_per_token=1.0))
        assert tc.cache_size() == 0  # cache evicted on strategy change


# ---------------------------------------------------------------------------
# TokenCounter — count()
# ---------------------------------------------------------------------------


class TestTokenCounterCount:
    def test_count_empty_string(self) -> None:
        tc = TokenCounter()
        assert tc.count("", provider="openai") == 0

    def test_count_with_openai_strategy(self) -> None:
        tc = TokenCounter()
        # "hello" = 5 chars, ceil(5/3.5) = 2
        result = tc.count("hello", provider="openai")
        assert result == 2

    def test_count_with_ollama_strategy(self) -> None:
        tc = TokenCounter()
        # "abcd" = 4 chars, ceil(4/4) = 1
        result = tc.count("abcd", provider="ollama")
        assert result == 1

    def test_count_no_provider_uses_default(self) -> None:
        tc = TokenCounter()
        result = tc.count("abcd")
        assert result == DEFAULT_STRATEGY.count("abcd")

    def test_count_caches_result(self) -> None:
        tc = TokenCounter(cache_size=10)
        tc.count("hello", provider="ollama")
        assert tc.cache_size() == 1
        tc.count("hello", provider="ollama")  # cache hit
        assert tc.cache_size() == 1  # no new entry

    def test_count_cache_hit_returns_same_value(self) -> None:
        tc = TokenCounter(cache_size=10)
        v1 = tc.count("hello world", provider="openai")
        v2 = tc.count("hello world", provider="openai")
        assert v1 == v2

    def test_count_no_caching_when_cache_size_zero(self) -> None:
        tc = TokenCounter(cache_size=0)
        tc.count("hello", provider="ollama")
        assert tc.cache_size() == 0

    def test_count_different_providers_cached_separately(self) -> None:
        tc = TokenCounter(cache_size=10)
        tc.count("hello", provider="openai")
        tc.count("hello", provider="ollama")
        assert tc.cache_size() == 2


# ---------------------------------------------------------------------------
# TokenCounter — cache eviction
# ---------------------------------------------------------------------------


class TestTokenCounterCacheEviction:
    def test_cache_evicts_oldest_when_full(self) -> None:
        tc = TokenCounter(cache_size=2)
        tc.count("a", provider="p")
        tc.count("b", provider="p")
        assert tc.cache_size() == 2
        tc.count("c", provider="p")
        # Still at max; one entry was evicted
        assert tc.cache_size() == 2

    def test_clear_cache_empties_all(self) -> None:
        tc = TokenCounter(cache_size=10)
        tc.count("x", provider="openai")
        tc.count("y", provider="ollama")
        assert tc.cache_size() == 2
        tc.clear_cache()
        assert tc.cache_size() == 0


# ---------------------------------------------------------------------------
# TokenCounter — count_messages()
# ---------------------------------------------------------------------------


class TestTokenCounterCountMessages:
    def test_count_messages_empty(self) -> None:
        tc = TokenCounter()
        assert tc.count_messages([], provider="openai") == 0

    def test_count_messages_single(self) -> None:
        tc = TokenCounter()
        msgs = [_msg("abcd")]
        result = tc.count_messages(msgs, provider="ollama")
        # HeuristicStrategy(4): count("abcd")=1, + 4 overhead = 5
        assert result == 5

    def test_count_messages_multiple(self) -> None:
        tc = TokenCounter()
        msgs = [_msg("abcd"), _msg("abcd"), _msg("abcd")]
        result = tc.count_messages(msgs, provider="ollama")
        assert result == 15  # 3 × 5

    def test_count_messages_no_provider_uses_default(self) -> None:
        tc = TokenCounter()
        msgs = [_msg("hello")]
        result = tc.count_messages(msgs)
        expected = DEFAULT_STRATEGY.count_messages(msgs)
        assert result == expected


# ---------------------------------------------------------------------------
# default_counter
# ---------------------------------------------------------------------------


class TestDefaultCounter:
    def test_default_counter_is_token_counter(self) -> None:
        assert isinstance(default_counter, TokenCounter)

    def test_default_counter_has_builtin_strategies(self) -> None:
        for provider in _BUILTIN_STRATEGIES:
            strat = default_counter.strategy_for(provider)
            assert isinstance(strat, TokenCountStrategy)

    def test_default_counter_counts_openai(self) -> None:
        result = default_counter.count("Hello, world!", provider="openai")
        assert result > 0

    def test_default_counter_counts_anthropic(self) -> None:
        result = default_counter.count("Hello, world!", provider="anthropic")
        assert result > 0
