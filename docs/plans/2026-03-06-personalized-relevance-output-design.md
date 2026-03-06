# Design: Personalized Relevance Output And Cadence

**Status:** APPROVED
**Date:** 2026-03-06

## Context

The current agent produces a technically correct triage memo, but the most important product question is still under-served: _why does this paper matter to this specific user right now_?

The local-overlap subsystem already computes overlap against the user's own drafts and notes, but the output mostly exposes scores and free-form overlap summaries. That makes the personalization signal harder to scan in the memo, harder to summarize in the digest, and less compelling in a hackathon demo.

The cron cadence is also still daily by default, even though this project does not autonomously discover arbitrary external papers yet. In the current product shape, a three-times-weekly default is a better noise/attention tradeoff.

## Decision

Ship a focused personalization layer rather than a new discovery subsystem.

The change set will:

1. add a normalized `relationship_type` label to each local-overlap match
2. add a memo-level `why_this_matters_to_you` explanation
3. propagate that personalized explanation into `batch_summary.json`
4. make the WhatsApp/digest path use the personalized explanation
5. make low-signal digests terse
6. change the default cron cadence to `Mon/Wed/Fri at 08:00`

## Why This Scope

This is the highest-leverage touch-up that:

- materially improves output quality
- improves demo clarity
- stays grounded in the existing architecture
- avoids building a brittle paper-discovery crawler under deadline pressure

## Output Contract

### Local Match

Each local match should include:

- `local_id`
- `local_title`
- `relevance`
- `relationship_type`
- `overlap_summary`

Recommended normalized relationship labels:

- `extends_your_work`
- `competes_with_your_idea`
- `method_transfer`
- `citation_candidate`
- `background_context`
- `same_problem_different_method`
- fallback: `related`

### Triage Memo

Each memo should include:

- the current one-line summary
- a new `why_this_matters_to_you` field

That explanation should explicitly reference:

- the user's local work when available
- whether the paper extends, competes with, or complements that work
- why the read decision follows from that relationship

### Batch Summary / Digest

`batch_summary.json` should carry:

- `why_this_matters_to_you`
- structured local-relationship snippets for top local matches

The compact digest should use the personalized reason for `READ IN FULL` and `SKIM`.

If a batch has no `read in full` or `skim` items, the digest should be terse rather than noisy.

## Cadence Decision

Default scheduled cadence becomes:

- `Mon/Wed/Fri at 08:00`

Rationale:

- own-source sync should still happen on every run
- external paper discovery is not fully autonomous yet
- a daily push is more likely to create noise than value in the current product shape

## Testing Strategy

Add tests first for:

- local-overlap relationship parsing
- memo markdown containing the personalized explanation
- batch digest using the personalized explanation
- low-signal digest suppression behavior
- cron default expression changing to `0 8 * * 1,3,5`

## Non-Goals

- building a new web crawler or feed watcher
- changing the core retrieval backend
- redesigning the entire memo schema
- adding new delivery channels
