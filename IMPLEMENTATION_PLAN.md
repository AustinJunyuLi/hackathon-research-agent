# Triage Memo Agent -- Implementation Plan

**Hackathon:** UK AI Agent Hack Ep4 (Mar 1-7, 2026)
**Team:** Austin + teammate
**Approach:** Abstract-only (no PDF parsing). Given an arXiv paper ID/URL, produce a structured "Triage Memo" with methodology critique, novelty assessment, and related work.

---

## 1. Architecture Overview

```
                          +---------------------+
                          |   CLI / OpenClaw     |
                          |   triage <arxiv-id>  |
                          +----------+----------+
                                     |
                                     v
                          +----------+----------+
                          |   ArxivClient        |
                          |   fetch_paper()      |
                          |   -> PaperCard       |
                          +----------+----------+
                                     |
                                     v
                          +----------+----------+
                          |   Orchestrator       |
                          |   run_triage()       |
                          +----------+----------+
                                     |
                       +-------------+-------------+
                       |             |             |
                       v             v             v
              +--------+---+ +------+------+ +----+--------+
              | Retriever  | |   Critic    | |  Novelty    |
              | Agent      | |   Agent     | |  Checker    |
              +--------+---+ +------+------+ +----+--------+
              |  S2 API    | |  LLM call   | | S2 API +    |
              |  citations | |  structured | | LLM call    |
              |  refs      | |  output     | | compare     |
              |  similar   | |             | | prior art   |
              +--------+---+ +------+------+ +----+--------+
                       |             |             |
                       v             v             v
                  list[Related] MethodCritique  NoveltyReport
                       |             |             |
                       +-------------+-------------+
                                     |
                                     v
                          +----------+----------+
                          |   Assembler (LLM)   |
                          |   one_line_summary   |
                          |   key_claims         |
                          |   relevance          |
                          |   read_decision      |
                          +----------+----------+
                                     |
                                     v
                          +----------+----------+
                          |   Formatter          |
                          |   Markdown / JSON    |
                          +----------+----------+
                                     |
                                     v
                              TriageMemo output
```

**Data flow summary:**
1. User provides arXiv ID or URL
2. `ArxivClient` fetches metadata + abstract from the arXiv Atom API (no auth needed)
3. `Orchestrator` fans out to 3 sub-agents in parallel via `asyncio.gather()`
4. Each sub-agent produces a typed result (Pydantic model)
5. An assembler LLM call synthesizes the final memo fields (summary, claims, relevance, decision)
6. Formatter renders the `TriageMemo` as Markdown or JSON

---

## 2. Data Models

All models are Pydantic v2 BaseModels in `triage_agent/models/`.

### 2.1 PaperCard (`models/paper.py`) -- DONE in skeleton

```python
class PaperCard(BaseModel):
    arxiv_id: str           # e.g. "2301.07041"
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]   # e.g. ["cs.CL", "cs.AI"]
    published: datetime | None
    updated: datetime | None
    url: str                # https://arxiv.org/abs/...
    pdf_url: str            # for reference only
```

**Properties:** `primary_category`, `short_authors` (e.g. "Smith et al.")

### 2.2 MethodCritique, NoveltyReport, TriageMemo (`models/memo.py`) -- DONE in skeleton

Key fields already defined:
- `MethodCritique`: summary, strengths, break_points (list[BreakPoint]), assumptions, verdict
- `NoveltyReport`: novelty_score (0.0-1.0), closest_prior_art, novel_contributions, overlap_notes
- `TriageMemo`: arxiv_id, title, authors, abstract, relevance (enum), one_line_summary, key_claims, method_critique, novelty_report, related_papers, read_decision, tags

### 2.3 AgendaProfile (stretch goal)

```python
class AgendaProfile(BaseModel):
    name: str                          # "Austin's Research Agenda"
    topics: list[str]                  # ["causal inference", "LLM evaluation"]
    arxiv_categories: list[str]        # ["cs.CL", "stat.ML", "econ.EM"]
    keywords: list[str]               # ["treatment effects", "instrumental variables"]
    authors_of_interest: list[str]     # ["Imbens", "Athey"]
    relevance_prompt: str              # Custom prompt for relevance scoring
```

