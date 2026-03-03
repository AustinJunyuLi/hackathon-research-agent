"""CLI entry point for the Triage Memo Agent."""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from triage_agent.api.arxiv import extract_arxiv_id
from triage_agent.formatters import render_json, render_markdown
from triage_agent.orchestrator import run_triage

console = Console()


async def run_batch(batch_file: str, output_format: str, output_dir: str | None) -> None:
    """Run triage on a batch of arXiv IDs/URLs listed in a file.

    Args:
        batch_file: Path to a text file with one arXiv ID/URL per line.
        output_format: "markdown" or "json".
        output_dir: Directory to write outputs (defaults to ./batch_output).
    """
    path = Path(batch_file)
    if not path.exists():
        console.print(f"[red]Batch file not found:[/red] {path}")
        return

    lines = path.read_text(encoding="utf-8").splitlines()
    inputs = [line.strip() for line in lines if line.strip()]
    if not inputs:
        console.print(f"[yellow]No arXiv IDs or URLs found in batch file:[/yellow] {path}")
        return

    out_dir = Path(output_dir) if output_dir else Path("./batch_output")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Limit concurrency to avoid overwhelming external APIs.
    semaphore = asyncio.Semaphore(5)

    async def _process_one(arxiv_input: str) -> None:
        async with semaphore:
            try:
                memo = await run_triage(arxiv_input)
            except Exception as e:
                console.print(f"[red]Error processing {arxiv_input}:[/red] {e}")
                return

            if output_format == "json":
                content = render_json(memo)
                ext = "json"
            else:
                content = render_markdown(memo)
                ext = "md"

            try:
                arxiv_id = extract_arxiv_id(arxiv_input)
            except ValueError:
                safe = (
                    arxiv_input.replace("/", "_")
                    .replace(":", "_")
                    .replace(" ", "_")
                )
                arxiv_id = safe

            out_path = out_dir / f"{arxiv_id}.{ext}"
            out_path.write_text(content, encoding="utf-8")
            console.print(f"[green]Memo written for {arxiv_id}:[/green] {out_path}")

    await asyncio.gather(*(_process_one(i) for i in inputs))


def main() -> None:
    """Main CLI entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="triage",
        description="Generate a Triage Memo for an arXiv paper",
    )
    parser.add_argument(
        "paper",
        nargs="?",
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
    parser.add_argument(
        "--batch-file",
        type=str,
        default=None,
        help="Path to a file with arXiv IDs/URLs (one per line) for batch triage",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to write batch outputs (default: ./batch_output)",
    )

    args = parser.parse_args()

    # Batch mode: use --batch-file and ignore single-paper output flag.
    if args.batch_file:
        try:
            asyncio.run(run_batch(args.batch_file, args.format, args.output_dir))
        except Exception as e:
            console.print(f"[red]Unexpected error during batch triage:[/red] {e}")
            sys.exit(1)
        return

    if not args.paper:
        console.print("[red]Error:[/red] No paper ID/URL provided and no --batch-file specified.")
        sys.exit(1)

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
