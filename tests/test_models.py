"""Tests for Pydantic data models."""

from triage_agent.models.memo import (
    BreakPoint,
    LocalOverlapMatch,
    LocalOverlapReport,
    MethodCritique,
    NoveltyReport,
    RelatedPaper,
    Relevance,
    TriageMemo,
)
from triage_agent.models.paper import PaperCard


def test_paper_card_basic() -> None:
    card = PaperCard(
        arxiv_id="2301.07041",
        title="Test Paper",
        authors=["Alice Smith", "Bob Jones", "Carol White"],
        abstract="This is a test abstract.",
        categories=["cs.CL", "cs.AI"],
        url="https://arxiv.org/abs/2301.07041",
    )
    assert card.primary_category == "cs.CL"
    assert card.short_authors == "Alice Smith et al."


def test_paper_card_two_authors() -> None:
    card = PaperCard(
        arxiv_id="2301.07041",
        title="Test Paper",
        authors=["Alice Smith", "Bob Jones"],
        abstract="Abstract text.",
        url="https://arxiv.org/abs/2301.07041",
    )
    assert card.short_authors == "Alice Smith and Bob Jones"


def test_paper_card_single_author() -> None:
    card = PaperCard(
        arxiv_id="2301.07041",
        title="Test Paper",
        authors=["Alice Smith"],
        abstract="Abstract text.",
        url="https://arxiv.org/abs/2301.07041",
    )
    assert card.short_authors == "Alice Smith"


def test_triage_memo_creation() -> None:
    memo = TriageMemo(
        arxiv_id="2301.07041",
        title="Test Paper",
        authors="Smith et al.",
        abstract="Test abstract.",
        relevance=Relevance.HIGH,
        one_line_summary="A test paper about testing.",
        why_this_matters_to_you="It directly extends the user's active project.",
        key_claims=["Claim 1", "Claim 2"],
        read_decision="read in full",
    )
    assert memo.relevance == Relevance.HIGH
    assert len(memo.key_claims) == 2
    assert memo.why_this_matters_to_you == "It directly extends the user's active project."


def test_local_overlap_match_tracks_relationship_type() -> None:
    match = LocalOverlapMatch(
        local_id="draft-1",
        local_title="Informal Bids",
        relevance=0.92,
        relationship_type="extends_your_work",
        overlap_summary="Uses a closely related bidder-learning setup.",
    )

    assert match.relationship_type == "extends_your_work"


def test_triage_memo_preserves_personalized_local_overlap() -> None:
    memo = TriageMemo(
        arxiv_id="2301.07041",
        title="Test Paper",
        authors="Smith et al.",
        abstract="Test abstract.",
        relevance=Relevance.HIGH,
        one_line_summary="A test paper about testing.",
        why_this_matters_to_you="It offers a method transfer into the user's draft.",
        key_claims=["Claim 1"],
        local_overlap=LocalOverlapReport(
            matches=[
                LocalOverlapMatch(
                    local_id="draft-1",
                    local_title="Informal Bids",
                    relevance=0.88,
                    relationship_type="method_transfer",
                    overlap_summary="The estimator could plug into the existing draft.",
                )
            ],
            overall_relevance=0.88,
        ),
        read_decision="read in full",
    )

    assert memo.local_overlap is not None
    assert memo.local_overlap.matches[0].relationship_type == "method_transfer"


def test_method_critique_with_break_points() -> None:
    critique = MethodCritique(
        summary="Solid methodology with some gaps.",
        strengths=["Good experimental design"],
        break_points=[
            BreakPoint(
                description="Small sample size",
                severity="major",
                location="Section 4",
            )
        ],
        assumptions=["IID data"],
        verdict="Mostly sound.",
    )
    assert len(critique.break_points) == 1
    assert critique.break_points[0].severity == "major"


def test_novelty_report_score_bounds() -> None:
    report = NoveltyReport(
        novelty_score=0.8,
        closest_prior_art=[
            RelatedPaper(
                title="Prior Work",
                authors="Jones et al.",
                year=2022,
            )
        ],
        novel_contributions=["New method"],
    )
    assert 0.0 <= report.novelty_score <= 1.0
    assert len(report.closest_prior_art) == 1
