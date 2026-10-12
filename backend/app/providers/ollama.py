import httpx
from typing import List, Optional
from fastapi import HTTPException
from app.providers.base import BaseProvider, ProviderMessage, ProviderResponse
from app.core.config import settings

class OllamaProvider(BaseProvider):
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip('/')
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.REQUEST_TIMEOUT

    async def generate(self, messages: List[ProviderMessage], system_instruction: Optional[str] = None) -> ProviderResponse:
        ollama_messages = []
        if system_instruction:
            ollama_messages.append({"role": "system", "content": system_instruction})
        
        for msg in messages:
            ollama_messages.append({"role": msg.role, "content": msg.content})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": ollama_messages,
                        "stream": False
                    }
                )
                
                if response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Ollama endpoint or model not found")
                
                response.raise_for_status()
                data = response.json()
                
                return ProviderResponse(
                    content=data["message"]["content"],
                    provider="ollama",
                    model=self.model,
                    metadata={"eval_count": data.get("eval_count"), "eval_duration": data.get("eval_duration")}
                )
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Ollama server is unavailable: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")
