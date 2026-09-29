from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.chat_node import chat_node
from app.agents.quote.agent import quote_node
from app.agents.sales.agent import sales_node
from app.agents.sdr.agent import sdr_node
from app.agents.state import GraphState
from app.agents.supervisor.agent import supervisor_node

_graph = None


def _route(state: GraphState) -> str:
    return state.get("route") or "chat"


def build_graph():
    builder = StateGraph(GraphState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("sales", sales_node)
    builder.add_node("quote", quote_node)
    builder.add_node("chat", chat_node)
    builder.add_node("sdr", sdr_node)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        _route,
        {
            "sales": "sales",
            "quote": "quote",
            "chat": "chat",
            "sdr": "sdr",
        },
    )
    builder.add_edge("sales", END)
    builder.add_edge("quote", END)
    builder.add_edge("chat", END)
    builder.add_edge("sdr", END)

    return builder.compile(checkpointer=MemorySaver())


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
