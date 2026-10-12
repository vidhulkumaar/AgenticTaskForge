from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    metadata_ = Column("metadata", JSON, nullable=True)

    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        CheckConstraint(role.in_(['user', 'assistant', 'system']), name='valid_role'),
    )
