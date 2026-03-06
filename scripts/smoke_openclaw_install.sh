#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
DEFAULT_PYTHON_BIN="${VENV_DIR}/bin/python"
PYTHON_BIN="${PYTHON_BIN:-${DEFAULT_PYTHON_BIN}}"
OPENCLAW_BIN="${OPENCLAW_BIN:-$(command -v openclaw || true)}"
SMOKE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/research-agent-smoke.XXXXXX")"
SOURCE_DIR="${SMOKE_ROOT}/source"
SOURCE_FILE="${SOURCE_DIR}/smoke_notes.md"

cleanup() {
  rm -rf "${SMOKE_ROOT}"
}

trap cleanup EXIT

if [[ "${PYTHON_BIN}" == "${DEFAULT_PYTHON_BIN}" && ! -x "${PYTHON_BIN}" ]]; then
  printf 'Missing bootstrap environment at %s. Run bash scripts/bootstrap_openclaw.sh first.\n' "${VENV_DIR}" >&2
  exit 1
fi

if [[ -z "${OPENCLAW_BIN}" ]]; then
  printf 'OpenClaw CLI not found. Run python scripts/verify_openclaw_install.py for details.\n' >&2
  exit 1
fi

cd "${REPO_ROOT}"

mkdir -p "${SOURCE_DIR}"
cat > "${SOURCE_FILE}" <<'EOF'
# Smoke Test Draft

This temporary note exists only to verify local-source enrollment and manifest sync.
EOF

export SOURCE_REGISTRY_PATH="${SMOKE_ROOT}/sources.json"
export LOCAL_MANIFEST_PATH="${SMOKE_ROOT}/local_manifest.json"

printf '[1/4] Verifying OpenClaw install\n'
"${PYTHON_BIN}" scripts/verify_openclaw_install.py

printf '[2/4] Checking skill readiness\n'
skill_info="$("${OPENCLAW_BIN}" skills info research-agent)"
printf '%s\n' "${skill_info}"
if [[ "${skill_info}" != *"Ready"* ]]; then
  printf 'Skill is not ready.\n' >&2
  exit 1
fi

printf '[3/4] Enrolling temporary local source\n'
"${PYTHON_BIN}" skill/scripts/enroll.py enroll local "Smoke Drafts" --path "${SOURCE_DIR}" >/dev/null
"${PYTHON_BIN}" skill/scripts/enroll.py sources >/dev/null

printf '[4/4] Syncing enrolled sources\n'
"${PYTHON_BIN}" skill/scripts/enroll.py sync >/dev/null

if [[ ! -s "${LOCAL_MANIFEST_PATH}" ]]; then
  printf 'Smoke sync did not create a local manifest.\n' >&2
  exit 1
fi

if ! grep -q '"papers"' "${LOCAL_MANIFEST_PATH}"; then
  printf 'Smoke sync created an invalid local manifest.\n' >&2
  exit 1
fi

printf 'PASS openclaw smoke test complete\n'
