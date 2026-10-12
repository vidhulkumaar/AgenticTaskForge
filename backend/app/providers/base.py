from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ProviderMessage(BaseModel):
    role: str
    content: str

class ProviderResponse(BaseModel):
    content: str
    provider: str
    model: str
    metadata: Optional[Dict[str, Any]] = None

class BaseProvider(ABC):
    @abstractmethod
    async def generate(self, messages: List[ProviderMessage], system_instruction: Optional[str] = None) -> ProviderResponse:
        """
        Generate a response given a list of messages.
        messages should be in chronological order.
        """
        pass
