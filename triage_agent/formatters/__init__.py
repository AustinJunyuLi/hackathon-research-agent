"""Output formatters for Triage Memos."""

from triage_agent.formatters.markdown import render_markdown
from triage_agent.formatters.json_fmt import render_json

__all__ = ["render_markdown", "render_json"]
