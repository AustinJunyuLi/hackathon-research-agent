"""Tests for enrolled-source content parsers."""

from __future__ import annotations

from triage_agent.sources.parsers import (
    parse_bib_file,
    parse_md_file,
    parse_python_file,
    parse_tex_file,
)


def test_parse_tex_file_extracts_title_and_abstract(tmp_path) -> None:
    tex_path = tmp_path / "paper.tex"
    tex_path.write_text(
        r"""
\title{My Great Paper}
\begin{abstract}
This paper studies something important about economics.
\end{abstract}
""".strip()
    )

    result = parse_tex_file(tex_path)

    assert result is not None
    assert result["title"] == "My Great Paper"
    assert "economics" in result["abstract"]


def test_parse_bib_file_extracts_titles(tmp_path) -> None:
    bib_path = tmp_path / "refs.bib"
    bib_path.write_text(
        """
@article{smith2024,
  title = {A Study of Markets},
  author = {Smith, John},
  year = {2024}
}
@inproceedings{doe2023,
  title = "Machine Learning for Auctions",
  author = "Doe, Jane"
}
""".strip()
    )

    titles = parse_bib_file(bib_path)

    assert len(titles) == 2
    assert "A Study of Markets" in titles
    assert "Machine Learning for Auctions" in titles


def test_parse_md_file_extracts_heading_and_body(tmp_path) -> None:
    md_path = tmp_path / "notes.md"
    md_path.write_text(
        "# Research Notes\n\nThis is about my ongoing work.\nMore details here.\n"
    )

    result = parse_md_file(md_path)

    assert result is not None
    assert result["title"] == "Research Notes"
    assert "ongoing work" in result["abstract"]


def test_parse_python_file_extracts_docstring(tmp_path) -> None:
    py_path = tmp_path / "analysis.py"
    py_path.write_text(
        '"""Analysis of procurement auction data.\n\nThis module processes bid data.\n"""\n'
        "import pandas\n"
    )

    result = parse_python_file(py_path)

    assert result is not None
    assert "procurement" in result["title"].lower() or "procurement" in result["abstract"].lower()


def test_parse_tex_file_returns_none_without_research_content(tmp_path) -> None:
    tex_path = tmp_path / "bare.tex"
    tex_path.write_text(r"\documentclass{article}\begin{document}Hello\end{document}")

    assert parse_tex_file(tex_path) is None
