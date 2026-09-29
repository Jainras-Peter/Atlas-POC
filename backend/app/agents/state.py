from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    route: Literal["sales", "quote", "chat", "sdr"] | None
    extracted_user: dict[str, Any] | None
    created_user: dict[str, Any] | None
    extracted_quote: dict[str, Any] | None
    created_quote: dict[str, Any] | None
    listed_quotes: list[dict[str, Any]] | None
    # SDR discovery
    locked_company_id: str | None
    listed_companies: list[dict[str, Any]] | None
    listed_customers: list[dict[str, Any]] | None
    # Sales HITL
    pending_approval: dict[str, Any] | None
