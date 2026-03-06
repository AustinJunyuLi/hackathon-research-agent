#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
WORKSPACE_ROOT="${OPENCLAW_WORKSPACE_ROOT:-${HOME}/.openclaw/workspace}"
TARGET_SKILL_DIR="${WORKSPACE_ROOT}/skills/research-agent"

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

cd "${REPO_ROOT}"
python -m pip install -e ".[dev]"

export REPO_ROOT TARGET_SKILL_DIR
python - <<'PY'
from __future__ import annotations

import os
import shutil
from pathlib import Path

source_root = Path(os.environ["REPO_ROOT"]) / "skill"
target_root = Path(os.environ["TARGET_SKILL_DIR"])
protected_paths = {
    Path("memory/profile.json"),
    Path("memory/seen.json"),
}

target_root.mkdir(parents=True, exist_ok=True)

for source_path in sorted(source_root.rglob("*")):
    relative_path = source_path.relative_to(source_root)
    if "__pycache__" in relative_path.parts or source_path.suffix == ".pyc":
        continue

    target_path = target_root / relative_path
    if source_path.is_dir():
        target_path.mkdir(parents=True, exist_ok=True)
        continue

    if relative_path in protected_paths and target_path.exists():
        continue

    if target_path.exists() and source_path.samefile(target_path):
        continue

    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
PY

printf 'Synced OpenClaw skill to %s\n' "${TARGET_SKILL_DIR}" >&2
printf '%s\n' \
  'python scripts/verify_openclaw_install.py' \
  'openclaw skills info research-agent' \
  "openclaw agent --agent main --message '/research-agent 2106.09685'"
