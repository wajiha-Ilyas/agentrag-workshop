"""LangGraph StateGraph definition: planner -> retriever/tools/answer -> generator -> reflect."""

import os
import re
from typing import List, Literal, TypedDict

from langgraph.graph import StateGraph, END

from src.prompts import GENERATOR_SYSTEM_PROMPT, PLANNER_SYSTEM_PROMPT, REFLECT_SYSTEM_PROMPT
from src.tools import TOOLS_BY_NAME

MAX_LOOPS = 3

# Maps a planner label like "tool:datetime" to the actual tool name in TOOLS_BY_NAME
TOOL_LABEL_TO_NAME = {
    "calculator": "calculator",
    "web_search": "web_search",
    "datetime": "get_current_datetime",
}

_EXPRESSION_RE = re.compile(r"[-+*/().\d\s%^]+")

# Deterministic fast-path so greetings/farewells/self-questions never depend on the
# LLM planner correctly classifying them — these should always go straight to "answer"
# without wasting a retrieval or tool call.
_GREETING_RE = re.compile(
    r"^\s*(hi|hello|hey|hiya|yo|greetings|good\s+(morning|afternoon|evening|night))\b",
    re.IGNORECASE,
)
_FAREWELL_RE = re.compile(
    r"\b(bye|goodbye|good\s*bye|see\s*you(\s+later)?|take\s*care|farewell)\b",
    re.IGNORECASE,
)
_SELF_META_RE = re.compile(
    r"\b(who are you|what are you|what can you do|your capabilit\w*|about yourself|tell me about you(r|rself)?)\b",
    re.IGNORECASE,
)


def _is_direct_answer_query(query: str) -> bool:
    return bool(_GREETING_RE.search(query) or _FAREWELL_RE.search(query) or _SELF_META_RE.search(query))


def _extract_expression(query: str) -> str:
    """Pulls the arithmetic expression out of a natural-language query, e.g.
    'What is 47 * 8 - 12?' -> '47 * 8 - 12'. Falls back to the raw query if
    nothing expression-like is found.
    """
    candidates = [m.strip() for m in _EXPRESSION_RE.findall(query) if any(ch.isdigit() for ch in m)]
    return max(candidates, key=len) if candidates else query


class AgentState(TypedDict):
    query: str
    history: str
    messages: List[str]
    context: List[str]
    tool_calls_made: int
    loop_count: int
    final_answer: str
    next_action: str


def get_llm():
    """Builds the chat model, honoring USE_OLLAMA for the offline fallback."""
    use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"

    if use_ollama:
        from langchain_ollama import ChatOllama

        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        return ChatOllama(model=model, temperature=0, timeout=30)

    from langchain_groq import ChatGroq

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    return ChatGroq(model=model, temperature=0, timeout=30, max_retries=1)


def planner_node(state: AgentState) -> AgentState:
    state["loop_count"] += 1

    if state["loop_count"] == 1 and not state["context"] and _is_direct_answer_query(state["query"]):
        state["next_action"] = "answer"
        state["messages"].append("planner -> answer (greeting/farewell/self fast-path)")
        return state

    llm = get_llm()
    gathered = "\n".join(state["context"]) if state["context"] else "(nothing gathered yet)"
    prompt = (
        f"{PLANNER_SYSTEM_PROMPT}\n\n"
        f"Conversation history:\n{state.get('history') or '(none)'}\n\n"
        f"User query: {state['query']}\n\n"
        f"Gathered so far:\n{gathered}"
    )
    response = llm.invoke(prompt)
    decision = response.content.strip().lower()

    valid_labels = {"retrieve", "tool:calculator", "tool:web_search", "tool:datetime", "answer"}
    if decision not in valid_labels:
        decision = "answer"

    state["next_action"] = decision
    state["messages"].append(f"planner -> {decision}")
    return state


def retriever_node(state: AgentState) -> AgentState:
    result = TOOLS_BY_NAME["retrieve_docs"].invoke({"query": state["query"]})
    state["context"].append(f"[retrieve_docs]\n{result}")
    state["tool_calls_made"] += 1
    state["messages"].append("retriever -> retrieve_docs")
    return state


def tool_executor_node(state: AgentState) -> AgentState:
    label = state["next_action"].split(":", 1)[1]
    tool_name = TOOL_LABEL_TO_NAME.get(label)
    tool_fn = TOOLS_BY_NAME.get(tool_name)

    if tool_fn is None:
        state["context"].append(f"[tool error] unknown tool label: {label}")
    else:
        if tool_name == "calculator":
            args = {"expression": _extract_expression(state["query"])}
        elif tool_name == "web_search":
            args = {"query": state["query"]}
        else:
            args = {}
        try:
            result = tool_fn.invoke(args) if args else tool_fn.invoke({})
        except Exception as e:
            result = f"Tool '{tool_name}' failed: {e}"
        state["context"].append(f"[{tool_name}]\n{result}")

    state["tool_calls_made"] += 1
    state["messages"].append(f"tool_executor -> {tool_name}")
    return state


def generator_node(state: AgentState) -> AgentState:
    llm = get_llm()
    context_text = "\n\n".join(state["context"]) if state["context"] else "(no context gathered)"
    history_text = state.get("history") or "(none)"
    system_prompt = GENERATOR_SYSTEM_PROMPT.format(context=context_text, history=history_text)
    prompt = f"{system_prompt}\n\nQuestion: {state['query']}"

    response = llm.invoke(prompt)
    state["final_answer"] = response.content.strip()
    state["messages"].append("generator -> drafted answer")
    return state


def reflect_node(state: AgentState) -> AgentState:
    if state["loop_count"] >= MAX_LOOPS:
        state["messages"].append("reflect -> loop cap reached, forcing done")
        state["next_action"] = "done"
        return state

    llm = get_llm()
    prompt = REFLECT_SYSTEM_PROMPT.format(query=state["query"], draft_answer=state["final_answer"])
    response = llm.invoke(prompt)
    verdict = response.content.strip().lower()

    state["next_action"] = "retry" if "retry" in verdict else "done"
    state["messages"].append(f"reflect -> {state['next_action']}")
    return state


def route_from_planner(state: AgentState) -> Literal["retriever", "tool_executor", "generator"]:
    action = state["next_action"]
    if action == "retrieve":
        return "retriever"
    if action.startswith("tool:"):
        return "tool_executor"
    return "generator"


def route_from_reflect(state: AgentState) -> Literal["planner", "__end__"]:
    if state["next_action"] == "retry":
        return "planner"
    return END


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("generator", generator_node)
    graph.add_node("reflect", reflect_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges(
        "planner",
        route_from_planner,
        {
            "retriever": "retriever",
            "tool_executor": "tool_executor",
            "generator": "generator",
        },
    )

    graph.add_edge("retriever", "generator")
    graph.add_edge("tool_executor", "generator")
    graph.add_edge("generator", "reflect")

    graph.add_conditional_edges(
        "reflect",
        route_from_reflect,
        {
            "planner": "planner",
            END: END,
        },
    )

    return graph.compile()
