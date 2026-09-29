import asyncio
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.agents.graph import get_graph
from app.agents.sales.execute import resolve_sales_execution
from app.agents.streaming import sse
from app.db import conversations_repo
from app.models.chat import ChatRequest

router = APIRouter(tags=["chat"])


class ResumeRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    approved: bool
    execution_id: str = Field(..., min_length=1)


def _normalize_part(part):
    if isinstance(part, tuple) and len(part) == 2:
        return part[0], part[1]
    if isinstance(part, dict) and part.get("type"):
        return part["type"], part.get("data")
    return "custom", part


async def _stream_graph(graph, input_payload, config):
    """Yield SSE payloads; flush between events so the UI updates live."""
    assistant_text = ""
    created_user = None
    created_quote = None
    listed_quotes = None
    listed_customer = None
    listed_companies = None
    listed_customers = None
    approval_payload = None

    async for part in graph.astream(
        input_payload,
        config=config,
        stream_mode=["custom", "updates"],
    ):
        mode, data = _normalize_part(part)
        if mode != "custom" or not isinstance(data, dict):
            continue
        event_type = data.get("type")
        if event_type == "assistant_delta":
            assistant_text += data.get("content") or ""
        if event_type == "assistant":
            assistant_text = data.get("content") or assistant_text
        if event_type == "approval" and data.get("approval"):
            approval_payload = data["approval"]
        if event_type == "result" and data.get("user"):
            created_user = data["user"]
        if event_type == "result" and data.get("quote"):
            created_quote = data["quote"]
        if event_type == "result" and data.get("companies") is not None:
            listed_companies = data["companies"]
        if event_type == "result" and data.get("customers") is not None:
            listed_customers = data["customers"]
        if event_type == "quotes" and data.get("quotes") is not None:
            listed_quotes = data["quotes"]
            listed_customer = data.get("customer")
        if event_type in {
            "status",
            "assistant",
            "assistant_delta",
            "approval",
            "result",
            "quotes",
        }:
            yield data
            await asyncio.sleep(0)

    yield {
        "_persist": {
            "assistant_text": assistant_text,
            "created_user": created_user,
            "created_quote": created_quote,
            "listed_quotes": listed_quotes,
            "listed_customer": listed_customer,
            "listed_companies": listed_companies,
            "listed_customers": listed_customers,
            "approval": approval_payload,
        }
    }


@router.post("/chat")
async def chat(body: ChatRequest):
    thread_id = body.thread_id or str(uuid.uuid4())
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    await conversations_repo.append_message(thread_id, "user", body.message)

    graph_input: dict = {"messages": [HumanMessage(content=body.message)]}
    if body.customers:
        graph_input["listed_customers"] = body.customers
    if body.companies:
        graph_input["listed_companies"] = body.companies
    if body.locked_company_id:
        graph_input["locked_company_id"] = body.locked_company_id

    async def event_stream():
        yield sse({"type": "thread", "thread_id": thread_id})
        await asyncio.sleep(0)
        try:
            async for data in _stream_graph(
                graph,
                graph_input,
                config,
            ):
                if "_persist" in data:
                    persist = data["_persist"]
                    if persist.get("assistant_text"):
                        await conversations_repo.append_message(
                            thread_id,
                            "assistant",
                            persist["assistant_text"],
                            user=persist.get("created_user"),
                            quote=persist.get("created_quote"),
                            quotes=persist.get("listed_quotes"),
                            quotes_customer=persist.get("listed_customer"),
                            companies=persist.get("listed_companies"),
                            customers=persist.get("listed_customers"),
                            approval=persist.get("approval"),
                        )
                else:
                    yield sse(data)
        except Exception as exc:
            yield sse({"type": "error", "message": str(exc)})
        yield sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/resume")
async def resume_chat(body: ResumeRequest):
    """Resolve a parked Sales execution (Approve / Reject) by execution_id."""
    thread_id = body.thread_id
    decision_label = "Approve" if body.approved else "Reject"
    await conversations_repo.append_message(
        thread_id, "user", f"[{decision_label}]"
    )

    async def event_stream():
        yield sse({"type": "thread", "thread_id": thread_id})
        await asyncio.sleep(0)
        try:
            result = await resolve_sales_execution(
                thread_id=thread_id,
                execution_id=body.execution_id,
                approved=body.approved,
            )
            for event in result.get("events") or []:
                yield sse(event)
                await asyncio.sleep(0)
            text = result.get("assistant_text") or ""
            if text:
                await conversations_repo.append_message(
                    thread_id, "assistant", text
                )
        except Exception as exc:
            yield sse({"type": "error", "message": str(exc)})
        yield sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
