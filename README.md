# Research Agent — Autonomous Paper Triage on OpenClaw

AI-powered research paper triage for arXiv papers.

## What It Does

Given an arXiv paper URL or ID, the agent:

1. **Fetches** abstract + metadata from the arXiv API (no PDF parsing)
2. **Retrieves** related papers via Semantic Scholar API
3. **Checks novelty** against closest prior art
4. **Checks local overlap** against your `local_kb/local_manifest.json`
5. **Assembles** a structured memo + read recommendation
6. **Optionally syncs enrolled sources** from Overleaf, GitHub, or a local folder before triage
7. **Delivers a daily digest** to Discord or WhatsApp through OpenClaw cron

## Architecture

```text
Input (arXiv URL/ID)
    |
    v
[arXiv Fetcher] --> PaperCard
    |
    v
[Orchestrator] -- parallel:
    |
    +-- [Retriever Agent]       --> RelatedPapers
    +-- [Novelty Checker Agent] --> NoveltyReport
    +-- [Local Overlap Agent]   --> LocalOverlapReport
    |
    v
[Assembler] --> TriageMemo
    |
    v
Output (Markdown / JSON)
```

## Setup

```bash
git clone <repo-url>
cd hackathon-research-agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Optional: add provider keys, model overrides, etc.

triage <arxiv-url-or-id>
```

## Configuration

Copy `.env.example` to `.env`.

- **Default backend is OpenClaw runtime** (`LLM_BACKEND=openclaw`).
- **Inside OpenClaw**: no direct OpenAI/Anthropic key env is required.
- **Standalone CLI**: you may optionally set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` and switch backend.
- `SEMANTIC_SCHOLAR_API_KEY` is optional but recommended to reduce rate-limit issues.

## Usage

```bash
# Single paper
triage 2301.07041
triage https://arxiv.org/abs/2301.07041

# Single paper JSON output
triage 2301.07041 --format json

# Batch mode (one arXiv ID/URL per line)
triage --batch-file ids.txt --format json --output-dir out
```

## OpenClaw Skill

Skill folder is under `skill/`.

- Skill metadata no longer requires a direct provider key.
- It is OpenClaw-backend-first by default.
- Entry script: `skill/scripts/run_triage.py`
- Source enrollment CLI: `skill/scripts/enroll.py`

### Enable Daily Morning Push

Install a daily cron digest (08:00 local time by default):

```bash
python3 skill/scripts/setup_daily_cron.py \
  --project-root /path/to/hackathon-research-agent \
  --cron "0 8 * * *" \
  --tz "Europe/London"
```

This cron job first syncs enrolled sources, rebuilds `local_kb/local_manifest.json`, then runs batch triage and announces a compact digest.

Target WhatsApp directly:

```bash
python3 skill/scripts/setup_daily_cron.py \
  --project-root /path/to/hackathon-research-agent \
  --whatsapp +447700900123
```

Check cron jobs:

```bash
openclaw cron list
```

## Source Enrollment

Track local research context without hand-editing the manifest:

```bash
python skill/scripts/enroll.py enroll overleaf "My Paper" --url https://git.overleaf.com/abc123 --token ol_xxx
python skill/scripts/enroll.py enroll github "Auction Repo" --url https://github.com/user/repo
python skill/scripts/enroll.py enroll local "Drafts" --path /home/user/research/drafts
python skill/scripts/enroll.py sources
python skill/scripts/enroll.py sync
```

Supported connectors:

- `overleaf` via Git mirror URL and token
- `github` via repository clone/pull
- `local` via recursive file scan of `.tex`, `.bib`, `.md`, and `.py`

## Future Extensions

- Scheduled monitoring for new category papers
- Telegram push summaries
- Additional read-decision factors (impact, recency, venue quality, etc.)
