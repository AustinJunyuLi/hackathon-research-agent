"""Connectors for syncing enrolled research sources."""

from __future__ import annotations

import fnmatch
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .models import EnrolledSource, SourceType
from .parsers import parse_bib_file, parse_md_file, parse_python_file, parse_tex_file

logger = logging.getLogger(__name__)

MIRROR_BASE = Path.home() / ".openclaw" / "workspace" / "research-agent" / "mirrors"

ParsedEntry = dict[str, str]
ManifestPaper = dict[str, str]
Manifest = dict[str, list[ManifestPaper]]


def sync_source(source: EnrolledSource) -> list[ParsedEntry]:
    """Sync a single source and return parsed research entries."""
    if source.type in {SourceType.OVERLEAF, SourceType.GITHUB}:
        return _sync_git_source(source)
    if source.type is SourceType.LOCAL:
        return _sync_local_source(source)

    logger.warning("Unknown source type: %s", source.type)
    return []


def _sync_git_source(source: EnrolledSource) -> list[ParsedEntry]:
    """Clone or pull a git-backed source and return parsed entries."""
    mirror_dir = Path(source.local_mirror) if source.local_mirror else MIRROR_BASE / source.id
    mirror_dir.parent.mkdir(parents=True, exist_ok=True)

    url = source.url or ""
    if not url:
        logger.warning("Git source %s has no URL", source.id)
        return []

    if source.token and "overleaf.com" in url:
        url = url.replace("https://", f"https://{source.token}@", 1)

    try:
        if (mirror_dir / ".git").exists():
            subprocess.run(
                ["git", "-C", str(mirror_dir), "pull", "--ff-only"],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
        else:
            subprocess.run(
                ["git", "clone", "--depth", "1", url, str(mirror_dir)],
                capture_output=True,
                text=True,
                timeout=120,
                check=True,
            )
    except (OSError, subprocess.CalledProcessError) as exc:
        logger.warning("Git sync failed for %s: %s", source.id, _error_text(exc))
        return []

    source.local_mirror = str(mirror_dir)
    source.last_synced = datetime.now(UTC)
    return _scan_directory(mirror_dir, source.include, source.exclude)


def _sync_local_source(source: EnrolledSource) -> list[ParsedEntry]:
    """Scan a local directory for research files."""
    if source.path is None:
        logger.warning("Local source %s has no path", source.id)
        return []

    local_path = Path(source.path)
    if not local_path.exists():
        logger.warning("Local path does not exist: %s", source.path)
        return []

    source.last_synced = datetime.now(UTC)
    return _scan_directory(local_path, source.include, source.exclude)


def _scan_directory(
    root: Path,
    include: list[str] | None,
    exclude: list[str] | None,
) -> list[ParsedEntry]:
    """Scan a directory for matching files and parse them into research entries."""
    include_patterns = include or ["*"]
    exclude_patterns = exclude or []
    entries: list[ParsedEntry] = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        relative = str(file_path.relative_to(root))
        name = file_path.name
        if not _matches_any(name, relative, include_patterns):
            continue
        if _matches_any(name, relative, exclude_patterns):
            continue

        if file_path.suffix.lower() == ".tex":
            parsed = parse_tex_file(file_path)
            if parsed is not None:
                entries.append(parsed)
            continue

        if file_path.suffix.lower() == ".bib":
            for title in parse_bib_file(file_path)[:5]:
                entries.append(
                    {
                        "title": title,
                        "abstract": f"Referenced work from {file_path.name}",
                        "source_file": str(file_path),
                    }
                )
            continue

        if file_path.suffix.lower() == ".md":
            parsed = parse_md_file(file_path)
            if parsed is not None:
                entries.append(parsed)
            continue

        if file_path.suffix.lower() == ".py":
            parsed = parse_python_file(file_path)
            if parsed is not None:
                entries.append(parsed)

    return entries


def build_manifest_from_entries(entries: list[ParsedEntry]) -> Manifest:
    """Convert parsed entries into the `local_manifest.json` shape."""
    papers: list[ManifestPaper] = []
    for index, entry in enumerate(entries):
        papers.append(
            {
                "id": f"enrolled-{index}",
                "title": entry.get("title", "Untitled"),
                "abstract": entry.get("abstract", ""),
            }
        )
    return {"papers": papers}


def _matches_any(name: str, relative: str, patterns: list[str]) -> bool:
    return any(
        fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(relative, pattern)
        for pattern in patterns
    )


def _error_text(exc: OSError | subprocess.CalledProcessError) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        return exc.stderr or str(exc)
    return str(exc)
