"""Tests for the judge-safe OpenClaw smoke script."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "smoke_openclaw_install.sh"


def _write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_smoke_script_runs_verifier_triage_and_enrollment(tmp_path: Path) -> None:
    python_log = tmp_path / "python.log"
    openclaw_log = tmp_path / "openclaw.log"
    fake_python = tmp_path / "bin" / "python"
    fake_openclaw = tmp_path / "bin" / "openclaw"

    _write_executable(
        fake_python,
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "${SMOKE_PYTHON_LOG}"

if [[ "$1" == "scripts/verify_openclaw_install.py" ]]; then
  printf 'PASS openclaw install ready\\n'
  exit 0
fi

if [[ "$1" == "skill/scripts/enroll.py" && "$2" == "enroll" ]]; then
  test -d "$6"
  printf '{"enrolled":"local-smoke"}\\n'
  exit 0
fi

if [[ "$1" == "skill/scripts/enroll.py" && "$2" == "sources" ]]; then
  printf '[{"label":"Smoke Drafts"}]\\n'
  exit 0
fi

if [[ "$1" == "skill/scripts/enroll.py" && "$2" == "sync" ]]; then
  mkdir -p "$(dirname "${LOCAL_MANIFEST_PATH}")"
  cat > "${LOCAL_MANIFEST_PATH}" <<'JSON'
{"papers":[{"id":"smoke-0","title":"Smoke Test Draft","abstract":"Synthetic entry"}]}
JSON
  printf 'Synced. Local manifest now has 1 papers.\\n'
  exit 0
fi

printf 'unexpected python command: %s\\n' "$*" >&2
exit 1
""",
    )
    _write_executable(
        fake_openclaw,
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "${SMOKE_OPENCLAW_LOG}"

if [[ "$1" == "skills" && "$2" == "info" && "$3" == "research-agent" ]]; then
  printf 'Ready\\n'
  exit 0
fi

printf 'unexpected openclaw command: %s\\n' "$*" >&2
exit 1
""",
    )
    env = os.environ.copy()
    env["PYTHON_BIN"] = str(fake_python)
    env["OPENCLAW_BIN"] = str(fake_openclaw)
    env["SMOKE_PYTHON_LOG"] = str(python_log)
    env["SMOKE_OPENCLAW_LOG"] = str(openclaw_log)
    env["TMPDIR"] = str(tmp_path)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "[1/4] Verifying OpenClaw install" in result.stdout
    assert "[3/4] Enrolling temporary local source" in result.stdout
    assert "[4/4] Syncing enrolled sources" in result.stdout
    assert "PASS openclaw smoke test complete" in result.stdout

    python_commands = python_log.read_text(encoding="utf-8").splitlines()
    assert python_commands[0] == "scripts/verify_openclaw_install.py"
    assert python_commands[1].startswith(
        "skill/scripts/enroll.py enroll local Smoke Drafts --path "
    )
    assert python_commands[2] == "skill/scripts/enroll.py sources"
    assert python_commands[3] == "skill/scripts/enroll.py sync"

    openclaw_commands = openclaw_log.read_text(encoding="utf-8").splitlines()
    assert openclaw_commands == ["skills info research-agent"]

    assert list(tmp_path.glob("research-agent-smoke.*")) == []


def test_smoke_script_requires_bootstrap_when_no_python_override(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    target_script = repo_root / "scripts" / "smoke_openclaw_install.sh"
    _write_executable(target_script, SCRIPT_PATH.read_text(encoding="utf-8"))

    result = subprocess.run(
        ["bash", str(target_script)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Run bash scripts/bootstrap_openclaw.sh first." in result.stderr
