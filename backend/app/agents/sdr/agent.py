"""SDR agent — readable LangGraph ReAct (agent ↔ tools) loop.

How the agent loop works
------------------------
This is a classic ReAct cycle implemented as an explicit StateGraph so you can
see each step (instead of a black-box create_react_agent one-liner):

    START → agent_node → (has tool_calls?) → tools_node → agent_node → …
                      └─ (no tool_calls) → END

1. **agent_node** — LLM (with tools bound) **streams** via Gemini `astream`.
   If the model returns tool_calls → go to tools. If it returns prose → deltas
   are pushed to the UI as `assistant_delta` events, then END.
2. **should_continue** — if the last AIMessage has tool_calls AND we are under
   the step cap → route to tools; else END.
3. **tools_node** — ToolNode runs search_companies / get_company_details /
   search_customers, appends ToolMessages, then loops back to agent_node.

The outer `sdr_node` runs the subgraph with `astream` so Gemini token deltas
forward to the HTTP SSE stream (status + assistant_delta + result cards).
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import StreamWriter

from app.agents.content import message_text
from app.agents.sdr.prompts import SDR_SYSTEM
from app.agents.sdr.tools import SDR_TOOLS
from app.agents.state import GraphState
from app.agents.streaming import (
    emit_assistant,
    emit_assistant_delta,
    emit_companies,
    emit_customers,
    emit_status,
)
from app.llm import get_llm

# Cap ReAct iterations so a buggy tool loop cannot run forever.
MAX_SDR_STEPS = 8

_COMPANY_ID_RE = re.compile(r"\b(CMP\d{3,})\b", re.IGNORECASE)


class SdrLoopState(TypedDict):
    """Internal state for the ReAct subgraph only."""

    messages: Annotated[list, add_messages]
    # How many agent→tools cycles we have already done this turn.
    step_count: int


def _last_ai_message(messages: list[BaseMessage]) -> AIMessage | None:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


def _chunk_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return message_text(content)


async def agent_node(state: SdrLoopState) -> dict:
    """Step A — LLM decides: call tools or answer the user.

    Uses Gemini **astream** so final prose tokens reach the UI live.
    Tool-calling turns still accumulate a full AIMessage (with tool_calls)
    before ToolNode runs — we skip streaming those as assistant text.
    """
    llm = get_llm(temperature=0).bind_tools(SDR_TOOLS)
    history = state.get("messages") or []

    try:
        stream_writer = get_stream_writer()
    except RuntimeError:
        stream_writer = None

    response: AIMessage | None = None
    # Once we see tool_call chunks, this turn is a tool round — don't paint text.
    saw_tool_calls = False

    async for chunk in llm.astream([SystemMessage(content=SDR_SYSTEM), *history]):
        response = chunk if response is None else response + chunk
        if getattr(chunk, "tool_call_chunks", None) or getattr(response, "tool_calls", None):
            saw_tool_calls = True
        piece = _chunk_text(chunk.content)
        if piece and stream_writer and not saw_tool_calls:
            # Live Gemini tokens → SSE `assistant_delta`
            stream_writer({"type": "assistant_delta", "content": piece})

    if response is None:
        response = AIMessage(content="I could not generate a response. Please try again.")

    return {
        "messages": [response],
        "step_count": int(state.get("step_count") or 0) + 1,
    }


def should_continue(state: SdrLoopState) -> Literal["tools", "__end__"]:
    """Step B — router after the LLM turn.

    - tool_calls present and under cap → run tools, then come back to agent
    - otherwise → END (final answer is already in the last AIMessage)
    """
    step = int(state.get("step_count") or 0)
    if step >= MAX_SDR_STEPS:
        return "__end__"

    last = _last_ai_message(state.get("messages") or [])
    if last and getattr(last, "tool_calls", None):
        return "tools"
    return "__end__"


# Step C — execute tools. ToolNode reads tool_calls from the last AIMessage,
# invokes matching @tool functions, and appends ToolMessage results.
tools_node = ToolNode(SDR_TOOLS)


def build_sdr_graph():
    """Compile the ReAct subgraph: agent ↔ tools until the model stops calling tools."""
    builder = StateGraph(SdrLoopState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tools_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "__end__": END,
        },
    )
    # After tools finish, always go back to the LLM so it can read results
    # and either call more tools or produce the final user-facing answer.
    builder.add_edge("tools", "agent")
    return builder.compile()


_sdr_graph = None


def get_sdr_graph():
    global _sdr_graph
    if _sdr_graph is None:
        _sdr_graph = build_sdr_graph()
    return _sdr_graph


def _last_user_text(state: GraphState) -> str:
    for message in reversed(state.get("messages") or []):
        if isinstance(message, HumanMessage):
            return message_text(message.content)
    return ""


def _extract_json_payloads(messages: list[BaseMessage]) -> tuple[list[dict], list[dict], str | None]:
    """Parse ToolMessage results for FE cards + locked company id."""
    companies: list[dict] = []
    customers: list[dict] = []
    locked: str | None = None

    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        content = message.content
        if not isinstance(content, str):
            continue
        name = message.name or ""
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue

        if name == "search_companies" or "companies" in data:
            rows = data.get("companies") or []
            if isinstance(rows, list) and rows:
                companies = rows
                if len(rows) == 1 and rows[0].get("companyId"):
                    locked = rows[0]["companyId"]

        if name == "get_company_details" and data.get("companyId"):
            locked = data["companyId"]
            companies = [
                {
                    "companyId": data.get("companyId"),
                    "name": data.get("name"),
                    "city": data.get("city", ""),
                    "country": data.get("country", ""),
                    "role": data.get("buyerSupplierRole", ""),
                    "teuPerMonth": data.get("teuPerMonth", 0),
                    "products": data.get("products") or [],
                    "hsCodes": data.get("hsCodes") or [],
                    "matchScore": 100,
                    "matchReasons": ["Selected company"],
                }
            ]

        if name == "search_customers" or "customers" in data:
            rows = data.get("customers") or []
            if isinstance(rows, list) and rows:
                customers = rows

    return companies, customers, locked


def _final_assistant_text(messages: list[BaseMessage]) -> str:
    last = _last_ai_message(messages)
    if not last:
        return "I could not generate a response. Please try again."
    text = message_text(last.content).strip()
    if text:
        return text
    return (
        "I found some results but could not finish summarising them. "
        "Please ask me to continue or pick a companyId."
    )


def _detect_company_id_in_text(text: str) -> str | None:
    match = _COMPANY_ID_RE.search(text or "")
    return match.group(1).upper() if match else None


def _normalize_stream_part(part: Any) -> tuple[str, Any]:
    if isinstance(part, tuple) and len(part) == 2:
        return part[0], part[1]
    if isinstance(part, dict) and part.get("type"):
        return "custom", part
    return "values", part


async def sdr_node(state: GraphState, writer: StreamWriter) -> dict:
    """Supervisor entry point — runs one ReAct turn and streams UI events.

    Subgraph custom events (`assistant_delta`) are forwarded to the parent
    StreamWriter so the HTTP SSE client sees Gemini tokens live.
    """
    emit_status(writer, "Atlas is searching…")

    latest = _last_user_text(state)
    prior_locked = state.get("locked_company_id")
    picked = _detect_company_id_in_text(latest)
    locked = (picked or prior_locked or "").strip() or None

    history = list(state.get("messages") or [])
    turn_messages: list[BaseMessage] = list(history)
    if locked:
        turn_messages = [
            *history,
            SystemMessage(
                content=(
                    f"Locked companyId for this thread: {locked}. "
                    "Prefer this id for get_company_details / search_customers "
                    "unless the user clearly switches to another company."
                )
            ),
        ]

    emit_status(writer, "Thinking with tools…")
    graph = get_sdr_graph()

    loop_messages: list[BaseMessage] = list(turn_messages)
    streamed_any = False

    # astream (not ainvoke) so agent_node's get_stream_writer deltas reach us
    async for part in graph.astream(
        {"messages": turn_messages, "step_count": 0},
        stream_mode=["custom", "values"],
    ):
        mode, data = _normalize_stream_part(part)
        if mode == "custom" and isinstance(data, dict):
            if data.get("type") == "assistant_delta":
                streamed_any = True
            # Forward Gemini chunks / any custom events to the HTTP SSE layer
            writer(data)
        elif mode == "values" and isinstance(data, dict):
            loop_messages = data.get("messages") or loop_messages

    companies, customers, tool_locked = _extract_json_payloads(loop_messages)
    if tool_locked:
        locked = tool_locked
    if picked:
        locked = picked.upper() if picked else locked

    assistant_text = _final_assistant_text(loop_messages)
    # Finalize with full text (for persistence + agents that did not stream)
    if not streamed_any and assistant_text:
        # Fallback: soft chunk-stream so UI still feels live if astream failed
        for i in range(0, len(assistant_text), 48):
            emit_assistant_delta(writer, assistant_text[i : i + 48])
    emit_assistant(writer, assistant_text)

    # Preserve prior discovery results — never wipe with None on a prose-only turn
    update: dict[str, Any] = {
        "messages": [AIMessage(content=assistant_text)],
    }
    if companies:
        update["listed_companies"] = companies
    if customers:
        update["listed_customers"] = customers
    if locked:
        update["locked_company_id"] = locked

    if companies:
        emit_companies(writer, companies)
    if customers:
        emit_customers(writer, customers, locked_company_id=locked)

    return update
