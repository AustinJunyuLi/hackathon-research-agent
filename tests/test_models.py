"""Tests for Pydantic data models."""

from triage_agent.models.paper import PaperCard
from triage_agent.models.memo import (
    BreakPoint,
    MethodCritique,
    NoveltyReport,
    RelatedPaper,
    Relevance,
    TriageMemo,
)


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
        key_claims=["Claim 1", "Claim 2"],
        read_decision="read in full",
    )
    assert memo.relevance == Relevance.HIGH
    assert len(memo.key_claims) == 2


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
