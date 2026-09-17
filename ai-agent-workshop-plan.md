# AgentRAG — Hands-On Project for "Building with AI Agents: Workflows & Modern AI"

> Workshop by Wajiha Ilyas (Mobiz) for CAIS — COMSATS AI Society, COMSATS University Islamabad
> This document is the implementation spec for the **"Build an Agent with Claude Code"** segment of the workshop. Feed this file to Claude Code (`claude` in an empty folder, then paste/reference this file) to scaffold the repo.

## 1. What we're building

**AgentRAG** — a command-line (and optional Streamlit) AI agent that:
- Answers questions over a small local document set using **RAG** (retrieval-augmented generation)
- Can call **tools** (calculator, web search, date/time) when the question needs something outside the documents
- Uses a **multi-step agentic loop** (plan → act → observe → decide again) instead of a single prompt-response call

This directly covers the learning outcomes: agent fundamentals, frameworks, routing/planning/tool use, and evaluation/guardrails — all in one buildable artifact.

## 2. Constraint: 100% free stack

No paid API keys, no credit card required anywhere. Everything below is free-tier or fully local.

| Layer | Choice | Why | Cost |
|---|---|---|---|
| LLM (primary) | **Groq API** (Llama 3.3 70B or 3.1 8B) | Free API key, no card, very fast inference — good for a live audience | Free |
| LLM (offline backup) | **Ollama** running `llama3.2` or `qwen2.5:7b` locally | Works with no internet/if Groq rate-limits during the session | Free |
| Embeddings | **sentence-transformers** (`all-MiniLM-L6-v2`) via HuggingFace | Runs locally, no API key at all | Free |
| Vector store | **ChromaDB** (embedded/local mode) | No server to stand up, persists to disk | Free |
| Orchestration | **LangGraph** | Purpose-built for the router/planner/tool-loop pattern you're teaching | Free (OSS) |
| Web search tool | **duckduckgo-search** (Python package) | No API key required | Free |
| Calculator tool | **simpleeval** | Safe expression evaluation, no API | Free |
| UI (optional) | **Streamlit** | One command to get a chat UI for the demo | Free |

Get a free Groq key at https://console.groq.com/keys (sign up, no card). Get Ollama at https://ollama.com if you want the offline fallback.

## 3. Architecture

```
                     ┌─────────────┐
        user query → │   PLANNER   │  (decides: answer directly / retrieve / use a tool)
                     └──────┬──────┘
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
        ┌──────────┐  ┌───────────┐  ┌───────────┐
        │ RETRIEVER │  │   TOOLS   │  │  DIRECT    │
        │ (Chroma)  │  │ (calc/    │  │  ANSWER    │
        │           │  │  search/  │  │            │
        │           │  │  time)    │  │            │
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │              │              │
              └──────────────┴──────────────┘
                            ▼
                     ┌─────────────┐
                     │  GENERATOR  │  (drafts answer using gathered context)
                     └──────┬──────┘
                            ▼
                     ┌─────────────┐
                     │  REFLECT?   │──── needs more info ──▶ back to PLANNER
                     └──────┬──────┘
                            ▼
                     final answer to user
```

This maps 1:1 to LangGraph's `StateGraph`: nodes = `planner`, `retriever`, `tool_executor`, `generator`, `reflect`; conditional edges route between them based on state.

## 4. Repository structure

```
agentrag/
├── README.md
├── requirements.txt
├── .env.example
├── data/
│   └── docs/                 # sample PDFs/markdown go here (see §8)
├── src/
│   ├── ingest.py             # loads docs, chunks, embeds, writes to Chroma
│   ├── tools.py              # calculator, web_search, get_current_datetime, retrieve_docs
│   ├── graph.py              # LangGraph StateGraph definition (planner/retriever/tools/generator)
│   ├── prompts.py            # system + planner prompt templates
│   ├── agent.py              # builds & compiles the graph, exposes `run_agent(query)`
│   └── cli.py                # simple REPL entrypoint
├── app_streamlit.py          # optional chat UI
├── eval/
│   ├── test_questions.jsonl  # ~10 sample Q&A pairs for the eval segment
│   └── run_eval.py           # runs test_questions through the agent, logs results
└── .chroma/                  # created at runtime (vector store persistence) — gitignore this
```

## 5. `requirements.txt`

```
langgraph>=0.2.0
langchain>=0.3.0
langchain-community>=0.3.0
langchain-groq>=0.2.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
duckduckgo-search>=6.0.0
simpleeval>=1.0.0
python-dotenv>=1.0.0
streamlit>=1.38.0
pypdf>=4.0.0
```

## 6. `.env.example`

```
GROQ_API_KEY=your_free_groq_key_here
# Optional: only needed if demoing the offline fallback
OLLAMA_MODEL=llama3.2
USE_OLLAMA=false
```

## 7. Build order (live-coding flow)

Structured so each phase is a working checkpoint you can demo before moving on — good for a live session where you don't want a broken half-built agent on screen.

**Phase 0 — Setup (5 min)**
- `python -m venv .venv`, install requirements, copy `.env.example` → `.env`, paste in a free Groq key
- Sanity check: one raw call to Groq via `langchain_groq.ChatGroq` printing a response

