from typing import List, Optional, Dict
from fastapi import HTTPException
from app.providers.base import BaseProvider, ProviderMessage, ProviderResponse
from app.providers.claude import ClaudeProvider
from app.providers.ollama import OllamaProvider
from app.core.config import settings

class ProviderRouter:
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        # Lazy initialization
    
    def _get_provider(self, name: str) -> BaseProvider:
        if name not in self._providers:
            if name == "claude":
                self._providers[name] = ClaudeProvider()
            elif name == "ollama":
                self._providers[name] = OllamaProvider()
            else:
                raise HTTPException(status_code=422, detail=f"Unknown provider: {name}")
        return self._providers[name]

    async def generate(self, provider_name: str, messages: List[ProviderMessage], system_instruction: Optional[str] = None) -> ProviderResponse:
        provider_name = provider_name or settings.DEFAULT_LLM_PROVIDER
        
        if provider_name not in ["claude", "ollama"]:
            raise HTTPException(status_code=422, detail=f"Unknown provider: {provider_name}")
            
        try:
            provider = self._get_provider(provider_name)
        except ValueError as e:
            # Catch missing API keys ValueError from provider init
            raise HTTPException(status_code=500, detail=str(e))
            
        return await provider.generate(messages, system_instruction)

provider_router = ProviderRouter()