This is a **stretch goal**. Not needed for MVP. If implemented, store as a YAML/JSON config file the user can edit.

---

## 3. API Integrations

### 3.1 arXiv API (`api/arxiv.py`) -- DONE in skeleton

**Endpoint:** `http://export.arxiv.org/api/query`
**Auth:** None required
**Rate limit:** 1 request per 3 seconds, single connection

**Fetch a single paper by ID:**
```
GET http://export.arxiv.org/api/query?id_list=2301.07041&max_results=1
```

**Search by query (for batch/monitoring stretch goal):**
```
GET http://export.arxiv.org/api/query?search_query=cat:cs.CL+AND+submittedDate:[20260301+TO+20260307]&sortBy=submittedDate&max_results=50
```

**Response format:** Atom 1.0 XML. Key fields per entry:
- `<title>` -- paper title
- `<summary>` -- abstract
- `<author><name>` -- author names
- `<arxiv:primary_category term="cs.CL">`
- `<published>`, `<updated>` -- ISO dates
- `<link title="pdf" href="...">` -- PDF URL

**Implementation status:** COMPLETE. The `ArxivClient` class handles:
- `fetch_paper(arxiv_input)` -- fetch single paper by ID/URL
- `search_papers(query, max_results, sort_by)` -- search papers
- XML parsing into `PaperCard` via `_parse_entry()`
- arXiv ID extraction from various URL formats

### 3.2 Semantic Scholar API (`api/semantic_scholar.py`) -- DONE in skeleton

**Base URL:** `https://api.semanticscholar.org/graph/v1`
**Auth:** Optional `x-api-key` header for higher rate limits. Without key: 1000 req/s shared pool.
**API key:** Request at https://www.semanticscholar.org/product/api#api-key-form

**Endpoints used:**

| Purpose | Endpoint | Method |
|---------|----------|--------|
| Look up paper by arXiv ID | `/paper/ARXIV:{arxiv_id}?fields=...` | GET |
| Get papers that cite it | `/paper/{id}/citations?fields=...&limit=10` | GET |
| Get referenced papers | `/paper/{id}/references?fields=...&limit=10` | GET |
| Search similar papers | `/paper/search?query=...&fields=...&limit=10` | GET |
| Get recommendations | `/recommendations/v1/papers/forpaper/{id}?limit=10` | GET |

**Useful paper fields to request:**
```
title,authors,year,url,citationCount,abstract,externalIds
```

**Example: look up a paper by arXiv ID:**
```
GET https://api.semanticscholar.org/graph/v1/paper/ARXIV:2301.07041?fields=title,authors,year,citationCount,abstract
```

**Example response (abbreviated):**
```json
{
  "paperId": "abc123...",
  "title": "Some Paper Title",
  "abstract": "We propose...",
  "year": 2023,
  "authors": [{"authorId": "1234", "name": "John Smith"}],
  "citationCount": 42
}
```

**Recommendations API (stretch goal):**
```
GET https://api.semanticscholar.org/recommendations/v1/papers/forpaper/ARXIV:2301.07041?limit=10&fields=title,authors,year,url
```

Or batch with positive/negative examples:
```
POST https://api.semanticscholar.org/recommendations/v1/papers/
Body: {"positivePaperIds": ["ARXIV:2301.07041"], "negativePaperIds": []}
```

**Implementation status:** COMPLETE. The `SemanticScholarClient` class handles:
- `get_paper_by_arxiv_id()` -- look up paper
- `get_citations()` -- forward citations
- `get_references()` -- backward references
- `search_similar()` -- keyword search

**TODO:** Add `get_recommendations()` method using the Recommendations API endpoint. This is better for finding similar papers than keyword search.

---

## 4. Sub-Agent Design

