"""Observability module for the application."""

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.core.config import settings
from app.core.logging import logger


def langfuse_init():
    """Initialize Langfuse."""
    if not settings.LANGFUSE_TRACING_ENABLED:
        logger.debug("langfuse_tracing_disabled")
        return

    langfuse = Langfuse(
        tracing_enabled=settings.LANGFUSE_TRACING_ENABLED,
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,
        environment=settings.ENVIRONMENT.value,
        debug=settings.DEBUG,
    )

    try:
        if langfuse.auth_check():
            logger.debug("langfuse_auth_success")
        else:
            logger.warning("langfuse_auth_failure")
    except Exception:
        logger.exception("langfuse_auth_check_failed")


def get_langfuse_callback_handler() -> CallbackHandler:
    """Create a Langfuse CallbackHandler for tracking LLM interactions.

    Returns:
        CallbackHandler: Configured Langfuse callback handler.
    """
    return CallbackHandler()


langfuse_callback_handler = get_langfuse_callback_handler()

# Placeholder values shipped in .env.example; treated as "unconfigured".
_LANGFUSE_PLACEHOLDERS = frozenset({"your-langfuse-public-key", "your-langfuse-secret-key"})

# Guards the one-time debug line emitted by get_vc_callbacks().
_vc_callbacks_logged = False


def _langfuse_configured() -> bool:
    """Return True only when Langfuse keys are real (non-empty, non-placeholder)."""
    if not settings.LANGFUSE_TRACING_ENABLED:
        return False
    public_key = settings.LANGFUSE_PUBLIC_KEY
    secret_key = settings.LANGFUSE_SECRET_KEY
    if not public_key or not secret_key:
        return False
    if public_key in _LANGFUSE_PLACEHOLDERS or secret_key in _LANGFUSE_PLACEHOLDERS:
        return False
    return True


def get_vc_callbacks() -> list:
    """Return Langfuse callbacks for the VC pipeline, or [] when tracing is off/unconfigured."""
    global _vc_callbacks_logged
    configured = _langfuse_configured()
    # Log the resolved tracing decision once to avoid flooding the VC pipeline logs.
    if not _vc_callbacks_logged:
        logger.debug("vc_callbacks_resolved", langfuse_enabled=configured)
        _vc_callbacks_logged = True
    if configured:
        return [langfuse_callback_handler]
    return []
