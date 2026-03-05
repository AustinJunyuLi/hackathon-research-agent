"""Tests for source sync connectors."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from triage_agent.sources.connectors import (
    _scan_directory,
    _sync_git_source,
    _sync_local_source,
    build_manifest_from_entries,
)
from triage_agent.sources.models import EnrolledSource, SourceType


def test_scan_directory_parses_tex_files(tmp_path: Path) -> None:
    tex_path = tmp_path / "paper.tex"
    tex_path.write_text(r"\title{Test Paper}\begin{abstract}A test.\end{abstract}")

    entries = _scan_directory(tmp_path, ["*.tex"], [])

    assert len(entries) == 1
    assert entries[0]["title"] == "Test Paper"


def test_scan_directory_respects_exclude_patterns(tmp_path: Path) -> None:
    (tmp_path / "paper.tex").write_text(r"\title{Good}\begin{abstract}Keep.</end{abstract}")
    (tmp_path / "paper.aux").write_text("junk")

    entries = _scan_directory(tmp_path, ["*.tex", "*.aux"], ["*.aux"])

    assert len(entries) == 1
    assert entries[0]["source_file"].endswith("paper.tex")


def test_build_manifest_from_entries() -> None:
    entries = [
        {"title": "Paper A", "abstract": "About A", "source_file": "a"},
        {"title": "Paper B", "abstract": "About B", "source_file": "b"},
    ]

    manifest = build_manifest_from_entries(entries)

    assert len(manifest["papers"]) == 2
    assert manifest["papers"][0]["id"] == "enrolled-0"
    assert manifest["papers"][1]["title"] == "Paper B"


def test_sync_local_source_updates_last_synced(tmp_path: Path) -> None:
    md_path = tmp_path / "notes.md"
    md_path.write_text("# My Notes\n\nSome research context here.\n")
    source = EnrolledSource(
        id="test-local",
        type=SourceType.LOCAL,
        label="Test",
        path=str(tmp_path),
        include=["*.md"],
    )

    entries = _sync_local_source(source)

    assert len(entries) == 1
    assert source.last_synced is not None


def test_sync_git_source_clones_and_scans(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mirror_dir = tmp_path / "mirror"
    source = EnrolledSource(
        id="github-test",
        type=SourceType.GITHUB,
        label="Repo",
        url="https://github.com/u/r.git",
        local_mirror=str(mirror_dir),
        include=["*.md"],
    )
    recorded: dict[str, list[str]] = {}

    def fake_run(
        cmd: list[str],
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        recorded["cmd"] = cmd
        (mirror_dir / ".git").mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("triage_agent.sources.connectors.subprocess.run", fake_run)
    fake_entries = [{"title": "Repo file", "abstract": "", "source_file": str(mirror_dir)}]
    monkeypatch.setattr(
        "triage_agent.sources.connectors._scan_directory",
        lambda root, include, exclude: fake_entries,
    )

    entries = _sync_git_source(source)

    assert recorded["cmd"] == ["git", "clone", "--depth", "1", source.url, str(mirror_dir)]
    assert source.local_mirror == str(mirror_dir)
    assert source.last_synced is not None
    assert entries[0]["title"] == "Repo file"


def test_sync_git_source_overleaf_injects_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mirror_dir = tmp_path / "mirror"
    source = EnrolledSource(
        id="overleaf-test",
        type=SourceType.OVERLEAF,
        label="Paper",
        url="https://git.overleaf.com/project123",
        token="secret-token",
        local_mirror=str(mirror_dir),
    )
    recorded: dict[str, list[str]] = {}

    def fake_run(
        cmd: list[str],
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        recorded["cmd"] = cmd
        (mirror_dir / ".git").mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("triage_agent.sources.connectors.subprocess.run", fake_run)
    monkeypatch.setattr("triage_agent.sources.connectors._scan_directory", lambda *_args: [])

    _sync_git_source(source)

    assert recorded["cmd"] == [
        "git",
        "clone",
        "--depth",
        "1",
        "https://secret-token@git.overleaf.com/project123",
        str(mirror_dir),
    ]


def test_sync_git_source_pulls_existing_repo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mirror_dir = tmp_path / "mirror"
    (mirror_dir / ".git").mkdir(parents=True)
    source = EnrolledSource(
        id="github-test",
        type=SourceType.GITHUB,
        label="Repo",
        url="https://github.com/u/r.git",
        local_mirror=str(mirror_dir),
    )
    recorded: dict[str, list[str]] = {}

    def fake_run(
        cmd: list[str],
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        recorded["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("triage_agent.sources.connectors.subprocess.run", fake_run)
    monkeypatch.setattr("triage_agent.sources.connectors._scan_directory", lambda *_args: [])

    _sync_git_source(source)

    assert recorded["cmd"] == ["git", "-C", str(mirror_dir), "pull", "--ff-only"]