All agents extend `BaseAgent` (in `agents/base.py`), which defines:
```python
class BaseAgent(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def run(self, paper: PaperCard) -> Any: ...
```

### 4.1 Retriever Agent (`agents/retriever.py`) -- skeleton DONE, needs parallelization

**Purpose:** Find related papers from multiple sources.

**Input:** `PaperCard`
**Output:** `list[RelatedPaper]`

**Logic:**
1. Construct S2 paper ID: `ARXIV:{paper.arxiv_id}`
2. Run 3 queries in parallel via `asyncio.gather()`:
   - `s2.get_citations(id, limit=5)` -- who cites this paper
   - `s2.get_references(id, limit=5)` -- what this paper cites
   - `s2.search_similar(paper.title, limit=5)` -- semantically similar
3. Tag each result with `relevance_note` ("Cites this paper", "Referenced by this paper", "Semantically similar")
4. Deduplicate by title (case-insensitive)
5. Sort by citation count (descending)
6. Return top N results

**What needs to be implemented:**
- Change the 3 sequential S2 calls to `asyncio.gather()` with `return_exceptions=True`
- Add logging for failed calls instead of bare `pass`
- Consider adding the Recommendations API as a 4th source

### 4.2 Critic Agent (`agents/critic.py`) -- skeleton DONE, LLM call TODO

**Purpose:** Analyze methodology and identify break points.

**Input:** `PaperCard`
**Output:** `MethodCritique`

**Logic:**
1. Format the system prompt (already defined in skeleton as `CRITIC_SYSTEM_PROMPT`)
2. Format the user prompt with paper details (title, authors, categories, abstract)
3. Call LLM with JSON mode requesting structured output
4. Parse response into `MethodCritique` fields

**LLM prompt structure (already in skeleton):**
- System: "You are a critical research methodology reviewer..."
- User: Paper details + "Please analyze this paper's methodology and provide: summary, strengths, break points (with severity), assumptions, verdict"

**What needs to be implemented:**
```python
async def run(self, paper: PaperCard) -> MethodCritique:
    user_prompt = CRITIC_USER_PROMPT.format(
        title=paper.title,
        authors=paper.short_authors,
        categories=", ".join(paper.categories),
        abstract=paper.abstract,
    )

    # Add JSON schema instruction to the prompt
    json_instruction = """
    Respond with a JSON object matching this schema:
    {
        "summary": "one paragraph methodology summary",
        "strengths": ["strength 1", "strength 2"],
        "break_points": [
            {"description": "...", "severity": "critical|major|minor", "location": "..."}
        ],
        "assumptions": ["assumption 1", "assumption 2"],
        "verdict": "overall assessment"
    }
    """

    result = await call_llm_json(
        system_prompt=CRITIC_SYSTEM_PROMPT,
        user_prompt=user_prompt + json_instruction,
    )

    return MethodCritique(
        summary=result["summary"],
        strengths=result.get("strengths", []),
        break_points=[BreakPoint(**bp) for bp in result.get("break_points", [])],
        assumptions=result.get("assumptions", []),
        verdict=result.get("verdict", ""),
    )
```

### 4.3 Novelty Checker Agent (`agents/novelty.py`) -- skeleton DONE, LLM call TODO

**Purpose:** Assess novelty by comparing against prior art.

**Input:** `PaperCard`
**Output:** `NoveltyReport`

**Logic:**
1. Search Semantic Scholar for closest prior art (by title)
2. Format prior art list into the prompt
3. Call LLM to compare target paper vs. prior art
4. Parse response into `NoveltyReport`

