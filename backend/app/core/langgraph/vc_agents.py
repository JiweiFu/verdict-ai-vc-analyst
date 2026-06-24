"""LangGraph node functions for the VC startup-evaluation pipeline.

The pipeline is one lightweight parser (``scout_node``) followed by three
specialist analysts (``market_node`` / ``product_node`` / ``founder_node``) that
run in parallel, and a chief integrator (``chief_node``). Every analyst node
emits structured output validated against a Pydantic schema via
``.with_structured_output(Model)``; the scout only parses raw text into a
``StartupInfo`` and does no scoring.

Each node builds its own chat model from the per-request provider/model/api_key
carried on the state, so the pipeline is provider-agnostic and uses the user's
own key (bring-your-own-key).
"""

from typing import cast

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)
from langgraph.config import get_stream_writer

from app.core.logging import logger
from app.core.prompts.vc import (
    CHIEF_SYSTEM_PROMPT,
    FOUNDER_SYSTEM_PROMPT,
    MARKET_SYSTEM_PROMPT,
    PRODUCT_SYSTEM_PROMPT,
    SCOUT_SYSTEM_PROMPT,
)
from app.schemas.startup import (
    FounderAnalysis,
    IntegratedAnalysis,
    MarketAnalysis,
    ProductAnalysis,
    StartupInfo,
)
from app.schemas.vc_state import VCState
from app.services.vc_llm import get_chat_model
from app.services.vc_memory import vc_memory


def _render_startup_info(startup_info: StartupInfo) -> str:
    """Render a ``StartupInfo`` as a readable bullet list, skipping empty fields.

    Args:
        startup_info: The parsed startup profile.

    Returns:
        A newline-delimited string of populated ``field: value`` pairs.
    """
    lines = [f"{field}: {value}" for field, value in startup_info.model_dump().items() if value]
    return "\n".join(lines)


def _apply_feedback(content: str, state: VCState, node: str) -> str:
    """Append per-agent user feedback (if any) to a human-message body.

    Args:
        content: The base human-message content.
        state: The current graph state (reads ``agent_feedback``).
        node: The node name used to look up feedback in ``agent_feedback``.

    Returns:
        The content with the user's authoritative feedback appended when
        present, otherwise the content unchanged.
    """
    feedback = state.agent_feedback.get(node)
    if feedback:
        content += (
            "\n\nAdditional context / corrections from the user "
            "(treat as authoritative, override earlier assumptions):\n"
            f"{feedback}"
        )
    return content


async def scout_node(state: VCState) -> dict:
    """Parse the raw company description into a structured ``StartupInfo``.

    This is a lightweight parser, not an analytical agent: it extracts fields
    and does no scoring or ML.

    Args:
        state: The current graph state (reads ``raw_input`` and the LLM config).

    Returns:
        A state update with the parsed ``startup_info``.
    """
    writer = get_stream_writer()
    writer({"type": "node_start", "node": "scout"})

    model = get_chat_model(state.provider, state.model, state.api_key).with_structured_output(StartupInfo)
    messages = [
        SystemMessage(content=SCOUT_SYSTEM_PROMPT),
        HumanMessage(content=state.raw_input),
    ]
    startup_info = cast(StartupInfo, await model.ainvoke(messages))
    logger.info("vc_scout_parsed", provider=state.provider, model=state.model, name=getattr(startup_info, "name", None))
    writer({"type": "node_complete", "node": "scout", "data": startup_info.model_dump() if startup_info else None})
    return {"startup_info": startup_info}


