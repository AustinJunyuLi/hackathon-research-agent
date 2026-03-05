# DoraHacks Submission Prep

## Project

- Name: `Research Agent — Autonomous Paper Triage on OpenClaw`
- Repo: `https://github.com/AustinJunyuLi/hackathon-research-agent`
- Branch: `feature/hackathon-final-push-20260305`

## Short Pitch

`Research Agent` is an OpenClaw-native research assistant that turns a raw arXiv ID list into actionable reading decisions. It fetches metadata, compares papers against prior art and the user's own drafts, then delivers a compact morning digest to Discord or WhatsApp. The latest version adds source enrollment for Overleaf, GitHub, and local research folders so the local-overlap signal stays current without manual manifest editing.

## What To Demo

1. `/research-agent 2106.09685` in OpenClaw
2. `python skill/scripts/enroll.py enroll local "Drafts" --path <folder>`
3. `python skill/scripts/enroll.py sync`
4. `triage --batch-file ids.txt --format json --output-dir out/demo`
5. `python skill/scripts/format_whatsapp.py out/demo/batch_summary.json`
6. `python skill/scripts/setup_daily_cron.py --project-root <repo> --channel discord --to <channel-id>`

## Submission Copy

### Description

`Research Agent` solves a practical research bottleneck: deciding what to read deeply, what to skim, and what to ignore when new papers keep arriving. The agent runs an autonomous triage pipeline over arXiv papers, combining retrieval, novelty checking, and local-overlap analysis against the user's own drafts. It is built for OpenClaw first, so it runs as a skill, supports scheduled daily digests, and can deliver concise updates to Discord or WhatsApp.

The final push adds a source enrollment system that mirrors Overleaf or GitHub repos and scans local research folders to rebuild the local manifest automatically. That keeps relevance judgments grounded in the user's current work instead of a stale hand-maintained file. The result is a demo-ready agent that can operate on a schedule and stay aligned with an active research workflow.

### Key Features

- OpenClaw-first skill execution with no direct provider key required in the normal path
- Single-paper memo generation and batch triage from `ids.txt`
- Daily scheduled digest via OpenClaw cron
- Discord and WhatsApp-friendly summary formatting
- Source enrollment for Overleaf, GitHub, and local folders
- Automatic manifest rebuild before triage runs

## Assets Checklist

- [ ] GitHub branch pushed
- [ ] Repo README reflects enrollment + cron flow
- [ ] One OpenClaw single-paper screenshot
- [ ] One digest screenshot or terminal capture
- [ ] Team member names added
- [ ] DoraHacks form populated