**What needs to be implemented:**
```python
async def run(self, paper: PaperCard) -> NoveltyReport:
    # Step 1: Find prior art
    prior_art: list[RelatedPaper] = []
    try:
        async with SemanticScholarClient() as s2:
            prior_art = await s2.search_similar(paper.title, limit=self.max_prior_art)
    except Exception as e:
        logger.warning(f"S2 search failed: {e}")

    # Step 2: Format prior art for prompt
    prior_art_text = "\n".join(
        f"- {p.title} ({p.authors}, {p.year})" for p in prior_art
    ) or "(No prior art found)"

    user_prompt = NOVELTY_USER_PROMPT.format(
        title=paper.title,
        abstract=paper.abstract,
        prior_art_list=prior_art_text,
    )

    json_instruction = """
    Respond with a JSON object:
    {
        "novelty_score": 0.0-1.0,
        "novel_contributions": ["contribution 1", ...],
        "overlap_notes": "description of overlap"
    }
    """

    result = await call_llm_json(
        system_prompt=NOVELTY_SYSTEM_PROMPT,
        user_prompt=user_prompt + json_instruction,
    )

    return NoveltyReport(
        novelty_score=result["novelty_score"],
        closest_prior_art=prior_art,
        novel_contributions=result.get("novel_contributions", []),
        overlap_notes=result.get("overlap_notes", ""),
    )
```

### 4.4 Orchestrator Assembly Step -- TODO

After all 3 agents return, the orchestrator needs one more LLM call to generate the synthesis fields:

```python
ASSEMBLER_SYSTEM_PROMPT = """\
You are a research paper triage assistant. Given a paper's abstract and analysis
from specialist agents, produce a final triage summary.
"""

ASSEMBLER_USER_PROMPT = """\
PAPER: {title}
ABSTRACT: {abstract}

METHODOLOGY VERDICT: {method_verdict}
NOVELTY SCORE: {novelty_score}/1.0
RELATED PAPERS FOUND: {num_related}

Based on the above, provide:
1. one_line_summary: A single sentence capturing the paper's main contribution
2. key_claims: 2-4 bullet points of the paper's main claims (from the abstract)
3. relevance: "high", "medium", "low", or "off_topic"
4. read_decision: "read in full", "skim", "skip", or "monitor authors"

Respond as JSON:
{{
    "one_line_summary": "...",
    "key_claims": ["...", "..."],
    "relevance": "high|medium|low|off_topic",
    "read_decision": "read in full|skim|skip|monitor authors"
}}
"""
```

---

## 5. Memo Template -- Exact Output Format

### Markdown Output (what the user sees)

```markdown
# Triage Memo: Attention Is All You Need

**Authors:** Vaswani et al.
**arXiv:** [1706.03762](https://arxiv.org/abs/1706.03762)
**Relevance:** HIGH
**Decision:** Read in full
**Tags:** cs.CL, cs.AI

> Proposes the Transformer architecture, replacing recurrence with self-attention for sequence transduction.

## Key Claims
- Self-attention alone is sufficient for sequence-to-sequence tasks
- Transformers achieve SOTA on WMT translation benchmarks
- Training is significantly more parallelizable than RNNs

## Abstract
[Full abstract text here]

## Methodology Critique
[One paragraph methodology summary]

### Strengths
- Large-scale empirical validation on standard benchmarks
- Clear ablation studies isolating each component's contribution

### Break Points
- [!] **CRITICAL** (Assumption 2): Assumes fixed-length positional encodings scale to arbitrary sequence lengths
- [*] **MAJOR** (Section 3): Quadratic memory complexity in attention limits practical sequence length

### Key Assumptions
- Attention patterns can capture all relevant sequential dependencies
- Positional encoding is sufficient to represent order

**Verdict:** Methodologically sound with well-designed experiments, but scalability claims need qualification.

## Novelty Assessment
**Novelty Score:** 0.9 / 1.0

### Novel Contributions
- First architecture to achieve competitive results using only attention (no recurrence or convolution)
- Multi-head attention mechanism as a general-purpose sequence modeling primitive

### Overlap with Prior Work
Builds on earlier attention mechanisms (Bahdanau et al., 2014) but makes the architectural leap of removing recurrence entirely.

### Closest Prior Art
- Neural Machine Translation by Jointly Learning to Align and Translate (2014) -- Bahdanau et al. [12000 citations]
- Sequence to Sequence Learning with Neural Networks (2014) -- Sutskever et al. [9500 citations]

## Related Papers
- BERT: Pre-training of Deep Bidirectional Transformers (2018) -- *Cites this paper*
- GPT-2: Language Models are Unsupervised Multitask Learners (2019) -- *Cites this paper*
- Convolutional Sequence to Sequence Learning (2017) -- *Referenced by this paper*

---
*Generated by Triage Memo Agent*
```

