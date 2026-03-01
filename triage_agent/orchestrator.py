"""Orchestrator — coordinates sub-agents and assembles the Triage Memo.

This is the main pipeline: fetch paper -> fan out to agents -> assemble memo.
"""

import asyncio

from triage_agent.agents.critic import CriticAgent
from triage_agent.agents.novelty import NoveltyCheckerAgent
from triage_agent.agents.retriever import RetrieverAgent
from triage_agent.api.arxiv import ArxivClient
from triage_agent.models.memo import Relevance, TriageMemo
from triage_agent.models.paper import PaperCard


async def run_triage(arxiv_input: str) -> TriageMemo:
    """Run the full triage pipeline for a single paper.

    Steps:
    1. Fetch paper metadata + abstract from arXiv
    2. Fan out to sub-agents in parallel (Retriever, Critic, Novelty Checker)
    3. Assemble results into a TriageMemo

    Args:
        arxiv_input: An arXiv URL or bare ID (e.g. '2301.07041').

    Returns:
        A completed TriageMemo.

    Raises:
        ValueError: If the arXiv ID is invalid or paper not found.
    """
    # Step 1: Fetch paper
    async with ArxivClient() as arxiv:
        paper = await arxiv.fetch_paper(arxiv_input)

    # Step 2: Run sub-agents concurrently
    memo = await _run_agents_and_assemble(paper)

    return memo


async def _run_agents_and_assemble(paper: PaperCard) -> TriageMemo:
    """Run all sub-agents concurrently and assemble the memo.

    Args:
        paper: The fetched PaperCard.

    Returns:
        The assembled TriageMemo.
    """
    retriever = RetrieverAgent()
    critic = CriticAgent()
    novelty = NoveltyCheckerAgent()

    # Fan out — all agents run in parallel
    related_papers, method_critique, novelty_report = await asyncio.gather(
        retriever.run(paper),
        critic.run(paper),
        novelty.run(paper),
    )

    # Step 3: Assemble the memo
    # TODO: Use LLM to generate one_line_summary, key_claims, relevance, read_decision
    #       from the paper abstract + agent outputs. For now, use placeholders.
    memo = TriageMemo(
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        authors=paper.short_authors,
        abstract=paper.abstract,
        relevance=Relevance.MEDIUM,  # TODO: LLM-determined
        one_line_summary="TODO: LLM-generated one-line summary",
        key_claims=["TODO: Extract key claims from abstract"],
        method_critique=method_critique,
        novelty_report=novelty_report,
        related_papers=related_papers,
        read_decision="TODO: LLM-determined read decision",
        tags=paper.categories[:3],
    )

    return memo
