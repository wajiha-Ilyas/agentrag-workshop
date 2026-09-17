# ReAct: Synergizing Reasoning and Acting in Language Models

Source: summary of Yao et al., 2022 (arXiv:2210.03629)

ReAct is a prompting framework that interleaves **reasoning traces** (the model
thinking step by step in natural language) with **actions** (calls to external
tools or environments, such as a search API). Instead of choosing between
"reason only" (chain-of-thought) or "act only" (plain tool use), ReAct lets a
language model alternate between the two in a single loop:

1. **Thought** — the model reasons about the current state and what to do next.
2. **Action** — the model issues a tool call (e.g., search a knowledge base).
3. **Observation** — the tool's result is appended to the model's context.
4. Repeat until the model decides it has enough information to answer.

Key findings from the paper:
- On knowledge-intensive tasks (HotpotQA, FEVER), ReAct reduces hallucination
  compared to chain-of-thought-only prompting, because the reasoning is
  grounded in retrieved evidence rather than the model's parametric memory.
- On decision-making tasks (ALFWorld, WebShop), ReAct outperforms pure
  action-only baselines because the interleaved reasoning helps the model
  recover from unexpected observations (e.g., a failed action) instead of
  getting stuck in a loop.
- The pattern of "think → act → observe → decide again" generalizes to almost
  any agent architecture, including the planner/retriever/tool/generator loop
  used in this workshop's AgentRAG project.

ReAct is one of the earliest and most influential formulations of what is now
generally called the "agentic loop."
