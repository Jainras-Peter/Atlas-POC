import re
from datetime import datetime, timezone
from typing import Any

from app.db import users_repo
from app.db.mongo import get_db
from app.models.chat import ChatMessage, ConversationOut, ConversationSummary

_USER_ID_RE = re.compile(r"\bID:\s*([a-f0-9]{24})\b", re.IGNORECASE)
_TITLE_MAX = 60


def _title_from_text(content: str) -> str:
    text = " ".join((content or "").split())
    if not text:
        return "New chat"
    if len(text) <= _TITLE_MAX:
        return text
    return text[: _TITLE_MAX - 1].rstrip() + "…"


async def append_message(
    thread_id: str,
    role: str,
    content: str,
    user: dict[str, Any] | None = None,
    quote: dict[str, Any] | None = None,
    quotes: list[dict[str, Any]] | None = None,
    quotes_customer: dict[str, Any] | None = None,
    companies: list[dict[str, Any]] | None = None,
    customers: list[dict[str, Any]] | None = None,
    approval: dict[str, Any] | None = None,
) -> None:
    db = get_db()
    now = datetime.now(timezone.utc)
    message: dict[str, Any] = {"role": role, "content": content, "created_at": now}
    if user:
        message["user"] = user
    if quote:
        message["quote"] = quote
    if quotes is not None:
        message["quotes"] = quotes
    if quotes_customer:
        message["quotesCustomer"] = quotes_customer
    if companies is not None:
        message["companies"] = companies
    if customers is not None:
        message["customers"] = customers
    if approval:
        message["approval"] = approval


    set_fields: dict[str, Any] = {"updated_at": now}
    set_on_insert: dict[str, Any] = {"thread_id": thread_id}

    if role == "user":
        existing = await db.conversations.find_one(
            {"thread_id": thread_id}, {"title": 1}
        )
        if not existing:
            set_on_insert["title"] = _title_from_text(content)
        elif not existing.get("title"):
            set_fields["title"] = _title_from_text(content)

    await db.conversations.update_one(
        {"thread_id": thread_id},
        {
            "$push": {"messages": message},
            "$set": set_fields,
            "$setOnInsert": set_on_insert,
        },
        upsert=True,
    )


async def _hydrate_message(item: dict) -> ChatMessage:
    payload = dict(item)
    if payload.get("user") is None and payload.get("role") == "assistant":
        match = _USER_ID_RE.search(payload.get("content") or "")
        if match:
            user = await users_repo.get_user_by_id(match.group(1))
            if user:
                payload["user"] = user.model_dump(mode="json")
    return ChatMessage(**payload)


async def get_conversation(thread_id: str) -> ConversationOut | None:
    db = get_db()
    doc = await db.conversations.find_one({"thread_id": thread_id})
    if not doc:
        return None
    messages = [await _hydrate_message(item) for item in doc.get("messages", [])]
    return ConversationOut(
        thread_id=doc["thread_id"],
        messages=messages,
        updated_at=doc["updated_at"],
        title=doc.get("title") or "New chat",
    )


async def list_conversations(limit: int = 50) -> list[ConversationSummary]:
    db = get_db()
    cursor = db.conversations.find(
        {},
        {"thread_id": 1, "title": 1, "updated_at": 1, "messages": {"$slice": 1}},
    ).sort("updated_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    out: list[ConversationSummary] = []
    for doc in docs:
        title = doc.get("title")
        if not title:
            msgs = doc.get("messages") or []
            if msgs:
                title = _title_from_text(msgs[0].get("content") or "")
            else:
                title = "New chat"
        out.append(
            ConversationSummary(
                thread_id=doc["thread_id"],
                title=title,
                updated_at=doc["updated_at"],
            )
        )
    return out


async def delete_conversation(thread_id: str) -> bool:
    db = get_db()
    result = await db.conversations.delete_one({"thread_id": thread_id})
    return result.deleted_count > 0