**Phase 1 — Ingestion & retrieval baseline (15 min)**
- `src/ingest.py`: load files from `data/docs/`, split with `RecursiveCharacterTextSplitter` (chunk_size ~800, overlap ~100), embed with `HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")`, persist to `Chroma` at `.chroma/`
- Prove retrieval works standalone: query → top-k chunks printed, before any agent logic exists

**Phase 2 — Tools (10 min)**
- `src/tools.py` with four functions, each wrapped as a LangChain `@tool`:
  - `retrieve_docs(query: str) -> str` — similarity search against the Chroma store, returns concatenated top-3 chunks with source filenames
  - `calculator(expression: str) -> str` — `simpleeval.simple_eval(expression)`, catches exceptions and returns an error string instead of raising
  - `web_search(query: str) -> str` — `duckduckgo_search.DDGS().text(query, max_results=3)`, returns titles + snippets
  - `get_current_datetime() -> str` — returns ISO timestamp (shows students a "trivial but real" tool)

**Phase 3 — The graph (20 min, the core teaching moment)**
- `src/graph.py`: define `AgentState` (TypedDict: `query`, `messages`, `context`, `tool_calls_made`, `final_answer`)
- `planner` node: LLM call with a system prompt (see §9) that outputs a routing decision — `retrieve`, `tool:<name>`, or `answer`
- `tool_executor` node: dispatches to the matching function in `tools.py`, appends result to `context`
- `generator` node: LLM call that drafts an answer using `context` + original `query`
- `reflect` node: cheap check — does the draft answer actually address the query, or does it need another retrieval/tool pass? (cap at 3 loops to avoid infinite cycles — this is the guardrail you'll reference in Phase 6)
- Wire with `add_conditional_edges` from `planner` based on its decision, and from `reflect` back to `planner` or to `END`

**Phase 4 — CLI (5 min)**
- `src/cli.py`: a `while True` loop reading input, calling `run_agent(query)`, printing the answer and (optionally) which tools fired — the tool trace is genuinely useful for the audience to see the "thinking"

**Phase 5 — Streamlit UI (10 min, optional if time allows)**
- `app_streamlit.py`: `st.chat_input` / `st.chat_message` wrapping the same `run_agent` function — no new agent logic, just a UI on top

**Phase 6 — Guardrails & evaluation (10 min)**
- Loop cap (already in Phase 3) — prevents runaway tool-calling
- Simple hallucination check: if `retrieve_docs` returns nothing relevant, the generator prompt must instruct the model to say so rather than guess
- `eval/test_questions.jsonl`: ~10 questions split across "should retrieve", "should use a tool", "should answer directly" — `eval/run_eval.py` runs them all and logs which path the planner chose, so students can see routing mistakes

**Phase 7 — Final challenge (remaining time)**
- Hand off to students to extend: see §11

## 8. Sample dataset

Keep it small (3–6 files) so ingestion is fast on stage. Good free, on-theme options to drop in `data/docs/`:
- A few AI-agent arXiv paper abstracts/PDFs (all freely downloadable), e.g. the ReAct paper (arxiv.org/abs/2210.03629) and a survey paper on LLM agents
- Or something more relatable to the audience: COMSATS AI Society's own past event write-ups / a public course syllabus — anything text-based works, since the point is to demonstrate the RAG mechanics, not the content itself

## 9. Prompt skeletons (`src/prompts.py`)

```python
PLANNER_SYSTEM_PROMPT = """You are the planning module of an AI agent.
Given the user's query and what has been gathered so far, decide the single next action:
- "retrieve" if the answer likely lives in the local document set
- "tool:calculator" if it needs arithmetic
- "tool:web_search" if it needs current/external info not in the documents
- "tool:datetime" if it needs the current date/time
- "answer" if you already have enough to respond
Respond with only the action label."""

GENERATOR_SYSTEM_PROMPT = """You are answering the user's question using ONLY the context provided below.
If the context does not contain enough information, say so explicitly instead of guessing.
Cite which source (document name or tool) each piece of your answer came from.

Context:
{context}"""
```

## 10. Evaluation checklist (for the "Evaluation & Production Considerations" segment)

- [ ] Does the planner route correctly on all 10 test questions in `eval/test_questions.jsonl`?
- [ ] Does the generator refuse/flag when retrieval returns nothing relevant (no hallucinated answers)?
- [ ] Is the loop cap actually preventing infinite planner↔reflect cycles?
- [ ] What's the latency per query (Groq call count × avg response time)? Worth timing live.
- [ ] What happens if `web_search` or the Groq API call fails? (Should degrade gracefully, not crash the CLI.)

## 11. Final challenge ideas (for students)

- Add a fifth tool (e.g., a unit converter, or a second local document collection)
- Add short-term memory so the agent remembers earlier turns in the same session
- Add a basic guardrail: reject queries asking the agent to do something outside its declared scope
- Swap the Groq model for the local Ollama model and compare answer quality/speed
- Add a confidence score to the generator's output and route low-confidence answers back through `reflect`

## 12. Free resource links (recap)

- Groq free API keys: https://console.groq.com/keys
- Ollama (local models): https://ollama.com
- LangGraph docs: https://langchain-ai.github.io/langgraph/
- Chroma docs: https://docs.trychroma.com/
- sentence-transformers models: https://www.sbert.net/
- duckduckgo-search package: https://pypi.org/project/duckduckgo-search/
- Streamlit docs: https://docs.streamlit.io/