### JSON Output

The JSON output is the Pydantic model serialized via `model_dump_json(indent=2)`, which produces a complete JSON representation of the `TriageMemo` model.

---

## 6. Day-by-Day Build Plan (Mar 1-7)

### Day 1 (Saturday, Mar 1) -- Foundation
**Goal:** Working end-to-end pipeline with placeholder LLM calls.

| Task | Owner | Est. Time | Status |
|------|-------|-----------|--------|
| Set up repo, install deps, verify skeleton runs | Both | 30 min | Skeleton ready |
| Implement + test `ArxivClient.fetch_paper()` against live API | A | 1 hr | Done in skeleton |
| Implement + test `SemanticScholarClient` methods against live API | B | 1 hr | Done in skeleton |
| Wire up orchestrator with placeholder agents | A | 30 min | Done in skeleton |
| Test full pipeline end-to-end with a real arXiv ID | Both | 30 min | **TODO** |

**Day 1 deliverable:** `triage 2301.07041` runs and prints a placeholder memo with real metadata from arXiv and real related papers from S2.

### Day 2 (Sunday, Mar 2) -- LLM Integration
**Goal:** All three sub-agents produce real LLM-generated analysis.

| Task | Owner | Est. Time |
|------|-------|-----------|
| Implement `call_llm()` and `call_llm_json()` in `utils/llm.py` | A | 1 hr |
| Implement Critic Agent LLM call with JSON structured output | A | 1.5 hr |
| Implement Novelty Checker LLM call (S2 search + LLM compare) | B | 1.5 hr |
| Parallelize Retriever's 3 S2 calls with `asyncio.gather()` | B | 30 min |
| Implement Assembler LLM call in orchestrator | A | 1 hr |
| End-to-end test: verify memo quality on 3 different papers | Both | 1 hr |

**Day 2 deliverable:** `triage 2301.07041` produces a fully populated, high-quality memo.

### Day 3 (Monday, Mar 3) -- Quality + Error Handling
**Goal:** Production-quality error handling, prompt tuning, output polish.

| Task | Owner | Est. Time |
|------|-------|-----------|
| Add retry logic for API calls (httpx retries, backoff) | A | 1 hr |
| Add logging throughout (replace bare `except: pass`) | A | 30 min |
| Tune Critic prompts -- test on 5+ papers, refine severity calibration | B | 2 hr |
| Tune Novelty prompts -- test prior art matching accuracy | B | 1 hr |
| Add `--verbose` flag to CLI for debugging | A | 30 min |
| Write unit tests for models and formatters | A | 1 hr |

**Day 3 deliverable:** Robust pipeline that handles edge cases (paper not on S2, API timeouts, malformed abstracts).

### Day 4 (Tuesday, Mar 4) -- OpenClaw Skill Integration
**Goal:** Package as an OpenClaw skill.

| Task | Owner | Est. Time |
|------|-------|-----------|
| Create `SKILL.md` with frontmatter and instructions | A | 1 hr |
| Create `openclaw.json` config entry | A | 30 min |
| Test skill loading in OpenClaw: `openclaw skills list` | A | 30 min |
| Test invocation: "Triage this paper: 2301.07041" in OpenClaw | Both | 1 hr |
| Add Recommendations API to Retriever as 4th source | B | 1 hr |

**Day 4 deliverable:** Working OpenClaw skill that responds to natural language requests.

### Day 5 (Wednesday, Mar 5) -- Stretch Goals
**Goal:** Add agenda personalization and batch mode.

