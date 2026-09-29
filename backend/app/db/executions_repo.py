"""Durable per-conversation executions (e.g. Sales HITL waiting for Approve).

Conversation
  ├── execution-001 → sales → waiting
  ├── execution-002 → sdr → completed
  └── execution-003 → quote → running

Approve/Reject targets ``execution_id``, so later chat turns do not kill HITL.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.db.mongo import get_db


async def create_waiting(
    *,
    thread_id: str,
    agent: str,
    action: str,
    message: str,
    users: list[dict[str, Any]],
) -> dict[str, Any]:
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "execution_id": str(uuid4()),
        "thread_id": thread_id,
        "agent": agent,
        "action": action,
        "message": message,
        "users": users,
        "status": "waiting",
        "created_at": now,
        "resolved_at": None,
        "result_text": None,
    }
    await db.executions.insert_one(doc)
    return doc


async def get_by_id(execution_id: str) -> dict[str, Any] | None:
    db = get_db()
    return await db.executions.find_one({"execution_id": execution_id}, {"_id": 0})


async def claim_waiting(execution_id: str, thread_id: str) -> dict[str, Any] | None:
    """Atomically move waiting → resolving so double-Approve is idempotent."""
    from pymongo import ReturnDocument

    db = get_db()
    now = datetime.now(timezone.utc)
    doc = await db.executions.find_one_and_update(
        {
            "execution_id": execution_id,
            "thread_id": thread_id,
            "status": "waiting",
        },
        {"$set": {"status": "resolving", "resolved_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        return None
    doc.pop("_id", None)
    return doc


async def mark_finished(
    execution_id: str,
    *,
    status: str,
    result_text: str,
) -> None:
    db = get_db()
    await db.executions.update_one(
        {"execution_id": execution_id},
        {
            "$set": {
                "status": status,
                "result_text": result_text,
                "resolved_at": datetime.now(timezone.utc),
            }
        },
    )


async def release_claim(execution_id: str) -> None:
    """Put back to waiting if resolve crashed before finish."""
    db = get_db()
    await db.executions.update_one(
        {"execution_id": execution_id, "status": "resolving"},
        {"$set": {"status": "waiting", "resolved_at": None}},
    )


def to_approval_payload(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_id": doc["execution_id"],
        "action": doc["action"],
        "message": doc.get("message") or "",
        "users": doc.get("users") or [],
    }
