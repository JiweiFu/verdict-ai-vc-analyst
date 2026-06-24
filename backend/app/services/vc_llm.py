"""Provider-agnostic chat-model factory for the VC analysis pipeline.

Unlike ``app.services.llm`` (which drives the chat agent off a fixed OpenAI
registry), this factory builds a fresh LangChain chat model per request from a
user-supplied ``provider`` / ``model`` / ``api_key`` triple. This is the
bring-your-own-key path: the VC who opens the app picks a provider and pastes
their own key, so the key must never be read solely from server env.

Three providers are supported: Anthropic (default, ``claude-opus-4-8``), OpenAI
(e.g. ``gpt-4o`` / ``gpt-5``), and DeepSeek (``deepseek-chat``). DeepSeek uses
``langchain-deepseek`` when installed and otherwise falls back to ``ChatOpenAI``
pointed at DeepSeek's OpenAI-compatible endpoint.
"""

from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import settings
from app.core.logging import logger

try:
    from langchain_deepseek import ChatDeepSeek

    _HAS_LANGCHAIN_DEEPSEEK = True
except ImportError:  # pragma: no cover - optional dependency
    ChatDeepSeek = None  # type: ignore[assignment,misc]
    _HAS_LANGCHAIN_DEEPSEEK = False

# Default model per provider, used when the caller does not specify one.
DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-opus-4-8",
    "openai": "gpt-4o",
    "deepseek": "deepseek-chat",
}

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def get_chat_model(provider: str, model: str, api_key: str) -> BaseChatModel:
    """Build a LangChain chat model for the given provider with the user's key.

    Args:
        provider: One of ``"anthropic"``, ``"openai"``, or ``"deepseek"``
            (case-insensitive).
        model: The provider-specific model name. Falls back to the provider's
            default when empty.
        api_key: The user's API key for the provider (bring-your-own-key).

    Returns:
        A configured ``BaseChatModel`` ready for ``.with_structured_output(...)``.

    Raises:
        ValueError: When the provider is unknown or no API key is available.
    """
    normalized = provider.strip().lower()
    chosen_model = model or DEFAULT_MODELS.get(normalized, "")

    if not api_key:
        logger.error("vc_llm_missing_api_key", provider=normalized)
        raise ValueError(f"no api key supplied for provider '{provider}'")

    if normalized == "anthropic":
        logger.info("vc_chat_model_created", provider=normalized, model=chosen_model)
        return ChatAnthropic(
            model_name=chosen_model,
            api_key=SecretStr(api_key),
            timeout=settings.LLM_TOTAL_TIMEOUT,
            max_tokens_to_sample=settings.VC_LLM_MAX_TOKENS,
            stop=None,
        )

    if normalized == "openai":
        logger.info("vc_chat_model_created", provider=normalized, model=chosen_model)
        return ChatOpenAI(model=chosen_model, api_key=SecretStr(api_key))

    if normalized == "deepseek":
        if _HAS_LANGCHAIN_DEEPSEEK and ChatDeepSeek is not None:
            logger.info("vc_chat_model_created", provider=normalized, model=chosen_model, backend="langchain_deepseek")
            return ChatDeepSeek(model=chosen_model, api_key=SecretStr(api_key))
        # Fallback: DeepSeek exposes an OpenAI-compatible API.
        logger.info("vc_chat_model_created", provider=normalized, model=chosen_model, backend="openai_compatible")
        return ChatOpenAI(model=chosen_model, api_key=SecretStr(api_key), base_url=DEEPSEEK_BASE_URL)

    logger.error("vc_llm_unknown_provider", provider=provider)
    raise ValueError(f"unknown provider '{provider}'. supported: anthropic, openai, deepseek")


def resolve_api_key(provider: str, api_key: Optional[str]) -> str:
    """Resolve the API key, falling back to the matching server env var.

    Used for local CLI runs where the user has not pasted a key; the deployed
    app always passes the user's key explicitly.

    Args:
        provider: The chosen provider (case-insensitive).
        api_key: An explicit key, or ``None`` to fall back to env.

    Returns:
        The resolved key, or an empty string when none is configured.
    """
    if api_key:
        return api_key

    normalized = provider.strip().lower()
    fallbacks = {
        "anthropic": settings.ANTHROPIC_API_KEY,
        "openai": settings.OPENAI_API_KEY,
        "deepseek": settings.DEEPSEEK_API_KEY,
    }
    return fallbacks.get(normalized, "")
