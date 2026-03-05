"""Manage enrolled research sources."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

from .models import EnrolledSource, SourceRegistry, SourceType

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_PATH = Path("skill/memory/sources.json")


def _resolve_registry_path() -> Path:
    env_path = os.environ.get("SOURCE_REGISTRY_PATH")
    if env_path:
        return Path(env_path)

    search_roots = [Path.cwd(), Path(__file__).resolve().parents[2]]
    for root in search_roots:
        candidate = root / "skill" / "memory" / "sources.json"
        if candidate.parent.exists():
            return candidate

    return DEFAULT_REGISTRY_PATH


def load_registry(path: Path | None = None) -> SourceRegistry:
    registry_path = path or _resolve_registry_path()
    if not registry_path.exists():
        return SourceRegistry()

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        return SourceRegistry.model_validate(data)
    except (OSError, json.JSONDecodeError, ValueError):
        logger.warning("Failed to load source registry from %s", registry_path)
        return SourceRegistry()


def save_registry(registry: SourceRegistry, path: Path | None = None) -> None:
    registry_path = path or _resolve_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        registry.model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )


def enroll_source(
    registry: SourceRegistry,
    source_type: SourceType,
    label: str,
    url: str | None = None,
    path: str | None = None,
    token: str | None = None,
    include: list[str] | None = None,
) -> EnrolledSource:
    raw_id = url or path or label
    source_hash = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:8]
    source_id = f"{source_type.value}-{source_hash}"

    for existing in registry.sources:
        if existing.id == source_id:
            logger.info("Source %s already enrolled", source_id)
            return existing

    source = EnrolledSource(
        id=source_id,
        type=source_type,
        label=label,
        url=url,
        path=path,
        token=token,
        include=include if include is not None else ["*.tex", "*.bib", "*.md"],
    )
    registry.sources.append(source)
    return source


def remove_source(registry: SourceRegistry, source_id: str) -> bool:
    before = len(registry.sources)
    registry.sources = [source for source in registry.sources if source.id != source_id]
    return len(registry.sources) < before


def list_sources(registry: SourceRegistry) -> list[dict[str, str | None]]:
    return [
        {
            "id": source.id,
            "type": source.type.value,
            "label": source.label,
            "url": source.url,
            "path": source.path,
            "last_synced": (
                source.last_synced.isoformat() if source.last_synced is not None else None
            ),
        }
        for source in registry.sources
    ]
