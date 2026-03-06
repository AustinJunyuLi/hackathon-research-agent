"""Tests for output formatters."""

import json

from triage_agent.formatters import render_json, render_markdown
from triage_agent.models.memo import LocalOverlapMatch, LocalOverlapReport, Relevance, TriageMemo


def _make_sample_memo() -> TriageMemo:
    return TriageMemo(
        arxiv_id="2301.07041",
        title="Test Paper on Testing",
        authors="Smith et al.",
        abstract="We present a novel approach to testing.",
        relevance=Relevance.HIGH,
        one_line_summary="A novel testing framework.",
        why_this_matters_to_you=(
            "Relevant to your Informal Bids draft because it extends the same learning "
            "problem with a cleaner identification strategy."
        ),
        key_claims=["Testing is important", "Our method is better"],
        local_overlap=LocalOverlapReport(
            matches=[
                LocalOverlapMatch(
                    local_id="draft-1",
                    local_title="Informal Bids",
                    relevance=0.93,
                    relationship_type="extends_your_work",
                    overlap_summary="Targets the same economic setting with a stronger estimator.",
                )
            ],
            overall_relevance=0.93,
        ),
        read_decision="read in full",
        tags=["cs.SE", "cs.AI"],
    )


def test_render_markdown_contains_title() -> None:
    output = render_markdown(_make_sample_memo())
    assert "Test Paper on Testing" in output
    assert "# Triage Memo" in output


def test_render_markdown_contains_key_sections() -> None:
    output = render_markdown(_make_sample_memo())
    assert "Key Claims" in output
    assert "Abstract" in output
    assert "read in full" in output


def test_render_markdown_contains_personalized_relevance_section() -> None:
    output = render_markdown(_make_sample_memo())

    assert "Why This Matters To You" in output
    assert "extends your work" in output
    assert "Informal Bids" in output


def test_render_json_is_valid() -> None:
    output = render_json(_make_sample_memo())
    data = json.loads(output)
    assert data["arxiv_id"] == "2301.07041"
    assert data["relevance"] == "high"
    assert "why_this_matters_to_you" in data
    assert data["local_overlap"]["matches"][0]["relationship_type"] == "extends_your_work"
