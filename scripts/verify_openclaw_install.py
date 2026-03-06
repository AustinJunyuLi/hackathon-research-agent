#!/usr/bin/env python3
"""Print a concise pass/fail report for the OpenClaw-first install path."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-root",
        type=Path,
        help="Override the OpenClaw workspace root (defaults to ~/.openclaw/workspace).",
    )
    return parser


def _load_checker():
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from triage_agent.install_checks import check_openclaw_install

    return check_openclaw_install


def main() -> int:
    args = _build_parser().parse_args()
    check_openclaw_install = _load_checker()
    result = check_openclaw_install(workspace_root=args.workspace_root)

    if result.ready:
        print(
            "PASS openclaw install ready "
            f"(workspace={result.workspace_root}, "
            f"openclaw={result.binary_paths['openclaw']}, "
            f"triage={result.binary_paths['triage']}, "
            f"skill={result.skill_dir})"
        )
        return 0

    print("FAIL openclaw install not ready")
    for check in result.checks:
        if check.ok:
            continue
        location = f" ({check.path})" if check.path else ""
        print(f"- {check.name}: {check.detail}{location}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
