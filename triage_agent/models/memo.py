"""Data models for the Triage Memo output and sub-agent results."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Relevance(StrEnum):
    """How relevant the paper is to the user's research agenda."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OFF_TOPIC = "off_topic"


class BreakPoint(BaseModel):
    """A specific weakness or failure mode identified in the paper."""

    description: str = Field(description="What the weakness is")
    severity: str = Field(description="How serious: 'critical', 'major', 'minor'")
    location: str = Field(
        default="",
        description="Where in the paper this issue appears (e.g. 'Section 3', 'Assumption 2')",
    )


class MethodCritique(BaseModel):
    """Output of the Critic sub-agent: methodology analysis."""

    summary: str = Field(description="One-paragraph summary of the methodology")
    strengths: list[str] = Field(default_factory=list, description="Key methodological strengths")
    break_points: list[BreakPoint] = Field(
        default_factory=list,
        description="Identified weaknesses and failure modes",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Key assumptions the results depend on",
    )
    verdict: str = Field(
        default="",
        description="Overall assessment of methodological soundness",
    )


class RelatedPaper(BaseModel):
    """A related paper found by the Retriever sub-agent."""

    title: str = Field(description="Paper title")
    authors: str = Field(description="Author string")
    year: int | None = Field(default=None, description="Publication year")
    url: str = Field(default="", description="URL to the paper")
    relevance_note: str = Field(
        default="",
        description="Why this paper is relevant to the target paper",
    )
    citation_count: int | None = Field(default=None, description="Number of citations")


class NoveltyReport(BaseModel):
    """Output of the Novelty Checker sub-agent."""

    novelty_score: float = Field(
        ge=0.0,
        le=1.0,
        description="0.0 = entirely derivative, 1.0 = completely novel",
    )
    closest_prior_art: list[RelatedPaper] = Field(
        default_factory=list,
        description="Papers most similar to the target paper",
    )
    novel_contributions: list[str] = Field(
        default_factory=list,
        description="What this paper contributes beyond prior work",
    )
    overlap_notes: str = Field(
        default="",
        description="Description of overlap with existing work",
    )


class LocalOverlapMatch(BaseModel):
    """A match between the target paper and a local draft/paper."""

    local_id: str = Field(description="ID of the local paper/draft from the manifest")
    local_title: str = Field(description="Title of the local paper/draft")
    relevance: float = Field(
        ge=0.0,
        le=1.0,
        description="How relevant this target paper is to the local draft (0.0–1.0)",
    )
    relationship_type: str = Field(
        default="related",
        description=(
            "Normalized relationship label, e.g. extends_your_work, "
            "competes_with_your_idea, method_transfer, citation_candidate, "
            "background_context, same_problem_different_method, or related"
        ),
    )
    overlap_summary: str = Field(
        description=(
            "Short natural-language summary of how this paper overlaps "
            "with the local draft"
        ),
    )


class LocalOverlapReport(BaseModel):
    """Overlap between the target paper and the user's local drafts/papers."""

    matches: list[LocalOverlapMatch] = Field(
        default_factory=list,
        description="Per-local-paper overlap and relevance assessments",
    )
    overall_relevance: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Overall relevance of the target paper to the user's local work (0.0–1.0)",
    )


class TriageMemo(BaseModel):
    """The final structured output: a complete Triage Memo for one paper.

    Assembled from the PaperCard and all sub-agent outputs.
    """

    arxiv_id: str = Field(description="arXiv identifier")
    title: str = Field(description="Paper title")
    authors: str = Field(description="Author string")
    abstract: str = Field(description="Full abstract")
    relevance: Relevance = Field(description="Relevance to user's research agenda")
    one_line_summary: str = Field(description="One-sentence summary of the paper's contribution")
    why_this_matters_to_you: str = Field(
        default="",
        description="Short personalized explanation of why the paper matters to the user's work",
    )
    key_claims: list[str] = Field(
        default_factory=list,
        description="Main claims made by the paper",
    )
    method_critique: MethodCritique | None = Field(
        default=None,
        description="Methodology analysis from Critic agent",
    )
    novelty_report: NoveltyReport | None = Field(
        default=None,
        description="Novelty assessment from Novelty Checker agent",
    )
    related_papers: list[RelatedPaper] = Field(
        default_factory=list,
        description="Related papers from Retriever agent",
    )
    local_overlap: LocalOverlapReport | None = Field(
        default=None,
        description="Overlap with user's local drafts (from Local Overlap agent)",
    )
    read_decision: str = Field(
        default="",
        description="Recommendation: 'read in full', 'skim', 'skip', 'monitor authors'",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Topic tags for categorization",
    )
