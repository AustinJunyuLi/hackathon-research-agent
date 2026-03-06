# Design: OpenClaw-First Shipping & Install

**Status:** APPROVED
**Date:** 2026-03-05
**Deadline:** 2026-03-07 23:59
**Hackathon:** UK AI Agent Hackathon EP4 x OpenClaw

---

## Context

The project is being shipped into an OpenClaw-focused hackathon where the judging surface is the DoraHacks BUIDL submission, not a package registry. The official hackathon page emphasizes production-ready AI agents, real-world tools, and sponsor integrations. Current submissions in the same hackathon expose GitHub, demo video, docs, and optional release links; they do not depend on a package-manager distribution to be considered valid.

The repo currently has working core functionality, but the install story is still mixed:
- `README.md` presents both standalone CLI and OpenClaw usage as if they are equally primary
- the installed skill and the repo can drift apart
- source enrollment is optional but not yet framed clearly as a post-install step
- there is no single “judge-safe” bootstrap path with a verification command

That ambiguity is the main shipping risk.

---

## Decision

Ship a **single canonical install path**:

1. clone the repo
2. run one OpenClaw-oriented bootstrap command from the repo
3. run one smoke test
4. optionally enroll local / GitHub / Overleaf sources

Do **not** spend deadline time on publishing a package release as the primary install mechanism. A release tag is optional; a registry-grade package is post-hackathon work.

---

## Goals

- Make OpenClaw the unmistakable primary onboarding path
- Get a judge from repo clone to first successful `research-agent` run in under 10 minutes
- Ensure first-run success does not require OpenAI or Anthropic provider keys
- Stage private credentials (Overleaf token, private GitHub repos) as optional post-install configuration
- Give outside users a deterministic quickstart and verification path

## Non-Goals

- Cross-platform installer polish beyond Linux/macOS shell + Python 3.11+
- Publishing to PyPI / Homebrew / ClawHub as the required install path
- Automatic Overleaf enrollment without an explicit Git URL and token
- Zero-step setup for users who do not already have OpenClaw installed

---

## User Journeys

### 1. Hackathon Judge

The judge already has the repo link from DoraHacks. They should be able to:

1. clone the repo
2. install dependencies with one documented command block
3. verify the OpenClaw skill is registered and ready
4. run one single-paper example
5. optionally run one local-source enrollment and batch digest example

The judge does **not** need to configure Overleaf or private GitHub to understand the product.

### 2. Outside OpenClaw User

The outside user already has OpenClaw or is willing to install it first. They should be able to:

1. follow the same canonical quickstart
2. verify the skill works before touching private credentials
3. add local/GitHub/Overleaf sources later using explicit enrollment commands
4. set up the daily cron only after the single-paper path succeeds

---

## Shipping Approach Options

### Option A — OpenClaw-First Bootstrap from GitHub Clone (**Recommended**)

Use a repo-local bootstrap helper and verification helper. README leads with this path only. Standalone `triage` remains documented, but as a secondary mode.

**Pros**
- best fit with hackathon judging surface
- lowest deadline risk
- keeps the demo aligned with the actual product story
- avoids package publishing work

**Cons**
- assumes users can clone a repo and run a shell/Python bootstrap
- still requires documenting OpenClaw as a prerequisite

### Option B — Dual-Primary Docs

Keep CLI and OpenClaw as equal first-class onboarding paths.

**Pros**
- more flexible for technical users

**Cons**
- increases README confusion
- weakens the “built on OpenClaw” story
- raises support burden during judging

### Option C — Registry / Package Release First

Publish the project as the primary install method.

**Pros**
- stronger long-term outside-user story

**Cons**
- not required by hackathon rules
- highest deadline risk
- packaging/debugging time competes with demo polish

---

## Recommended UX Contract

### Canonical Quickstart

The README should lead with a single path:

```bash
git clone <repo-url>
cd hackathon-research-agent
./scripts/bootstrap_openclaw.sh
./scripts/verify_openclaw_install.sh
```

After that, the first success path is:

```bash
openclaw skills info research-agent
openclaw agent --agent main --message '/research-agent 2106.09685'
```

### Optional Configuration Stages

After first success, the README should stage optional steps in this order:

1. enroll a local source
2. sync enrolled sources
3. run batch triage
4. set up daily digest cron
5. enroll GitHub / Overleaf sources

This keeps private credentials out of the base install path.

---

## Required Repo Changes

### 1. README Restructure

`README.md` should have these top sections in order:

1. What it does
2. Prerequisites
3. OpenClaw-first quickstart
4. First successful run
5. Optional source enrollment
6. Optional daily digest
7. Troubleshooting

The standalone CLI path should move below the OpenClaw path and be labeled secondary.

### 2. Bootstrap Helper

Add a repo-local bootstrap helper that:
- creates/uses `.venv`
- installs the package in editable mode
- syncs the latest `skill/` contents into the OpenClaw workspace
- prints the next verification commands

### 3. Verification Helper

Add a verification helper that checks:
- `openclaw` exists
- `triage` exists
- the `research-agent` skill files are in place
- the installed skill exposes the new enrollment scripts
- the current environment is ready for a first-run smoke test

### 4. Troubleshooting Surface

Document only the failure modes judges/outside users are likely to hit:
- `openclaw` missing
- skill not synced
- `triage` missing
- provider-key confusion
- Semantic Scholar rate limits
- Overleaf not enrolled yet

---

## Demo/Submission Consequences

For DoraHacks, the project should ship as:

- public GitHub repo
- strong OpenClaw-first README
- demo video
- clear links in the BUIDL submission
- optional release tag / GitHub Pages if time remains

The install story should reinforce the demo:
- one canonical setup path
- one single-paper success example
- one optional personalization example via source enrollment

---

## Acceptance Criteria

- A user with OpenClaw installed can follow one quickstart path and reach first success without provider-key confusion
- A judge can verify the install and run a demo example in under ~10 minutes
- Overleaf/GitHub credentials are clearly optional and post-install
- README has one primary onboarding path, not two competing ones
- The skill sync/install path is deterministic and repeatable
- The submission materials point to the same canonical install path used in the README
