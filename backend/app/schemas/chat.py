from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class Citation(BaseModel):
    document_id: str
    chunk_id: str
    episode_title: Optional[str] = None
    source_url: Optional[str] = None
    content: str
    timestamp_start: Optional[str] = None
    speaker: Optional[str] = None

class ChatRequest(BaseModel):
    content: str
    provider: Optional[str] = None
    system_instruction: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: UUID
    message_id: UUID
    provider: str
    model: str
    content: str
    created_at: datetime
    citations: List[Citation] = []

class EssayRequest(BaseModel):
    topic: str
    target_audience: Optional[str] = "General founders and product managers"
    central_argument: Optional[str] = "Growth requires a systematic approach based on PMF and retention."
    provider: Optional[str] = None

class Artifact(BaseModel):
    id: UUID
    type: str  # e.g., 'markdown', 'html', 'css'
    content: str

class EssayResponse(BaseModel):
    session_id: UUID
    message_id: UUID
    title: str
    body: str
    word_count: int
    citations: List[Citation] = []
    limitations: Optional[str] = None
    artifact: Optional[Artifact] = None
