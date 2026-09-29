from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from app.agents.content import message_text
from app.agents.state import GraphState
from app.agents.streaming import emit_status
from app.agents.supervisor.intent import (
    has_open_quote_create,
    has_open_sales,
    has_open_sdr,
    is_cancel_intent,
    is_explicit_lookup_intent,
    is_lookup_intent,
    is_quote_create_intent,
    is_quote_list_intent,
    is_sales_intent,
    is_sdr_intent,
    looks_like_import,
)
from app.agents.supervisor.prompts import SUPERVISOR_SYSTEM
from app.agents.supervisor.schema import RouteDecision
from app.llm import get_llm

# Atlas is the supervisor — status lines use the Atlas brand.
ROUTE_STATUS = {
    "sales": "Sales agent assigned…",
    "quote": "Quote agent assigned…",
    "chat": "Atlas is thinking…",
    "sdr": "SDR agent is assigned…",
}


def _last_user_text(state: GraphState) -> str:
    for message in reversed(state.get("messages") or []):
        if isinstance(message, HumanMessage):
            return message_text(message.content)
    return ""


async def supervisor_node(state: GraphState, writer: StreamWriter) -> dict:
    emit_status(writer, "Atlas is routing your request…")
    latest = _last_user_text(state)
    update: dict = {}
    route: str

    # 0) Import / delete ALWAYS wins — before sticky SDR discovery
    #    ("Import this customers…" must never stay on the SDR agent.)
    if is_sales_intent(latest) or looks_like_import(latest):
        route = "sales"
        emit_status(writer, ROUTE_STATUS[route])
        update["route"] = route
        if state.get("created_user"):
            update["created_user"] = None
            update["extracted_user"] = None
        return update

    # 1) Cancel clears open drafts
    if is_cancel_intent(latest) and (
        has_open_quote_create(state) or has_open_sales(state) or has_open_sdr(state)
    ):
        route = "chat"
        update["extracted_quote"] = None
        update["extracted_user"] = None
        update["listed_quotes"] = None
        update["locked_company_id"] = None
        update["listed_companies"] = None
        update["listed_customers"] = None
        update["pending_approval"] = None
        emit_status(writer, ROUTE_STATUS[route])
        update["route"] = route
        return update

    # 2) Sticky incomplete quote create
    if has_open_quote_create(state) and not (
        is_quote_list_intent(latest)
        or is_explicit_lookup_intent(latest)
        or is_sdr_intent(latest)
    ):
        route = "quote"
        emit_status(writer, ROUTE_STATUS[route])
        update["route"] = route
        return update

    # 3) Sticky incomplete sales draft
    if has_open_sales(state) and not (
        is_quote_list_intent(latest)
        or is_quote_create_intent(latest)
        or is_explicit_lookup_intent(latest)
        or is_sdr_intent(latest)
        or is_cancel_intent(latest)
    ):
        route = "sales"
        emit_status(writer, ROUTE_STATUS[route])
        update["route"] = route
        return update

    # 4) Sticky SDR (company/customer discovery follow-ups)
    if has_open_sdr(state) and not (
        is_quote_list_intent(latest) or is_quote_create_intent(latest)
    ):
        if is_explicit_lookup_intent(latest) and not is_sdr_intent(latest):
            pass
        else:
            route = "sdr"
            emit_status(writer, ROUTE_STATUS[route])
            update["route"] = route
            return update

    # 5) Regex ladder — quote before SDR so "quote for customer …" wins
    if is_quote_list_intent(latest) or is_quote_create_intent(latest):
        route = "quote"
    elif is_sdr_intent(latest):
        route = "sdr"
    elif is_lookup_intent(latest):
        route = "chat"
    else:
        llm = get_llm().with_structured_output(RouteDecision)
        history = state.get("messages") or []
        recent = history[-8:] or [HumanMessage(content="hello")]
        decision = await llm.ainvoke([SystemMessage(content=SUPERVISOR_SYSTEM), *recent])
        route = decision.route
        # Safety: LLM must not send imports to SDR
        if looks_like_import(latest):
            route = "sales"

    emit_status(writer, ROUTE_STATUS.get(route, "Atlas is thinking…"))
    update["route"] = route

    if route == "quote" and state.get("created_quote") and is_quote_create_intent(latest):
        update["created_quote"] = None
        update["extracted_quote"] = None
        update["listed_quotes"] = None
    return update
