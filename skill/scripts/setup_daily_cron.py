#!/usr/bin/env python3
"""Install/update a daily OpenClaw cron job for research-agent digests.

This helper creates a cron job that asks the OpenClaw agent to run batch triage
and announce a compact morning digest.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def _build_message(project_root: Path, batch_file: str, output_dir: str) -> str:
    return (
        "Automated daily research digest task.\n"
        "Run exactly these steps:\n"
        f"1) Execute shell command: cd {project_root} && "
        "if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi && "
        f"triage --batch-file {batch_file} --format json --output-dir {output_dir}\n"
        f"2) Read {output_dir}/batch_summary.json\n"
        "3) Reply with a concise digest (max 8 bullets), prioritizing high relevance, then medium.\n"
        "Each bullet: arxiv_id | short title | read_decision | relevance | novelty_score | local_relevance.\n"
        "If no valid/new items, explicitly say so."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Install daily OpenClaw cron for research-agent")
    parser.add_argument("--name", default="research-agent-daily")
    parser.add_argument("--cron", default="0 8 * * *", help='Cron expression (default: "0 8 * * *")')
    parser.add_argument("--tz", default="Europe/London", help="IANA timezone")
    parser.add_argument("--agent", default="main")
    parser.add_argument("--channel", default="last", help="Delivery channel for announce")
    parser.add_argument("--to", default="", help="Optional explicit destination")
    parser.add_argument(
        "--project-root",
        default="",
        help="Project root containing ids.txt/.venv (default: auto from script path)",
    )
    parser.add_argument(
        "--batch-file",
        default="ids.txt",
        help="Batch input file relative to project root (default: ids.txt)",
    )
    parser.add_argument(
        "--output-dir",
        default="out/daily_latest",
        help="Batch output directory relative to project root",
    )
    args = parser.parse_args()

    detected_root = Path(__file__).resolve().parents[2]
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else detected_root

    message = _build_message(project_root, args.batch_file, args.output_dir)

    cmd = [
        "openclaw",
        "cron",
        "add",
        "--name",
        args.name,
        "--description",
        "Daily morning triage digest for research-agent",
        "--agent",
        args.agent,
        "--cron",
        args.cron,
        "--tz",
        args.tz,
        "--session",
        "isolated",
        "--announce",
        "--channel",
        args.channel,
        "--message",
        message,
        "--json",
    ]
    if args.to:
        cmd.extend(["--to", args.to])

    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(completed.stdout)
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