| Task | Owner | Est. Time |
|------|-------|-----------|
| Implement `AgendaProfile` model and YAML config loader | A | 1 hr |
| Add relevance scoring against user's research agenda | A | 1.5 hr |
| Add batch mode: `triage --category cs.CL --days 1` | B | 2 hr |
| Add daily digest formatter (multiple memos in one output) | B | 1 hr |

**Day 5 deliverable:** Personalized triage memos that score relevance to the user's research interests.

### Day 6 (Thursday, Mar 6) -- Demo Prep + Polish
**Goal:** Demo-ready presentation.

| Task | Owner | Est. Time |
|------|-------|-----------|
| Write demo script (see Section 7) | Both | 1 hr |
| Record backup demo video (in case of live demo failure) | Both | 1 hr |
| Polish Markdown output formatting | A | 30 min |
| Add `--output` file writing with nice filename generation | A | 30 min |
| Final bug fixes and edge case testing | Both | 2 hr |
| Write/update README with screenshots | B | 1 hr |

**Day 6 deliverable:** Polished demo with backup recording.

### Day 7 (Friday, Mar 7) -- Submission
**Goal:** Submit and present.

| Task | Owner | Est. Time |
|------|-------|-----------|
| Final testing on fresh machine (clone + install + run) | A | 1 hr |
| Record final demo if needed | Both | 30 min |
| Write submission description | B | 30 min |
| Submit project | Both | 15 min |
| Practice 2-minute pitch | Both | 30 min |
| Present to judges | Both | -- |

---

## 7. Demo Script (2 Minutes)

### Setup (before demo starts)
- Terminal open with the project directory
- `.env` configured with API keys
- One "impressive" paper ready (a well-known, highly-cited paper works best -- e.g. "Attention Is All You Need")

### Script

**[0:00-0:15] Hook**
"Every week, hundreds of papers drop on arXiv. Researchers waste hours skimming abstracts. Our Triage Memo Agent reads the abstract for you and tells you whether a paper is worth your time -- in 30 seconds."

**[0:15-0:30] Live demo -- single paper**
```bash
triage 1706.03762
```
(While it runs, explain: "It fetches the abstract from arXiv, finds related papers on Semantic Scholar, and runs three AI sub-agents in parallel -- a methodology critic, a novelty checker, and a related work retriever.")

**[0:30-1:00] Show the output**
Scroll through the memo. Highlight:
- The one-line summary and read decision ("Read in full" vs "Skip")
- The break points with severity levels
- The novelty score and closest prior art
- "All from just the abstract -- no PDF parsing needed."

**[1:00-1:20] Architecture explanation**
Show the ASCII diagram from the README.
"Three sub-agents run in parallel. The Critic uses an LLM to identify methodological weaknesses. The Novelty Checker searches Semantic Scholar for prior art and compares. The Retriever finds citing and cited papers."

**[1:20-1:40] Stretch: batch / personalized (if implemented)**
```bash
triage --category cs.CL --days 1 --agenda my_agenda.yaml
```
"You can also monitor entire arXiv categories. It filters papers against your research agenda and only surfaces what matters to you."

**[1:40-2:00] Closing**
"Built as an OpenClaw skill. Install it once, then just ask your AI assistant: 'Triage this paper.' We plan to add daily email digests and citation graph visualization. The Triage Memo Agent -- your personal research paper screener."

---

## 8. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Semantic Scholar API rate limit / downtime** | Medium | High | Cache S2 responses locally (dict/file cache). Fall back to arXiv-only mode (skip novelty/related if S2 is down). Use API key for higher limits. |
| 2 | **LLM produces malformed JSON** | Medium | Medium | Wrap `call_llm_json()` with retry (max 2 attempts). Strip markdown fences before parsing (already in skeleton). Add fallback: if JSON fails, return placeholder with error note. |
| 3 | **arXiv API returns no results for valid ID** | Low | Medium | Some very new papers take hours to appear in the API. Show clear error message. For demo, pre-test the paper IDs. |
| 4 | **LLM hallucination in critique/novelty** | Medium | Medium | System prompts explicitly instruct "note when critique is speculative and would need full paper to confirm." Novelty assessment is grounded in actual S2 search results. |
| 5 | **Demo fails live** | Low | Critical | Record a backup demo video on Day 6. Have screenshots ready. Pre-cache a demo run's output as a fallback file. |
| 6 | **OpenClaw skill integration issues** | Medium | Medium | Start integration on Day 4 (not last day). If skill framework is problematic, fall back to CLI-only demo. The core value is the pipeline, not the skill wrapper. |
| 7 | **Slow response time (>30s per memo)** | Medium | Low | LLM calls are the bottleneck. All 3 agents already run in parallel. Use faster model (claude-haiku-4-5) if latency is a concern for demo. Pre-warm with a dummy call before demo. |

