"""LangGraph workflow for the VC startup-evaluation pipeline.

Graph shape::

    scout ──┬──▶ market ──┐
            ├──▶ product ─┼──▶ chief ──▶ END
            └──▶ founder ─┘

The scout parses raw text into a ``StartupInfo``; the three specialist nodes fan
out and run in parallel; the chief integrates their outputs into a final
recommendation. This is a one-shot pipeline, so the graph compiles WITHOUT a
Postgres checkpointer (no persistence needed) — unlike the chat graph in
``app.core.langgraph.graph``.
"""

from typing import (
    AsyncIterator,
    Optional,
)

from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import (
    END,
    START,
    StateGraph,
)
from langgraph.graph.state import CompiledStateGraph

from app.core.langgraph.vc_agents import (
    chief_node,
    founder_node,
    market_node,
    product_node,
    scout_node,
)
from app.core.logging import logger
from app.core.observability import get_vc_callbacks
from app.schemas.vc_state import VCState
from app.services.vc_llm import resolve_api_key

# The compiled graph is stateless and reusable, so build it once at import.
_vc_graph: Optional[CompiledStateGraph] = None


def build_vc_graph() -> CompiledStateGraph:
    """Build and compile the VC analysis ``StateGraph``.

    Returns:
        The compiled graph (no checkpointer — one-shot pipeline).
    """
    builder = StateGraph(VCState)

    builder.add_node("scout", scout_node)
    builder.add_node("market", market_node)
    builder.add_node("product", product_node)
    builder.add_node("founder", founder_node)
    builder.add_node("chief", chief_node)

    builder.add_edge(START, "scout")
    # Fan out from scout to the three specialists in parallel.
    builder.add_edge("scout", "market")
    builder.add_edge("scout", "product")
    builder.add_edge("scout", "founder")
    # Fan in: chief runs only after all three specialists complete.
    builder.add_edge("market", "chief")
    builder.add_edge("product", "chief")
    builder.add_edge("founder", "chief")
    builder.add_edge("chief", END)

    graph = builder.compile(name="VC Analysis Pipeline")
    logger.info("vc_graph_compiled")
    return graph


def get_vc_graph() -> CompiledStateGraph:
    """Return the compiled VC graph, building it on first access.

    Returns:
        The cached compiled graph.
    """
    global _vc_graph
    if _vc_graph is None:
        _vc_graph = build_vc_graph()
    return _vc_graph


async def run_vc_analysis(
    raw_input: str,
    provider: str = "anthropic",
    model: str = "claude-opus-4-8",
    api_key: Optional[str] = None,
) -> dict:
    """Run the full VC analysis pipeline on a raw company description.

    Args:
        raw_input: The raw startup/company description text.
        provider: LLM provider — ``"anthropic"`` (default), ``"openai"``, or
            ``"deepseek"``.
        model: The provider-specific model name.
        api_key: The user's API key. When ``None``, falls back to the matching
            provider env var (``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` /
            ``DEEPSEEK_API_KEY``) for local CLI runs.

    Returns:
        A dict with ``startup_info``, ``market_analysis``, ``product_analysis``,
        ``founder_analysis``, and ``final`` (each a Pydantic model or ``None``).

    Raises:
        ValueError: When no API key can be resolved for the provider.
    """
    resolved_key = resolve_api_key(provider, api_key)
    if not resolved_key:
        raise ValueError(
            f"no api key for provider '{provider}'. pass api_key or set the matching provider env var."
        )

    graph = get_vc_graph()
    initial_state = VCState(raw_input=raw_input, provider=provider, model=model, api_key=resolved_key)

    # Langfuse tracing: get_vc_callbacks() returns [] when Langfuse is not
    # configured, so this is a no-op unless real keys are present. Callbacks
    # propagate to every nested LLM call in the graph.
    config: RunnableConfig = {"callbacks": get_vc_callbacks()}

    logger.info("vc_analysis_started", provider=provider, model=model)
    result = await graph.ainvoke(initial_state, config=config)
    logger.info("vc_analysis_completed", provider=provider, model=model)

    # ``ainvoke`` returns the final state as a dict (Pydantic-state values).
    return {
        "startup_info": result.get("startup_info"),
        "market_analysis": result.get("market_analysis"),
        "product_analysis": result.get("product_analysis"),
        "founder_analysis": result.get("founder_analysis"),
        "final": result.get("final"),
    }


# Maps the writer's node names to the public result keys used in the ``done`` event.
_NODE_TO_RESULT_KEY: dict[str, str] = {
    "scout": "startup_info",
    "market": "market_analysis",
    "product": "product_analysis",
    "founder": "founder_analysis",
    "chief": "final",
}


async def stream_vc_analysis(
    raw_input: str,
    provider: str,
    model: str,
    api_key: Optional[str],
    agent_feedback: Optional[dict] = None,
) -> AsyncIterator[dict]:
    """Stream the VC analysis pipeline as protocol events for the API layer.

    Drives the same compiled graph as :func:`run_vc_analysis`, but consumes the
    custom-stream events emitted by each node's ``get_stream_writer`` so the API
    can serialize them as NDJSON. Each yielded dict is one protocol event:
    ``node_start`` / ``node_complete`` (per node), a final ``done`` carrying the
    assembled result map, or a terminal ``error`` if anything fails.

    Args:
        raw_input: The raw startup/company description text.
        provider: LLM provider — ``"anthropic"``, ``"openai"``, or ``"deepseek"``.
        model: The provider-specific model name.
        api_key: The user's API key. When falsy, falls back to the matching
            provider env var via :func:`resolve_api_key`.
        agent_feedback: Optional per-agent user feedback, keyed by node name.

    Yields:
        Protocol event dicts per the NDJSON event contract.
    """
    try:
        resolved_key = resolve_api_key(provider, api_key)
        if not resolved_key:
            raise ValueError(
                f"no api key for provider '{provider}'. pass api_key or set the matching provider env var."
            )

        initial_state = VCState(
            raw_input=raw_input,
            provider=provider,
            model=model,
            api_key=resolved_key,
            agent_feedback=agent_feedback or {},
        )

        graph = get_vc_graph()

        # Langfuse tracing: get_vc_callbacks() returns [] when Langfuse is not
        # configured, so this is a no-op unless real keys are present.
        config: RunnableConfig = {"callbacks": get_vc_callbacks()}

        logger.info("vc_stream_started", provider=provider, model=model)

        # Accumulate node_complete payloads so we can assemble the final result.
        node_data: dict[str, Optional[dict]] = {}

        async for chunk in graph.astream(initial_state, stream_mode="custom", config=config):
            # Each chunk IS already a protocol dict emitted by a node's writer.
            if chunk.get("type") == "node_complete":
                node_data[chunk["node"]] = chunk.get("data")
            yield chunk

        result = {key: node_data.get(node) for node, key in _NODE_TO_RESULT_KEY.items()}
        logger.info("vc_stream_completed", provider=provider, model=model)
        yield {"type": "done", "result": result}
    except Exception as exc:
        logger.exception("vc_stream_failed", provider=provider, model=model)
        yield {"type": "error", "detail": str(exc)}
