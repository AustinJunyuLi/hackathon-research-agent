"""CLI entry point for the Triage Memo Agent."""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from triage_agent.formatters import render_json, render_markdown
from triage_agent.orchestrator import run_triage

console = Console()


def main() -> None:
    """Main CLI entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="triage",
        description="Generate a Triage Memo for an arXiv paper",
    )
    parser.add_argument(
        "paper",
        help="arXiv paper URL or ID (e.g. 2301.07041 or https://arxiv.org/abs/2301.07041)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Write output to file instead of stdout",
    )

    args = parser.parse_args()

    try:
        memo = asyncio.run(run_triage(args.paper))
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        sys.exit(1)

    # Format output
    if args.format == "json":
        output = render_json(memo)
    else:
        output = render_markdown(memo)

    # Write or display
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
        console.print(f"[green]Memo written to:[/green] {path}")
    else:
        if args.format == "markdown":
            console.print(Markdown(output))
        else:
            console.print(output)


if __name__ == "__main__":
    main()
