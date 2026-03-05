"""Tests for source enrollment registry models and CRUD helpers."""

from __future__ import annotations

from triage_agent.sources.models import SourceRegistry, SourceType
from triage_agent.sources.registry import (
    enroll_source,
    list_sources,
    load_registry,
    remove_source,
    save_registry,
)


def test_enroll_and_list_source() -> None:
    registry = SourceRegistry()

    source = enroll_source(
        registry,
        SourceType.LOCAL,
        "My drafts",
        path="/home/user/drafts",
    )

    assert source.type is SourceType.LOCAL
    assert len(registry.sources) == 1
    listing = list_sources(registry)
    assert listing[0]["label"] == "My drafts"
    assert listing[0]["path"] == "/home/user/drafts"


def test_enroll_duplicate_source_returns_existing() -> None:
    registry = SourceRegistry()

    first = enroll_source(
        registry,
        SourceType.GITHUB,
        "Repo",
        url="https://github.com/u/r",
    )
    second = enroll_source(
        registry,
        SourceType.GITHUB,
        "Repo",
        url="https://github.com/u/r",
    )

    assert first.id == second.id
    assert len(registry.sources) == 1


def test_remove_source() -> None:
    registry = SourceRegistry()
    source = enroll_source(registry, SourceType.LOCAL, "Test", path="/tmp/test")

    assert remove_source(registry, source.id) is True
    assert registry.sources == []
    assert remove_source(registry, "missing") is False


def test_save_and_load_registry(tmp_path) -> None:
    registry_path = tmp_path / "sources.json"
    registry = SourceRegistry()
    enroll_source(
        registry,
        SourceType.OVERLEAF,
        "Paper",
        url="https://git.overleaf.com/abc",
    )

    save_registry(registry, registry_path)
    loaded = load_registry(registry_path)

    assert len(loaded.sources) == 1
    assert loaded.sources[0].type is SourceType.OVERLEAF


def test_load_missing_registry_returns_empty(tmp_path) -> None:
    loaded = load_registry(tmp_path / "missing.json")

    assert loaded.sources == []
