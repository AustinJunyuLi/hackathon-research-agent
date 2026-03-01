"""JSON formatter for Triage Memos."""

from triage_agent.models.memo import TriageMemo


def render_json(memo: TriageMemo) -> str:
    """Render a TriageMemo as formatted JSON.

    Args:
        memo: The completed TriageMemo to format.

    Returns:
        A JSON string with indentation.
    """
    return memo.model_dump_json(indent=2)
