from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any, Dict, Literal
from datetime import datetime
from uuid import UUID

class MessageCreate(BaseModel):
    role: Literal['user', 'assistant', 'system']
    content: str
    metadata_: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime
    metadata_: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    page: int
    size: int
