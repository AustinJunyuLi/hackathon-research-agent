"""Tests for output formatters."""

import json

from triage_agent.formatters import render_json, render_markdown
from triage_agent.models.memo import Relevance, TriageMemo


def _make_sample_memo() -> TriageMemo:
    return TriageMemo(
        arxiv_id="2301.07041",
        title="Test Paper on Testing",
        authors="Smith et al.",
        abstract="We present a novel approach to testing.",
        relevance=Relevance.HIGH,
        one_line_summary="A novel testing framework.",
        key_claims=["Testing is important", "Our method is better"],
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


def test_render_json_is_valid() -> None:
    output = render_json(_make_sample_memo())
    data = json.loads(output)
    assert data["arxiv_id"] == "2301.07041"
    assert data["relevance"] == "high"
