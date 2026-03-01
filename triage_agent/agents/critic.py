"""Critic Agent — analyzes methodology and identifies break points.

This agent uses an LLM to critically evaluate a paper's methodology
based on its abstract. It identifies strengths, weaknesses (break points),
and key assumptions.
"""

from triage_agent.agents.base import BaseAgent
from triage_agent.models.memo import BreakPoint, MethodCritique
from triage_agent.models.paper import PaperCard

CRITIC_SYSTEM_PROMPT = """\
You are a critical research methodology reviewer. Given a paper's title and abstract,
analyze the methodology and identify potential weaknesses.

Be specific, fair, and constructive. Focus on:
1. What methodology is described or implied
2. Key assumptions the results likely depend on
3. Potential break points (weaknesses that could invalidate the results)
4. Overall methodological strengths

Since you only have the abstract, note when your critique is speculative
and would need the full paper to confirm.
"""

CRITIC_USER_PROMPT = """\
Paper: {title}
Authors: {authors}
Categories: {categories}

Abstract:
{abstract}

Please analyze this paper's methodology and provide:
1. A one-paragraph summary of the methodology
2. Key strengths (as a list)
3. Break points / weaknesses (each with severity: critical/major/minor)
4. Key assumptions the results depend on
5. An overall verdict on methodological soundness
"""


class CriticAgent(BaseAgent):
    """Analyzes paper methodology using an LLM."""

    @property
    def name(self) -> str:
        return "Critic"

    async def run(self, paper: PaperCard) -> MethodCritique:
        """Analyze the paper's methodology and identify break points.

        Uses an LLM to evaluate the methodology described in the abstract.
        Returns structured critique with strengths, weaknesses, and assumptions.

        Args:
            paper: The target paper to critique.

        Returns:
            A MethodCritique with the analysis results.
        """
        # TODO: Implement LLM call using the configured provider (OpenAI/Anthropic)
        #
        # Implementation plan:
        # 1. Format the CRITIC_USER_PROMPT with paper details
        # 2. Call the LLM with structured output (JSON mode or function calling)
        # 3. Parse the response into a MethodCritique
        #
        # For now, return a placeholder
        _ = CRITIC_SYSTEM_PROMPT  # Will be used as system message
        _ = CRITIC_USER_PROMPT.format(
            title=paper.title,
            authors=paper.short_authors,
            categories=", ".join(paper.categories),
            abstract=paper.abstract,
        )

        return MethodCritique(
            summary="TODO: LLM-generated methodology summary",
            strengths=["TODO: Identify strengths from abstract"],
            break_points=[
                BreakPoint(
                    description="TODO: LLM-identified weakness",
                    severity="major",
                    location="Abstract",
                )
            ],
            assumptions=["TODO: Extract key assumptions"],
            verdict="TODO: Overall assessment pending LLM integration",
        )
