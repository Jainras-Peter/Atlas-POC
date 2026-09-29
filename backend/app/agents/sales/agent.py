"""Sales agent — import / delete CRM users with durable execution HITL.

Multi-execution model
---------------------
Instead of LangGraph ``interrupt()`` (which owns the whole thread), Sales
parks a waiting **execution** in Mongo and ends the graph turn. The user can
keep chatting (SDR / Quote). Approve/Reject later calls ``/api/chat/resume``
with ``execution_id`` and applies the stored plan.

Flow:
  1. Build import/delete plan
  2. Persist execution (status=waiting) + emit SSE ``approval``
  3. Graph ends — conversation stays free for other agents
  4. Approve → ``sales.execute.resolve_sales_execution``
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.config import get_config
from langgraph.types import StreamWriter

from app.agents.content import message_text
from app.agents.sales.prompts import SALES_SYSTEM
from app.agents.sales.schema import SalesExtract
from app.agents.sales.tools import (
    find_users_by_name,
    find_users_created_since,
)
from app.agents.state import GraphState
from app.agents.streaming import emit_approval, emit_assistant, emit_status
from app.db import executions_repo, users_repo
from app.llm import get_llm


def _last_user_text(state: GraphState) -> str:
    for message in reversed(state.get("messages") or []):
        if isinstance(message, HumanMessage):
            return message_text(message.content)
    return ""


def _thread_id() -> str:
    try:
        cfg = get_config() or {}
        return str((cfg.get("configurable") or {}).get("thread_id") or "unknown")
    except RuntimeError:
        return "unknown"


def _day_bounds(which: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    if which == "today":
        return start_today, start_today + timedelta(days=1)
    if which == "yesterday":
        start_y = start_today - timedelta(days=1)
        return start_y, start_today
    return start_today - timedelta(days=7), start_today + timedelta(days=1)


def _customer_to_import_candidate(row: dict[str, Any]) -> dict[str, Any] | None:
    name = (row.get("name") or "").strip()
    email = (row.get("email") or "").strip()
    if not name:
        return None
    if not email:
        cid = row.get("customerId") or "unknown"
        email = f"{cid.lower()}@atlas.import.local"
    return {
        "name": name,
        "email": email.lower(),
        "age": None,
        "contact_number": row.get("phone") or None,
        "is_active": True,
        "source_customer_id": row.get("customerId"),
    }


def _build_import_candidates(state: GraphState, extract: SalesExtract) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for row in state.get("listed_customers") or []:
        if isinstance(row, dict):
            item = _customer_to_import_candidate(row)
            if item:
                candidates.append(item)

    if extract.name and extract.email:
        candidates.append(
            {
                "name": extract.name.strip(),
                "email": str(extract.email).strip().lower(),
                "age": extract.age,
                "contact_number": extract.contact_number,
                "is_active": True if extract.is_active is None else extract.is_active,
            }
        )
    elif extract.name or extract.email:
        collected = state.get("extracted_user") or {}
        name = extract.name or collected.get("name")
        email = extract.email or collected.get("email")
        if name and email:
            candidates.append(
                {
                    "name": str(name).strip(),
                    "email": str(email).strip().lower(),
                    "age": extract.age if extract.age is not None else collected.get("age"),
                    "contact_number": extract.contact_number
                    or collected.get("contact_number"),
                    "is_active": True,
                }
            )

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for c in candidates:
        key = c["email"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique


async def _build_delete_candidates(
    extract: SalesExtract, latest: str
) -> tuple[list[dict[str, Any]], str | None]:
    when = (extract.time_filter or "").lower()
    if "today" in latest.lower() or when == "today":
        start, end = _day_bounds("today")
        users = await find_users_created_since(start, end)
        return (
            [u.model_dump(mode="json") for u in users],
            None if users else "No users were imported today.",
        )
    if "yesterday" in latest.lower() or when == "yesterday":
        start, end = _day_bounds("yesterday")
        users = await find_users_created_since(start, end)
        return (
            [u.model_dump(mode="json") for u in users],
            None if users else "No users were imported yesterday.",
        )

    name = (extract.target_name or extract.name or "").strip()
    if name:
        users = await find_users_by_name(name)
        if not users:
            return [], f'No users found named "{name}".'
        if len(users) > 1:
            lines = "\n".join(
                f"- {u.name} · {u.email} · id `{u.id}`" for u in users
            )
            return (
                [u.model_dump(mode="json") for u in users],
                f'Multiple users match "{name}". Tell me which email or id to delete:\n{lines}',
            )
        return [users[0].model_dump(mode="json")], None

    if extract.target_user_id:
        user = await users_repo.get_user_by_id(extract.target_user_id)
        if not user:
            return [], f"No user with id {extract.target_user_id}."
        return [user.model_dump(mode="json")], None

    return [], "Tell me whose users to delete (name, today, or yesterday)."


async def _park_approval(
    writer: StreamWriter,
    *,
    action: str,
    message: str,
    users: list[dict[str, Any]],
) -> dict:
    """Persist waiting execution, emit approval card, end graph turn."""
    thread_id = _thread_id()
    doc = await executions_repo.create_waiting(
        thread_id=thread_id,
        agent="sales",
        action=action,
        message=message,
        users=users,
    )
    approval = executions_repo.to_approval_payload(doc)
    emit_status(writer, "Waiting for your approval… (you can keep chatting)")
    emit_approval(writer, approval)
    content = (
        f"{message}\n\n"
        "Approve or Reject when ready — you can ask Atlas something else first."
    )
    emit_assistant(writer, content)
    return {
        "messages": [AIMessage(content=content)],
        "pending_approval": approval,
    }


async def sales_node(state: GraphState, writer: StreamWriter) -> dict:
    emit_status(writer, "Sales agent preparing action…")

    latest = _last_user_text(state)
    llm = get_llm().with_structured_output(SalesExtract)
    history = state.get("messages") or []
    extract: SalesExtract = await llm.ainvoke(
        [
            SystemMessage(
                content=(
                    f"{SALES_SYSTEM}\n\n"
                    f"Listed Atlas customers in state: "
                    f"{state.get('listed_customers') or 'none'}.\n"
                    f"Fields already collected: {state.get('extracted_user') or 'none'}."
                )
            ),
            *history[-10:],
        ]
    )

    intent = (extract.intent or "import").lower()
    if "delete" in latest.lower() or "remove" in latest.lower():
        intent = "delete"
    elif any(
        w in latest.lower()
        for w in ("import", "add to atlas", "save to atlas", "onboard", "create user")
    ):
        intent = "import"

    if intent == "delete":
        candidates, clarify = await _build_delete_candidates(extract, latest)
        if clarify and (not candidates or "Multiple users" in clarify):
            emit_assistant(writer, clarify)
            return {
                "messages": [AIMessage(content=clarify)],
                "pending_approval": None,
            }
        if not candidates:
            msg = clarify or "No matching users to delete."
            emit_assistant(writer, msg)
            return {"messages": [AIMessage(content=msg)], "pending_approval": None}

        return await _park_approval(
            writer,
            action="delete",
            message=f"Delete {len(candidates)} user(s) from Atlas CRM?",
            users=candidates,
        )

    candidates = _build_import_candidates(state, extract)
    if not candidates:
        missing = []
        collected = dict(state.get("extracted_user") or {})
        if extract.name:
            collected["name"] = extract.name
        if extract.email:
            collected["email"] = extract.email
        if extract.age is not None:
            collected["age"] = extract.age
        if extract.contact_number:
            collected["contact_number"] = extract.contact_number
        if not collected.get("name"):
            missing.append("name")
        if not collected.get("email"):
            missing.append("email")
        if missing:
            follow = extract.follow_up_question or (
                "To import, I need " + " and ".join(missing) + "."
            )
            emit_assistant(writer, follow)
            return {
                "extracted_user": collected,
                "messages": [AIMessage(content=follow)],
            }
        candidates = [
            {
                "name": collected["name"],
                "email": str(collected["email"]).lower(),
                "age": collected.get("age"),
                "contact_number": collected.get("contact_number"),
                "is_active": collected.get("is_active", True),
            }
        ]

    return await _park_approval(
        writer,
        action="import",
        message=f"Import {len(candidates)} contact(s) into Atlas Customers?",
        users=candidates,
    )
