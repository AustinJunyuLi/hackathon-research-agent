"""Novelty Checker Agent — assesses how novel a paper is vs. prior art.

This agent combines Semantic Scholar data with LLM analysis to determine:
1. How similar the paper is to existing work
2. What genuinely novel contributions it makes
3. Which prior papers overlap most
"""

from triage_agent.agents.base import BaseAgent
from triage_agent.api.semantic_scholar import SemanticScholarClient
from triage_agent.models.memo import NoveltyReport, RelatedPaper
from triage_agent.models.paper import PaperCard

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
        except Exception:
            pass  # TODO: Log warning, proceed with empty prior art

        # Step 2: Use LLM to assess novelty
        # TODO: Implement LLM call
        #
        # Implementation plan:
        # 1. Format prior art into a readable list for the prompt
        # 2. Call LLM with NOVELTY_SYSTEM_PROMPT and NOVELTY_USER_PROMPT
        # 3. Parse structured response into NoveltyReport fields
        #
        # For now, suppress unused variable warnings and return placeholder
        _ = NOVELTY_SYSTEM_PROMPT
        _ = NOVELTY_USER_PROMPT.format(
            title=paper.title,
            abstract=paper.abstract,
            prior_art_list="\n".join(
                f"- {p.title} ({p.authors}, {p.year})" for p in prior_art
            ) or "(No prior art found)",
        )

        return NoveltyReport(
            novelty_score=0.5,  # TODO: LLM-determined score
            closest_prior_art=prior_art,
            novel_contributions=["TODO: LLM-identified novel contributions"],
            overlap_notes="TODO: LLM-generated overlap analysis",
        )
