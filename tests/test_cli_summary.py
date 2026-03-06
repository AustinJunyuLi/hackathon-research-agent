"""Tests for batch-summary personalization fields."""

from triage_agent.cli import _build_summary
from triage_agent.models.memo import LocalOverlapMatch, LocalOverlapReport, Relevance, TriageMemo


def test_build_summary_includes_personalized_reason_and_relationships() -> None:
    memo = TriageMemo(
        arxiv_id="2301.07041",
        title="Personalized Paper",
        authors="Smith et al.",
        abstract="Abstract",
        relevance=Relevance.HIGH,
        one_line_summary="Summary",
        why_this_matters_to_you="Useful because it extends the user's ongoing draft.",
        key_claims=["Claim"],
        local_overlap=LocalOverlapReport(
            matches=[
                LocalOverlapMatch(
                    local_id="draft-1",
                    local_title="Informal Bids",
                    relevance=0.94,
                    relationship_type="extends_your_work",
                    overlap_summary="Strong conceptual overlap.",
                )
            ],
            overall_relevance=0.94,
        ),
        read_decision="read in full",
    )

    summary = _build_summary([("2301.07041", memo)])[0]

    assert (
        summary["why_this_matters_to_you"]
        == "Useful because it extends the user's ongoing draft."
    )
    assert summary["local_related"][0]["relationship_type"] == "extends_your_work"
