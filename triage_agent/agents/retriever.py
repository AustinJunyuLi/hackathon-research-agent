"""Retriever Agent — finds related papers via Semantic Scholar.

This agent takes a PaperCard and searches for:
1. Papers that cite it (forward citations)
2. Papers it references (backward references)
3. Semantically similar papers (via title/abstract search)
"""

from triage_agent.agents.base import BaseAgent
from triage_agent.api.semantic_scholar import SemanticScholarClient
from triage_agent.models.memo import RelatedPaper
from triage_agent.models.paper import PaperCard


class RetrieverAgent(BaseAgent):
    """Finds related papers using the Semantic Scholar API."""

    @property
    def name(self) -> str:
        return "Retriever"

    def __init__(self, max_results_per_source: int = 5) -> None:
        self.max_results = max_results_per_source

    async def run(self, paper: PaperCard) -> list[RelatedPaper]:
        """Retrieve related papers from multiple sources.

        Searches Semantic Scholar for:
        - Forward citations (who cited this paper)
        - Backward references (what this paper cites)
        - Semantically similar papers (by title search)

        Results are deduplicated by title and sorted by citation count.

        Args:
            paper: The target paper to find related work for.

        Returns:
            Deduplicated list of RelatedPaper objects.
        """
        related: list[RelatedPaper] = []

        async with SemanticScholarClient() as s2:
            s2_paper_id = f"ARXIV:{paper.arxiv_id}"

            # Fetch from all three sources
            # TODO: Run these three calls concurrently with asyncio.gather
            #       and handle individual failures gracefully

            try:
                citations = await s2.get_citations(s2_paper_id, limit=self.max_results)
                for p in citations:
                    p.relevance_note = "Cites this paper"
                related.extend(citations)
            except Exception:
                pass  # TODO: Log warning

            try:
                references = await s2.get_references(s2_paper_id, limit=self.max_results)
                for p in references:
                    p.relevance_note = "Referenced by this paper"
                related.extend(references)
            except Exception:
                pass  # TODO: Log warning

            try:
                similar = await s2.search_similar(paper.title, limit=self.max_results)
                for p in similar:
                    p.relevance_note = "Semantically similar"
                related.extend(similar)
            except Exception:
                pass  # TODO: Log warning

        # Deduplicate by title (case-insensitive)
        seen_titles: set[str] = set()
        unique: list[RelatedPaper] = []
        for p in related:
            key = p.title.lower().strip()
            if key not in seen_titles:
                seen_titles.add(key)
                unique.append(p)

        # Sort by citation count (highest first), None values last
        unique.sort(key=lambda p: p.citation_count or 0, reverse=True)

        return unique
