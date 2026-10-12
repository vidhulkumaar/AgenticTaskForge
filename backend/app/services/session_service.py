from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, Tuple
from uuid import UUID

from app.models.session import ChatSession
from app.models.message import Message
from app.schemas.session import SessionCreate
from app.schemas.message import MessageCreate

class SessionService:
    @staticmethod
    async def create_session(db: AsyncSession, session_in: SessionCreate) -> ChatSession:
        db_session = ChatSession(
            title=session_in.title,
            metadata_=session_in.metadata_
        )
        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)
        return db_session

    @staticmethod
    async def get_session(db: AsyncSession, session_id: UUID) -> Optional[ChatSession]:
        result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
        return result.scalars().first()

    @staticmethod
    async def list_sessions(db: AsyncSession, page: int = 1, size: int = 50) -> Tuple[list[ChatSession], int]:
        count_result = await db.execute(select(func.count(ChatSession.id)))
        total = count_result.scalar_one()

        result = await db.execute(
            select(ChatSession)
            .order_by(ChatSession.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def delete_session(db: AsyncSession, session_id: UUID) -> bool:
        session = await SessionService.get_session(db, session_id)
        if not session:
            return False
        await db.delete(session)
        await db.commit()
        return True

    @staticmethod
    async def add_message(db: AsyncSession, session_id: UUID, message_in: MessageCreate) -> Message:
        db_message = Message(
            session_id=session_id,
            role=message_in.role,
            content=message_in.content,
            metadata_=message_in.metadata_
        )
        db.add(db_message)
        await db.commit()
        await db.refresh(db_message)
        return db_message

    @staticmethod
    async def get_messages(db: AsyncSession, session_id: UUID, page: int = 1, size: int = 50) -> Tuple[list[Message], int]:
        count_result = await db.execute(select(func.count(Message.id)).where(Message.session_id == session_id))
        total = count_result.scalar_one()

        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .offset((page - 1) * size)
            .limit(size)
        )
        return list(result.scalars().all()), total
