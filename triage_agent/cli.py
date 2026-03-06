"""CLI entry point for the Triage Memo Agent."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from triage_agent.api.arxiv import extract_arxiv_id
from triage_agent.formatters import render_json, render_markdown
from triage_agent.models.memo import TriageMemo
from triage_agent.orchestrator import run_triage

console = Console()


class LocalRelatedSummary(TypedDict):
    local_id: str
    local_title: str
    relationship_type: str


class BatchSummaryRow(TypedDict):
    arxiv_id: str
    title: str
    summary: str
    why_this_matters_to_you: str
    read_decision: str
    novelty_score: float
    relevance: str
    local_relevance: float
    local_related: list[LocalRelatedSummary]


def _bootstrap_default_paths() -> None:
    """Set best-effort defaults so local_kb works outside repo CWD."""
    project_root = Path(__file__).resolve().parent.parent
    local_manifest = project_root / "local_kb" / "local_manifest.json"
    if local_manifest.exists():
        os.environ.setdefault("TRIAGE_PROJECT_ROOT", str(project_root))
        os.environ.setdefault("LOCAL_MANIFEST_PATH", str(local_manifest))


def _build_summary(memos: list[tuple[str, TriageMemo]]) -> list[BatchSummaryRow]:
    """Build summary list for batch: one_line_summary, read_decision, scores, local links."""
    out: list[BatchSummaryRow] = []
    for arxiv_id, memo in memos:
        novelty_score = 0.0
        if memo.novelty_report is not None:
            novelty_score = memo.novelty_report.novelty_score

        local_relevance = 0.0
        local_related: list[LocalRelatedSummary] = []
        if memo.local_overlap is not None:
            local_relevance = memo.local_overlap.overall_relevance
            local_related = [
                {
                    "local_id": m.local_id,
                    "local_title": m.local_title,
                    "relationship_type": m.relationship_type,
                }
                for m in memo.local_overlap.matches
            ]

        out.append(
            {
                "arxiv_id": arxiv_id,
                "title": memo.title,
                "summary": memo.one_line_summary,
                "why_this_matters_to_you": memo.why_this_matters_to_you,
                "read_decision": memo.read_decision,
                "novelty_score": round(novelty_score, 2),
                "relevance": memo.relevance.value,
                "local_relevance": round(local_relevance, 2),
                "local_related": local_related,
            }
        )
    return out


def _render_summary_md(summaries: list[BatchSummaryRow]) -> str:
    """Render summary as Markdown table."""
    lines = [
        "# Batch Triage Summary",
        "",
        "| arXiv ID | Title | Summary | 可不可读 | 创新性 | 相关性 | 本地相关性 | 相关本地文章 |",
        "|----------|-------|---------|----------|--------|--------|------------|--------------|",
    ]
    for s in summaries:
        title_short = (s["title"][:40] + "…") if len(s["title"]) > 40 else s["title"]
        summary_short = (
            (s.get("summary") or "")[:60] + "…"
            if len(s.get("summary") or "") > 60
            else (s.get("summary") or "")
        )
        local_str = ", ".join(
            f"{x['local_id']}" for x in s["local_related"]
        ) or "—"
        lines.append(
            f"| {s['arxiv_id']} | {title_short} | {summary_short} | {s['read_decision']} | "
            f"{s['novelty_score']} | {s['relevance']} | {s['local_relevance']} | {local_str} |"
        )
    lines.append("")
    return "\n".join(lines)


async def run_batch(batch_file: str, output_format: str, output_dir: str | None) -> None:
    """Run triage on a batch: one full output per paper + one summary file.

    - Writes one file per paper (e.g. 1406.2661.json / .md) with full memo.
    - Writes batch_summary.json and batch_summary.md: for each paper only
      read_decision, novelty_score, relevance, local_relevance, local_related.
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

    semaphore = asyncio.Semaphore(5)

    async def _process_one(arxiv_input: str) -> tuple[str | None, TriageMemo | None]:
        async with semaphore:
            try:
                memo = await run_triage(arxiv_input)
                try:
                    aid = extract_arxiv_id(arxiv_input)
                except ValueError:
                    aid = arxiv_input.replace("/", "_").replace(":", "_").replace(" ", "_")
                console.print(f"[green]Done:[/green] {aid}")
                return (aid, memo)
            except Exception as e:
                console.print(f"[red]Error processing {arxiv_input}:[/red] {e}")
                return (None, None)

    results = await asyncio.gather(*(_process_one(i) for i in inputs))
    memos = [(aid, m) for aid, m in results if aid is not None and m is not None]
    if not memos:
        console.print("[yellow]No memos to write.[/yellow]")
        return

    ext = "json" if output_format == "json" else "md"
    for arxiv_id, memo in memos:
        if output_format == "json":
            content = render_json(memo)
        else:
            content = render_markdown(memo)
        out_path = out_dir / f"{arxiv_id}.{ext}"
        out_path.write_text(content, encoding="utf-8")
    console.print(f"[green]Per-paper outputs:[/green] {len(memos)} files in {out_dir}")

    # Summary: read_decision, novelty_score, relevance, local_relevance, local_related
    summaries = _build_summary(memos)
    summary_json_path = out_dir / "batch_summary.json"
    summary_json_path.write_text(
        json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    summary_md_path = out_dir / "batch_summary.md"
    summary_md_path.write_text(_render_summary_md(summaries), encoding="utf-8")
    console.print(f"[green]Summary written:[/green] {summary_json_path}, {summary_md_path}")


def main() -> None:
    """Main CLI entry point."""
    load_dotenv()
    _bootstrap_default_paths()

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
