"""Long-term memory for the VC analysis pipeline — fully local, no external API key.

This is a SEPARATE, parallel service to ``app/services/memory.py`` (the chat
app's mem0 wrapper). It preserves the app's bring-your-own-key story by using a
LOCAL embedder, so storing and recalling past deal analyses needs zero external
API keys.

Design choices:
- Local embedder: mem0 ``huggingface`` provider running
  ``sentence-transformers/all-MiniLM-L6-v2`` (384-dim) on-device via
  sentence-transformers. No OpenAI/HF API key required.
- ``infer=False`` on every ``add()``: mem0 stores the raw analysis text WITHOUT
  invoking an LLM for fact-extraction. mem0's default LLM is OpenAI, which would
  require a key — skipping inference keeps the whole memory path key-free
  (search only uses the embedder, never an LLM).
- Separate pgvector collection ``vc_memory``: the local embedder's 384-dim
  vectors are incompatible with the chat app's OpenAI 1536-dim collection, so
  they must live in their own table.
- Single-user partition ``user_id = "vc-global"``: this is a single-user local
  desktop app, so all analyses share one memory space and recall works across
  past deals.
- Fully optional / graceful: any failure (missing dep, model download failure,
  Postgres/pgvector down, anything) disables memory permanently and turns every
  method into a silent no-op. Memory never crashes the caller.

SECURITY: only analysis CONTENT (company name, signals, recommendation) is ever
stored or logged — the user's LLM api_key is NEVER written to memory or logged.
"""

from typing import Optional

from mem0 import AsyncMemory

from app.core.config import settings
from app.core.logging import logger

# Local embedder configuration — on-device, no external API key needed.
_VC_MEMORY_COLLECTION_NAME = "vc_memory"
_VC_MEMORY_USER_ID = "vc-global"
_VC_EMBEDDER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_VC_EMBEDDER_DIMS = 384


class VCMemoryService:
    """Optional local long-term memory for VC deal analyses (mem0 + pgvector)."""

    def __init__(self):
        """Initialize the service in a lazy, not-yet-loaded state."""
        self._memory: AsyncMemory | None = None
        self._disabled: bool = False

    async def _get_memory(self) -> Optional[AsyncMemory]:
        """Lazily build and cache the local-embedder ``AsyncMemory`` instance.

        Returns ``None`` if memory is (or becomes) disabled. On any init failure
        the service is permanently disabled and a single warning is logged.
        """
        if self._disabled:
            return None
        if self._memory is not None:
            return self._memory
        try:
            self._memory = await AsyncMemory.from_config(
                config_dict={
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "collection_name": _VC_MEMORY_COLLECTION_NAME,
                            "embedding_model_dims": _VC_EMBEDDER_DIMS,
                            "dbname": settings.POSTGRES_DB,
                            "user": settings.POSTGRES_USER,
                            "password": settings.POSTGRES_PASSWORD,
                            "host": settings.POSTGRES_HOST,
                            "port": settings.POSTGRES_PORT,
                        },
                    },
                    "embedder": {
                        "provider": "huggingface",
                        "config": {
                            "model": _VC_EMBEDDER_MODEL,
                            "embedding_dims": _VC_EMBEDDER_DIMS,
                        },
                    },
                }
            )
            return self._memory
        except Exception as e:
            self._disabled = True
            logger.warning("vc_memory_unavailable_disabled", error=str(e))
            return None

    async def store_analysis(
        self,
        *,
        company_name: str,
        summary: str,
        recommendation: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Store a compact record of a VC deal analysis in local memory.

        Stores only analysis content (company, summary, recommendation) — never
        an api_key. No-op if memory is disabled or any error occurs.
        """
        if self._disabled:
            return
        try:
            memory = await self._get_memory()
            if memory is None:
                return

            parts = [f"Company: {company_name}", f"Summary: {summary}"]
            if recommendation:
                parts.append(f"Recommendation: {recommendation}")
            content = "\n".join(parts)

            await memory.add(
                [{"role": "user", "content": content}],
                user_id=_VC_MEMORY_USER_ID,
                metadata=metadata,
                infer=False,
            )
            logger.info("vc_memory_stored", company_name=company_name, recommendation=recommendation)
        except Exception as e:
            logger.warning("vc_memory_store_failed", company_name=company_name, error=str(e))

    async def recall_similar(self, query: str, limit: int = 3) -> str:
        """Recall analyses similar to ``query`` from local memory.

        Returns a short bulleted string of matching memories, or ``""`` when
        memory is disabled, there are no hits, or any error occurs.
        """
        if self._disabled:
            return ""
        try:
            memory = await self._get_memory()
            if memory is None:
                return ""

            results = await memory.search(query=query, user_id=_VC_MEMORY_USER_ID, limit=limit)
            hits = results.get("results", []) if isinstance(results, dict) else []
            if not hits:
                return ""
            return "\n".join([f"* {hit['memory']}" for hit in hits])
        except Exception as e:
            logger.warning("vc_memory_recall_failed", error=str(e))
            return ""


vc_memory = VCMemoryService()
