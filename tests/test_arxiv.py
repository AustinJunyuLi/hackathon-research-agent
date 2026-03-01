"""Tests for arXiv API client."""

import pytest

from triage_agent.api.arxiv import extract_arxiv_id


def test_extract_bare_id() -> None:
    assert extract_arxiv_id("2301.07041") == "2301.07041"


def test_extract_from_abs_url() -> None:
    assert extract_arxiv_id("https://arxiv.org/abs/2301.07041") == "2301.07041"


def test_extract_from_pdf_url() -> None:
    assert extract_arxiv_id("https://arxiv.org/pdf/2301.07041") == "2301.07041"


def test_extract_with_version() -> None:
    assert extract_arxiv_id("2301.07041v2") == "2301.07041v2"


def test_extract_with_whitespace() -> None:
    assert extract_arxiv_id("  2301.07041  ") == "2301.07041"


def test_extract_invalid_raises() -> None:
    with pytest.raises(ValueError, match="Could not extract"):
        extract_arxiv_id("not-an-arxiv-id")


def test_extract_empty_raises() -> None:
    with pytest.raises(ValueError, match="Could not extract"):
        extract_arxiv_id("")
