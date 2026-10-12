import pytest
from app.providers.router import ProviderRouter
from app.providers.base import ProviderMessage
from fastapi import HTTPException
from unittest.mock import patch, MagicMock

@pytest.fixture
def router():
    return ProviderRouter()

@pytest.mark.asyncio
async def test_unknown_provider(router):
    with pytest.raises(HTTPException) as excinfo:
        await router.generate("unknown_provider", [ProviderMessage(role="user", content="Hi")])
    assert excinfo.value.status_code == 422

@pytest.mark.asyncio
async def test_ollama_provider_success(router):
    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "model": "qwen3:4b",
                "message": {"content": "Hello from Ollama"},
                "eval_count": 10,
                "eval_duration": 100
            }
        def raise_for_status(self):
            pass

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MockResponse()
        mock_post.return_value = mock_response
        
        response = await router.generate("ollama", [ProviderMessage(role="user", content="Hi")])
        assert response.content == "Hello from Ollama"
        assert response.provider == "ollama"
        assert response.model == "qwen3:4b"

@pytest.mark.asyncio
async def test_ollama_provider_connection_error(router):
    import httpx
    with patch("httpx.AsyncClient.post", side_effect=httpx.RequestError("Connection failed")):
        with pytest.raises(HTTPException) as excinfo:
            await router.generate("ollama", [ProviderMessage(role="user", content="Hi")])
        assert excinfo.value.status_code == 503
