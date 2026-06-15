"""Tests for mas.llm.validation.model_validator."""

import dataclasses

import pytest

from mas.llm.config import AnthropicConfig, HuggingFaceConfig, LLMConfig, OllamaConfig, OpenAIConfig
from mas.llm.validation.model_validator import (
    ModelCapabilities,
    ModelInfo,
    ModelValidator,
    ValidationResult,
    _build_default_validator,
    _ParameterBounds,
    default_validator,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_model(name: str = "m", provider: str = "p") -> ModelInfo:
    return ModelInfo(name=name, provider=provider)


def _make_validator(*models: ModelInfo) -> ModelValidator:
    v = ModelValidator()
    for m in models:
        v.register(m)
    return v


# ---------------------------------------------------------------------------
# ModelCapabilities
# ---------------------------------------------------------------------------


class TestModelCapabilities:
    def test_defaults(self) -> None:
        caps = ModelCapabilities()
        assert caps.supports_system_messages is True
        assert caps.supports_streaming is False
        assert caps.max_context_tokens == 4096
        assert caps.max_output_tokens == 4096

    def test_custom_values(self) -> None:
        caps = ModelCapabilities(
            supports_system_messages=False,
            supports_streaming=True,
            max_context_tokens=128000,
            max_output_tokens=8192,
        )
        assert caps.supports_system_messages is False
        assert caps.supports_streaming is True
        assert caps.max_context_tokens == 128000
        assert caps.max_output_tokens == 8192

    def test_frozen(self) -> None:
        caps = ModelCapabilities()
        with pytest.raises(dataclasses.FrozenInstanceError):
            caps.max_context_tokens = 1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ModelInfo
# ---------------------------------------------------------------------------


class TestModelInfo:
    def test_defaults(self) -> None:
        m = ModelInfo(name="llama2", provider="ollama")
        assert m.name == "llama2"
        assert m.provider == "ollama"
        assert isinstance(m.capabilities, ModelCapabilities)

    def test_custom_capabilities(self) -> None:
        caps = ModelCapabilities(supports_streaming=True, max_context_tokens=8192)
        m = ModelInfo(name="gpt-4o", provider="openai", capabilities=caps)
        assert m.capabilities.supports_streaming is True
        assert m.capabilities.max_context_tokens == 8192

    def test_frozen(self) -> None:
        m = _make_model()
        with pytest.raises(dataclasses.FrozenInstanceError):
            m.name = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_ok(self) -> None:
        r = ValidationResult.ok()
        assert r.valid is True
        assert r.errors == ()

    def test_fail_single_error(self) -> None:
        r = ValidationResult.fail("bad input")
        assert r.valid is False
        assert r.errors == ("bad input",)

    def test_fail_multiple_errors(self) -> None:
        r = ValidationResult.fail("err1", "err2", "err3")
        assert r.valid is False
        assert len(r.errors) == 3

    def test_frozen(self) -> None:
        r = ValidationResult.ok()
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.valid = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# _ParameterBounds
# ---------------------------------------------------------------------------


class TestParameterBounds:
    def test_in_range_returns_none(self) -> None:
        b = _ParameterBounds("temperature", 0.0, 2.0)
        assert b.check(1.0) is None
        assert b.check(0.0) is None
        assert b.check(2.0) is None

    def test_below_min_returns_error(self) -> None:
        b = _ParameterBounds("temperature", 0.0, 2.0)
        msg = b.check(-0.1)
        assert msg is not None
        assert "temperature" in msg

    def test_above_max_returns_error(self) -> None:
        b = _ParameterBounds("top_p", 0.0, 1.0)
        msg = b.check(1.1)
        assert msg is not None
        assert "top_p" in msg


# ---------------------------------------------------------------------------
# ModelValidator — catalog management
# ---------------------------------------------------------------------------


class TestModelValidatorCatalog:
    def test_empty_validator(self) -> None:
        v = ModelValidator()
        assert v.all_providers() == []
        assert v.models_for_provider("ollama") == []

    def test_register_and_is_known(self) -> None:
        v = _make_validator(_make_model("llama2", "ollama"))
        assert v.is_known("llama2", "ollama") is True
        assert v.is_known("llama2", "openai") is False
        assert v.is_known("gpt-4o", "openai") is False

    def test_register_replaces_existing(self) -> None:
        v = ModelValidator()
        caps1 = ModelCapabilities(max_context_tokens=1024)
        caps2 = ModelCapabilities(max_context_tokens=8192)
        v.register(ModelInfo("m", "p", caps1))
        v.register(ModelInfo("m", "p", caps2))
        assert v.get("m", "p") is not None
        assert v.get("m", "p").capabilities.max_context_tokens == 8192  # type: ignore[union-attr]

    def test_get_returns_none_for_unknown(self) -> None:
        v = _make_validator(_make_model("a", "p"))
        assert v.get("b", "p") is None
        assert v.get("a", "q") is None

    def test_get_returns_model_info(self) -> None:
        m = _make_model("llama2", "ollama")
        v = _make_validator(m)
        result = v.get("llama2", "ollama")
        assert result is m

    def test_models_for_provider_sorted(self) -> None:
        v = _make_validator(
            _make_model("z-model", "p"),
            _make_model("a-model", "p"),
            _make_model("m-model", "p"),
        )
        names = [m.name for m in v.models_for_provider("p")]
        assert names == ["a-model", "m-model", "z-model"]

    def test_models_for_provider_filters_others(self) -> None:
        v = _make_validator(
            _make_model("a", "p1"),
            _make_model("b", "p2"),
        )
        assert len(v.models_for_provider("p1")) == 1
        assert v.models_for_provider("p1")[0].name == "a"

    def test_all_providers_sorted(self) -> None:
        v = _make_validator(
            _make_model("a", "ollama"),
            _make_model("b", "openai"),
            _make_model("c", "anthropic"),
        )
        assert v.all_providers() == ["anthropic", "ollama", "openai"]

    def test_all_providers_deduplicates(self) -> None:
        v = _make_validator(
            _make_model("a", "ollama"),
            _make_model("b", "ollama"),
        )
        assert v.all_providers() == ["ollama"]


# ---------------------------------------------------------------------------
# ModelValidator — validate_model
# ---------------------------------------------------------------------------


class TestValidateModel:
    def test_known_model_passes(self) -> None:
        v = _make_validator(_make_model("llama2", "ollama"))
        result = v.validate_model("llama2", "ollama")
        assert result.valid is True

    def test_unknown_model_fails(self) -> None:
        v = _make_validator(_make_model("llama2", "ollama"))
        result = v.validate_model("gpt-4o", "ollama")
        assert result.valid is False
        assert "gpt-4o" in result.errors[0]

    def test_wrong_provider_fails(self) -> None:
        v = _make_validator(_make_model("llama2", "ollama"))
        result = v.validate_model("llama2", "openai")
        assert result.valid is False

    def test_empty_model_name_fails(self) -> None:
        v = ModelValidator()
        result = v.validate_model("", "ollama")
        assert result.valid is False
        assert "empty" in result.errors[0]

    def test_empty_provider_name_fails(self) -> None:
        v = ModelValidator()
        result = v.validate_model("llama2", "")
        assert result.valid is False
        assert "empty" in result.errors[0]


# ---------------------------------------------------------------------------
# ModelValidator — validate_parameters
# ---------------------------------------------------------------------------


class TestValidateParameters:
    def test_empty_params_passes(self) -> None:
        v = ModelValidator()
        assert v.validate_parameters({}).valid is True

    def test_valid_temperature_passes(self) -> None:
        v = ModelValidator()
        assert v.validate_parameters({"temperature": 0.7}).valid is True

    def test_temperature_zero_passes(self) -> None:
        v = ModelValidator()
        assert v.validate_parameters({"temperature": 0.0}).valid is True

    def test_temperature_two_passes(self) -> None:
        v = ModelValidator()
        assert v.validate_parameters({"temperature": 2.0}).valid is True

    def test_temperature_out_of_range_fails(self) -> None:
        v = ModelValidator()
        result = v.validate_parameters({"temperature": 2.1})
        assert result.valid is False
        assert "temperature" in result.errors[0]

    def test_temperature_negative_fails(self) -> None:
        v = ModelValidator()
        result = v.validate_parameters({"temperature": -0.1})
        assert result.valid is False

    def test_top_p_valid_passes(self) -> None:
        v = ModelValidator()
        assert v.validate_parameters({"top_p": 0.9}).valid is True

    def test_top_p_above_one_fails(self) -> None:
        v = ModelValidator()
        result = v.validate_parameters({"top_p": 1.1})
        assert result.valid is False
        assert "top_p" in result.errors[0]

    def test_max_tokens_positive_passes(self) -> None:
        v = ModelValidator()
        assert v.validate_parameters({"max_tokens": 100}).valid is True

    def test_max_tokens_zero_fails(self) -> None:
        v = ModelValidator()
        result = v.validate_parameters({"max_tokens": 0})
        assert result.valid is False
        assert "max_tokens" in result.errors[0]

    def test_max_tokens_negative_fails(self) -> None:
        v = ModelValidator()
        result = v.validate_parameters({"max_tokens": -1})
        assert result.valid is False

    def test_max_tokens_float_fails(self) -> None:
        v = ModelValidator()
        result = v.validate_parameters({"max_tokens": 1.5})
        assert result.valid is False

    def test_frequency_penalty_valid_passes(self) -> None:
        v = ModelValidator()
        assert v.validate_parameters({"frequency_penalty": 0.5}).valid is True

    def test_frequency_penalty_out_of_range_fails(self) -> None:
        v = ModelValidator()
        result = v.validate_parameters({"frequency_penalty": 3.0})
        assert result.valid is False

    def test_presence_penalty_valid_passes(self) -> None:
        v = ModelValidator()
        assert v.validate_parameters({"presence_penalty": -1.0}).valid is True

    def test_presence_penalty_out_of_range_fails(self) -> None:
        v = ModelValidator()
        result = v.validate_parameters({"presence_penalty": 2.5})
        assert result.valid is False

    def test_numeric_param_non_numeric_fails(self) -> None:
        v = ModelValidator()
        result = v.validate_parameters({"temperature": "warm"})
        assert result.valid is False
        assert "temperature" in result.errors[0]

    def test_unknown_parameter_passes(self) -> None:
        v = ModelValidator()
        assert v.validate_parameters({"seed": 42, "stop": ["\n"]}).valid is True

    def test_multiple_errors_collected(self) -> None:
        v = ModelValidator()
        result = v.validate_parameters({"temperature": 5.0, "max_tokens": -1})
        assert result.valid is False
        assert len(result.errors) == 2

    def test_integer_temperature_accepted(self) -> None:
        v = ModelValidator()
        assert v.validate_parameters({"temperature": 1}).valid is True


# ---------------------------------------------------------------------------
# ModelValidator — validate_config
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_ollama_config_known_model(self) -> None:
        result = default_validator.validate_config(OllamaConfig(model="llama2"))
        assert result.valid is True

    def test_huggingface_config_known_model(self) -> None:
        result = default_validator.validate_config(
            HuggingFaceConfig(model="gpt2", api_key="hf-x")
        )
        assert result.valid is True

    def test_openai_config_known_model(self) -> None:
        result = default_validator.validate_config(
            OpenAIConfig(model="gpt-4o", api_key="sk-x")
        )
        assert result.valid is True

    def test_anthropic_config_known_model(self) -> None:
        result = default_validator.validate_config(
            AnthropicConfig(model="claude-3-5-sonnet-20241022", api_key="sk-ant-x")
        )
        assert result.valid is True

    def test_unknown_model_in_valid_provider_fails(self) -> None:
        result = default_validator.validate_config(
            OpenAIConfig(model="gpt-99", api_key="sk-x")
        )
        assert result.valid is False
        assert "gpt-99" in result.errors[0]

    def test_unknown_config_type_fails(self) -> None:
        result = default_validator.validate_config(LLMConfig(model="anything"))
        assert result.valid is False
        assert "LLMConfig" in result.errors[0]


# ---------------------------------------------------------------------------
# ModelValidator — capabilities()
# ---------------------------------------------------------------------------


class TestCapabilities:
    def test_known_model_returns_capabilities(self) -> None:
        caps = default_validator.capabilities("gpt-4o", "openai")
        assert caps is not None
        assert caps.max_context_tokens == 128000

    def test_unknown_model_returns_none(self) -> None:
        caps = default_validator.capabilities("nonexistent", "openai")
        assert caps is None

    def test_ollama_model_supports_streaming(self) -> None:
        caps = default_validator.capabilities("llama2", "ollama")
        assert caps is not None
        assert caps.supports_streaming is True

    def test_huggingface_model_no_system_messages(self) -> None:
        caps = default_validator.capabilities("gpt2", "huggingface")
        assert caps is not None
        assert caps.supports_system_messages is False


# ---------------------------------------------------------------------------
# default_validator — built-in catalog completeness
# ---------------------------------------------------------------------------


class TestDefaultValidator:
    def test_ollama_models_registered(self) -> None:
        for name in ["llama2", "llama3", "mistral", "codellama", "phi3", "qwen2", "gemma", "gemma2"]:
            assert default_validator.is_known(name, "ollama"), f"ollama/{name} missing"

    def test_huggingface_models_registered(self) -> None:
        for name in ["gpt2", "distilgpt2", "EleutherAI/gpt-j-6B", "bigscience/bloom"]:
            assert default_validator.is_known(name, "huggingface"), f"huggingface/{name} missing"

    def test_openai_models_registered(self) -> None:
        for name in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]:
            assert default_validator.is_known(name, "openai"), f"openai/{name} missing"

    def test_anthropic_models_registered(self) -> None:
        for name in [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]:
            assert default_validator.is_known(name, "anthropic"), f"anthropic/{name} missing"

    def test_all_four_providers_present(self) -> None:
        providers = default_validator.all_providers()
        for p in ["anthropic", "huggingface", "ollama", "openai"]:
            assert p in providers

    def test_build_default_validator_returns_fresh_instance(self) -> None:
        v1 = _build_default_validator()
        v2 = _build_default_validator()
        assert v1 is not v2
        assert v1.is_known("gpt-4o", "openai")
        assert v2.is_known("gpt-4o", "openai")

    def test_models_for_provider_not_empty(self) -> None:
        for provider in ["ollama", "huggingface", "openai", "anthropic"]:
            assert len(default_validator.models_for_provider(provider)) > 0

    def test_anthropic_large_context_window(self) -> None:
        caps = default_validator.capabilities("claude-3-opus-20240229", "anthropic")
        assert caps is not None
        assert caps.max_context_tokens == 200000

    def test_openai_mini_large_context(self) -> None:
        caps = default_validator.capabilities("gpt-4o-mini", "openai")
        assert caps is not None
        assert caps.max_context_tokens == 128000