---

## 9. Stretch Goals (Priority Order)

### 9.1 Agenda Personalization (Day 5)
- Add `AgendaProfile` model with user's research interests
- Load from `~/.triage/agenda.yaml`
- Pass agenda context to the assembler LLM call for relevance scoring
- "HIGH relevance" means it matches the user's declared interests

### 9.2 Batch / Daily Monitoring (Day 5)
- `triage --category cs.CL --days 1` -- fetch recent papers from a category
- Uses arXiv date-range search: `submittedDate:[YYYYMMDD+TO+YYYYMMDD]`
- Generate a "Daily Digest" with multiple memos sorted by relevance
- Stretch-stretch: cron job + email/Telegram delivery

### 9.3 Semantic Scholar Recommendations API (Day 4)
- Add `get_recommendations(arxiv_id)` to `SemanticScholarClient`
- Uses `GET /recommendations/v1/papers/forpaper/ARXIV:{id}`
- Better similarity matching than keyword search
- Use as 4th source in Retriever agent

### 9.4 Citation Graph Visualization (Day 5-6)
- Generate a simple DOT/Mermaid graph of the paper's citation neighborhood
- Include in the Markdown output as a code block
- Tools: `graphviz` or just Mermaid syntax in Markdown

### 9.5 SSRN / RePEc Integration (Post-hackathon)
- Add additional paper sources beyond arXiv
- SSRN has an API for working papers
- Useful for economics/finance papers not on arXiv

### 9.6 Full PDF Parsing (Post-hackathon)
- Use `pymupdf` or `pdfplumber` to extract full text
- Feed sections to the Critic for deeper analysis
- Significantly increases accuracy but adds complexity and latency

---

## 10. File-by-File Implementation Checklist

This is the exact list of files to modify, in priority order.

### Must-Have (Days 1-3)

| File | Status | What to Do |
|------|--------|------------|
| `triage_agent/utils/llm.py` | Skeleton done | **Test with real API keys.** Verify Anthropic and OpenAI calls work. Handle rate limits. |
| `triage_agent/agents/critic.py` | Skeleton done | **Implement `run()` method.** Replace placeholder with `call_llm_json()` call. Parse JSON into `MethodCritique`. |
| `triage_agent/agents/novelty.py` | Skeleton done | **Implement `run()` method.** S2 search + `call_llm_json()` call. Parse into `NoveltyReport`. |
| `triage_agent/agents/retriever.py` | Skeleton done | **Parallelize S2 calls.** Change sequential to `asyncio.gather(return_exceptions=True)`. Add logging. |
| `triage_agent/orchestrator.py` | Skeleton done | **Add assembler LLM call.** After agents return, call LLM to generate `one_line_summary`, `key_claims`, `relevance`, `read_decision`. |
| `triage_agent/api/semantic_scholar.py` | Skeleton done | **Add `get_recommendations()` method.** New endpoint: `/recommendations/v1/papers/forpaper/{id}`. |

### Should-Have (Day 4)

| File | Status | What to Do |
|------|--------|------------|
| `config/SKILL.md` | Not created | **Create OpenClaw skill definition.** See Section 10.1 below. |
| `openclaw.json` | Not created | **Create OpenClaw config.** Enable skill, set env vars. |

### Nice-to-Have (Days 5-6)

