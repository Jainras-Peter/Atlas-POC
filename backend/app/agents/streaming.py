import json
from typing import Any


def sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def emit_status(writer, message: str) -> None:
    writer({"type": "status", "message": message})


def emit_assistant(writer, content: str) -> None:
    writer({"type": "assistant", "content": content})


def emit_assistant_delta(writer, content: str) -> None:
    """Stream a token/chunk of the final assistant reply (Gemini astream)."""
    if content:
        writer({"type": "assistant_delta", "content": content})


def emit_approval(writer, approval: dict[str, Any]) -> None:
    """Ask the human to Approve / Reject a parked execution (execution_id)."""
    writer({"type": "approval", "approval": approval})


def emit_result(writer, user: dict[str, Any]) -> None:
    writer({"type": "result", "user": user})


def emit_quote_result(writer, quote: dict[str, Any]) -> None:
    writer({"type": "result", "quote": quote})


def emit_quotes(
    writer,
    quotes: list[dict[str, Any]],
    customer: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {"type": "quotes", "quotes": quotes}
    if customer:
        payload["customer"] = customer
    writer(payload)


def emit_companies(writer, companies: list[dict[str, Any]]) -> None:
    writer({"type": "result", "companies": companies})


def emit_customers(
    writer,
    customers: list[dict[str, Any]],
    locked_company_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {"type": "result", "customers": customers}
    if locked_company_id:
        payload["locked_company_id"] = locked_company_id
    writer(payload)
