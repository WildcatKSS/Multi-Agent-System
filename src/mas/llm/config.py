"""LLM provider configuration contracts.

Frozen, validated configuration dataclasses for the LLM provider layer: a shared
:class:`LLMConfig` base plus provider-specific configs (Ollama, HuggingFace,
OpenAI, Anthropic). They follow the same immutable, ``__post_init__``-validated
pattern as the rest of the LLM contracts, and raise
:class:`~mas.llm.contracts.ValidationError` on invalid input.

The configs are plain data with no I/O. ``to_dict``/``from_dict`` provide a
round-trippable mapping form for serialization; note that the dict includes
``api_key`` and must therefore be treated as sensitive.
"""

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, get_args
from urllib.parse import urlparse

from mas.llm.contracts import ValidationError

#: HuggingFace inference task types.
HFTask = Literal["text-generation", "text2text"]
_VALID_HF_TASKS: frozenset[str] = frozenset(get_args(HFTask))

#: Known Anthropic API versions (the ``anthropic-version`` header value).
AnthropicVersion = Literal["2023-06-01", "2023-01-01"]
_VALID_ANTHROPIC_VERSIONS: frozenset[str] = frozenset(get_args(AnthropicVersion))


def _validate_url(url: str, field: str) -> None:
    """Validate that ``url`` is a well-formed http(s) URL.

    Args:
        url: The URL to validate.
        field: Field name, used in the error message.

    Raises:
        ValidationError: If the URL has no http/https scheme or no host.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError(f"{field} must be a valid http(s) URL, got {url!r}")


@dataclass(frozen=True)
class LLMConfig:
    """Base configuration shared by all LLM providers.

    Immutable (``frozen=True``) and validated on creation.

    Attributes:
        model: Model identifier to use. Must not be empty.
        api_key: API credential, or ``None`` for providers that need none
            (e.g. a local Ollama server).
        timeout_seconds: Per-call timeout in seconds. Must be > 0.
        max_retries: Maximum retries for transient failures. Must be >= 0.

    Raises:
        ValidationError: If ``model`` is empty, ``timeout_seconds`` <= 0, or
            ``max_retries`` < 0.
    """

    model: str
    api_key: str | None = None
    timeout_seconds: int = 30
    max_retries: int = 3

    def __post_init__(self) -> None:
        """Validate the configuration on creation."""
        if not self.model or not self.model.strip():
            raise ValidationError("model cannot be empty")
        if self.timeout_seconds <= 0:
            raise ValidationError(
                f"timeout_seconds must be > 0, got {self.timeout_seconds}"
            )
        if self.max_retries < 0:
            raise ValidationError(
                f"max_retries cannot be negative, got {self.max_retries}"
            )

    def _require_api_key(self, provider: str) -> None:
        """Raise if this config has no usable API key.

        Args:
            provider: Provider name, used in the error message.

        Raises:
            ValidationError: If ``api_key`` is missing or empty.
        """
        if not self.api_key:
            raise ValidationError(f"{provider} requires a non-empty api_key")

    def to_dict(self) -> dict[str, Any]:
        """Serialize this config to a plain dict.

        Returns:
            A dict of all fields. Includes ``api_key`` -- treat as sensitive.
        """
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LLMConfig":
        """Construct a config from a mapping (inverse of :meth:`to_dict`).

        Args:
            data: Mapping of field names to values.

        Returns:
            A validated config instance.

        Raises:
            ValidationError: If the resulting config is invalid.
            TypeError: If ``data`` contains unknown fields.
        """
        return cls(**data)


@dataclass(frozen=True)
class OllamaConfig(LLMConfig):
    """Configuration for a local Ollama server.

    Attributes:
        base_url: Base URL of the Ollama server. Must be a valid http(s) URL.

    Raises:
        ValidationError: If ``base_url`` is not a valid http(s) URL (in addition
            to the base validations).
    """

    base_url: str = "http://localhost:11434"

    def __post_init__(self) -> None:
        """Validate Ollama configuration."""
        super().__post_init__()
        _validate_url(self.base_url, "base_url")


@dataclass(frozen=True)
class HuggingFaceConfig(LLMConfig):
    """Configuration for the HuggingFace Inference API.

    Attributes:
        task: Inference task type, one of ``"text-generation"`` or
            ``"text2text"``.

    Raises:
        ValidationError: If ``api_key`` is missing or ``task`` is invalid.
    """

    task: HFTask = "text-generation"

    def __post_init__(self) -> None:
        """Validate HuggingFace configuration."""
        super().__post_init__()
        self._require_api_key("HuggingFace")
        if self.task not in _VALID_HF_TASKS:
            raise ValidationError(
                f"task must be one of {sorted(_VALID_HF_TASKS)}, got {self.task!r}"
            )


@dataclass(frozen=True)
class OpenAIConfig(LLMConfig):
    """Configuration for the OpenAI API.

    Attributes:
        organization: Optional OpenAI organization identifier.

    Raises:
        ValidationError: If ``api_key`` is missing.
    """

    organization: str | None = None

    def __post_init__(self) -> None:
        """Validate OpenAI configuration."""
        super().__post_init__()
        self._require_api_key("OpenAI")


@dataclass(frozen=True)
class AnthropicConfig(LLMConfig):
    """Configuration for the Anthropic API.

    Attributes:
        version: The ``anthropic-version`` header value. Must be a known version.

    Raises:
        ValidationError: If ``api_key`` is missing or ``version`` is unknown.
    """

    version: AnthropicVersion = "2023-06-01"

    def __post_init__(self) -> None:
        """Validate Anthropic configuration."""
        super().__post_init__()
        self._require_api_key("Anthropic")
        if self.version not in _VALID_ANTHROPIC_VERSIONS:
            raise ValidationError(
                f"version must be one of {sorted(_VALID_ANTHROPIC_VERSIONS)}, "
                f"got {self.version!r}"
            )
