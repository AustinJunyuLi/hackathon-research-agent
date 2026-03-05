"""Local Overlap Agent — compares a paper against the user's local drafts.

This agent looks at the target paper's abstract and the local manifest
(`local_kb/local_manifest.json`) and summarizes where the target paper
overlaps with or is relevant to the user's own work.

For now we only use the JSON manifest (no local_profile.md), to keep the
implementation simple and focused.
"""

from __future__ import annotations

import logging
from typing import Any

from triage_agent.agents.base import BaseAgent
from triage_agent.local_kb import LocalManifest, LocalPaper, load_local_manifest
from triage_agent.models.memo import LocalOverlapMatch, LocalOverlapReport
from triage_agent.models.paper import PaperCard
from triage_agent.utils.llm import call_llm_json


logger = logging.getLogger(__name__)


LOCAL_SYSTEM_PROMPT = """\
You are a research assistant helping a researcher decide which new papers
are relevant to their own ongoing work.

You are given:
- A TARGET PAPER (title + abstract)
- A list of LOCAL DRAFTS (each with id, title, abstract) representing the
  researcher's current projects, notes, or ideas.

Your job is to:
1. Identify which local drafts the target paper is most related to.
2. For each related local draft, briefly summarize how the target paper
   overlaps with or is relevant to that draft (methods, goals, setting, etc.).
3. Assign a relevance score from 0.0 (not related) to 1.0 (highly relevant)
   for each local draft.
4. Provide an overall relevance score from 0.0 to 1.0 for how important this
   target paper is to the researcher's current work.
"""


LOCAL_USER_PROMPT = """\
TARGET PAPER:
Title: {title}
Abstract: {abstract}

LOCAL DRAFTS:
{local_list}

Analyze how the TARGET PAPER relates to the LOCAL DRAFTS above.

Return a JSON object with:
- "matches": a list of objects, each with:
    - "local_id": string (from the input)
    - "local_title": string
    - "relevance": float between 0.0 and 1.0
    - "overlap_summary": short string (1-3 sentences) describing the overlap
- "overall_relevance": float between 0.0 and 1.0
"""


class LocalOverlapAgent(BaseAgent):
    """Assesses overlap between the target paper and local drafts."""

    @property
    def name(self) -> str:
        return "Local Overlap"

    async def run(self, paper: PaperCard) -> LocalOverlapReport:
        """Compare the target paper against the user's local drafts.

        If no local manifest is found, returns an empty LocalOverlapReport
        with overall_relevance = 0.0.
        """
        manifest = load_local_manifest()
        if manifest is None or not manifest.papers:
            return LocalOverlapReport(matches=[], overall_relevance=0.0)

        local_list = _format_local_list(manifest)

        user_prompt = LOCAL_USER_PROMPT.format(
            title=paper.title,
            abstract=paper.abstract,
            local_list=local_list,
        )

        try:
            raw: dict[str, Any] = await call_llm_json(
                system_prompt=LOCAL_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except Exception as exc:  # pragma: no cover - network/pathological errors
            logger.warning(
                "Local overlap LLM call failed for '%s': %s",
                paper.title,
                exc,
            )
            return LocalOverlapReport(matches=[], overall_relevance=0.0)

        return _parse_local_overlap_response(raw, manifest)


def _format_local_list(manifest: LocalManifest) -> str:
    """Format local drafts as a bullet list for the prompt."""
    if not manifest.papers:
        return "(No local drafts provided)"
    lines: list[str] = []
    for p in manifest.papers:
        lines.append(f"- id={p.id} | {p.title}")
        lines.append(f"  abstract: {p.abstract}")
    return "\n".join(lines)


def _parse_local_overlap_response(
    raw: dict[str, Any],
    manifest: LocalManifest,
) -> LocalOverlapReport:
    """Convert the LLM JSON response into a LocalOverlapReport."""
    matches_raw = raw.get("matches") or []
    overall_raw = raw.get("overall_relevance", 0.0)

    try:
        overall = float(overall_raw)
    except (TypeError, ValueError):
        overall = 0.0
    overall = max(0.0, min(1.0, overall))

    # Build a quick lookup from local_id to LocalPaper for nicer fallbacks.
    by_id: dict[str, LocalPaper] = {p.id: p for p in manifest.papers}

    matches: list[LocalOverlapMatch] = []
    if isinstance(matches_raw, list):
        for item in matches_raw:
            if not isinstance(item, dict):
                continue
            local_id = str(item.get("local_id", "")).strip()
            if not local_id:
                continue

            lp = by_id.get(local_id)
            local_title = str(item.get("local_title") or (lp.title if lp else "")).strip()

            try:
                relevance = float(item.get("relevance", 0.0))
            except (TypeError, ValueError):
                relevance = 0.0
            relevance = max(0.0, min(1.0, relevance))

            overlap_summary = str(item.get("overlap_summary", "")).strip()

            matches.append(
                LocalOverlapMatch(
                    local_id=local_id,
                    local_title=local_title or (lp.title if lp else local_id),
                    relevance=relevance,
                    overlap_summary=overlap_summary,
                )
            )

    return LocalOverlapReport(matches=matches, overall_relevance=overall)

