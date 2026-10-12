from fastapi import APIRouter
from app.api.v1.endpoints import sessions, chat

api_router = APIRouter()
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(chat.router, prefix="/sessions", tags=["chat"])
