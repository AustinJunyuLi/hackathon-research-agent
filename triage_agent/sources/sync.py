"""Sync all enrolled sources and rebuild the local manifest."""

from __future__ import annotations

import logging
from pathlib import Path

from triage_agent.local_kb import write_local_manifest

from .connectors import build_manifest_from_entries, sync_source
from .registry import load_registry, save_registry

logger = logging.getLogger(__name__)

Manifest = dict[str, list[dict[str, str]]]


def sync_all_sources(
    registry_path: Path | None = None,
    manifest_output: Path | None = None,
) -> Manifest:
    """Sync all enrolled sources and rebuild `local_manifest.json`."""
    registry = load_registry(registry_path)

    all_entries: list[dict[str, str]] = []
    for source in registry.sources:
        logger.info("Syncing source: %s (%s)", source.label, source.type.value)
        try:
            entries = sync_source(source)
        except Exception:
            logger.exception("Failed to sync source %s", source.id)
            continue

        logger.info("Found %d entries from %s", len(entries), source.label)
        all_entries.extend(entries)

    save_registry(registry, registry_path)

    manifest = (
        build_manifest_from_entries(all_entries)
        if all_entries
        else {"papers": []}
    )
    output_path = write_local_manifest(manifest, manifest_output)
    logger.info("Wrote %d papers to %s", len(manifest["papers"]), output_path)
    return manifest
