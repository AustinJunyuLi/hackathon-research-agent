"""Semantic Scholar API client for finding related papers.

Reference: https://api.semanticscholar.org/api-docs/
"""

import os

import httpx

from triage_agent.models.memo import RelatedPaper

S2_API_URL = "https://api.semanticscholar.org/graph/v1"

# Fields to request from the S2 API
PAPER_FIELDS = "title,authors,year,url,citationCount,abstract,externalIds"
SEARCH_FIELDS = "title,authors,year,url,citationCount"


class SemanticScholarClient:
    """Async client for the Semantic Scholar Academic Graph API."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
        headers: dict[str, str] = {}
        if api_key:
            headers["x-api-key"] = api_key

        self._client = client or httpx.AsyncClient(
            timeout=30.0,
            headers=headers,
        )
        self._owns_client = client is None

    async def get_paper_by_arxiv_id(self, arxiv_id: str) -> dict | None:
        """Look up a paper on Semantic Scholar by its arXiv ID.

        Args:
            arxiv_id: The arXiv identifier (e.g. '2301.07041').

        Returns:
            Paper data dict, or None if not found.
        """
        response = await self._client.get(
            f"{S2_API_URL}/paper/ARXIV:{arxiv_id}",
            params={"fields": PAPER_FIELDS},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def get_citations(
        self,
        paper_id: str,
        limit: int = 10,
    ) -> list[RelatedPaper]:
        """Get papers that cite the given paper.

        Args:
            paper_id: Semantic Scholar paper ID or arXiv:ID format.
            limit: Maximum number of citations to return.

        Returns:
            List of RelatedPaper objects.
        """
        response = await self._client.get(
            f"{S2_API_URL}/paper/{paper_id}/citations",
            params={"fields": SEARCH_FIELDS, "limit": str(limit)},
        )
        response.raise_for_status()
        data = response.json()
        return [
            _s2_to_related_paper(cite["citingPaper"])
            for cite in data.get("data", [])
            if cite.get("citingPaper", {}).get("title")
        ]

    async def get_references(
        self,
        paper_id: str,
        limit: int = 10,
    ) -> list[RelatedPaper]:
        """Get papers referenced by the given paper.

        Args:
            paper_id: Semantic Scholar paper ID or arXiv:ID format.
            limit: Maximum number of references to return.

        Returns:
            List of RelatedPaper objects.
        """
        response = await self._client.get(
            f"{S2_API_URL}/paper/{paper_id}/references",
            params={"fields": SEARCH_FIELDS, "limit": str(limit)},
        )
        response.raise_for_status()
        data = response.json()
        return [
            _s2_to_related_paper(ref["citedPaper"])
            for ref in data.get("data", [])
            if ref.get("citedPaper", {}).get("title")
        ]

    async def search_similar(
        self,
        query: str,
        limit: int = 10,
    ) -> list[RelatedPaper]:
        """Search for papers similar to a query string.

        Args:
            query: Natural language search query (e.g. paper title or abstract excerpt).
            limit: Maximum number of results.

        Returns:
            List of RelatedPaper objects.
        """
        response = await self._client.get(
            f"{S2_API_URL}/paper/search",
            params={
                "query": query,
                "limit": str(limit),
                "fields": SEARCH_FIELDS,
            },
        )
        response.raise_for_status()
        data = response.json()
        return [
            _s2_to_related_paper(paper)
            for paper in data.get("data", [])
            if paper.get("title")
        ]

    async def close(self) -> None:
        """Close the underlying HTTP client if we own it."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "SemanticScholarClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


def _s2_to_related_paper(data: dict) -> RelatedPaper:
    """Convert a Semantic Scholar paper dict to a RelatedPaper model."""
    authors_list = data.get("authors", [])
    author_str = ", ".join(a.get("name", "") for a in authors_list[:3])
    if len(authors_list) > 3:
        author_str += " et al."

    return RelatedPaper(
        title=data.get("title", ""),
        authors=author_str,
        year=data.get("year"),
        url=data.get("url", ""),
        citation_count=data.get("citationCount"),
    )
