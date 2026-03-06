# Personalized Relevance Output Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve the quality of the triage output by making it explicitly personalized to the user's local knowledge base and adjust the default push cadence to a lower-noise schedule.

**Architecture:** Extend the local-overlap schema with normalized relationship labels, extend the memo schema with a memo-level personalized explanation, propagate that explanation into batch summaries and digests, and tighten the cron defaults so the delivery cadence matches the current product shape.

**Tech Stack:** Python 3.11+, Pydantic models, existing formatter stack, OpenClaw cron helpers, pytest, Ruff.

---

### Task 1: Add failing tests for personalized memo fields

**Files:**
- Modify: `tests/test_models.py`
- Modify: `tests/test_formatters.py`

**Step 1: Write failing tests**

Add tests covering:
- `LocalOverlapMatch.relationship_type`
- `TriageMemo.why_this_matters_to_you`
- Markdown output showing a `Why This Matters To You` section

**Step 2: Run the targeted tests**

Run: `pytest tests/test_models.py tests/test_formatters.py -q`

Expected: FAIL because the schema/formatter fields do not exist yet.

**Step 3: Implement minimal model/formatter changes**

Touch:
- `triage_agent/models/memo.py`
- `triage_agent/formatters/markdown.py`

**Step 4: Re-run tests**

Run: `pytest tests/test_models.py tests/test_formatters.py -q`

Expected: PASS

---

### Task 2: Add relationship labels to local-overlap parsing

**Files:**
- Modify: `triage_agent/agents/local_overlap.py`
- Add or modify tests for local-overlap parsing

**Step 1: Write failing test**

Add a targeted parser test verifying:
- a raw LLM match with `relationship_type` is preserved
- unknown labels normalize to `related`

**Step 2: Run test**

Run: `pytest <targeted-local-overlap-test> -q`

Expected: FAIL

**Step 3: Implement minimal parser/prompt change**

Update:
- prompt contract to request `relationship_type`
- parser normalization logic

**Step 4: Re-run test**

Run: `pytest <targeted-local-overlap-test> -q`

Expected: PASS

---

### Task 3: Add personalized assembler output and batch summary propagation

**Files:**
- Modify: `triage_agent/orchestrator.py`
- Modify: `triage_agent/cli.py`
- Add targeted tests for summary propagation

**Step 1: Write failing tests**

Add tests covering:
- assembler output schema includes `why_this_matters_to_you`
- batch summary carries the personalized field

**Step 2: Run targeted tests**

Run: `pytest <targeted-summary-tests> -q`

Expected: FAIL

**Step 3: Implement minimal code**

Update:
- assembler prompt
- assembler parsing
- `TriageMemo` construction
- summary builder

**Step 4: Re-run targeted tests**

Run: `pytest <targeted-summary-tests> -q`

Expected: PASS

---

### Task 4: Improve digest quality and default cadence

**Files:**
- Modify: `skill/scripts/format_whatsapp.py`
- Modify: `skill/scripts/setup_daily_cron.py`
- Modify: `skill/openclaw.json`
- Modify: `tests/test_skill_scripts.py`

**Step 1: Write failing tests**

Add tests for:
- digest using `why_this_matters_to_you`
- terse low-signal digest behavior
- default cron cadence of `0 8 * * 1,3,5`

**Step 2: Run targeted tests**

Run: `pytest tests/test_skill_scripts.py -q`

Expected: FAIL

**Step 3: Implement minimal changes**

Update:
- digest formatting
- cron helper defaults
- skill metadata cron schedule

**Step 4: Re-run tests**

Run: `pytest tests/test_skill_scripts.py -q`

Expected: PASS

---

### Task 5: Update README and verify the shipping surface

**Files:**
- Modify: `README.md`
- Modify: `docs/openclaw_quickstart.md`
- Modify: `docs/dorahacks_submission.md`

**Step 1: Update docs**

Document:
- personalized local relationship labels
- `why_this_matters_to_you`
- Mon/Wed/Fri default cadence
- the fact that source sync runs every scheduled push while discovery is still driven by `ids.txt`

**Step 2: Run verification**

Run:

```bash
pytest tests/test_models.py \
       tests/test_formatters.py \
       tests/test_skill_scripts.py \
       tests/test_install_checks.py \
       tests/test_smoke_openclaw_install.py \
       tests/test_enroll_script.py \
       tests/test_source_registry.py \
       tests/test_parsers.py \
       tests/test_connectors.py \
       tests/test_sync.py -q

ruff check triage_agent/models/memo.py \
           triage_agent/agents/local_overlap.py \
           triage_agent/orchestrator.py \
           triage_agent/cli.py \
           triage_agent/formatters/markdown.py \
           skill/scripts/format_whatsapp.py \
           skill/scripts/setup_daily_cron.py \
           tests/test_models.py \
           tests/test_formatters.py \
           tests/test_skill_scripts.py
```

Expected: PASS
