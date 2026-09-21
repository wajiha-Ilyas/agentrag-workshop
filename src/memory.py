"""Redis-backed storage for the last N conversation sessions (used by the demo frontend).

Keeps up to MAX_SESSIONS full conversations. Older sessions are evicted (both their
metadata and messages) whenever a newer one pushes the count over the cap.
"""

import json
import os
import time
import uuid
from typing import List, Optional

import redis

MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "5"))
SESSIONS_INDEX_KEY = "agentrag:sessions:index"

_redis_client = None


def get_redis() -> "redis.Redis":
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True,
        )
    return _redis_client


def _meta_key(session_id: str) -> str:
    return f"agentrag:session:{session_id}:meta"


def _messages_key(session_id: str) -> str:
    return f"agentrag:session:{session_id}:messages"


def _evict_old_sessions() -> None:
    r = get_redis()
    ids = r.lrange(SESSIONS_INDEX_KEY, 0, -1)

    seen = set()
    deduped = []
    for sid in ids:
        if sid not in seen:
            seen.add(sid)
            deduped.append(sid)

    keep, drop = deduped[:MAX_SESSIONS], deduped[MAX_SESSIONS:]

    pipe = r.pipeline()
    pipe.delete(SESSIONS_INDEX_KEY)
    if keep:
        pipe.rpush(SESSIONS_INDEX_KEY, *keep)
    for sid in drop:
        pipe.delete(_meta_key(sid))
        pipe.delete(_messages_key(sid))
    pipe.execute()


def create_session(first_message: str) -> str:
    r = get_redis()
    session_id = str(uuid.uuid4())
    title = first_message.strip()[:60] or "New conversation"
    now = time.time()

    r.hset(
        _meta_key(session_id),
        mapping={"id": session_id, "title": title, "created_at": now, "updated_at": now},
    )
    r.lpush(SESSIONS_INDEX_KEY, session_id)
    _evict_old_sessions()
    return session_id


def touch_session(session_id: str) -> None:
    r = get_redis()
    r.hset(_meta_key(session_id), "updated_at", time.time())
    r.lrem(SESSIONS_INDEX_KEY, 0, session_id)
    r.lpush(SESSIONS_INDEX_KEY, session_id)
    _evict_old_sessions()


def session_exists(session_id: str) -> bool:
    r = get_redis()
    return bool(r.exists(_meta_key(session_id)))


def append_message(session_id: str, role: str, content: str, trace: Optional[List[str]] = None) -> None:
    r = get_redis()
    message = {"role": role, "content": content, "trace": trace or [], "timestamp": time.time()}
    r.rpush(_messages_key(session_id), json.dumps(message))
    touch_session(session_id)


def get_messages(session_id: str) -> List[dict]:
    r = get_redis()
    raw = r.lrange(_messages_key(session_id), 0, -1)
    return [json.loads(m) for m in raw]


def list_sessions() -> List[dict]:
    r = get_redis()
    ids = r.lrange(SESSIONS_INDEX_KEY, 0, MAX_SESSIONS - 1)
    sessions = []
    for sid in ids:
        meta = r.hgetall(_meta_key(sid))
        if meta:
            sessions.append(meta)
    return sessions
