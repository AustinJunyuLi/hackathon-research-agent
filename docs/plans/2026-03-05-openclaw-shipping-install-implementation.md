# OpenClaw Shipping & Install Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the project submission-ready for judges and outside users by shipping one canonical OpenClaw-first install path, one verification path, and one README story that matches the actual product.

**Architecture:** Keep the product OpenClaw-first and GitHub-clone based. Add small repo-local helper scripts for bootstrap and verification, then rewrite the docs so first-run success happens before any private source enrollment. Preserve standalone CLI support, but downgrade it to a secondary path.

**Tech Stack:** Bash for thin bootstrap wrappers, Python 3.11+ for verification logic, editable install via `pip`, OpenClaw CLI, existing `triage` package entrypoint, pytest for helper tests.

---

### Task 1: Add an install verification helper

**Files:**
- Create: `triage_agent/install_checks.py`
- Create: `tests/test_install_checks.py`
- Create: `scripts/verify_openclaw_install.py`

**Step 1: Write the failing tests**

Create `tests/test_install_checks.py` with checks for:
- missing `openclaw`
- missing `triage`
- missing workspace skill directory
- missing `enroll.py`
- success case returning a ready status payload

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_install_checks.py -v`

Expected: FAIL because `triage_agent.install_checks` does not exist yet.

**Step 3: Write minimal implementation**

Implement `triage_agent/install_checks.py` with helpers that:
- inspect required binaries using `shutil.which`
- inspect expected OpenClaw workspace paths
- return a machine-readable result object

Create `scripts/verify_openclaw_install.py` to print a concise pass/fail report and non-zero exit on failure.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_install_checks.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add triage_agent/install_checks.py tests/test_install_checks.py scripts/verify_openclaw_install.py
git commit -m "feat: add OpenClaw install verification helper"
```

---

### Task 2: Add a canonical bootstrap helper

**Files:**
- Create: `scripts/bootstrap_openclaw.sh`
- Modify: `scripts/verify_openclaw_install.py`
- Test: `tests/test_install_checks.py`

**Step 1: Write the failing test case**

Add a test that verifies the verifier recognizes the synced skill layout expected after bootstrap:
- workspace skill exists
- `run_triage.py`
- `enroll.py`
- `setup_daily_cron.py`
- `format_whatsapp.py`

**Step 2: Run the targeted test**

Run: `pytest tests/test_install_checks.py -k workspace -v`

Expected: FAIL until the expected layout contract is encoded.

**Step 3: Write minimal implementation**

Create `scripts/bootstrap_openclaw.sh` that:
- creates `.venv` if missing
- activates `.venv`
- runs `pip install -e ".[dev]"`
- syncs `skill/` into `~/.openclaw/workspace/skills/research-agent`
- prints the exact next commands:
  - `python scripts/verify_openclaw_install.py`
  - `openclaw skills info research-agent`
  - `openclaw agent --agent main --message '/research-agent 2106.09685'`

Keep the script idempotent and non-destructive to `memory/profile.json` and `memory/seen.json`.

**Step 4: Run verification**

Run:

```bash
bash scripts/bootstrap_openclaw.sh
python scripts/verify_openclaw_install.py
```

Expected: verifier reports ready or gives only prerequisite failures external to the repo.

**Step 5: Commit**

```bash
git add scripts/bootstrap_openclaw.sh scripts/verify_openclaw_install.py tests/test_install_checks.py
git commit -m "feat: add OpenClaw bootstrap workflow"
```

---

### Task 3: Rewrite README around one primary path

**Files:**
- Modify: `README.md`
- Create: `docs/openclaw_quickstart.md`

**Step 1: Write the doc acceptance checklist**

Create a short checklist inside `docs/openclaw_quickstart.md` covering:
- prerequisites
- bootstrap
- verification
- first run
- optional source enrollment
- optional daily digest

**Step 2: Review current README before editing**

Run: `sed -n '1,220p' README.md`

Expected: current README still mixes standalone CLI and OpenClaw as peer paths.

**Step 3: Rewrite minimally**

Update `README.md` so the section order is:
1. What it does
2. Prerequisites
3. OpenClaw-first quickstart
4. First successful run
5. Optional source enrollment
6. Optional daily digest
7. Secondary standalone CLI usage
8. Troubleshooting

Create `docs/openclaw_quickstart.md` as the longer judge/outside-user walkthrough.

**Step 4: Verify docs are consistent**

Run:

```bash
rg -n "bootstrap_openclaw|verify_openclaw_install|research-agent 2106.09685|enroll.py" README.md docs/openclaw_quickstart.md
```

Expected: all canonical commands match exactly.

**Step 5: Commit**

```bash
git add README.md docs/openclaw_quickstart.md
git commit -m "docs: make OpenClaw-first quickstart the canonical install path"
```

---

### Task 4: Add a judge-safe smoke test path

**Files:**
- Create: `scripts/smoke_openclaw_install.sh`
- Modify: `docs/dorahacks_submission.md`
- Modify: `docs/openclaw_quickstart.md`

**Step 1: Define smoke test contract**

The smoke test should verify:
- `openclaw skills info research-agent`
- one single-paper run
- one local-source enroll/list/sync path (using a temp local folder, not private credentials)

**Step 2: Write the smoke script**

Create `scripts/smoke_openclaw_install.sh` that:
- runs the verifier
- checks the skill readiness
- creates a small temp markdown source with a heading and paragraph
- enrolls that temp folder as a local source
- runs `python skill/scripts/enroll.py sync`

Keep it non-destructive by removing the temp folder afterward.

**Step 3: Run the smoke script**

Run: `bash scripts/smoke_openclaw_install.sh`

Expected: PASS with explicit success messages and no manual approvals needed.

**Step 4: Update submission docs**

In `docs/dorahacks_submission.md`, replace generic demo wording with the exact bootstrap + smoke-test path to use in the live demo and submission notes.

**Step 5: Commit**

```bash
git add scripts/smoke_openclaw_install.sh docs/dorahacks_submission.md docs/openclaw_quickstart.md
git commit -m "docs: add judge-safe OpenClaw smoke test path"
```

---

### Task 5: Final verification and handoff

**Files:**
- Verify only; no new files required unless fixes are needed

**Step 1: Run targeted tests**

Run:

```bash
pytest tests/test_install_checks.py tests/test_enroll_script.py tests/test_skill_scripts.py -v
```

Expected: PASS

**Step 2: Run formatter/lint on touched files**

Run:

```bash
ruff check triage_agent/install_checks.py scripts/verify_openclaw_install.py README.md docs/openclaw_quickstart.md docs/dorahacks_submission.md
```

Expected: no lint issues in touched Python files; if README/docs are skipped by Ruff, note that explicitly.

**Step 3: Run the end-to-end smoke path**

Run:

```bash
bash scripts/bootstrap_openclaw.sh
python scripts/verify_openclaw_install.py
bash scripts/smoke_openclaw_install.sh
```

Expected: all steps pass without approval prompts.

**Step 4: Update submission checklist**

Confirm the repo now has:
- one canonical quickstart
- one smoke test
- one demo path consistent with DoraHacks submission copy

**Step 5: Commit**

```bash
git add README.md docs/openclaw_quickstart.md docs/dorahacks_submission.md scripts/bootstrap_openclaw.sh scripts/smoke_openclaw_install.sh scripts/verify_openclaw_install.py triage_agent/install_checks.py tests/test_install_checks.py
git commit -m "feat: ship a judge-safe OpenClaw-first install flow"
```
