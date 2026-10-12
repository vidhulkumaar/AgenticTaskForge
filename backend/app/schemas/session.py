from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict
from datetime import datetime
from uuid import UUID

class SessionCreate(BaseModel):
    title: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None

class SessionResponse(BaseModel):
    id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata_: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class SessionListResponse(BaseModel):
    items: list[SessionResponse]
    total: int
    page: int
    size: int
