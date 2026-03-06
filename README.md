# Research Agent — Autonomous Paper Triage on OpenClaw

`Research Agent` is an OpenClaw-first skill and Python package for triaging arXiv papers into `read in full`, `skim`, or `skip`.

The project is designed for a concrete research workflow:

- fetch a paper from arXiv
- retrieve related work from Semantic Scholar
- compare the paper against the user’s own drafts and notes
- assemble a structured memo and read decision
- optionally run batch triage from `ids.txt`
- optionally send a compact morning digest through OpenClaw cron to Discord or WhatsApp

This README is the canonical technical record for the shipped hackathon bundle: what is implemented, how it works, how to install it, how to test it, and how to demo or submit it.

For a shorter install-only walkthrough, see `docs/openclaw_quickstart.md`.

## Table Of Contents

1. [Hackathon Shipping Scope](#hackathon-shipping-scope)
2. [What The System Does](#what-the-system-does)
3. [Architecture](#architecture)
4. [Technical Implementation](#technical-implementation)
5. [Repository Layout](#repository-layout)
6. [OpenClaw-First Installation](#openclaw-first-installation)
7. [Configuration Reference](#configuration-reference)
8. [Usage](#usage)
9. [Testing And Verification](#testing-and-verification)
10. [Submission And Demo Bundle](#submission-and-demo-bundle)
11. [Troubleshooting](#troubleshooting)
12. [Known Limitations](#known-limitations)

## Hackathon Shipping Scope

This bundle intentionally optimizes for a DoraHacks/OpenClaw judging flow, not package-registry distribution.

The shipped surface is:

- a public GitHub repo
- an OpenClaw-first install path
- a deterministic bootstrap script
- an install verifier
- a judge-safe smoke test
- source enrollment for local folders, GitHub repos, and Overleaf Git mirrors
- OpenClaw cron setup for daily digests

The bundle is meant to get a judge or outside user from clone to first success quickly, before any private credentials are introduced.

## What The System Does

For a single paper URL or arXiv ID, `Research Agent`:

1. extracts the arXiv ID
2. fetches title, authors, abstract, and categories from arXiv
3. retrieves related work from Semantic Scholar
4. evaluates novelty against related work
5. compares the paper with the user’s local research context
6. asks an LLM to assemble a memo and read decision
7. returns either Markdown or JSON

For batch mode, it:

- reads one arXiv ID or URL per line from `ids.txt`
- runs the pipeline for each paper
- writes per-paper memo files
- writes `batch_summary.json`
- writes `batch_summary.md`

For OpenClaw automation, it:

- syncs enrolled sources first
- rebuilds `local_kb/local_manifest.json`
- runs batch triage
- announces a compact digest grouped by `READ IN FULL`, `SKIM`, and `SKIP`

## Architecture

```text
Input (arXiv URL/ID or ids.txt)
    |
    v
[arXiv Fetcher] --> PaperCard
    |
    v
[Orchestrator] -- parallel fan-out:
    |
    +-- [Retriever Agent]       --> RelatedPapers
    +-- [Novelty Checker Agent] --> NoveltyReport
    +-- [Local Overlap Agent]   --> LocalOverlapReport
    |
    v
[Assembler LLM] --> TriageMemo
    |
    +-- per-paper Markdown / JSON
    +-- batch_summary.json
    +-- batch_summary.md
    +-- optional OpenClaw cron digest
```

The source-enrollment subsystem runs alongside that core pipeline:

```text
Enrolled Sources (local / GitHub / Overleaf)
    |
    v
[registry + connectors + parsers]
    |
    v
local_kb/local_manifest.json
    |
    v
[Local Overlap Agent]
```

## Technical Implementation

### Core Runtime

The Python package is defined in `pyproject.toml`. The CLI entrypoint is:

- `triage = triage_agent.cli:main`

The package targets Python `3.11+` and currently depends on:

- `pydantic`
- `httpx`
- `openai`
- `anthropic`
- `rich`
- `jinja2`
- `python-dotenv`

Development tooling includes:

- `pytest`
- `pytest-asyncio`
- `ruff`
- `mypy`

### Pipeline Orchestration

The main runtime pipeline lives in `triage_agent/orchestrator.py`.

Important behavior:

- `run_triage(...)` fetches metadata from arXiv first
- `_run_agents_and_assemble(...)` fans out three sub-agents in parallel using `asyncio.gather(...)`
- the final assembler call merges novelty and local-overlap signals into:
  - `one_line_summary`
  - `key_claims`
  - `relevance`
  - `read_decision`

The current implementation is deliberately abstract-first:

- it does **not** parse PDFs
- it uses arXiv metadata and abstract text
- it uses Semantic Scholar for related-work retrieval

### CLI Surface

The package CLI lives in `triage_agent/cli.py`.

Supported modes:

- single-paper Markdown output
- single-paper JSON output
- batch mode with one output file per paper
- batch summary generation

Batch output shape:

- per-paper file: `<arxiv_id>.md` or `<arxiv_id>.json`
- summary files:
  - `batch_summary.json`
  - `batch_summary.md`

The summary object currently includes:

- `arxiv_id`
- `title`
- `summary`
- `read_decision`
- `novelty_score`
- `relevance`
- `local_relevance`
- `local_related`

### LLM Backend Selection

LLM backend selection is implemented in `triage_agent/utils/llm.py`.

Supported backends:

- `openclaw`
- `openai`
- `anthropic`
- `auto`

Current shipping default:

- `LLM_BACKEND=openclaw`

That choice matters because the normal OpenClaw skill path should work without direct `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` values inside this repo.

Backend resolution behavior:

- `LLM_BACKEND=openclaw` forces calls through `openclaw agent`
- `LLM_BACKEND=openai` forces OpenAI Chat Completions
- `LLM_BACKEND=anthropic` forces Anthropic Messages
- `LLM_BACKEND=auto` prefers direct provider keys if available, otherwise falls back to OpenClaw

### Local Research Context

The local-context surface is `local_kb/local_manifest.json`, loaded by `triage_agent/local_kb.py`.

The `Local Overlap Agent` compares the incoming paper against that manifest and produces:

- an overall local relevance score
- matching local drafts
- overlap summaries

This signal is included in both the detailed memo and the batch summary.

### Source Enrollment System

The source-enrollment implementation is the main extension added for the hackathon final push.

Core files:

- `triage_agent/sources/models.py`
- `triage_agent/sources/registry.py`
- `triage_agent/sources/parsers.py`
- `triage_agent/sources/connectors.py`
- `triage_agent/sources/sync.py`
- `skill/scripts/enroll.py`

The model supports three source types:

- `local`
- `github`
- `overleaf`

Current behavior:

- local sources are scanned recursively
- GitHub and Overleaf sources are cloned or pulled into a local mirror
- supported parsed file types are:
  - `.tex`
  - `.bib`
  - `.md`
  - `.py`

Registry behavior:

- sources are stored in `skill/memory/sources.json`
- `SOURCE_REGISTRY_PATH` can override the path
- repeated enrollment of the same logical source is deduplicated by hashed source identity

Sync behavior:

- `sync_all_sources(...)` loads the registry
- each source is synced through connector dispatch
- parsed entries are converted into `local_manifest.json` shape
- empty registries write `{"papers": []}` explicitly to avoid stale manifests

Git-backed connector behavior:

- mirrors are stored below `~/.openclaw/workspace/research-agent/mirrors`
- GitHub sources use standard clone/pull
- Overleaf sources use the Git mirror URL and token injection

### OpenClaw Skill Integration

The OpenClaw skill lives under `skill/`.

Important files:

- `skill/SKILL.md`
- `skill/openclaw.json`
- `skill/scripts/run_triage.py`
- `skill/scripts/enroll.py`
- `skill/scripts/setup_daily_cron.py`
- `skill/scripts/format_whatsapp.py`

The skill contract is:

- user-invocable `/research-agent`
- OpenClaw-managed runtime by default
- no direct provider key required in the normal path

`skill/scripts/run_triage.py` does the bridge work:

- best-effort repo-root discovery
- `LLM_BACKEND=openclaw` default when OpenClaw is available
- default manifest bootstrapping
- source sync before triage if the sync module is importable
- Python import path first, CLI fallback second
- `seen.json` tracking in `skill/memory/seen.json`

### Daily Digest Automation

Daily digest installation is implemented in `skill/scripts/setup_daily_cron.py`.

The helper creates an OpenClaw cron task that instructs the agent to:

1. `cd` into the project root
2. activate `.venv` if present
3. run `python3 skill/scripts/enroll.py sync`
4. run `triage --batch-file ids.txt --format json --output-dir out/daily_latest`
5. read `out/daily_latest/batch_summary.json`
6. announce a compact grouped digest

WhatsApp formatting is handled by `skill/scripts/format_whatsapp.py`.

The digest groups papers into:

- `READ IN FULL`
- `SKIM`
- `SKIP`

and asks the user to reply with a paper ID for drill-down.

### Shipping Helpers Added For The Hackathon

The install/shipping helpers added in this branch are:

- `scripts/bootstrap_openclaw.sh`
- `scripts/verify_openclaw_install.py`
- `triage_agent/install_checks.py`
- `scripts/smoke_openclaw_install.sh`

Their roles are:

- `bootstrap_openclaw.sh`
  - creates or reuses `.venv`
  - runs `pip install -e ".[dev]"`
  - syncs `skill/` into `~/.openclaw/workspace/skills/research-agent`
  - preserves `memory/profile.json` and `memory/seen.json`
- `verify_openclaw_install.py`
  - checks `openclaw`
  - checks `triage`
  - checks the synced workspace skill
  - checks required skill scripts
- `smoke_openclaw_install.sh`
  - reruns the verifier
  - checks `openclaw skills info research-agent`
  - uses a temporary local source
  - runs enroll/list/sync with temporary registry and manifest paths
  - avoids mutating the user’s real enrolled-source state

The smoke test is intentionally deterministic. It is designed to validate the public install surface after the first live `/research-agent` call has already been demonstrated.

## Repository Layout

Important top-level paths:

- `triage_agent/` — Python package implementation
- `skill/` — OpenClaw skill metadata, memory, and helper scripts
- `local_kb/` — local research manifest consumed by local-overlap logic
- `scripts/` — repo-level install and smoke helpers
- `tests/` — unit and integration-style tests
- `docs/openclaw_quickstart.md` — condensed install walkthrough
- `docs/dorahacks_submission.md` — submission/demo copy

High-value files to know:

- `triage_agent/cli.py`
- `triage_agent/orchestrator.py`
- `triage_agent/utils/llm.py`
- `triage_agent/sources/sync.py`
- `skill/scripts/run_triage.py`
- `skill/scripts/enroll.py`
- `skill/scripts/setup_daily_cron.py`
- `scripts/bootstrap_openclaw.sh`
- `scripts/verify_openclaw_install.py`
- `scripts/smoke_openclaw_install.sh`

## OpenClaw-First Installation

### Prerequisites

- OpenClaw installed and working locally
- Python `3.11+`
- `git`
- a shell environment with `bash`

Optional but recommended:

- `SEMANTIC_SCHOLAR_API_KEY` for reduced rate limiting during heavier retrieval

### Canonical Quickstart

```bash
git clone https://github.com/AustinJunyuLi/hackathon-research-agent.git
cd hackathon-research-agent
bash scripts/bootstrap_openclaw.sh
python scripts/verify_openclaw_install.py
```

Expected result:

- `.venv` exists
- package is installed in editable mode
- `~/.openclaw/workspace/skills/research-agent` exists
- verifier prints `PASS openclaw install ready`

### First Live Success

After the verifier passes, run:

```bash
openclaw skills info research-agent
openclaw agent --agent main --message '/research-agent 2106.09685'
```

Expected result:

- `openclaw skills info research-agent` reports the skill as `Ready`
- `/research-agent 2106.09685` returns a structured memo

### Judge-Safe Smoke Test

After the first live success path is shown once, run:

```bash
bash scripts/smoke_openclaw_install.sh
```

This verifies:

- install readiness
- skill readiness
- local-source enroll/list/sync behavior

without requiring:

- GitHub credentials
- Overleaf credentials
- mutation of the real `sources.json`
- mutation of the real `local_manifest.json`

## Configuration Reference

The environment reference lives in `.env.example`.

Default shipped values:

```bash
LLM_BACKEND=openclaw
LLM_MODEL=claude-sonnet-4-6
OPENCLAW_LLM_AGENT=main
OPENCLAW_LLM_TIMEOUT_SECONDS=180
LLM_TEMPERATURE=0.2
OUTPUT_FORMAT=markdown
OUTPUT_DIR=./output
```

### LLM Variables

- `LLM_BACKEND`
  - `openclaw`
  - `openai`
  - `anthropic`
  - `auto`
- `LLM_MODEL`
- `OPENAI_MODEL`
- `ANTHROPIC_MODEL`
- `LLM_TEMPERATURE`
- `OPENCLAW_LLM_AGENT`
- `OPENCLAW_LLM_TIMEOUT_SECONDS`
- `OPENCLAW_LLM_THINKING`

### Provider Keys

Only needed outside the normal OpenClaw path:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

### Retrieval Variable

- `SEMANTIC_SCHOLAR_API_KEY`

This is optional, but recommended if retrieval gets throttled.

### Output Variables

- `OUTPUT_FORMAT`
- `OUTPUT_DIR`

## Usage

### Single Paper Via OpenClaw

```bash
openclaw agent --agent main --message '/research-agent 2106.09685'
```

### Single Paper Via CLI

```bash
source .venv/bin/activate
triage 2106.09685
triage 2106.09685 --format json
triage https://arxiv.org/abs/2106.09685
```

### Batch Mode

Create `ids.txt` with one arXiv ID or URL per line, then run:

```bash
triage --batch-file ids.txt --format json --output-dir out/demo
```

Expected outputs:

- `out/demo/<paper>.json`
- `out/demo/batch_summary.json`
- `out/demo/batch_summary.md`

### Source Enrollment

Local source:

```bash
python skill/scripts/enroll.py enroll local "Drafts" --path /path/to/research/drafts
python skill/scripts/enroll.py sources
python skill/scripts/enroll.py sync
```

GitHub source:

```bash
python skill/scripts/enroll.py enroll github "Auction Repo" --url https://github.com/user/repo
python skill/scripts/enroll.py sync
```

Overleaf source:

```bash
python skill/scripts/enroll.py enroll overleaf "My Paper" --url https://git.overleaf.com/abc123 --token ol_xxx
python skill/scripts/enroll.py sync
```

### Daily Digest Setup

Install a daily cron:

```bash
python3 skill/scripts/setup_daily_cron.py \
  --project-root "$(pwd)" \
  --cron "0 8 * * *" \
  --tz "Europe/London"
```

Target WhatsApp directly:

```bash
python3 skill/scripts/setup_daily_cron.py \
  --project-root "$(pwd)" \
  --whatsapp +447700900123
```

Inspect installed jobs:

```bash
openclaw cron list
```

Render a compact digest manually:

```bash
python3 skill/scripts/format_whatsapp.py out/demo/batch_summary.json
```

## Testing And Verification

This repo now has a clear shipping-test surface. Use these checks before demoing or submitting.

### 1. Install Surface

```bash
bash scripts/bootstrap_openclaw.sh
python scripts/verify_openclaw_install.py
```

### 2. First Live Demo Step

```bash
openclaw skills info research-agent
openclaw agent --agent main --message '/research-agent 2106.09685'
```

### 3. Deterministic Smoke Test

```bash
bash scripts/smoke_openclaw_install.sh
```

### 4. Shipping-Focused Test Suite

```bash
pytest tests/test_install_checks.py \
       tests/test_smoke_openclaw_install.py \
       tests/test_enroll_script.py \
       tests/test_skill_scripts.py -q
```

This covers:

- bootstrap and install verification
- smoke-test behavior
- enrollment CLI behavior
- skill-script behavior
- cron prompt construction
- WhatsApp digest formatting

### 5. Source-Enrollment Backend Tests

```bash
pytest tests/test_source_registry.py \
       tests/test_parsers.py \
       tests/test_connectors.py \
       tests/test_sync.py -q
```

This covers:

- registry persistence
- parser behavior
- connector clone/pull and local scanning
- manifest rebuild orchestration

### 6. Lint And Type Checks

```bash
ruff check triage_agent/install_checks.py \
           scripts/verify_openclaw_install.py \
           tests/test_install_checks.py \
           tests/test_smoke_openclaw_install.py

mypy triage_agent/install_checks.py
```

### Recommended Pre-Submission Verification Sequence

Run these in order:

```bash
bash scripts/bootstrap_openclaw.sh
python scripts/verify_openclaw_install.py
openclaw skills info research-agent
openclaw agent --agent main --message '/research-agent 2106.09685'
bash scripts/smoke_openclaw_install.sh
pytest tests/test_install_checks.py \
       tests/test_smoke_openclaw_install.py \
       tests/test_enroll_script.py \
       tests/test_skill_scripts.py -q
```

## Submission And Demo Bundle

The submission bundle should tell one coherent story:

1. install the skill from the repo
2. verify the install
3. show one live paper triage
4. show non-destructive local-source personalization
5. show or describe the automated daily digest

### Exact Demo Commands

```bash
bash scripts/bootstrap_openclaw.sh
python scripts/verify_openclaw_install.py
openclaw skills info research-agent
openclaw agent --agent main --message '/research-agent 2106.09685'
bash scripts/smoke_openclaw_install.sh
python3 skill/scripts/setup_daily_cron.py --project-root "$(pwd)" --channel discord --to <channel-id>
```

### What To Include In The DoraHacks Submission

- GitHub repo URL
- a demo video
- one screenshot of the single-paper OpenClaw run
- one screenshot or terminal capture of the smoke path or digest
- short description of source enrollment
- short description of the daily digest flow

### Suggested Submission Narrative

Use this structure:

- problem: too many papers, not enough time
- method: retrieve prior art + compare against my own drafts + produce a read decision
- OpenClaw value: skill-native runtime, cron automation, channel delivery
- personalization value: local/GitHub/Overleaf enrollment keeps the local-overlap signal fresh
- bundle quality: install verifier + smoke test + docs make the repo judge-usable

### Bundle Files Worth Linking

- `README.md`
- `docs/openclaw_quickstart.md`
- `docs/dorahacks_submission.md`
- `skill/SKILL.md`

## Troubleshooting

### `openclaw` not found

Install OpenClaw first, then rerun:

```bash
python scripts/verify_openclaw_install.py
```

### `triage` not found

Rerun:

```bash
bash scripts/bootstrap_openclaw.sh
```

### Skill not synced

Resync the workspace skill:

```bash
bash scripts/bootstrap_openclaw.sh
openclaw skills info research-agent
```

### Provider-Key Confusion

The normal shipped path is OpenClaw-managed runtime auth.

You do **not** need direct repo-level API keys for the default skill path.

Use direct `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` only if you intentionally switch away from the OpenClaw backend.

### Semantic Scholar Rate Limits

Set:

```bash
export SEMANTIC_SCHOLAR_API_KEY=...
```

before heavier batch runs.

### Overleaf Not Enrolled Yet

That is not a base-install blocker.

First get the following working:

```bash
python scripts/verify_openclaw_install.py
openclaw agent --agent main --message '/research-agent 2106.09685'
bash scripts/smoke_openclaw_install.sh
```

Then add Overleaf later with the explicit Git mirror URL and token.

### OpenClaw Doctor Warnings About `safeBins`

Those warnings are currently environmental OpenClaw configuration warnings. They do not block the shipped verifier or smoke path, but they are worth cleaning up in your local OpenClaw install if you want a quieter demo.

## Known Limitations

- current paper understanding is abstract-first and does not parse PDFs
- Semantic Scholar is the main related-work dependency and may throttle without an API key
- the smoke test validates install and personalization plumbing, not the full expensive LLM pipeline a second time
- Overleaf enrollment requires an explicit Git mirror URL and token
- repo-wide lint/type cleanup outside the touched shipping/install surface is not part of this bundle

## Secondary Standalone CLI Path

The standalone CLI still works if you want to use the repo outside OpenClaw:

```bash
source .venv/bin/activate
cp .env.example .env
triage 2301.07041
triage --batch-file ids.txt --format json --output-dir out
```

This path is secondary. The canonical shipped experience for the hackathon is OpenClaw-first.
