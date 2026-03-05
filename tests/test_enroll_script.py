"""Tests for the source enrollment CLI script."""

from __future__ import annotations

import json
from importlib import util
from pathlib import Path

from triage_agent.sources.models import EnrolledSource, SourceRegistry, SourceType
from triage_agent.sources.registry import save_registry

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "skill" / "scripts" / "enroll.py"


def _load_module(path: Path, name: str) -> object:
    assert path.exists(), f"Missing script: {path}"
    spec = util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_enroll_script_enrolls_and_lists_sources(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "sources.json"
    module = _load_module(SCRIPT_PATH, "enroll_script")
    monkeypatch.setenv("SOURCE_REGISTRY_PATH", str(registry_path))

    monkeypatch.setattr(
        "sys.argv",
        ["enroll.py", "enroll", "local", "Drafts", "--path", str(tmp_path)],
    )
    module.main()
    enrolled = json.loads(capsys.readouterr().out)

    assert enrolled["type"] == "local"
    assert enrolled["label"] == "Drafts"

    monkeypatch.setattr("sys.argv", ["enroll.py", "sources"])
    module.main()
    listed = json.loads(capsys.readouterr().out)

    assert listed[0]["label"] == "Drafts"
    assert listed[0]["path"] == str(tmp_path)


def test_enroll_script_sync_reports_manifest_count(monkeypatch, capsys) -> None:
    module = _load_module(SCRIPT_PATH, "enroll_script_sync")
    monkeypatch.setattr(
        module,
        "sync_all_sources",
        lambda: {"papers": [{"id": "enrolled-0"}, {"id": "enrolled-1"}]},
    )
    monkeypatch.setattr("sys.argv", ["enroll.py", "sync"])

    module.main()

    assert "2 papers" in capsys.readouterr().out


def test_enroll_script_remove_deletes_source(monkeypatch, capsys, tmp_path: Path) -> None:
    registry_path = tmp_path / "sources.json"
    save_registry(
        SourceRegistry(
            sources=[
                EnrolledSource(
                    id="local-deadbeef",
                    type=SourceType.LOCAL,
                    label="Drafts",
                    path=str(tmp_path),
                )
            ]
        ),
        registry_path,
    )
    module = _load_module(SCRIPT_PATH, "enroll_script_remove")
    monkeypatch.setenv("SOURCE_REGISTRY_PATH", str(registry_path))
    monkeypatch.setattr("sys.argv", ["enroll.py", "remove", "local-deadbeef"])

    module.main()

    assert "Removed source: local-deadbeef" in capsys.readouterr().out
    payload = json.loads(registry_path.read_text())
    assert payload["sources"] == []
