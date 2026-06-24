"""CLI for the VC startup-evaluation pipeline.

Runs the LangGraph pipeline (scout -> market/product/founder -> chief) on a
company description and pretty-prints the specialist analyses and the chief's
final recommendation with ``rich``.

Examples::

    # Default: Anthropic claude-opus-4-8 on the built-in Turismocity sample
    python run_vc.py

    # Custom description and provider
    python run_vc.py "Acme builds ..." --provider openai --model gpt-4o
    python run_vc.py --provider deepseek --model deepseek-chat

The API key is read from the matching provider env var
(``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` / ``DEEPSEEK_API_KEY``).
"""

import argparse
import asyncio
import os

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.core.langgraph.vc_graph import run_vc_analysis

# SSFF's sample company, used as the default so the CLI runs out of the box.
TURISMOCITY_SAMPLE = (
    "Turismocity is a travel search engine for Latin America that provides price "
    "comparison tools and travel deals. Eugenio Fage, the CTO and co-founder, has a "
    "background in software engineering and extensive experience in developing travel "
    "technology solutions."
)

# Maps each provider to the env var its API key is read from.
PROVIDER_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}

console = Console()


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        The parsed namespace (``description``, ``provider``, ``model``).
    """
    parser = argparse.ArgumentParser(description="Evaluate a startup with the VC AI agent pipeline.")
    parser.add_argument(
        "description",
        nargs="?",
        default=TURISMOCITY_SAMPLE,
        help="The company description to evaluate (defaults to the Turismocity sample).",
    )
    parser.add_argument(
        "--provider",
        default="anthropic",
        choices=["anthropic", "openai", "deepseek"],
        help="LLM provider (default: anthropic).",
    )
    parser.add_argument(
        "--model",
        default="claude-opus-4-8",
        help="Provider-specific model name (default: claude-opus-4-8).",
    )
    return parser.parse_args()


def _render_results(results: dict) -> None:
    """Pretty-print the pipeline results with rich panels and tables.

    Args:
        results: The dict returned by ``run_vc_analysis``.
    """
    startup_info = results["startup_info"]
    market = results["market_analysis"]
    product = results["product_analysis"]
    founder = results["founder_analysis"]
    final = results["final"]

    if startup_info is not None:
        console.print(Panel(f"[bold]{startup_info.name}[/bold]\n{startup_info.description}", title="Startup"))

    scores = Table(title="Specialist Scores", show_header=True, header_style="bold cyan")
    scores.add_column("Dimension")
    scores.add_column("Score", justify="right")
    if market is not None:
        scores.add_row("Market viability", f"{market.market_viability_score}/10")
    if product is not None:
        scores.add_row("Product potential", f"{product.potential_score}/10")
    if founder is not None:
        scores.add_row("Founder competency", f"{founder.competency_score}/10")
        scores.add_row("Founder segmentation", f"L{founder.segmentation}")
    console.print(scores)

    if market is not None:
        console.print(Panel(market.analysis, title=f"Market — {market.market_viability_score}/10", border_style="blue"))
    if product is not None:
        console.print(Panel(product.analysis, title=f"Product — {product.potential_score}/10", border_style="green"))
    if founder is not None:
        console.print(
            Panel(
                founder.analysis,
                title=f"Founder — {founder.competency_score}/10 (L{founder.segmentation})",
                border_style="magenta",
            )
        )

    if final is not None:
        rec_color = {"Invest": "bold green", "Hold": "bold yellow", "Pass": "bold red"}.get(
            final.recommendation, "bold"
        )
        body = (
            f"[{rec_color}]Recommendation: {final.recommendation}[/{rec_color}]  "
            f"(confidence {final.confidence:.0%})\n\n"
            f"{final.overall_assessment}\n\n"
            f"[bold]Strengths:[/bold]\n"
            + "\n".join(f"  • {s}" for s in final.key_strengths)
            + "\n\n[bold]Risks:[/bold]\n"
            + "\n".join(f"  • {r}" for r in final.key_risks)
            + f"\n\n[bold]Rationale:[/bold]\n{final.rationale}"
        )
        console.print(Panel(body, title="Chief Analyst — Final Recommendation", border_style=rec_color))


async def _main_async(args: argparse.Namespace) -> None:
    """Run the pipeline and render the results.

    Args:
        args: Parsed CLI arguments.
    """
    env_var = PROVIDER_ENV_VARS[args.provider]
    api_key = os.getenv(env_var, "")
    if not api_key:
        console.print(f"[bold red]Error:[/bold red] no API key found. Set {env_var} in your environment.")
        return

    with console.status(f"Running VC analysis via {args.provider}/{args.model}…", spinner="dots"):
        results = await run_vc_analysis(
            raw_input=args.description,
            provider=args.provider,
            model=args.model,
            api_key=api_key,
        )
    _render_results(results)


def main() -> None:
    """CLI entry point."""
    args = _parse_args()
    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()
