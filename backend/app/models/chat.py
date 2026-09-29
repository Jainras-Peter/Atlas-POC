from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: str | None = None
    # Optional: FE re-sends last customer cards on "Import this" so Sales HITL
    # still works even if graph state was wiped by a prior SDR turn.
    customers: list[dict[str, Any]] | None = None
    companies: list[dict[str, Any]] | None = None
    locked_company_id: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    user: dict[str, Any] | None = None
    quote: dict[str, Any] | None = None
    quotes: list[dict[str, Any]] | None = None
    quotesCustomer: dict[str, Any] | None = None
    companies: list[dict[str, Any]] | None = None
    customers: list[dict[str, Any]] | None = None
    approval: dict[str, Any] | None = None



class ConversationOut(BaseModel):
    thread_id: str
    messages: list[ChatMessage]
    updated_at: datetime
    title: str = "New chat"


class ConversationSummary(BaseModel):
    thread_id: str
    title: str
    updated_at: datetime


class StreamEvent(BaseModel):
    type: Literal[
        "thread",
        "status",
        "assistant",
        "assistant_delta",
        "approval",
        "result",
        "quotes",
        "done",
        "error",
    ]
    message: str | None = None
    content: str | None = None
    thread_id: str | None = None
    user: dict[str, Any] | None = None
    quote: dict[str, Any] | None = None
    quotes: list[dict[str, Any]] | None = None
    customer: dict[str, Any] | None = None
    companies: list[dict[str, Any]] | None = None
    customers: list[dict[str, Any]] | None = None
    locked_company_id: str | None = None
    approval: dict[str, Any] | None = None
