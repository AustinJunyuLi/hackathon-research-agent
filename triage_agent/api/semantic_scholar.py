"""Semantic Scholar API client for finding related papers.

Reference: https://api.semanticscholar.org/api-docs/
"""

import os
from collections.abc import Sequence
from typing import cast

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

    async def get_paper_by_arxiv_id(self, arxiv_id: str) -> dict[str, object] | None:
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
        return _response_json_dict(response)

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
        data = _response_json_dict(response)
        return [
            _s2_to_related_paper(citing_paper)
            for citing_paper in _paper_dicts(data.get("data"), "citingPaper")
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
        data = _response_json_dict(response)
        return [
            _s2_to_related_paper(cited_paper)
            for cited_paper in _paper_dicts(data.get("data"), "citedPaper")
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
        data = _response_json_dict(response)
        return [
            _s2_to_related_paper(paper)
            for paper in _paper_dicts(data.get("data"))
        ]

    async def close(self) -> None:
        """Close the underlying HTTP client if we own it."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "SemanticScholarClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


def _response_json_dict(response: httpx.Response) -> dict[str, object]:
    payload = response.json()
    if isinstance(payload, dict):
        return cast(dict[str, object], payload)
    return {}


def _paper_dicts(items: object, nested_key: str | None = None) -> list[dict[str, object]]:
    if not isinstance(items, Sequence) or isinstance(items, str | bytes):
        return []

    papers: list[dict[str, object]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        paper = item.get(nested_key) if nested_key is not None else item
        if not isinstance(paper, dict):
            continue
        title = paper.get("title")
        if isinstance(title, str) and title:
            papers.append(cast(dict[str, object], paper))
    return papers


def _authors_to_string(authors: object) -> str:
    if not isinstance(authors, Sequence) or isinstance(authors, str | bytes):
        return ""

    names: list[str] = []
    for author in authors[:3]:
        if not isinstance(author, dict):
            continue
        name = author.get("name")
        if isinstance(name, str) and name:
            names.append(name)

    author_str = ", ".join(names)
    if len(authors) > 3 and author_str:
        author_str += " et al."
    return author_str


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _s2_to_related_paper(data: dict[str, object]) -> RelatedPaper:
    """Convert a Semantic Scholar paper dict to a RelatedPaper model."""
    return RelatedPaper(
        title=_optional_str(data.get("title")),
        authors=_authors_to_string(data.get("authors")),
        year=_optional_int(data.get("year")),
        url=_optional_str(data.get("url")),
        citation_count=_optional_int(data.get("citationCount")),
    )
