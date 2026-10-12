import pytest
from httpx import AsyncClient
from app.main import app
from uuid import UUID

@pytest.mark.asyncio
async def test_chat_success(client, db_session):
    # Create a session
    response = await client.post("/api/v1/sessions", json={"title": "Test Chat", "metadata_": {}})
    assert response.status_code == 201
    session_id = response.json()["id"]

    # Mock the provider router to return a fake response
    from app.providers.router import provider_router
    from app.providers.base import ProviderResponse
    
    async def mock_generate(*args, **kwargs):
        return ProviderResponse(
            content="Mocked Assistant Response",
            provider="ollama",
            model="qwen3:4b"
        )
    
    # We patch the instance method
    from unittest.mock import patch
    with patch.object(provider_router, 'generate', new=mock_generate):
        chat_resp = await client.post(
            f"/api/v1/sessions/{session_id}/chat",
            json={"content": "Hello", "provider": "ollama"}
        )
    
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["content"] == "Mocked Assistant Response"
    assert data["provider"] == "ollama"
    assert "message_id" in data

    # Verify persistence
    messages_resp = await client.get(f"/api/v1/sessions/{session_id}/messages")
    assert messages_resp.status_code == 200
    msgs = messages_resp.json()["items"]
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Hello"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "Mocked Assistant Response"
    assert msgs[1]["metadata_"]["provider"] == "ollama"

@pytest.mark.asyncio
async def test_chat_provider_failure_does_not_create_fake_response(client, db_session):
    # Create a session
    response = await client.post("/api/v1/sessions", json={"title": "Test Error"})
    session_id = response.json()["id"]

    from app.providers.router import provider_router
    from fastapi import HTTPException
    
    async def mock_generate_error(*args, **kwargs):
        raise HTTPException(status_code=500, detail="Provider failed")
    
    from unittest.mock import patch
    with patch.object(provider_router, 'generate', new=mock_generate_error):
        chat_resp = await client.post(
            f"/api/v1/sessions/{session_id}/chat",
            json={"content": "This will fail"}
        )
    
    assert chat_resp.status_code == 500

    # Verify NO messages were persisted (neither user nor assistant)
    messages_resp = await client.get(f"/api/v1/sessions/{session_id}/messages")
    msgs = messages_resp.json()["items"]
    assert len(msgs) == 0, f"Expected 0 messages on provider failure, got {len(msgs)}"
