#!/usr/bin/env python3
"""Format triage batch summaries for compact chat delivery."""

from __future__ import annotations

import json
import sys
import textwrap
from datetime import date
from pathlib import Path
from typing import Any


def _load_items(summary_path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(summary_path).read_text())
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _shorten(text: str, width: int = 80) -> str:
    compact = " ".join(text.split())
    return textwrap.shorten(compact, width=width, placeholder="…")


def format_whatsapp_digest(summary_path: str | Path) -> str:
    """Read batch_summary.json and produce a compact WhatsApp digest."""
    items = _load_items(summary_path)
    grouped = {
        "READ IN FULL": [item for item in items if item.get("read_decision") == "read in full"],
        "SKIM": [item for item in items if item.get("read_decision") == "skim"],
        "SKIP": [
            item
            for item in items
            if item.get("read_decision") in {"skip", "monitor authors", "monitor"}
        ],
    }

    lines = [f"Research Digest -- {date.today().isoformat()}", ""]

    for heading, papers in grouped.items():
        if not papers:
            continue
        lines.append(heading)
        for paper in papers:
            title = paper.get("title", "Untitled paper")
            arxiv_id = paper.get("arxiv_id", "unknown-id")
            if heading == "SKIP":
                reason = paper.get("relevance", "low")
                lines.append(f"  {title} -- {reason}")
                continue

            lines.append(f"  {title} ({arxiv_id})")
            novelty = paper.get("novelty_score")
            local_relevance = paper.get("local_relevance")
            score_parts = []
            if isinstance(novelty, int | float):
                score_parts.append(f"novelty {novelty:.2f}")
            if isinstance(local_relevance, int | float):
                score_parts.append(f"local {local_relevance:.2f}")
            if score_parts:
                lines.append(f"  {' | '.join(score_parts)}")

            summary = paper.get("summary")
            if isinstance(summary, str) and summary.strip():
                lines.append(f"  {_shorten(summary)}")
        lines.append("")

    lines.append("Reply with a paper ID for the full memo.")
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: format_whatsapp.py <batch_summary.json>")
        raise SystemExit(1)
    print(format_whatsapp_digest(sys.argv[1]))


if __name__ == "__main__":
    main()
