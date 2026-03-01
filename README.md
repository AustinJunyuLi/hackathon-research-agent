# Triage Memo Agent

AI-powered research paper analysis tool that generates structured "Triage Memos" from arXiv papers.

## What It Does

Given an arXiv paper URL or ID, the agent:

1. **Fetches** abstract + metadata from the arXiv API (no PDF parsing)
2. **Retrieves** related papers via Semantic Scholar API
3. **Critiques** methodology and identifies break points
4. **Checks novelty** against closest prior art
5. **Outputs** a structured Triage Memo

## Architecture

```
Input (arXiv URL/ID)
    |
    v
[arXiv Fetcher] -- abstract + metadata --> PaperCard
    |
    v
[Orchestrator] -- fans out to sub-agents in parallel:
    |
    +-- [Retriever Agent]       --> RelatedPapers
    +-- [Critic Agent]          --> MethodCritique
    +-- [Novelty Checker Agent] --> NoveltyReport
    |
    v
[Memo Formatter] -- assembles --> TriageMemo
    |
    v
Output (Markdown / JSON)
```

## Setup

```bash
# Clone and install
git clone <repo-url>
cd hackathon-research-agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
triage <arxiv-url-or-id>
```

## Configuration

Copy `.env.example` to `.env` and set:

- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` — for LLM-based sub-agents
- `SEMANTIC_SCHOLAR_API_KEY` — optional, for higher rate limits

## Usage

```bash
# By arXiv ID
triage 2301.07041

# By URL
triage https://arxiv.org/abs/2301.07041

# Output as JSON
triage 2301.07041 --format json
```

## Future Extensions

- Cron-based daily monitoring of arXiv categories
- Telegram / WhatsApp delivery of daily memos
- Agenda personalization based on research interests
- Batch processing of multiple papers
