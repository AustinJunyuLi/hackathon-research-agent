#!/usr/bin/env python3
"""Entry point for running triage from the OpenClaw skill.

Usage (from skill context):
    python3 scripts/run_triage.py <arxiv-id-or-url> [--format json|markdown] [--output path]

This script bridges the OpenClaw skill interface to the triage_agent package.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the project root to sys.path so triage_agent is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from triage_agent.api.arxiv import extract_arxiv_id
from triage_agent.formatters import render_json, render_markdown
from triage_agent.orchestrator import run_triage


SKILL_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = SKILL_DIR / "memory"
SEEN_FILE = MEMORY_DIR / "seen.json"


def load_seen() -> dict[str, str]:
    """Load the set of previously triaged paper IDs."""
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}


def save_seen(seen: dict[str, str]) -> None:
    """Persist the seen papers dict."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(seen, indent=2))


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: run_triage.py <arxiv-id-or-url> [--format json|markdown]")
        sys.exit(1)

    arxiv_input = sys.argv[1]
    output_format = "markdown"
    output_path = None

    # Simple arg parsing
    args = sys.argv[2:]
    for i, arg in enumerate(args):
        if arg == "--format" and i + 1 < len(args):
            output_format = args[i + 1]
        elif arg == "--output" and i + 1 < len(args):
            output_path = args[i + 1]

    # Extract ID and check if already seen
    try:
        arxiv_id = extract_arxiv_id(arxiv_input)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    seen = load_seen()
    if arxiv_id in seen:
        print(f"Paper {arxiv_id} was already triaged on {seen[arxiv_id]}.")
        print("Re-running triage anyway...")

    # Run triage
    memo = await run_triage(arxiv_input)

    # Mark as seen
    from datetime import datetime, timezone
    seen[arxiv_id] = datetime.now(timezone.utc).isoformat()
    save_seen(seen)

    # Format and output
    if output_format == "json":
        output = render_json(memo)
    else:
        output = render_markdown(memo)

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output)
        print(f"Memo written to: {path}")
    else:
        print(output)


if __name__ == "__main__":
    asyncio.run(main())
