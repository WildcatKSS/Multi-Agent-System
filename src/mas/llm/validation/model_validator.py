"""Model validation: catalog, parameter bounds, and capability detection.

Provides a :class:`ModelValidator` that maintains a catalog of known models
per provider, validates generation parameters against declared bounds, and
exposes capability metadata (context window size, system-message support, etc.)
without performing any network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mas.llm.config import AnthropicConfig, HuggingFaceConfig, LLMConfig, OllamaConfig, OpenAIConfig

_CONFIG_PROVIDER: dict[type[LLMConfig], str] = {
    OllamaConfig: "ollama",
    HuggingFaceConfig: "huggingface",
    OpenAIConfig: "openai",
    AnthropicConfig: "anthropic",
}


@dataclass(frozen=True)
class ModelCapabilities:
    """Declared capabilities of a specific model.

    Attributes:
        supports_system_messages: Whether the model accepts a ``system`` role message.
        supports_streaming: Whether the model/provider supports streaming output.
        max_context_tokens: Maximum total tokens the model accepts (prompt + completion).
        max_output_tokens: Maximum tokens the model can produce in one response.
    """

    supports_system_messages: bool = True
    supports_streaming: bool = False
    max_context_tokens: int = 4096
    max_output_tokens: int = 4096


@dataclass(frozen=True)
class ModelInfo:
    """Metadata about a single model in the catalog.

    Attributes:
        name: Model identifier string (e.g. ``"gpt-4o"``).
        provider: Provider name (e.g. ``"openai"``).
        capabilities: Declared capability set for this model.
    """

    name: str
    provider: str
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)


@dataclass(frozen=True)
class ValidationResult:
    """Result of a model or parameter validation check.

    Attributes:
        valid: Whether the subject passed validation.
        errors: Tuple of human-readable error messages (empty when valid).
    """

    valid: bool
    errors: tuple[str, ...] = ()

    @classmethod
    def ok(cls) -> ValidationResult:
        """Return a passing result with no errors."""
        return cls(valid=True)

    @classmethod
    def fail(cls, *errors: str) -> ValidationResult:
        """Return a failing result with one or more error messages."""
        return cls(valid=False, errors=errors)


# ---------------------------------------------------------------------------
# Parameter-bounds registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _ParameterBounds:
    name: str
    min_value: float
    max_value: float

    def check(self, value: float) -> str | None:
        """Return an error string if value is out of range, else None."""
        if value < self.min_value or value > self.max_value:
            return f"{self.name} must be between {self.min_value} and {self.max_value}, got {value}"
        return None


_BOUNDS: dict[str, _ParameterBounds] = {
    "temperature": _ParameterBounds("temperature", 0.0, 2.0),
    "top_p": _ParameterBounds("top_p", 0.0, 1.0),
    "frequency_penalty": _ParameterBounds("frequency_penalty", -2.0, 2.0),
    "presence_penalty": _ParameterBounds("presence_penalty", -2.0, 2.0),
}


# ---------------------------------------------------------------------------
# ModelValidator
# ---------------------------------------------------------------------------

class ModelValidator:
    """Validates models, parameters, and configs for LLM providers.

    Maintains an in-memory catalog of :class:`ModelInfo` objects. Register
    models with :meth:`register`; then call :meth:`validate_model`,
    :meth:`validate_parameters`, or :meth:`validate_config` to check inputs
    before dispatching to a provider.

    The module-level :data:`default_validator` is pre-populated with catalog
    entries for all four built-in providers.
    """

    def __init__(self) -> None:
        # keyed by (provider, model_name)
        self._catalog: dict[tuple[str, str], ModelInfo] = {}

    # ------------------------------------------------------------------
    # Catalog management
    # ------------------------------------------------------------------

    def register(self, model: ModelInfo) -> None:
        """Add a :class:`ModelInfo` to the catalog.

        If a model with the same ``(provider, name)`` pair already exists, it
        is silently replaced.

        Args:
            model: The model metadata to register.
        """
        self._catalog[(model.provider, model.name)] = model

    def get(self, model: str, provider: str) -> ModelInfo | None:
        """Return the :class:`ModelInfo` for ``(provider, model)``, or ``None``.

        Args:
            model: Model identifier.
            provider: Provider name.

        Returns:
            The registered :class:`ModelInfo`, or ``None`` if not found.
        """
        return self._catalog.get((provider, model))

    def is_known(self, model: str, provider: str) -> bool:
        """Return whether ``model`` is catalogued under ``provider``.

        Args:
            model: Model identifier.
            provider: Provider name.
        """
        return (provider, model) in self._catalog

    def models_for_provider(self, provider: str) -> list[ModelInfo]:
        """Return all catalogued models for ``provider``, sorted by name.

        Args:
            provider: Provider name.

        Returns:
            A sorted list of :class:`ModelInfo` objects (may be empty).
        """
        return sorted(
            [info for (p, _), info in self._catalog.items() if p == provider],
            key=lambda m: m.name,
        )

    def all_providers(self) -> list[str]:
        """Return a sorted list of provider names that have at least one model."""
        return sorted({p for p, _ in self._catalog})

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_model(self, model: str, provider: str) -> ValidationResult:
        """Check that ``model`` is catalogued for ``provider``.

        Args:
            model: Model identifier to look up.
            provider: Provider name to look up under.

        Returns:
            :class:`ValidationResult` — passing if the model is in the catalog.
        """
        if not model:
            return ValidationResult.fail("model name cannot be empty")
        if not provider:
            return ValidationResult.fail("provider name cannot be empty")
        if not self.is_known(model, provider):
            return ValidationResult.fail(
                f"model {model!r} is not known for provider {provider!r}"
            )
        return ValidationResult.ok()

    def validate_parameters(self, params: dict[str, Any]) -> ValidationResult:
        """Validate generation parameters against declared bounds.

        Checked parameters:

        - ``temperature``: ``[0.0, 2.0]``
        - ``top_p``: ``[0.0, 1.0]``
        - ``frequency_penalty``: ``[-2.0, 2.0]``
        - ``presence_penalty``: ``[-2.0, 2.0]``
        - ``max_tokens``: must be a positive integer

        Unknown parameter names are accepted without error.

        Args:
            params: Generation kwargs to validate.

        Returns:
            :class:`ValidationResult` — passing iff no bound violations found.
        """
        errors: list[str] = []
        for key, value in params.items():
            if key == "max_tokens":
                if not isinstance(value, int) or value <= 0:
                    errors.append(f"max_tokens must be a positive integer, got {value!r}")
            elif key in _BOUNDS:
                if not isinstance(value, (int, float)):
                    errors.append(f"{key} must be a number, got {value!r}")
                else:
                    msg = _BOUNDS[key].check(float(value))
                    if msg:
                        errors.append(msg)
        if errors:
            return ValidationResult.fail(*errors)
        return ValidationResult.ok()

    def validate_config(self, config: LLMConfig) -> ValidationResult:
        """Validate that the model in ``config`` is known for its provider.

        Dispatches on the concrete config type to determine the provider name,
        then delegates to :meth:`validate_model`.

        Args:
            config: Provider configuration to validate.

        Returns:
            :class:`ValidationResult` — passing if the model is in the catalog.
        """
        provider = next((p for cls, p in _CONFIG_PROVIDER.items() if isinstance(config, cls)), None)
        if provider is None:
            return ValidationResult.fail(f"unrecognised config type: {type(config).__name__!r}")
        return self.validate_model(config.model, provider)

    def capabilities(self, model: str, provider: str) -> ModelCapabilities | None:
        """Return the :class:`ModelCapabilities` for a catalogued model.

        Args:
            model: Model identifier.
            provider: Provider name.

        Returns:
            The model's :class:`ModelCapabilities`, or ``None`` if not in catalog.
        """
        info = self.get(model, provider)
        return info.capabilities if info else None


# ---------------------------------------------------------------------------
# Default validator — pre-populated with built-in provider catalogs
# ---------------------------------------------------------------------------

def _build_default_validator() -> ModelValidator:
    v = ModelValidator()

    # --- Ollama ---
    _ollama_streaming = ModelCapabilities(
        supports_system_messages=True, supports_streaming=True,
        max_context_tokens=8192, max_output_tokens=4096,
    )
    for name in ["llama2", "llama3", "llama3.1", "llama3.2", "mistral", "codellama"]:
        v.register(ModelInfo(name=name, provider="ollama", capabilities=_ollama_streaming))
    for name, ctx in [("phi3", 4096), ("qwen2", 32768), ("gemma", 8192), ("gemma2", 8192)]:
        v.register(ModelInfo(
            name=name, provider="ollama",
            capabilities=ModelCapabilities(
                supports_system_messages=True, supports_streaming=True,
                max_context_tokens=ctx, max_output_tokens=4096,
            ),
        ))

    # --- HuggingFace ---
    _hf_caps = ModelCapabilities(
        supports_system_messages=False, supports_streaming=False,
        max_context_tokens=1024, max_output_tokens=512,
    )
    for name in ["gpt2", "distilgpt2"]:
        v.register(ModelInfo(name=name, provider="huggingface", capabilities=_hf_caps))
    _hf_large_caps = ModelCapabilities(
        supports_system_messages=False, supports_streaming=False,
        max_context_tokens=2048, max_output_tokens=1024,
    )
    for name in ["EleutherAI/gpt-j-6B", "bigscience/bloom", "facebook/opt-1.3b"]:
        v.register(ModelInfo(name=name, provider="huggingface", capabilities=_hf_large_caps))

    # --- OpenAI ---
    for name, ctx, out in [
        ("gpt-4o", 128000, 16384),
        ("gpt-4o-mini", 128000, 16384),
        ("gpt-4-turbo", 128000, 4096),
        ("gpt-4", 8192, 8192),
        ("gpt-3.5-turbo", 16385, 4096),
    ]:
        v.register(ModelInfo(
            name=name, provider="openai",
            capabilities=ModelCapabilities(
                supports_system_messages=True, supports_streaming=True,
                max_context_tokens=ctx, max_output_tokens=out,
            ),
        ))

    # --- Anthropic ---
    for name, ctx, out in [
        ("claude-3-5-sonnet-20241022", 200000, 8192),
        ("claude-3-5-haiku-20241022", 200000, 8192),
        ("claude-3-opus-20240229", 200000, 4096),
        ("claude-3-sonnet-20240229", 200000, 4096),
        ("claude-3-haiku-20240307", 200000, 4096),
    ]:
        v.register(ModelInfo(
            name=name, provider="anthropic",
            capabilities=ModelCapabilities(
                supports_system_messages=True, supports_streaming=True,
                max_context_tokens=ctx, max_output_tokens=out,
            ),
        ))

    return v


#: Pre-populated :class:`ModelValidator` with catalog entries for all built-in providers.
default_validator: ModelValidator = _build_default_validator()
