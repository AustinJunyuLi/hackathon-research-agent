"""Install verification helpers for the OpenClaw-first workflow."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_SKILL_NAME = "research-agent"
DEFAULT_WORKSPACE_ROOT = Path.home() / ".openclaw" / "workspace"
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SKILL_SCRIPTS = (
    "run_triage.py",
    "enroll.py",
    "setup_daily_cron.py",
    "format_whatsapp.py",
)


class InstallCheck(BaseModel):
    """One install readiness check."""

    name: str
    ok: bool
    detail: str
    path: str | None = None


class InstallStatus(BaseModel):
    """Machine-readable OpenClaw install readiness payload."""

    status: str
    ready: bool
    workspace_root: str
    skill_dir: str
    enroll_script: str
    binary_paths: dict[str, str | None]
    missing: list[str] = Field(default_factory=list)
    checks: list[InstallCheck] = Field(default_factory=list)


def _binary_check(name: str, fallback_path: Path | None = None) -> InstallCheck:
    binary_path = shutil.which(name)
    location_label = "PATH"
    if binary_path is None and fallback_path and fallback_path.is_file():
        binary_path = str(fallback_path)
        location_label = "local venv"
    if binary_path:
        return InstallCheck(
            name=name,
            ok=True,
            detail=f"Found via {location_label} at {binary_path}.",
            path=binary_path,
        )

    return InstallCheck(
        name=name,
        ok=False,
        detail=f"Missing `{name}` on PATH.",
    )


def _path_check(name: str, path: Path, kind: str) -> InstallCheck:
    exists = path.is_dir() if kind == "dir" else path.is_file()
    descriptor = "directory" if kind == "dir" else "file"
    if exists:
        return InstallCheck(
            name=name,
            ok=True,
            detail=f"Found expected {descriptor}.",
            path=str(path),
        )

    return InstallCheck(
        name=name,
        ok=False,
        detail=f"Missing expected {descriptor}.",
        path=str(path),
    )


def _local_venv_binary(project_root: Path, name: str) -> Path:
    bin_dir = "Scripts" if os.name == "nt" else "bin"
    return project_root / ".venv" / bin_dir / name


def check_openclaw_install(
    workspace_root: Path | str | None = None,
    skill_name: str = DEFAULT_SKILL_NAME,
    project_root: Path | str | None = None,
) -> InstallStatus:
    """Check whether the OpenClaw-first install is ready to use."""

    resolved_workspace_root = Path(workspace_root) if workspace_root else DEFAULT_WORKSPACE_ROOT
    resolved_project_root = Path(project_root) if project_root else DEFAULT_PROJECT_ROOT
    skill_dir = resolved_workspace_root / "skills" / skill_name
    enroll_script = skill_dir / "scripts" / "enroll.py"
    script_checks = [
        _path_check(script_name, skill_dir / "scripts" / script_name, "file")
        for script_name in REQUIRED_SKILL_SCRIPTS
    ]

    checks = [
        _binary_check("openclaw"),
        _binary_check("triage", fallback_path=_local_venv_binary(resolved_project_root, "triage")),
        _path_check("workspace_skill_dir", skill_dir, "dir"),
        *script_checks,
    ]
    missing = [check.name for check in checks if not check.ok]
    binary_paths = {
        check.name: check.path for check in checks if check.name in {"openclaw", "triage"}
    }

    return InstallStatus(
        status="ready" if not missing else "not_ready",
        ready=not missing,
        workspace_root=str(resolved_workspace_root),
        skill_dir=str(skill_dir),
        enroll_script=str(enroll_script),
        binary_paths=binary_paths,
        missing=missing,
        checks=checks,
    )
