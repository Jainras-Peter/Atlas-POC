from datetime import datetime, timezone

from fastapi import APIRouter

from app.db import conversations_repo
from app.models.chat import ConversationOut, ConversationSummary

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def list_conversations() -> list[ConversationSummary]:
    return await conversations_repo.list_conversations()


@router.get("/{thread_id}", response_model=ConversationOut)
async def get_conversation(thread_id: str) -> ConversationOut:
    conversation = await conversations_repo.get_conversation(thread_id)
    if conversation is None:
        return ConversationOut(
            thread_id=thread_id,
            messages=[],
            updated_at=datetime.now(timezone.utc),
            title="New chat",
        )
    return conversation


@router.delete("/{thread_id}")
async def delete_conversation(thread_id: str) -> dict:
    deleted = await conversations_repo.delete_conversation(thread_id)
    return {"deleted": deleted, "thread_id": thread_id}
