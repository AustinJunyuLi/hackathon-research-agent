"""Parse research content from enrolled source files."""

from __future__ import annotations

import re
from pathlib import Path

TEX_COMMAND_PATTERN = r"\\{command}\s*\{{"
TEX_ENV_PATTERN = r"\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}"
TEX_MACRO_PATTERN = r"\\[a-zA-Z]+\{([^}]*)\}"
PYTHON_DOCSTRING_PATTERN = (
    r"^(?:#!/.*\n)?(?:#.*\n)*\s*(?:\"\"\"(.*?)\"\"\"|'''(.*?)''')"
)


def parse_tex_file(path: Path) -> dict[str, str] | None:
    """Extract title and abstract from a TeX file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    title = _extract_tex_command(text, "title")
    abstract = _extract_tex_environment(text, "abstract")
    if title is None and abstract is None:
        return None

    return {
        "title": title or path.stem,
        "abstract": abstract or "",
        "source_file": str(path),
    }


def parse_bib_file(path: Path) -> list[str]:
    """Extract title fields from a BibTeX file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    matches = re.findall(
        r"title\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|\"([^\"]*)\")",
        text,
        flags=re.IGNORECASE,
    )
    titles = [first or second for first, second in matches]
    return [title.strip() for title in titles if title.strip()]


def parse_md_file(path: Path) -> dict[str, str] | None:
    """Extract a heading and first few non-empty lines from a Markdown file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    lines = text.strip().splitlines()
    title: str | None = None
    body_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if title is None and stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            continue
        if title is not None and stripped:
            body_lines.append(stripped)
            if len(body_lines) >= 5:
                break

    if title is None:
        return None

    return {
        "title": title,
        "abstract": " ".join(body_lines)[:500],
        "source_file": str(path),
    }


def parse_python_file(path: Path) -> dict[str, str] | None:
    """Extract a meaningful top-level module docstring from a Python file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    match = re.match(PYTHON_DOCSTRING_PATTERN, text, flags=re.DOTALL)
    if match is None:
        return None

    docstring = (match.group(1) or match.group(2) or "").strip()
    if len(docstring) < 20:
        return None

    title = docstring.splitlines()[0].strip()[:100]
    return {
        "title": title,
        "abstract": docstring[:500],
        "source_file": str(path),
    }


def _extract_tex_command(text: str, command: str) -> str | None:
    """Extract content from a TeX command, handling nested braces."""
    match = re.search(TEX_COMMAND_PATTERN.format(command=command), text)
    if match is None:
        return None

    start = match.end()
    depth = 1
    index = start
    while index < len(text) and depth > 0:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1

    content = text[start : index - 1].strip()
    return _normalize_tex_text(content)


def _extract_tex_environment(text: str, env: str) -> str | None:
    """Extract content from a TeX environment."""
    match = re.search(TEX_ENV_PATTERN.format(env=env), text, flags=re.DOTALL)
    if match is None:
        return None

    return _normalize_tex_text(match.group(1).strip())


def _normalize_tex_text(text: str) -> str | None:
    normalized = re.sub(TEX_MACRO_PATTERN, r"\1", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or None
