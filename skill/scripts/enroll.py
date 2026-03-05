#!/usr/bin/env python3
"""Enrollment commands for the research-agent skill."""

from __future__ import annotations

import argparse
import json
import sys
from importlib import import_module
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
for parent in [SCRIPT_DIR.parent.parent, SCRIPT_DIR.parent]:
    if (parent / "triage_agent").is_dir():
        sys.path.insert(0, str(parent))
        break

SourceType = import_module("triage_agent.sources.models").SourceType
registry_module = import_module("triage_agent.sources.registry")
enroll_source = registry_module.enroll_source
list_sources = registry_module.list_sources
load_registry = registry_module.load_registry
remove_source = registry_module.remove_source
save_registry = registry_module.save_registry
sync_all_sources = import_module("triage_agent.sources.sync").sync_all_sources


def cmd_enroll(args: argparse.Namespace) -> None:
    registry = load_registry()
    source = enroll_source(
        registry,
        source_type=SourceType(args.type),
        label=args.label,
        url=args.url,
        path=args.path,
        token=args.token,
    )
    save_registry(registry)
    print(
        json.dumps(
            {"enrolled": source.id, "type": source.type.value, "label": source.label},
            indent=2,
        )
    )


def cmd_remove(args: argparse.Namespace) -> None:
    registry = load_registry()
    removed = remove_source(registry, args.source_id)
    if removed:
        save_registry(registry)
        print(f"Removed source: {args.source_id}")
        return

    print(f"Source not found: {args.source_id}")
    raise SystemExit(1)


def cmd_sources(_: argparse.Namespace) -> None:
    registry = load_registry()
    sources = list_sources(registry)
    if not sources:
        print("No sources enrolled.")
        return

    print(json.dumps(sources, indent=2, default=str))


def cmd_sync(_: argparse.Namespace) -> None:
    manifest = sync_all_sources()
    count = len(manifest.get("papers", []))
    print(f"Synced. Local manifest now has {count} papers.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage enrolled research sources")
    subcommands = parser.add_subparsers(dest="command")

    enroll_parser = subcommands.add_parser("enroll")
    enroll_parser.add_argument("type", choices=[source_type.value for source_type in SourceType])
    enroll_parser.add_argument("label")
    enroll_parser.add_argument("--url")
    enroll_parser.add_argument("--path")
    enroll_parser.add_argument("--token")
    enroll_parser.set_defaults(handler=cmd_enroll)

    remove_parser = subcommands.add_parser("remove")
    remove_parser.add_argument("source_id")
    remove_parser.set_defaults(handler=cmd_remove)

    list_parser = subcommands.add_parser("list")
    list_parser.set_defaults(handler=cmd_sources)

    sources_parser = subcommands.add_parser("sources")
    sources_parser.set_defaults(handler=cmd_sources)

    sync_parser = subcommands.add_parser("sync")
    sync_parser.set_defaults(handler=cmd_sync)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        raise SystemExit(1)

    handler(args)


if __name__ == "__main__":
    main()
