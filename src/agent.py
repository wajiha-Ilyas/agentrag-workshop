"""Builds & compiles the AgentRAG graph, and exposes run_agent(query)."""

from dotenv import load_dotenv

from src.graph import build_graph

load_dotenv()

_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_agent(query: str) -> dict:
    """Runs the agent on a single query.

    Returns a dict with:
        answer: str            -- the final answer
        trace: list[str]       -- the sequence of node transitions (for showing "thinking")
        tool_calls_made: int   -- how many retrieval/tool calls happened
    """
    graph = _get_graph()

    initial_state = {
        "query": query,
        "messages": [],
        "context": [],
        "tool_calls_made": 0,
        "loop_count": 0,
        "final_answer": "",
        "next_action": "",
    }

    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        return {
            "answer": f"Sorry, something went wrong while processing your question: {e}",
            "trace": [],
            "tool_calls_made": 0,
        }

    return {
        "answer": final_state.get("final_answer", "").strip() or "I wasn't able to generate an answer.",
        "trace": final_state.get("messages", []),
        "tool_calls_made": final_state.get("tool_calls_made", 0),
    }
