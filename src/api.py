"""FastAPI backend for the AgentRAG demo frontend.

Serves the JSON API under /api/* and the static frontend/ directory at /.

Run with:
    uvicorn src.api:app --reload
"""

import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from src import memory
from src.agent import run_agent

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

app = FastAPI(title="AgentRAG Demo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


@app.get("/api/sessions")
def get_sessions():
    try:
        return memory.list_sessions()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {e}")


@app.get("/api/sessions/{session_id}")
def get_session_messages(session_id: str):
    try:
        if not memory.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        return {"session_id": session_id, "messages": memory.get_messages(session_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {e}")


@app.post("/api/message")
def post_message(req: MessageRequest):
    query = req.message.strip()
    if not query:
        raise HTTPException(status_code=400, detail="message cannot be empty")

    session_id = req.session_id
    try:
        if not session_id or not memory.session_exists(session_id):
            session_id = memory.create_session(query)
        memory.append_message(session_id, "user", query)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {e}")

    result = run_agent(query)

    try:
        memory.append_message(session_id, "assistant", result["answer"], result["trace"])
    except Exception:
        pass  # still return the answer even if persistence fails

    return {
        "session_id": session_id,
        "answer": result["answer"],
        "trace": result["trace"],
        "tool_calls_made": result["tool_calls_made"],
    }


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
