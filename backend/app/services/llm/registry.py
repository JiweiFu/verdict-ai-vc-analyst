"""LLM model registry with lazily-initialized instances."""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
)

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import (
    Environment,
    settings,
)
from app.core.logging import logger

_TOKEN_LIMIT: Dict[str, Any] = {"max_completion_tokens": settings.MAX_TOKENS}

# Placeholder used only so ``ChatOpenAI(...)`` can be constructed at import time
# when OpenAI is not the active provider (e.g. the Anthropic-only VC endpoint).
# The chat graph still needs a real OPENAI_API_KEY set to actually run against OpenAI.
_PLACEHOLDER_OPENAI_KEY = "sk-no-openai-key-configured"


def _resolve_openai_key() -> SecretStr:
    """Resolve the OpenAI API key at build time.

    Reads ``settings.OPENAI_API_KEY`` when this is called (not at import) and
    falls back to a non-empty placeholder so the ``ChatOpenAI`` constructor does
    not raise ``openai.OpenAIError`` when no key is configured.

    Returns:
        SecretStr wrapping either the real key or the placeholder.
    """
    return SecretStr(settings.OPENAI_API_KEY or _PLACEHOLDER_OPENAI_KEY)


class _LazyLLMEntry:
    """Lazy registry entry preserving the dict-like interface ``service.py`` relies on.

    Supports ``entry["name"]`` (cheap, never builds) and ``entry["llm"]`` (builds
    the ``ChatOpenAI`` instance on first access and caches it). This keeps the
    external contract of the old plain-dict entries while deferring construction.
    """

    def __init__(self, name: str, builder: Callable[[], BaseChatModel]) -> None:
        self._name = name
        self._builder = builder
        self._llm: Optional[BaseChatModel] = None

    def __getitem__(self, key: str) -> Any:
        if key == "name":
            return self._name
        if key == "llm":
            if self._llm is None:
                self._llm = self._builder()
            return self._llm
        raise KeyError(key)


class LLMRegistry:
    """Registry of available LLM models with lazily-initialized instances.

    This class maintains a list of LLM configurations and provides
    methods to retrieve them by name with optional argument overrides.
    No ``ChatOpenAI`` is constructed merely by importing this module; each
    model's client is built on first access of its ``["llm"]`` and cached.
    """

    LLMS: List[_LazyLLMEntry] = [
        _LazyLLMEntry(
            "gpt-5-mini",
            lambda: ChatOpenAI(
                model="gpt-5-mini",
                api_key=_resolve_openai_key(),
                model_kwargs=_TOKEN_LIMIT,
                reasoning={"effort": "low"},
            ),
        ),
        _LazyLLMEntry(
            "gpt-5.4",
            lambda: ChatOpenAI(
                model="gpt-5",
                api_key=_resolve_openai_key(),
                model_kwargs=_TOKEN_LIMIT,
                reasoning={"effort": "medium"},
            ),
        ),
        _LazyLLMEntry(
            "gpt-5.4-nano",
            lambda: ChatOpenAI(
                model="gpt-5.4-nano",
                api_key=_resolve_openai_key(),
                model_kwargs=_TOKEN_LIMIT,
                reasoning={"effort": "low"},
            ),
        ),
        _LazyLLMEntry(
            "gpt-5",
            lambda: ChatOpenAI(
                model="gpt-5",
                api_key=_resolve_openai_key(),
                model_kwargs=_TOKEN_LIMIT,
                top_p=0.95 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.8,
                presence_penalty=0.1 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.0,
                frequency_penalty=0.1 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.0,
            ),
        ),
    ]

    @classmethod
    def get(cls, model_name: str, **kwargs) -> BaseChatModel:
        """Get an LLM by name with optional argument overrides.

        When kwargs are provided a fresh ChatOpenAI instance is returned with
        those overrides applied, leaving the shared registry entry untouched.

        Args:
            model_name: Name of the model to retrieve.
            **kwargs: Optional arguments to override default model configuration.

        Returns:
            BaseChatModel instance.

        Raises:
            ValueError: If model_name is not found in LLMS.
        """
        model_entry = next((e for e in cls.LLMS if e["name"] == model_name), None)

        if not model_entry:
            available = ", ".join(e["name"] for e in cls.LLMS)
            raise ValueError(f"model '{model_name}' not found in registry. available models: {available}")

        if kwargs:
            logger.debug("creating_llm_with_custom_args", model_name=model_name, custom_args=list(kwargs.keys()))
            return ChatOpenAI(model=model_name, api_key=_resolve_openai_key(), **kwargs)

        logger.debug("using_default_llm_instance", model_name=model_name)
        return model_entry["llm"]

    @classmethod
    def get_all_names(cls) -> List[str]:
        """Return all registered model names in order.

        Returns:
            List of model name strings.
        """
        return [e["name"] for e in cls.LLMS]

    @classmethod
    def get_model_at_index(cls, index: int) -> _LazyLLMEntry:
        """Return the model entry at a specific index, wrapping to 0 if out of range.

        Args:
            index: Index into LLMS.

        Returns:
            Model entry (its ``["llm"]`` is still built lazily on access).
        """
        if 0 <= index < len(cls.LLMS):
            return cls.LLMS[index]
        return cls.LLMS[0]
