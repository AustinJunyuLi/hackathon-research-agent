"""Tests for the OpenClaw install verification helper."""

from __future__ import annotations

import os
import shlex
import shutil
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

from triage_agent.install_checks import check_openclaw_install

BOOTSTRAP_SKILL_FILES = (
    "run_triage.py",
    "enroll.py",
    "setup_daily_cron.py",
    "format_whatsapp.py",
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _create_executable(path: Path) -> Path:
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def _set_path(monkeypatch, tmp_path: Path, *binaries: str) -> dict[str, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    created = {name: _create_executable(bin_dir / name) for name in binaries}
    monkeypatch.setenv("PATH", str(bin_dir))
    return created


def _create_local_venv_binary(project_root: Path, name: str) -> Path:
    path = project_root / ".venv" / "bin" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return _create_executable(path)


def _install_workspace_skill(
    workspace_root: Path,
    script_names: tuple[str, ...] = ("enroll.py",),
) -> Path:
    skill_dir = workspace_root / "skills" / "research-agent"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: research-agent\n---\n")
    for script_name in script_names:
        (skill_dir / "scripts" / script_name).write_text("print('ok')\n")
    return skill_dir


def _create_fake_bootstrap_venv(repo_root: Path) -> None:
    venv_dir = repo_root / ".venv"
    bin_dir = venv_dir / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "activate").write_text(
        textwrap.dedent(
            f"""\
            VIRTUAL_ENV={shlex.quote(str(venv_dir))}
            export VIRTUAL_ENV
            PATH="$VIRTUAL_ENV/bin:$PATH"
            export PATH
            """
        )
    )
    (bin_dir / "python").write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            if [[ "$#" -ge 2 && "$1" == "-m" && "$2" == "pip" ]]; then
              exit 0
            fi
            exec {shlex.quote(sys.executable)} "$@"
            """
        )
    )
    (bin_dir / "python").chmod((bin_dir / "python").stat().st_mode | stat.S_IEXEC)


def _copy_bootstrap_fixture(repo_root: Path) -> None:
    shutil.copytree(
        PROJECT_ROOT / "skill",
        repo_root / "skill",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    (repo_root / "scripts").mkdir(parents=True)
    shutil.copy2(
        PROJECT_ROOT / "scripts" / "bootstrap_openclaw.sh",
        repo_root / "scripts" / "bootstrap_openclaw.sh",
    )


def test_check_openclaw_install_reports_missing_openclaw(monkeypatch, tmp_path: Path) -> None:
    binaries = _set_path(monkeypatch, tmp_path, "triage")
    workspace_root = tmp_path / "workspace"
    _install_workspace_skill(workspace_root)
    project_root = tmp_path / "project"

    result = check_openclaw_install(
        workspace_root=workspace_root,
        project_root=project_root,
    )

    assert result.ready is False
    assert result.status == "not_ready"
    assert "openclaw" in result.missing
    assert result.binary_paths["openclaw"] is None
    assert result.binary_paths["triage"] == str(binaries["triage"])


def test_check_openclaw_install_reports_missing_triage(monkeypatch, tmp_path: Path) -> None:
    binaries = _set_path(monkeypatch, tmp_path, "openclaw")
    workspace_root = tmp_path / "workspace"
    _install_workspace_skill(workspace_root)
    project_root = tmp_path / "project"

    result = check_openclaw_install(
        workspace_root=workspace_root,
        project_root=project_root,
    )

    assert result.ready is False
    assert result.status == "not_ready"
    assert "triage" in result.missing
    assert result.binary_paths["openclaw"] == str(binaries["openclaw"])
    assert result.binary_paths["triage"] is None


def test_check_openclaw_install_accepts_repo_local_triage_binary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    binaries = _set_path(monkeypatch, tmp_path, "openclaw")
    project_root = tmp_path / "project"
    local_triage = _create_local_venv_binary(project_root, "triage")
    workspace_root = tmp_path / "workspace"
    _install_workspace_skill(workspace_root, script_names=BOOTSTRAP_SKILL_FILES)

    result = check_openclaw_install(
        workspace_root=workspace_root,
        project_root=project_root,
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.binary_paths["openclaw"] == str(binaries["openclaw"])
    assert result.binary_paths["triage"] == str(local_triage)


def test_check_openclaw_install_reports_missing_workspace_skill_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _set_path(monkeypatch, tmp_path, "openclaw", "triage")
    workspace_root = tmp_path / "workspace"
    project_root = tmp_path / "project"

    result = check_openclaw_install(
        workspace_root=workspace_root,
        project_root=project_root,
    )

    assert result.ready is False
    assert result.status == "not_ready"
    assert "workspace_skill_dir" in result.missing
    assert result.skill_dir == str(workspace_root / "skills" / "research-agent")


def test_check_openclaw_install_reports_missing_bootstrap_workspace_scripts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _set_path(monkeypatch, tmp_path, "openclaw", "triage")
    workspace_root = tmp_path / "workspace"
    _install_workspace_skill(workspace_root, script_names=("enroll.py",))
    project_root = tmp_path / "project"

    result = check_openclaw_install(
        workspace_root=workspace_root,
        project_root=project_root,
    )

    assert result.ready is False
    assert result.status == "not_ready"
    assert "run_triage.py" in result.missing
    assert "setup_daily_cron.py" in result.missing
    assert "format_whatsapp.py" in result.missing


def test_check_openclaw_install_reports_missing_enroll_script(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _set_path(monkeypatch, tmp_path, "openclaw", "triage")
    workspace_root = tmp_path / "workspace"
    project_root = tmp_path / "project"
    skill_dir = _install_workspace_skill(
        workspace_root,
        script_names=tuple(
            script_name
            for script_name in BOOTSTRAP_SKILL_FILES
            if script_name != "enroll.py"
        ),
    )

    result = check_openclaw_install(
        workspace_root=workspace_root,
        project_root=project_root,
    )

    assert result.ready is False
    assert result.status == "not_ready"
    assert "enroll.py" in result.missing
    assert result.enroll_script == str(skill_dir / "scripts" / "enroll.py")


def test_check_openclaw_install_returns_ready_payload(monkeypatch, tmp_path: Path) -> None:
    binaries = _set_path(monkeypatch, tmp_path, "openclaw", "triage")
    workspace_root = tmp_path / "workspace"
    project_root = tmp_path / "project"
    skill_dir = _install_workspace_skill(workspace_root, script_names=BOOTSTRAP_SKILL_FILES)

    payload = check_openclaw_install(
        workspace_root=workspace_root,
        project_root=project_root,
    ).model_dump()

    assert payload["status"] == "ready"
    assert payload["ready"] is True
    assert payload["missing"] == []
    assert payload["skill_dir"] == str(skill_dir)
    assert payload["enroll_script"] == str(skill_dir / "scripts" / "enroll.py")
    assert payload["binary_paths"] == {
        "openclaw": str(binaries["openclaw"]),
        "triage": str(binaries["triage"]),
    }


def test_bootstrap_openclaw_syncs_required_skill_files_and_prints_next_commands(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _copy_bootstrap_fixture(repo_root)
    _create_fake_bootstrap_venv(repo_root)
    _create_local_venv_binary(repo_root, "triage")

    workspace_root = tmp_path / "workspace"
    skill_dir = workspace_root / "skills" / "research-agent"
    memory_dir = skill_dir / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "profile.json").write_text('{"preserve":"profile"}\n')
    (memory_dir / "seen.json").write_text('{"preserve":"seen"}\n')

    openclaw_bin_dir = tmp_path / "bin"
    openclaw_bin_dir.mkdir()
    _create_executable(openclaw_bin_dir / "openclaw")

    env = os.environ.copy()
    env["HOME"] = str(tmp_path / "home")
    env["OPENCLAW_WORKSPACE_ROOT"] = str(workspace_root)
    env["PATH"] = f"{openclaw_bin_dir}{os.pathsep}{env['PATH']}"

    completed = subprocess.run(
        ["bash", "scripts/bootstrap_openclaw.sh"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout.splitlines() == [
        "python scripts/verify_openclaw_install.py",
        "openclaw skills info research-agent",
        "openclaw agent --agent main --message '/research-agent 2106.09685'",
    ]

    for script_name in BOOTSTRAP_SKILL_FILES:
        assert (skill_dir / "scripts" / script_name).is_file()

    assert (memory_dir / "profile.json").read_text() == '{"preserve":"profile"}\n'
    assert (memory_dir / "seen.json").read_text() == '{"preserve":"seen"}\n'

    monkeypatch.setenv("PATH", str(openclaw_bin_dir))
    result = check_openclaw_install(
        workspace_root=workspace_root,
        project_root=repo_root,
    )

    assert result.ready is True


def test_bootstrap_openclaw_skips_samefile_entries(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _copy_bootstrap_fixture(repo_root)
    _create_fake_bootstrap_venv(repo_root)

    workspace_root = tmp_path / "workspace"
    skill_dir = workspace_root / "skills" / "research-agent"
    samefile_target = skill_dir / "memory" / "sources.json"
    samefile_target.parent.mkdir(parents=True, exist_ok=True)
    os.link(repo_root / "skill" / "memory" / "sources.json", samefile_target)

    openclaw_bin_dir = tmp_path / "bin"
    openclaw_bin_dir.mkdir()
    _create_executable(openclaw_bin_dir / "openclaw")

    env = os.environ.copy()
    env["OPENCLAW_WORKSPACE_ROOT"] = str(workspace_root)
    env["PATH"] = f"{openclaw_bin_dir}{os.pathsep}{env['PATH']}"

    completed = subprocess.run(
        ["bash", "scripts/bootstrap_openclaw.sh"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "python scripts/verify_openclaw_install.py" in completed.stdout
    assert samefile_target.samefile(repo_root / "skill" / "memory" / "sources.json")
