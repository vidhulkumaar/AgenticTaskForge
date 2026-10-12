from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.session import get_db
from app.services.session_service import SessionService
from app.schemas.session import SessionCreate, SessionResponse, SessionListResponse
from app.schemas.message import MessageCreate, MessageResponse, MessageListResponse

router = APIRouter()

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(session_in: SessionCreate, db: AsyncSession = Depends(get_db)):
    return await SessionService.create_session(db, session_in)

@router.get("", response_model=SessionListResponse)
async def list_sessions(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    items, total = await SessionService.list_sessions(db, page, size)
    return {"items": items, "total": total, "page": page, "size": size}

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    session = await SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    success = await SessionService.delete_session(db, session_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(session_id: UUID, message_in: MessageCreate, db: AsyncSession = Depends(get_db)):
    session = await SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return await SessionService.add_message(db, session_id, message_in)

@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def list_messages(session_id: UUID, page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    session = await SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    items, total = await SessionService.get_messages(db, session_id, page, size)
    return {"items": items, "total": total, "page": page, "size": size}
