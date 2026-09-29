from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from app.agents.content import message_text
from app.agents.quote.prompts import QUOTE_SYSTEM
from app.agents.quote.schema import QuoteExtract
from app.agents.quote.tools import (
    create_quote_for_customer,
    list_quotes_for_customer,
    resolve_customer,
)
from app.agents.state import GraphState
from app.agents.streaming import emit_assistant, emit_quote_result, emit_quotes, emit_status
from app.agents.supervisor.intent import is_quote_list_intent
from app.llm import get_llm

REQUIRED_CREATE = ("origin", "destination", "mode", "cargo", "cut_off_date")


def _last_user_text(state: GraphState) -> str:
    for message in reversed(state.get("messages") or []):
        if isinstance(message, HumanMessage):
            return message_text(message.content)
    return ""


def _merge_extracted(previous: dict | None, incoming: QuoteExtract) -> dict:
    merged = dict(previous or {})
    for key in (
        "intent",
        "customer_name",
        "customer_email",
        "customer_id",
        "origin",
        "destination",
        "mode",
        "cargo",
        "cut_off_date",
    ):
        value = getattr(incoming, key)
        if value is not None and value != "":
            merged[key] = value
    return merged


def _has_customer_identity(extracted: dict) -> bool:
    return bool(
        extracted.get("customer_email")
        or extracted.get("customer_id")
        or extracted.get("customer_name")
    )


def _missing_lane_fields(extracted: dict) -> list[str]:
    return [
        key.replace("_", " ")
        for key in REQUIRED_CREATE
        if not extracted.get(key)
    ]


def _lane_follow_up(missing: list[str], extract: QuoteExtract) -> str:
    if extract.follow_up_question:
        return extract.follow_up_question
    labels = ", ".join(missing)
    return (
        f"I can create the quote once I have: {labels}. "
        "Please share the missing fields (e.g. Origin: Shanghai, Destination: Rotterdam, "
        "Mode: FCL, Cargo: FAK, Cut Off Date: 25th June)."
    )


def _quote_payload(quote) -> dict:
    return quote.model_dump(mode="json")


async def _resolve_or_clarify(extracted: dict, writer: StreamWriter):
    """Return (user, extracted, clarify_message)."""
    emit_status(writer, "Resolving customer...")
    user, clarify = await resolve_customer(
        extracted.get("customer_id"),
        extracted.get("customer_email"),
        extracted.get("customer_name"),
    )
    if user:
        extracted["customer_id"] = user.id
        extracted["customer_email"] = str(user.email)
        extracted["customer_name"] = user.name
    return user, extracted, clarify


async def quote_node(state: GraphState, writer: StreamWriter) -> dict:
    latest = _last_user_text(state)
    collected = {} if state.get("created_quote") else (state.get("extracted_quote") or {})

    emit_status(writer, "Quote agent extracting details…")
    llm = get_llm().with_structured_output(QuoteExtract)
    history = state.get("messages") or []
    extract: QuoteExtract = await llm.ainvoke(
        [
            SystemMessage(
                content=(
                    f"{QUOTE_SYSTEM}\n\n"
                    f"Fields already collected: {collected or 'none yet'}."
                )
            ),
            *history[-10:],
        ]
    )

    extracted = _merge_extracted(collected, extract)
    prior_intent = (collected.get("intent") or "").lower()
    continuing_create = bool(collected) and prior_intent != "list" and not state.get(
        "created_quote"
    )

    if is_quote_list_intent(latest) and not continuing_create:
        intent = "list"
    elif continuing_create:
        intent = "create"
    else:
        intent = (extracted.get("intent") or extract.intent or "create").lower()
        if is_quote_list_intent(latest):
            intent = "list"
    extracted["intent"] = intent

    if intent == "list":
        if not _has_customer_identity(extracted):
            follow_up = (
                extract.follow_up_question
                or "Which customer should I list quotes for? Share their name, email, or id."
            )
            emit_assistant(writer, follow_up)
            return {
                "extracted_quote": extracted,
                "messages": [AIMessage(content=follow_up)],
            }

        user, extracted, clarify = await _resolve_or_clarify(extracted, writer)
        if user is None:
            content = clarify or "Could not resolve that customer."
            emit_assistant(writer, content)
            return {
                "extracted_quote": extracted,
                "messages": [AIMessage(content=content)],
            }

        quotes = await list_quotes_for_customer(user)
        payloads = [_quote_payload(q) for q in quotes]
        if not payloads:
            content = f"No quotes found for {user.name} ({user.email})."
            emit_assistant(writer, content)
            return {
                "extracted_quote": extracted,
                "listed_quotes": [],
                "messages": [AIMessage(content=content)],
            }

        content = f"Found {len(payloads)} quote(s) for {user.name}."
        emit_assistant(writer, content)
        emit_quotes(
            writer,
            payloads,
            customer={"id": user.id, "name": user.name, "email": str(user.email)},
        )
        return {
            "extracted_quote": extracted,
            "listed_quotes": payloads,
            "messages": [AIMessage(content=content)],
        }

    # ---------- create path ----------
    if not _has_customer_identity(extracted):
        follow_up = (
            extract.follow_up_question
            or "Which customer is this quote for? Share their name, email, or id."
        )
        emit_assistant(writer, follow_up)
        return {
            "extracted_quote": extracted,
            "messages": [AIMessage(content=follow_up)],
        }

    user, extracted, clarify = await _resolve_or_clarify(extracted, writer)
    if user is None:
        # Ambiguous name or not found — ask, keep draft sticky
        content = clarify or "Could not resolve that customer."
        emit_assistant(writer, content)
        return {
            "extracted_quote": extracted,
            "messages": [AIMessage(content=content)],
        }

    missing = _missing_lane_fields(extracted)
    if missing:
        follow_up = _lane_follow_up(missing, extract)
        emit_assistant(writer, follow_up)
        return {
            "extracted_quote": extracted,
            "messages": [AIMessage(content=follow_up)],
        }

    emit_status(writer, "Saving quote in the DB…")
    quote = await create_quote_for_customer(
        user=user,
        origin=extracted["origin"],
        destination=extracted["destination"],
        mode=extracted["mode"],
        cargo=extracted["cargo"],
        cut_off_date=extracted["cut_off_date"],
    )
    payload = _quote_payload(quote)
    content = (
        f"Quote {quote.quote_number} created successfully for {user.name} "
        f"({user.email})."
    )
    emit_assistant(writer, content)
    emit_quote_result(writer, payload)
    return {
        "extracted_quote": extracted,
        "created_quote": payload,
        "messages": [AIMessage(content=content)],
    }
