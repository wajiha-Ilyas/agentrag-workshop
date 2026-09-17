# LLM Agents: A Brief Survey

An "LLM agent" is a system where a large language model is placed in a loop
with memory, tools, and an environment, and is allowed to take multiple steps
toward a goal rather than producing a single response. Most agent
architectures share four core components:

## 1. Planning
The agent breaks a high-level goal into smaller steps, and decides — at each
step — what to do next: answer directly, retrieve information, or call a
tool. Planning can be implicit (baked into a single prompt) or explicit (a
dedicated "planner" or "router" step, as in this workshop's AgentRAG design).

## 2. Memory
Short-term memory is typically the running conversation/context window.
Long-term memory is usually an external store (a vector database, a file, a
key-value store) that the agent can read from and write to across sessions.

## 3. Tool use
Agents extend what a language model can do by giving it access to external
functions: calculators, search engines, code execution, APIs, databases.
Tool use turns a static text generator into a system that can act on the
world and incorporate fresh, verifiable information instead of relying only
on what was in its training data.

## 4. Retrieval-Augmented Generation (RAG)
RAG is a specific and very common tool: instead of (or in addition to)
general web search, the agent retrieves relevant chunks from a private
document collection (via embedding similarity search) and includes them as
context before generating an answer. RAG is the standard technique for
grounding an LLM's answers in a specific knowledge base and reducing
hallucination on domain-specific questions.

## Common failure modes
- **Infinite loops**: an agent that keeps calling tools without ever
  deciding it has enough information. The standard guardrail is a hard cap
  on the number of loop iterations.
- **Hallucinated citations**: an agent that claims a fact came from a
  document or tool when it did not. The standard guardrail is to instruct
  the generator to explicitly say "I don't have enough information" when
  retrieval returns nothing relevant.
- **Tool misuse**: calling the wrong tool for the query (e.g., using web
  search for a question the local documents already answer). This is
  primarily a planning/routing quality problem, and is usually evaluated
  with a small labeled set of test questions covering each routing path.
