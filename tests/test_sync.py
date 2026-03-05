"""Tests for source sync orchestration and manifest writing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from triage_agent.local_kb import load_local_manifest, write_local_manifest
from triage_agent.sources.models import EnrolledSource, SourceRegistry, SourceType
from triage_agent.sources.registry import load_registry, save_registry
from triage_agent.sources.sync import sync_all_sources


def test_write_local_manifest_round_trips(tmp_path: Path) -> None:
    manifest_path = tmp_path / "local_manifest.json"
    manifest_data = {
        "papers": [
            {"id": "enrolled-0", "title": "Paper A", "abstract": "About A"},
            {"id": "enrolled-1", "title": "Paper B", "abstract": "About B"},
        ]
    }

    written_path = write_local_manifest(manifest_data, manifest_path)
    loaded = load_local_manifest(written_path)

    assert written_path == manifest_path
    assert loaded is not None
    assert [paper.title for paper in loaded.papers] == ["Paper A", "Paper B"]


def test_sync_all_sources_writes_empty_manifest_for_empty_registry(tmp_path: Path) -> None:
    registry_path = tmp_path / "sources.json"
    manifest_path = tmp_path / "local_manifest.json"
    save_registry(SourceRegistry(), registry_path)

    manifest = sync_all_sources(registry_path, manifest_path)

    assert manifest == {"papers": []}
    assert json.loads(manifest_path.read_text()) == {"papers": []}


def test_sync_all_sources_rebuilds_manifest_and_persists_timestamps(
    monkeypatch, tmp_path: Path
) -> None:
    registry_path = tmp_path / "sources.json"
    manifest_path = tmp_path / "local_manifest.json"
    fixed_time = datetime(2026, 3, 5, 12, 0, tzinfo=UTC)
    registry = SourceRegistry(
        sources=[
            EnrolledSource(
                id="good",
                type=SourceType.LOCAL,
                label="Good source",
                path="/tmp/good",
            ),
            EnrolledSource(
                id="bad",
                type=SourceType.GITHUB,
                label="Bad source",
                url="https://github.com/u/r.git",
            ),
        ]
    )
    save_registry(registry, registry_path)

    def fake_sync_source(source: EnrolledSource) -> list[dict[str, str]]:
        if source.id == "bad":
            raise RuntimeError("boom")
        source.last_synced = fixed_time
        return [
            {
                "title": "Paper A",
                "abstract": "About A",
                "source_file": "/tmp/good/paper.tex",
            },
            {
                "title": "Paper B",
                "abstract": "About B",
                "source_file": "/tmp/good/notes.md",
            },
        ]

    monkeypatch.setattr("triage_agent.sources.sync.sync_source", fake_sync_source)

    manifest = sync_all_sources(registry_path, manifest_path)
    reloaded_registry = load_registry(registry_path)

    assert [paper["title"] for paper in manifest["papers"]] == ["Paper A", "Paper B"]
    assert json.loads(manifest_path.read_text()) == manifest
    assert reloaded_registry.sources[0].last_synced == fixed_time
    assert reloaded_registry.sources[1].last_synced is None