async def market_node(state: VCState) -> dict:
    """Run the market analyst over the parsed startup profile.

    Args:
        state: The current graph state (reads ``startup_info`` and LLM config).

    Returns:
        A state update with the ``market_analysis``.
    """
    writer = get_stream_writer()
    writer({"type": "node_start", "node": "market"})

    if state.startup_info is None:
        raise ValueError("market_node requires startup_info to be parsed first")

    model = get_chat_model(state.provider, state.model, state.api_key).with_structured_output(MarketAnalysis)
    human_content = _apply_feedback(
        f"Startup information:\n{_render_startup_info(state.startup_info)}", state, "market"
    )
    messages = [
        SystemMessage(content=MARKET_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]
    analysis = cast(MarketAnalysis, await model.ainvoke(messages))
    logger.info("vc_market_analyzed", score=getattr(analysis, "market_viability_score", None))
    writer({"type": "node_complete", "node": "market", "data": analysis.model_dump() if analysis else None})
    return {"market_analysis": analysis}


async def product_node(state: VCState) -> dict:
    """Run the product analyst over the parsed startup profile.

    Args:
        state: The current graph state (reads ``startup_info`` and LLM config).

    Returns:
        A state update with the ``product_analysis``.
    """
    writer = get_stream_writer()
    writer({"type": "node_start", "node": "product"})

    if state.startup_info is None:
        raise ValueError("product_node requires startup_info to be parsed first")

    model = get_chat_model(state.provider, state.model, state.api_key).with_structured_output(ProductAnalysis)
    human_content = _apply_feedback(
        f"Startup information:\n{_render_startup_info(state.startup_info)}", state, "product"
    )
    messages = [
        SystemMessage(content=PRODUCT_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]
    analysis = cast(ProductAnalysis, await model.ainvoke(messages))
    logger.info("vc_product_analyzed", score=getattr(analysis, "potential_score", None))
    writer({"type": "node_complete", "node": "product", "data": analysis.model_dump() if analysis else None})
    return {"product_analysis": analysis}


async def founder_node(state: VCState) -> dict:
    """Run the founder analyst (with L1-L5 segmentation) over the profile.

    Args:
        state: The current graph state (reads ``startup_info`` and LLM config).

    Returns:
        A state update with the ``founder_analysis``.
    """
    writer = get_stream_writer()
    writer({"type": "node_start", "node": "founder"})

    if state.startup_info is None:
        raise ValueError("founder_node requires startup_info to be parsed first")

    model = get_chat_model(state.provider, state.model, state.api_key).with_structured_output(FounderAnalysis)
    human_content = _apply_feedback(
        f"Startup information:\n{_render_startup_info(state.startup_info)}", state, "founder"
    )
    messages = [
        SystemMessage(content=FOUNDER_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]
    analysis = cast(FounderAnalysis, await model.ainvoke(messages))
    logger.info(
        "vc_founder_analyzed",
        competency=getattr(analysis, "competency_score", None),
        segmentation=getattr(analysis, "segmentation", None),
    )
    writer({"type": "node_complete", "node": "founder", "data": analysis.model_dump() if analysis else None})
    return {"founder_analysis": analysis}


async def chief_node(state: VCState) -> dict:
    """Integrate the three specialist analyses into a final recommendation.

    Args:
        state: The current graph state (reads the three analyses and LLM config).

    Returns:
        A state update with the integrated ``final`` recommendation.
    """
    writer = get_stream_writer()
    writer({"type": "node_start", "node": "chief"})

    if state.market_analysis is None or state.product_analysis is None or state.founder_analysis is None:
        raise ValueError("chief_node requires all three specialist analyses to be present")

    model = get_chat_model(state.provider, state.model, state.api_key).with_structured_output(IntegratedAnalysis)

    # Long-term memory recall: surface similar past evaluations so the chief can
    # weigh prior deals. Fully guarded inside vc_memory — an unavailable/empty
    # memory just yields "" and changes nothing.
    recall_query = state.raw_input
    if state.startup_info is not None:
        recall_query = f"{state.startup_info.name}. {state.startup_info.description}"
    past_evaluations = await vc_memory.recall_similar(query=recall_query)

    summary = (
        f"Market analysis (viability score {state.market_analysis.market_viability_score}/10):\n"
        f"{state.market_analysis.analysis}\n\n"
        f"Product analysis (potential score {state.product_analysis.potential_score}/10):\n"
        f"{state.product_analysis.analysis}\n\n"
        f"Founder analysis (competency {state.founder_analysis.competency_score}/10, "
        f"segmentation L{state.founder_analysis.segmentation}):\n"
        f"{state.founder_analysis.analysis}"
    )
    if past_evaluations:
        summary += (
            "\n\nRelevant past evaluations from your firm's memory (for context — "
            "weigh them, do not over-anchor on them):\n"
            f"{past_evaluations}"
        )

    summary = _apply_feedback(summary, state, "chief")

    messages = [
        SystemMessage(content=CHIEF_SYSTEM_PROMPT),
        HumanMessage(content=summary),
    ]
    final = cast(IntegratedAnalysis, await model.ainvoke(messages))
    logger.info(
        "vc_chief_integrated",
        recommendation=getattr(final, "recommendation", None),
        confidence=getattr(final, "confidence", None),
        had_past_context=bool(past_evaluations),
    )
    writer({"type": "node_complete", "node": "chief", "data": final.model_dump() if final else None})
    return {"final": final, "past_evaluations": past_evaluations}
