from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import StreamWriter

from app.agents.content import message_text
from app.agents.state import GraphState
from app.agents.streaming import emit_assistant, emit_assistant_delta, emit_result
from app.db import users_repo
from app.agents.supervisor.intent import EMAIL_RE, OBJECT_ID_RE
from app.llm import get_llm

CHAT_SYSTEM = """You are a helpful assistant for the Atlas CRM multi-agent POC.
You help look up existing users and answer light questions about the desk.
Be concise and friendly. If a lookup already happened, summarize only those facts.
Do not invent records. For imports, quotes, or company discovery, Atlas routes elsewhere.
"""


def _last_user_text(state: GraphState) -> str:
    for message in reversed(state.get("messages") or []):
        if isinstance(message, HumanMessage):
            return message_text(message.content)
    return ""


def _chunk_text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return message_text(content)


async def chat_node(state: GraphState, writer: StreamWriter) -> dict:
    user_text = _last_user_text(state)
    match = OBJECT_ID_RE.search(user_text)
    email_match = EMAIL_RE.search(user_text)
    user = None
    if match:
        user = await users_repo.get_user_by_id(match.group())
        if user is None:
            content = f"No user found with ID {match.group()}."
            emit_assistant(writer, content)
            return {"messages": [AIMessage(content=content)]}
    elif email_match:
        user = await users_repo.get_user_by_email(email_match.group())
        if user is None:
            content = f"No user found with email {email_match.group()}."
            emit_assistant(writer, content)
            return {"messages": [AIMessage(content=content)]}

    if user:
        payload = user.model_dump(mode="json")
        content = f"Here are the details for {user.name}."
        emit_assistant(writer, content)
        emit_result(writer, payload)
        return {"messages": [AIMessage(content=content)]}

    llm = get_llm(temperature=0.3)
    reply = None
    async for chunk in llm.astream(
        [SystemMessage(content=CHAT_SYSTEM), *(state.get("messages") or [])[-8:]]
    ):
        reply = chunk if reply is None else reply + chunk
        piece = _chunk_text(chunk.content)
        if piece:
            emit_assistant_delta(writer, piece)

    content = message_text(reply.content) if reply else ""
    emit_assistant(writer, content)
    return {"messages": [AIMessage(content=content)]}
