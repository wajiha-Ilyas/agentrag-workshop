# AgentRAG

A command-line (and optional Streamlit) AI agent built with **LangGraph**. It answers
questions over a small local document set using **RAG**, calls **tools**
(calculator, web search, date/time) when a question needs something outside the
documents, and runs a **multi-step agentic loop** (plan → act → observe → decide
again) instead of a single prompt-response call.

Built for the "Building with AI Agents: Workflows & Modern AI" workshop by Wajiha
Ilyas (Mobiz) for CAIS — COMSATS AI Society, COMSATS University Islamabad. See
[ai-agent-workshop-plan.md](ai-agent-workshop-plan.md) for the full implementation spec.

## Stack (100% free)

| Layer | Choice |
|---|---|
| LLM (primary) | Groq API (Llama 3.3 70B) |
| LLM (offline backup) | Ollama (`llama3.2`) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector store | ChromaDB (embedded/local) |
| Orchestration | LangGraph |
| Web search | duckduckgo-search |
| Calculator | simpleeval |
| UI (optional) | Streamlit |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate       # on Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and paste in a free Groq key from https://console.groq.com/keys
```

## Build the vector store

Ingests everything in `data/docs/`, chunks it, embeds it, and persists it to `.chroma/`:

```bash
python -m src.ingest
```

This also runs a sanity-check retrieval query and prints the top matching chunks.

## Run the CLI

```bash
python -m src.cli
```

Type a question, see the answer plus the agent's trace (which nodes fired and
which tools were called).

## Run the Streamlit UI

```bash
streamlit run app_streamlit.py
```

## Run the evaluation suite

```bash
python -m eval.run_eval
```

Runs all questions in `eval/test_questions.jsonl` and reports which route the
planner chose for each one (retrieve / tool:calculator / tool:web_search /
tool:datetime / answer) against the expected route.

## Offline fallback (Ollama)

If you don't have internet access or Groq rate-limits you, install
[Ollama](https://ollama.com), pull a model (`ollama pull llama3.2`), and set in `.env`:

```
USE_OLLAMA=true
OLLAMA_MODEL=llama3.2
```

## Repository structure

```
agentrag/
├── README.md
├── requirements.txt
├── .env.example
├── data/
│   └── docs/                 # sample docs (AI-agent topics) for RAG
├── src/
│   ├── ingest.py             # loads docs, chunks, embeds, writes to Chroma
│   ├── tools.py              # calculator, web_search, get_current_datetime, retrieve_docs
│   ├── graph.py              # LangGraph StateGraph definition
│   ├── prompts.py            # system + planner prompt templates
│   ├── agent.py              # builds & compiles the graph, exposes run_agent(query)
│   └── cli.py                # simple REPL entrypoint
├── app_streamlit.py          # optional chat UI
├── eval/
│   ├── test_questions.jsonl  # sample Q&A pairs for the eval segment
│   └── run_eval.py           # runs test_questions through the agent, logs results
└── .chroma/                  # created at runtime (vector store persistence) — gitignored
```

## Guardrails

- **Loop cap**: the planner↔reflect cycle is capped at 3 tool/retrieval calls to
  prevent runaway agentic loops.
- **No-hallucination instruction**: the generator prompt explicitly instructs the
  model to say when the gathered context doesn't contain enough information,
  rather than guessing.
- **Graceful degradation**: tool failures (web search, LLM calls) are caught and
  surfaced as error strings instead of crashing the CLI/UI.

## Extending it

See §11 of [ai-agent-workshop-plan.md](ai-agent-workshop-plan.md) for challenge ideas:
add a fifth tool, add short-term memory, add scope guardrails, swap in the local
Ollama model, or add a confidence score that routes low-confidence answers back
through `reflect`.
