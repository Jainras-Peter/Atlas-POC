from fastapi import APIRouter

from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.quotes import router as quotes_router
from app.api.users import router as users_router

api_router = APIRouter()
api_router.include_router(chat_router)
api_router.include_router(users_router)
api_router.include_router(quotes_router)
api_router.include_router(conversations_router)