| File | Status | What to Do |
|------|--------|------------|
| `triage_agent/models/agenda.py` | Not created | **Create `AgendaProfile` model** for personalized relevance. |
| `triage_agent/cli.py` | Skeleton done | **Add `--category`, `--days`, `--agenda` flags** for batch mode. |
| `triage_agent/formatters/markdown.py` | Skeleton done | **Add daily digest format** for batch output. |

### 10.1 OpenClaw Skill Definition (`config/SKILL.md`)

```yaml
---
name: triage-memo-agent
description: Generate a triage memo for an arXiv research paper with methodology critique, novelty assessment, and related work
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["ANTHROPIC_API_KEY"]
    primaryEnv: "ANTHROPIC_API_KEY"
---
```

```markdown
# Triage Memo Agent

Use this skill when the user wants to:
- Analyze a research paper from arXiv
- Get a summary or critique of a paper
- Check how novel a paper is
- Find related papers
- Triage whether a paper is worth reading

## Tools
Python CLI: `triage <arxiv-id-or-url>`

## Instructions
1. Extract the arXiv ID or URL from the user's message
2. Run `python3 -m triage_agent.cli <arxiv-id>`
3. Display the formatted memo to the user

## Example Usage
User: "Can you triage this paper? https://arxiv.org/abs/2301.07041"
Agent: [Runs triage CLI, displays memo]

User: "Is 2301.07041 worth reading?"
Agent: [Runs triage CLI, focuses on the read_decision and key_claims]
```

---

## 11. Quick Start for New Developer

```bash
# 1. Clone and enter the project
cd ~/hackathon-research-agent

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install in development mode
pip install -e ".[dev]"

# 4. Set up environment
cp .env.example .env
# Edit .env -- add at minimum ANTHROPIC_API_KEY

# 5. Test the arXiv client (should work without LLM keys)
python3 -c "
import asyncio
from triage_agent.api.arxiv import ArxivClient

async def test():
    async with ArxivClient() as client:
        paper = await client.fetch_paper('2301.07041')
        print(f'Title: {paper.title}')
        print(f'Authors: {paper.short_authors}')
        print(f'Abstract: {paper.abstract[:200]}...')

asyncio.run(test())
"

# 6. Test the Semantic Scholar client
python3 -c "
import asyncio
from triage_agent.api.semantic_scholar import SemanticScholarClient

async def test():
    async with SemanticScholarClient() as s2:
        paper = await s2.get_paper_by_arxiv_id('2301.07041')
        print(f'S2 ID: {paper[\"paperId\"]}')
        print(f'Citations: {paper[\"citationCount\"]}')

asyncio.run(test())
"

# 7. Run the full pipeline (needs LLM API key)
triage 2301.07041

# 8. Run tests
pytest tests/ -v

# 9. Lint
ruff check .
```

---

## 12. Key Design Decisions

1. **Abstract-only approach:** We deliberately skip PDF parsing. Abstracts are available instantly via API, and for triage purposes (read/skip/skim decisions), the abstract contains enough signal. PDF parsing adds latency, complexity, and failure modes.

2. **Parallel sub-agents:** All three agents run via `asyncio.gather()`. The LLM-based agents (Critic, Novelty) are the bottleneck (~5-15s each). Running them in parallel means total time is max(agents) not sum(agents).

3. **Structured JSON output from LLM:** We use JSON mode / instruction to get structured responses. This is more reliable than regex-parsing free-form text, and Pydantic validates the schema.

4. **httpx over requests:** Async HTTP client for non-blocking API calls. The skeleton already uses `httpx.AsyncClient` with context managers.

5. **Pydantic v2:** All data models use Pydantic v2 with `BaseModel`. This gives us validation, serialization (`model_dump_json`), and clear schemas.

6. **LLM provider abstraction:** The `utils/llm.py` module abstracts over Anthropic and OpenAI APIs. Switch providers by changing the `LLM_MODEL` env var. Default: `claude-sonnet-4-6`.
