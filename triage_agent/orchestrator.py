"""Orchestrator — coordinates sub-agents and assembles the Triage Memo.

This is the main pipeline: fetch paper -> fan out to agents -> assemble memo.
"""

import asyncio
import logging
from typing import Any

from triage_agent.agents.local_overlap import LocalOverlapAgent
from triage_agent.agents.novelty import NoveltyCheckerAgent
from triage_agent.agents.retriever import RetrieverAgent
from triage_agent.api.arxiv import ArxivClient
from triage_agent.models.memo import (
    LocalOverlapReport,
    NoveltyReport,
    Relevance,
    TriageMemo,
)
from triage_agent.models.paper import PaperCard
from triage_agent.utils.llm import call_llm_json

logger = logging.getLogger(__name__)

ASSEMBLER_SYSTEM_PROMPT = """\
You are a research triage assistant. Given a paper's title and abstract, plus:
- Novelty assessment (score, novel contributions, overlap with prior art)
- Relevance to the researcher's local work (their drafts/projects)

Produce:
1. A one-line summary:
   what the paper does, what method it uses, what it achieves
   (1-2 sentences, concise).
2. Why this matters to the researcher:
   1-2 sentences grounded in their local work if possible.
3. Key claims: 3-5 short bullet points of the main claims or contributions.
4. Relevance:
   how relevant is this paper to the researcher's own work?
   One of: high, medium, low, off_topic.
5. Read decision:
   should the researcher read it?
   One of: "read in full", "skim", "skip", "monitor authors".

Consider novelty and local relevance together:
- high novelty + high local relevance -> read in full
- low on both -> skip
- otherwise choose the middle ground appropriately
"""


def _assemble_user_prompt(
    paper: PaperCard,
    novelty_report: NoveltyReport,
    local_overlap_report: LocalOverlapReport,
) -> str:
    parts = [
        f"Title: {paper.title}",
        f"Abstract: {paper.abstract}",
        "",
        "Novelty:",
        f"- Score: {novelty_report.novelty_score:.1f} / 1.0",
    ]
    if novelty_report.novel_contributions:
        parts.append("- Novel contributions:")
        for c in novelty_report.novel_contributions:
            parts.append(f"  - {c}")
    if novelty_report.overlap_notes:
        parts.append(f"- Overlap with prior art: {novelty_report.overlap_notes}")
    parts.append("")
    parts.append("Relevance to researcher's local work:")
    parts.append(f"- Overall relevance: {local_overlap_report.overall_relevance:.1f} / 1.0")
    for m in local_overlap_report.matches:
        parts.append(f"- {m.local_title}: {m.overlap_summary}")
    if not local_overlap_report.matches:
        parts.append("- No local drafts or no overlap.")
    parts.append("")
    parts.append(
        'Return a JSON object with keys: "one_line_summary" (string), '
        '"why_this_matters_to_you" (string), "key_claims" (list of strings), '
        '"relevance" (one of: high, medium, low, off_topic), '
        '"read_decision" (one of: read in full, skim, skip, monitor authors).'
    )
    return "\n".join(parts)


def _parse_relevance(s: str) -> Relevance:
    v = (s or "").strip().lower()
    if v == "high":
        return Relevance.HIGH
    if v == "low":
        return Relevance.LOW
    if v == "off_topic":
        return Relevance.OFF_TOPIC
    return Relevance.MEDIUM


async def _assemble_memo_fields(
    paper: PaperCard,
    novelty_report: NoveltyReport,
    local_overlap_report: LocalOverlapReport,
) -> tuple[str, str, list[str], Relevance, str]:
    """Call LLM to produce summary, personalized reason, claims, relevance, and decision."""
    user_prompt = _assemble_user_prompt(paper, novelty_report, local_overlap_report)
    try:
        raw: dict[str, Any] = await call_llm_json(
            system_prompt=ASSEMBLER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
    except Exception as exc:
        logger.warning("Assembler LLM call failed for '%s': %s", paper.title, exc)
        return (
            "Summary unavailable (LLM error).",
            "Personalized relevance unavailable (LLM error).",
            ["Key claims unavailable."],
            Relevance.MEDIUM,
            "read_decision unavailable",
        )

    one_line = (raw.get("one_line_summary") or "").strip() or "No summary generated."
    why_this_matters = (
        (raw.get("why_this_matters_to_you") or "").strip()
        or "No personalized relevance explanation generated."
    )
    claims_raw = raw.get("key_claims") or []
    if isinstance(claims_raw, list):
        key_claims = [str(c).strip() for c in claims_raw if str(c).strip()]
    else:
        key_claims = []
    if not key_claims:
        key_claims = ["(No key claims extracted)"]

    relevance = _parse_relevance(str(raw.get("relevance", "")))
    read_decision_raw = (raw.get("read_decision") or "").strip().lower()
    if "read in full" in read_decision_raw or read_decision_raw == "read in full":
        read_decision = "read in full"
    elif "skip" in read_decision_raw:
        read_decision = "skip"
    elif "monitor" in read_decision_raw:
        read_decision = "monitor authors"
    else:
        read_decision = "skim"

    return (one_line, why_this_matters, key_claims, relevance, read_decision)


async def run_triage(arxiv_input: str) -> TriageMemo:
    """Run the full triage pipeline for a single paper.

    Steps:
    1. Fetch paper metadata + abstract from arXiv
    2. Fan out to sub-agents in parallel (Retriever, Critic, Novelty Checker)
    3. Assemble results into a TriageMemo

    Args:
        arxiv_input: An arXiv URL or bare ID (e.g. '2301.07041').

    Returns:
        A completed TriageMemo.

    Raises:
        ValueError: If the arXiv ID is invalid or paper not found.
    """
    # Step 1: Fetch paper
    async with ArxivClient() as arxiv:
        paper = await arxiv.fetch_paper(arxiv_input)

    # Step 2: Run sub-agents concurrently
    memo = await _run_agents_and_assemble(paper)

    return memo


async def _run_agents_and_assemble(paper: PaperCard) -> TriageMemo:
    """Run all sub-agents concurrently and assemble the memo.

    Args:
        paper: The fetched PaperCard.

    Returns:
        The assembled TriageMemo.
    """
    retriever = RetrieverAgent()
    novelty = NoveltyCheckerAgent()
    local_overlap_agent = LocalOverlapAgent()

    # Fan out — all active agents run in parallel
    related_papers, novelty_report, local_overlap_report = await asyncio.gather(
        retriever.run(paper),
        novelty.run(paper),
        local_overlap_agent.run(paper),
    )

    # Step 3: Assembler — one LLM call to fuse novelty + local overlap into summary & decision
    one_line_summary, why_this_matters, key_claims, relevance, read_decision = (
        await _assemble_memo_fields(
        paper, novelty_report, local_overlap_report
        )
    )

    memo = TriageMemo(
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        authors=paper.short_authors,
        abstract=paper.abstract,
        relevance=relevance,
        one_line_summary=one_line_summary,
        why_this_matters_to_you=why_this_matters,
        key_claims=key_claims,
        method_critique=None,
        novelty_report=novelty_report,
        related_papers=related_papers,
        read_decision=read_decision,
        tags=paper.categories[:3],
        local_overlap=local_overlap_report,
    )

    return memo
