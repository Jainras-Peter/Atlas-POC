"""Apply a parked Sales execution (Approve / Reject) without LangGraph interrupt."""

from __future__ import annotations

from typing import Any

from app.agents.sales.tools import create_user_record, delete_user_by_id
from app.db import executions_repo, users_repo


async def resolve_sales_execution(
    *,
    thread_id: str,
    execution_id: str,
    approved: bool,
) -> dict[str, Any]:
    """Return SSE-friendly events: status / assistant / done fields.

    Result shape:
      {"ok": bool, "events": [...], "assistant_text": str, "error": str|None}
    """
    claimed = await executions_repo.claim_waiting(execution_id, thread_id)
    if claimed is None:
        existing = await executions_repo.get_by_id(execution_id)
        if not existing:
            return {
                "ok": False,
                "events": [
                    {
                        "type": "error",
                        "message": "This approval expired or was not found. "
                        "Ask to import/delete again.",
                    }
                ],
                "assistant_text": "",
                "error": "not_found",
            }
        if existing.get("thread_id") != thread_id:
            return {
                "ok": False,
                "events": [
                    {
                        "type": "error",
                        "message": "This approval belongs to another conversation.",
                    }
                ],
                "assistant_text": "",
                "error": "wrong_thread",
            }
        status = existing.get("status")
        if status in {"approved", "rejected", "completed"}:
            text = existing.get("result_text") or "This approval was already handled."
            return {
                "ok": True,
                "events": [{"type": "assistant", "content": text}],
                "assistant_text": text,
                "error": "already_resolved",
            }
        return {
            "ok": False,
            "events": [
                {
                    "type": "error",
                    "message": f"Cannot approve right now (status={status}).",
                }
            ],
            "assistant_text": "",
            "error": "bad_status",
        }

    action = (claimed.get("action") or "import").lower()
    users = list(claimed.get("users") or [])
    events: list[dict[str, Any]] = []

    try:
        if not approved:
            content = (
                "Delete cancelled. No users were removed."
                if action == "delete"
                else "Import cancelled. Nothing was saved to Customers."
            )
            events.append({"type": "assistant", "content": content})
            await executions_repo.mark_finished(
                execution_id, status="rejected", result_text=content
            )
            return {
                "ok": True,
                "events": events,
                "assistant_text": content,
                "error": None,
            }

        if action == "delete":
            events.append({"type": "status", "message": "Deleting users…"})
            deleted: list[dict[str, Any]] = []
            for row in users:
                uid = row.get("id")
                if not uid:
                    continue
                if await delete_user_by_id(str(uid)):
                    deleted.append(row)
            content = (
                f"Deleted {len(deleted)} user(s)."
                if deleted
                else "Nothing was deleted."
            )
            events.append({"type": "assistant", "content": content})
            await executions_repo.mark_finished(
                execution_id, status="completed", result_text=content
            )
            return {
                "ok": True,
                "events": events,
                "assistant_text": content,
                "error": None,
            }

        # import
        events.append({"type": "status", "message": "Importing users…"})
        created: list[dict[str, Any]] = []
        skipped: list[str] = []
        for row in users:
            email = str(row.get("email") or "").lower()
            name = (row.get("name") or "").strip()
            if not email or not name:
                continue
            existing = await users_repo.get_user_by_email(email)
            if existing:
                skipped.append(str(existing.email))
                continue
            user = await create_user_record(
                name=name,
                email=email,
                age=row.get("age"),
                contact_number=row.get("contact_number") or row.get("phone"),
                is_active=bool(row.get("is_active", True)),
            )
            created.append(user.model_dump(mode="json"))

        parts: list[str] = []
        if created:
            names = ", ".join(str(u.get("name") or "Unknown") for u in created)
            parts.append(
                f"User names {names} are added successfully. "
                "See the details in the Customers tab."
            )
        if skipped:
            parts.append("Already existed: " + ", ".join(skipped))
        content = " ".join(parts) or "Nothing imported."
        events.append({"type": "assistant", "content": content})
        await executions_repo.mark_finished(
            execution_id, status="completed", result_text=content
        )
        return {
            "ok": True,
            "events": events,
            "assistant_text": content,
            "error": None,
        }
    except Exception as exc:
        await executions_repo.release_claim(execution_id)
        return {
            "ok": False,
            "events": [{"type": "error", "message": str(exc)}],
            "assistant_text": "",
            "error": "exception",
        }
