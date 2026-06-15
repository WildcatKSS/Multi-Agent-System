"""Tests for the LLM provider configuration dataclasses."""

import dataclasses

import pytest

from mas.llm.config import (
    AnthropicConfig,
    HuggingFaceConfig,
    LLMConfig,
    OllamaConfig,
    OpenAIConfig,
)
from mas.llm.contracts import ValidationError


class TestLLMConfig:
    def test_valid_config(self) -> None:
        cfg = LLMConfig(model="m", api_key="k", timeout_seconds=10, max_retries=2)
        assert cfg.model == "m"
        assert cfg.api_key == "k"
        assert cfg.timeout_seconds == 10
        assert cfg.max_retries == 2

    def test_defaults(self) -> None:
        cfg = LLMConfig(model="m")
        assert cfg.api_key is None
        assert cfg.timeout_seconds == 30
        assert cfg.max_retries == 3

    def test_empty_model_rejected(self) -> None:
        with pytest.raises(ValidationError, match="model cannot be empty"):
            LLMConfig(model="")

    def test_whitespace_model_rejected(self) -> None:
        with pytest.raises(ValidationError, match="model cannot be empty"):
            LLMConfig(model="   ")

    def test_zero_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError, match="timeout_seconds must be > 0"):
            LLMConfig(model="m", timeout_seconds=0)

    def test_negative_max_retries_rejected(self) -> None:
        with pytest.raises(ValidationError, match="max_retries cannot be negative"):
            LLMConfig(model="m", max_retries=-1)

    def test_is_frozen(self) -> None:
        cfg = LLMConfig(model="m")
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.model = "other"  # type: ignore[misc]


class TestOllamaConfig:
    def test_valid_with_defaults(self) -> None:
        cfg = OllamaConfig(model="llama3")
        assert cfg.base_url == "http://localhost:11434"
        assert cfg.api_key is None  # local server needs no key

    def test_custom_url(self) -> None:
        cfg = OllamaConfig(model="llama3", base_url="https://ollama.example.com:11434")
        assert cfg.base_url == "https://ollama.example.com:11434"

    def test_invalid_url_rejected(self) -> None:
        with pytest.raises(ValidationError, match="base_url must be a valid http"):
            OllamaConfig(model="llama3", base_url="localhost:11434")

    def test_empty_url_rejected(self) -> None:
        with pytest.raises(ValidationError, match="base_url must be a valid http"):
            OllamaConfig(model="llama3", base_url="")

    def test_base_validation_still_applies(self) -> None:
        with pytest.raises(ValidationError, match="model cannot be empty"):
            OllamaConfig(model="")

    def test_is_frozen(self) -> None:
        cfg = OllamaConfig(model="llama3")
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.base_url = "http://x"  # type: ignore[misc]


class TestHuggingFaceConfig:
    def test_valid(self) -> None:
        cfg = HuggingFaceConfig(model="gpt2", api_key="hf_x", task="text-generation")
        assert cfg.task == "text-generation"

    def test_default_task(self) -> None:
        cfg = HuggingFaceConfig(model="gpt2", api_key="hf_x")
        assert cfg.task == "text-generation"

    def test_text2text_task(self) -> None:
        cfg = HuggingFaceConfig(model="t5", api_key="hf_x", task="text2text")
        assert cfg.task == "text2text"

    def test_missing_api_key_rejected(self) -> None:
        with pytest.raises(ValidationError, match="HuggingFace requires a non-empty api_key"):
            HuggingFaceConfig(model="gpt2")

    def test_empty_api_key_rejected(self) -> None:
        with pytest.raises(ValidationError, match="HuggingFace requires a non-empty api_key"):
            HuggingFaceConfig(model="gpt2", api_key="")

    def test_invalid_task_rejected(self) -> None:
        with pytest.raises(ValidationError, match="task must be one of"):
            HuggingFaceConfig(model="gpt2", api_key="hf_x", task="translation")  # type: ignore[arg-type]


class TestOpenAIConfig:
    def test_valid(self) -> None:
        cfg = OpenAIConfig(model="gpt-4", api_key="sk_x")
        assert cfg.organization is None

    def test_with_organization(self) -> None:
        cfg = OpenAIConfig(model="gpt-4", api_key="sk_x", organization="org-123")
        assert cfg.organization == "org-123"

    def test_missing_api_key_rejected(self) -> None:
        with pytest.raises(ValidationError, match="OpenAI requires a non-empty api_key"):
            OpenAIConfig(model="gpt-4")


class TestAnthropicConfig:
    def test_valid_default_version(self) -> None:
        cfg = AnthropicConfig(model="claude-3", api_key="sk_x")
        assert cfg.version == "2023-06-01"

    def test_alternative_version(self) -> None:
        cfg = AnthropicConfig(model="claude-3", api_key="sk_x", version="2023-01-01")
        assert cfg.version == "2023-01-01"

    def test_missing_api_key_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Anthropic requires a non-empty api_key"):
            AnthropicConfig(model="claude-3")

    def test_unknown_version_rejected(self) -> None:
        with pytest.raises(ValidationError, match="version must be one of"):
            AnthropicConfig(model="claude-3", api_key="sk_x", version="1999-01-01")  # type: ignore[arg-type]


class TestSerialization:
    def test_to_dict(self) -> None:
        cfg = OpenAIConfig(model="gpt-4", api_key="sk_x", organization="org-1")
        data = cfg.to_dict()
        assert data == {
            "model": "gpt-4",
            "api_key": "sk_x",
            "timeout_seconds": 30,
            "max_retries": 3,
            "organization": "org-1",
        }

    def test_from_dict(self) -> None:
        data = {"model": "gpt-4", "api_key": "sk_x", "organization": "org-1"}
        cfg = OpenAIConfig.from_dict(data)
        assert isinstance(cfg, OpenAIConfig)
        assert cfg.model == "gpt-4"
        assert cfg.organization == "org-1"

    def test_round_trip(self) -> None:
        original = AnthropicConfig(model="claude-3", api_key="sk_x", version="2023-01-01")
        restored = AnthropicConfig.from_dict(original.to_dict())
        assert restored == original

    def test_from_dict_validates(self) -> None:
        with pytest.raises(ValidationError, match="model cannot be empty"):
            LLMConfig.from_dict({"model": ""})

    def test_from_dict_unknown_field_rejected(self) -> None:
        with pytest.raises(TypeError):
            LLMConfig.from_dict({"model": "m", "bogus": 1})
