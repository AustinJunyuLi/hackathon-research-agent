"""arXiv API client for fetching paper metadata and abstracts.

Uses the arXiv Atom feed API (no authentication required).
Reference: https://info.arxiv.org/help/api/index.html
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from triage_agent.models.paper import PaperCard

# arXiv API endpoint
ARXIV_API_URL = "http://export.arxiv.org/api/query"

# Atom namespace
ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"

# Pattern to extract arXiv ID from various URL formats
ARXIV_ID_PATTERN = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/|^)(\d{4}\.\d{4,5}(?:v\d+)?)"
)


def extract_arxiv_id(input_str: str) -> str:
    """Extract a clean arXiv ID from a URL or raw ID string.

    Args:
        input_str: An arXiv URL (abs or pdf) or a bare arXiv ID.

    Returns:
        The extracted arXiv ID (e.g. '2301.07041').

    Raises:
        ValueError: If no valid arXiv ID can be extracted.
    """
    input_str = input_str.strip()
    match = ARXIV_ID_PATTERN.search(input_str)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract arXiv ID from: {input_str}")


def _parse_entry(entry: ET.Element) -> PaperCard:
    """Parse a single Atom entry element into a PaperCard."""
    def text(tag: str, ns: str = ATOM_NS) -> str:
        el = entry.find(f"{{{ns}}}{tag}")
        return el.text.strip() if el is not None and el.text else ""

    # Extract ID (remove version suffix for canonical ID)
    raw_id = text("id")
    arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id

    # Authors
    authors = [
        name_el.text.strip()
        for author_el in entry.findall(f"{{{ATOM_NS}}}author")
        if (name_el := author_el.find(f"{{{ATOM_NS}}}name")) is not None
        and name_el.text
    ]

    # Categories
    categories = [
        cat.get("term", "")
        for cat in entry.findall(f"{{{ARXIV_NS}}}primary_category")
    ]
    categories += [
        cat.get("term", "")
        for cat in entry.findall(f"{{{ATOM_NS}}}category")
        if cat.get("term", "") not in categories
    ]

    # Dates
    published = None
    pub_text = text("published")
    if pub_text:
        published = datetime.fromisoformat(pub_text.replace("Z", "+00:00"))

    updated = None
    upd_text = text("updated")
    if upd_text:
        updated = datetime.fromisoformat(upd_text.replace("Z", "+00:00"))

    # Links
    url = ""
    pdf_url = ""
    for link in entry.findall(f"{{{ATOM_NS}}}link"):
        if link.get("type") == "text/html":
            url = link.get("href", "")
        elif link.get("title") == "pdf":
            pdf_url = link.get("href", "")

    # Clean up abstract whitespace
    abstract = " ".join(text("summary").split())

    return PaperCard(
        arxiv_id=arxiv_id,
        title=" ".join(text("title").split()),
        authors=authors,
        abstract=abstract,
        categories=categories,
        published=published,
        updated=updated,
        url=url or f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=pdf_url,
    )


class ArxivClient:
    """Async client for the arXiv API."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def fetch_paper(self, arxiv_input: str) -> PaperCard:
        """Fetch metadata for a single paper by arXiv ID or URL.

        Args:
            arxiv_input: An arXiv URL or bare ID string.

        Returns:
            A PaperCard with the paper's metadata and abstract.

        Raises:
            ValueError: If the ID cannot be extracted or paper not found.
            httpx.HTTPError: On network errors.
        """
        arxiv_id = extract_arxiv_id(arxiv_input)
        response = await self._client.get(
            ARXIV_API_URL,
            params={"id_list": arxiv_id, "max_results": "1"},
        )
        response.raise_for_status()

        root = ET.fromstring(response.text)
        entries = root.findall(f"{{{ATOM_NS}}}entry")

        if not entries:
            raise ValueError(f"No paper found for arXiv ID: {arxiv_id}")

        return _parse_entry(entries[0])

    async def search_papers(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance",
    ) -> list[PaperCard]:
        """Search arXiv for papers matching a query.

        Args:
            query: Search query string (supports arXiv query syntax).
            max_results: Maximum number of results to return.
            sort_by: Sort order — 'relevance', 'lastUpdatedDate', or 'submittedDate'.

        Returns:
            List of PaperCard objects.
        """
        response = await self._client.get(
            ARXIV_API_URL,
            params={
                "search_query": query,
                "max_results": str(max_results),
                "sortBy": sort_by,
            },
        )
        response.raise_for_status()

        root = ET.fromstring(response.text)
        entries = root.findall(f"{{{ATOM_NS}}}entry")
        return [_parse_entry(entry) for entry in entries]

    async def close(self) -> None:
        """Close the underlying HTTP client if we own it."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "ArxivClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
