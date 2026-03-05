"""Novelty Checker Agent — assesses how novel a paper is vs. prior art.

This agent combines Semantic Scholar data with LLM analysis to determine:
1. How similar the paper is to existing work
2. What genuinely novel contributions it makes
3. Which prior papers overlap most
"""

import logging

from triage_agent.agents.base import BaseAgent
from triage_agent.api.semantic_scholar import SemanticScholarClient
from triage_agent.models.memo import NoveltyReport, RelatedPaper
from triage_agent.models.paper import PaperCard
from triage_agent.utils.llm import call_llm_json


logger = logging.getLogger(__name__)

NOVELTY_SYSTEM_PROMPT = """\
You are a research novelty assessor. Given a target paper's abstract and a list of
related prior papers, assess how novel the target paper's contributions are.

Consider:
1. Does it propose a genuinely new method, or apply existing methods to a new domain?
2. Are the claimed contributions already present in prior work?
3. What is the delta between this paper and the closest prior art?

Be fair — incremental but solid contributions still have value.
Provide a novelty score from 0.0 (entirely derivative) to 1.0 (groundbreaking).
"""

NOVELTY_USER_PROMPT = """\
TARGET PAPER:
Title: {title}
Abstract: {abstract}

CLOSEST PRIOR ART:
{prior_art_list}

Assess the novelty of the target paper relative to the prior art listed above.
Provide:
1. A novelty score (0.0 to 1.0)
2. What genuinely novel contributions this paper makes
3. Where it overlaps with existing work
"""


class NoveltyCheckerAgent(BaseAgent):
    """Assesses paper novelty by comparing against prior art."""

    @property
    def name(self) -> str:
        return "Novelty Checker"

    def __init__(self, max_prior_art: int = 5) -> None:
        self.max_prior_art = max_prior_art

    async def run(self, paper: PaperCard) -> NoveltyReport:
        """Assess the novelty of a paper against prior art.

        Steps:
        1. Search Semantic Scholar for the closest prior art
        2. Use an LLM to compare the target paper's abstract against prior work
        3. Produce a structured NoveltyReport

        Args:
            paper: The target paper to assess.

        Returns:
            A NoveltyReport with novelty score and analysis.
        """
        # Step 1: Find closest prior art via Semantic Scholar
        prior_art: list[RelatedPaper] = []
        try:
            async with SemanticScholarClient() as s2:
                prior_art = await s2.search_similar(
                    paper.title,
                    limit=self.max_prior_art,
                )
        except Exception as exc:  # pragma: no cover - network/pathological errors
            # If Semantic Scholar is unavailable, proceed with empty prior art,
            # but record a warning so users can diagnose missing prior art.
            logger.warning(
                "Semantic Scholar search_similar failed for '%s': %s",
                paper.title,
                exc,
            )
            prior_art = []

        # Step 2: Use LLM to assess novelty
        prior_art_list = "\n".join(
            f"- {p.title} ({p.authors}, {p.year or 'n.d.'})" for p in prior_art
        ) or "(No prior art found)"

        user_prompt = NOVELTY_USER_PROMPT.format(
            title=paper.title,
            abstract=paper.abstract,
            prior_art_list=prior_art_list,
        )

        # LLM backend is selected centrally in utils/llm.py (provider keys
        # when available; OpenClaw runtime fallback otherwise).
        try:
            llm_response = await call_llm_json(
                system_prompt=NOVELTY_SYSTEM_PROMPT,
                user_prompt=(
                    user_prompt
                    + "\n\nReturn a JSON object with keys "
                    "'novelty_score' (float 0-1), "
                    "'novel_contributions' (list of strings), "
                    "and 'overlap_notes' (string)."
                ),
            )

            raw_score = float(llm_response.get("novelty_score", 0.5))
            # Clamp into [0.0, 1.0] to satisfy the Pydantic constraints.
            novelty_score = max(0.0, min(1.0, raw_score))

            contributions = llm_response.get("novel_contributions", [])
            if isinstance(contributions, str):
                contributions = [contributions]
            if not isinstance(contributions, list):
                contributions = []

            overlap_notes = llm_response.get("overlap_notes", "")
            if not isinstance(overlap_notes, str):
                overlap_notes = str(overlap_notes)

            return NoveltyReport(
                novelty_score=novelty_score,
                closest_prior_art=prior_art,
                novel_contributions=contributions,
                overlap_notes=overlap_notes,
            )
        except Exception as exc:  # pragma: no cover - network/pathological errors
            # On any LLM failure, fall back to a neutral report but still
            # include the discovered prior art so downstream consumers have
            # something to work with.
            logger.warning(
                "LLM novelty assessment failed for '%s': %s",
                paper.title,
                exc,
            )
            return NoveltyReport(
                novelty_score=0.5,
                closest_prior_art=prior_art,
                novel_contributions=[],
                overlap_notes="Novelty assessment unavailable due to LLM error.",
            )
