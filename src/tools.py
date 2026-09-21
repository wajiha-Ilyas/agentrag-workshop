"""Tools available to the AgentRAG agent: retrieval, calculator, web search, datetime."""

from datetime import datetime, timezone

from langchain_core.tools import tool
from simpleeval import simple_eval

from src.ingest import load_vectorstore

_vectorstore = None


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = load_vectorstore()
    return _vectorstore


@tool
def retrieve_docs(query: str) -> str:
    """Search the local document collection for chunks relevant to the query.
    Returns the top-3 matching chunks concatenated with their source filenames.
    Use this when the answer likely lives in the local knowledge base.
    """
    vectorstore = _get_vectorstore()
    results = vectorstore.similarity_search(query, k=3)
    if not results:
        return "No relevant documents found."

    parts = []
    for doc in results:
        source = doc.metadata.get("source", "unknown")
        parts.append(f"[source: {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


@tool
def calculator(expression: str) -> str:
    """Safely evaluate a math expression (e.g. '2 + 2 * 10' or '(15 - 3) / 4').
    Use this for any arithmetic the user asks for.
    """
    try:
        result = simple_eval(expression)
        return str(result)
    except Exception as e:
        return f"Error evaluating expression '{expression}': {e}"


@tool
def web_search(query: str) -> str:
    """Search the web for current or external information not found in local documents.
    Returns up to 3 results as titles + snippets.
    """
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return "No web search results found."

        parts = []
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            parts.append(f"{title}\n{body}\n({href})")
        return "\n\n".join(parts)
    except Exception as e:
        return f"Web search failed: {e}"


@tool
def get_current_datetime() -> str:
    """Return the current date and time in ISO 8601 format (UTC)."""
    return datetime.now(timezone.utc).isoformat()


ALL_TOOLS = [retrieve_docs, calculator, web_search, get_current_datetime]

TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}
