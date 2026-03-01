"""Data models for paper metadata fetched from arXiv."""

from datetime import datetime

from pydantic import BaseModel, Field


class PaperCard(BaseModel):
    """Core metadata for a single research paper.

    Populated from the arXiv API response. This is the primary input
    to all downstream sub-agents.
    """

    arxiv_id: str = Field(description="arXiv identifier (e.g. '2301.07041')")
    title: str = Field(description="Paper title")
    authors: list[str] = Field(description="List of author names")
    abstract: str = Field(description="Full abstract text")
    categories: list[str] = Field(
        default_factory=list,
        description="arXiv categories (e.g. ['cs.CL', 'cs.AI'])",
    )
    published: datetime | None = Field(
        default=None,
        description="Publication date",
    )
    updated: datetime | None = Field(
        default=None,
        description="Last updated date",
    )
    url: str = Field(description="URL to the arXiv abstract page")
    pdf_url: str = Field(default="", description="URL to the PDF (for reference only)")

    @property
    def primary_category(self) -> str:
        """Return the first (primary) arXiv category."""
        return self.categories[0] if self.categories else "unknown"

    @property
    def short_authors(self) -> str:
        """Return abbreviated author string (e.g. 'Smith et al.')."""
        if len(self.authors) == 1:
            return self.authors[0]
        if len(self.authors) == 2:
            return f"{self.authors[0]} and {self.authors[1]}"
        return f"{self.authors[0]} et al."
