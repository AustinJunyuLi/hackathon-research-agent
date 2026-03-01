"""Base class for sub-agents."""

from abc import ABC, abstractmethod
from typing import Any

from triage_agent.models.paper import PaperCard


class BaseAgent(ABC):
    """Abstract base for all Triage Memo sub-agents.

    Each sub-agent receives a PaperCard and produces a typed result.
    Sub-agents are designed to run concurrently via asyncio.gather().
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this agent."""
        ...

    @abstractmethod
    async def run(self, paper: PaperCard) -> Any:
        """Execute this agent's analysis on the given paper.

        Args:
            paper: The PaperCard with metadata and abstract.

        Returns:
            Agent-specific result (MethodCritique, NoveltyReport, list[RelatedPaper], etc.)
        """
        ...
