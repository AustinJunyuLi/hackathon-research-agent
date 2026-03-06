# DoraHacks Submission Prep

## Project

- Name: `Research Agent — Autonomous Paper Triage on OpenClaw`
- Repo: `https://github.com/AustinJunyuLi/hackathon-research-agent`
- Branch: `feature/hackathon-final-push-20260305`

## Short Pitch

`Research Agent` is an OpenClaw-native research assistant that turns a raw arXiv ID list into actionable reading decisions. It fetches metadata, compares papers against prior art and the user's own drafts, explains why each paper matters to that specific user, then delivers a compact digest to Discord or WhatsApp. The latest version adds source enrollment for Overleaf, GitHub, and local research folders so the local-overlap signal stays current without manual manifest editing.

## What To Demo

1. `bash scripts/bootstrap_openclaw.sh`
2. `python scripts/verify_openclaw_install.py`
3. `openclaw skills info research-agent`
4. `openclaw agent --agent main --message '/research-agent 2106.09685'`
5. `bash scripts/smoke_openclaw_install.sh`
6. `python3 skill/scripts/setup_daily_cron.py --project-root "$(pwd)" --channel discord --to <channel-id>`

## Submission Copy

### Description

`Research Agent` solves a practical research bottleneck: deciding what to read deeply, what to skim, and what to ignore when new papers keep arriving. The agent runs an autonomous triage pipeline over arXiv papers, combining retrieval, novelty checking, and local-overlap analysis against the user's own drafts. It is built for OpenClaw first, so it runs as a skill, supports scheduled digests on a lower-noise Mon/Wed/Fri cadence, and can deliver concise updates to Discord or WhatsApp.

The final push adds a source enrollment system that mirrors Overleaf or GitHub repos and scans local research folders to rebuild the local manifest automatically. That keeps relevance judgments grounded in the user's current work instead of a stale hand-maintained file. It also adds relationship labels and a personalized `why this matters to you` explanation to each memo, so the output is not just a scorecard but an explicit connection to the user's active projects.

The canonical install and demo path is now repo clone plus OpenClaw bootstrap, verification, and a judge-safe smoke test. That keeps the first-run path public and reproducible before any private GitHub or Overleaf credentials are introduced.

### Key Features

- OpenClaw-first skill execution with no direct provider key required in the normal path
- Single-paper memo generation and batch triage from `ids.txt`
- Daily scheduled digest via OpenClaw cron
- Discord and WhatsApp-friendly summary formatting
- Source enrollment for Overleaf, GitHub, and local folders
- Automatic manifest rebuild before triage runs
- Personalized memo output with local relationship labels and user-specific relevance reasons
- Mon/Wed/Fri default push cadence to reduce notification noise
- Judge-safe bootstrap and smoke-test flow for installation and demo

## Assets Checklist

- [ ] GitHub branch pushed
- [ ] Repo README reflects bootstrap + smoke-test flow
- [ ] `docs/openclaw_quickstart.md` matches the live demo commands
- [ ] One OpenClaw single-paper screenshot
- [ ] One digest screenshot or terminal capture
- [ ] Team member names added
- [ ] DoraHacks form populated
