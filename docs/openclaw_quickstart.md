# OpenClaw Quickstart

This is the canonical install and verification path for both hackathon judges and outside users.

## Acceptance Checklist

- [ ] OpenClaw is already installed and working
- [ ] Python `3.11+` and `git` are installed
- [ ] `bash scripts/bootstrap_openclaw.sh` completes successfully
- [ ] `python scripts/verify_openclaw_install.py` reports `PASS`
- [ ] `openclaw skills info research-agent` reports `Ready`
- [ ] `openclaw agent --agent main --message '/research-agent 2106.09685'` returns a triage result
- [ ] The memo explains why the paper matters to your current drafts or notes
- [ ] `bash scripts/smoke_openclaw_install.sh` passes without manual approvals
- [ ] Optional source enrollment succeeds without editing `local_kb/local_manifest.json` by hand
- [ ] Optional daily digest is configured only after the single-paper path works

## 1. Clone And Bootstrap

```bash
git clone https://github.com/AustinJunyuLi/hackathon-research-agent.git
cd hackathon-research-agent
bash scripts/bootstrap_openclaw.sh
```

The bootstrap helper:

- creates or reuses `.venv`
- runs `pip install -e ".[dev]"`
- syncs `skill/` into `~/.openclaw/workspace/skills/research-agent`
- preserves `memory/profile.json` and `memory/seen.json`

## 2. Verify The Install

```bash
python scripts/verify_openclaw_install.py
openclaw skills info research-agent
```

If the install is healthy, the verifier prints `PASS openclaw install ready` and the skill status reports `Ready`.

## 3. First Successful Run

```bash
openclaw agent --agent main --message '/research-agent 2106.09685'
```

This is the minimum success condition. Do not move on to private source enrollment until this works.

The memo should now include a personalized explanation of why the paper matters to your existing work and, when there are strong local matches, a relationship label such as `extends_your_work` or `method_transfer`.

## 4. Judge-Safe Smoke Test

After the first successful single-paper run, verify the full public demo path:

```bash
bash scripts/smoke_openclaw_install.sh
```

The smoke script:

- reruns the install verifier
- checks `openclaw skills info research-agent`
- enrolls a temporary local markdown source
- runs `python skill/scripts/enroll.py sync`
- removes the temporary smoke-test files automatically

The smoke test uses temporary registry and manifest paths, so it does not mutate your real enrolled-source state or depend on a second live model call.

## 5. Optional Local Source Enrollment

Use a local folder first. It exercises the same manifest-rebuild path without requiring private credentials.

```bash
python skill/scripts/enroll.py enroll local "Drafts" --path /path/to/research/drafts
python skill/scripts/enroll.py sources
python skill/scripts/enroll.py sync
```

Expected result:

- the source appears in `sources`
- sync reports the number of papers or entries written into the local manifest

## 6. Optional GitHub And Overleaf Enrollment

Add private sources only after the public local-path flow is working.

```bash
python skill/scripts/enroll.py enroll github "Auction Repo" --url https://github.com/user/repo
python skill/scripts/enroll.py enroll overleaf "My Paper" --url https://git.overleaf.com/abc123 --token ol_xxx
python skill/scripts/enroll.py sync
```

Notes:

- GitHub enrollment uses clone/pull semantics
- Overleaf enrollment requires an explicit Git mirror URL and token
- base install success does not depend on either connector

## 7. Optional Daily Digest

After the single-paper and source-sync paths work, install the daily digest:

```bash
python3 skill/scripts/setup_daily_cron.py \
  --project-root "$(pwd)" \
  --tz "Europe/London"
```

Or target WhatsApp directly:

```bash
python3 skill/scripts/setup_daily_cron.py \
  --project-root "$(pwd)" \
  --whatsapp +447700900123
```

Default cadence is `Mon/Wed/Fri at 08:00`. The cron flow syncs enrolled sources first, rebuilds `local_kb/local_manifest.json`, then runs batch triage. Low-signal cycles stay terse instead of producing a long noisy digest.

## 8. Troubleshooting

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

### Skill not ready

Resync the skill, then recheck:

```bash
bash scripts/bootstrap_openclaw.sh
openclaw skills info research-agent
```

### Provider-key confusion

The normal path is OpenClaw-managed runtime auth. Direct repo-level OpenAI or Anthropic keys are optional for standalone CLI usage only.

### Semantic Scholar rate limits

Set `SEMANTIC_SCHOLAR_API_KEY` before heavier batch runs if retrieval gets throttled.
