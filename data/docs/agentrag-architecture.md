# AgentRAG Architecture Notes

AgentRAG is the hands-on project for the "Building with AI Agents: Workflows
& Modern AI" workshop, run for CAIS (COMSATS AI Society) at COMSATS
University Islamabad by Wajiha Ilyas (Mobiz).

## Why LangGraph
LangGraph models the agent as a `StateGraph`: a set of named nodes (planner,
retriever, tool_executor, generator, reflect) connected by edges, some of
which are conditional on the current state. This maps directly onto the
"plan → act → observe → decide again" loop that defines an agentic system,
and makes the control flow explicit and inspectable instead of hiding it
inside a single giant prompt.

## Why Groq
Groq provides free, no-credit-card API access to open models (such as Llama
3.3 70B) with very low latency, which matters for a live workshop demo where
the audience is watching each step happen in real time. Ollama is kept as an
offline backup in case the venue's internet or the Groq free tier rate-limits
during the session.

## Why ChromaDB + sentence-transformers
ChromaDB runs embedded (no server process to stand up) and persists to a
local `.chroma/` directory, so ingestion and retrieval work entirely offline
once the embedding model is downloaded. `all-MiniLM-L6-v2` is a small,
fast, free sentence-transformers model that is more than sufficient for a
handful of short documents.

## Guardrails built into the design
1. A hard cap of 3 planner↔reflect loops, to prevent runaway tool-calling.
2. A generator prompt that instructs the model to say "I don't have enough
   information" rather than guess, when retrieval returns nothing relevant.
3. An evaluation set (`eval/test_questions.jsonl`) covering all three
   routing paths — retrieve, tool use, and direct answer — so routing
   mistakes are caught before the workshop rather than during it.
