import pytest
from httpx import AsyncClient
from uuid import uuid4
from fastapi import status
from app.models.message import Message

@pytest.mark.asyncio
async def test_generate_essay_success(client: AsyncClient, db_session, monkeypatch):
    # Setup session
    from app.services.session_service import SessionService
    from app.schemas.session import SessionCreate
    session = await SessionService.create_session(db_session, SessionCreate(title="Test"))
    
    # Send essay request
    essay_request = {
        "topic": "Product-Led Growth",
        "target_audience": "Founders",
        "central_argument": "PLG is superior",
        "provider": "claude"
    }
    
    from app.providers.router import provider_router
    from app.providers.base import ProviderResponse
    
    async def mock_generate(*args, **kwargs):
        return ProviderResponse(
            content="<essay>\n# The Power of PLG\n\n" + "Word " * 1250 + "</essay>",
            provider="claude",
            model="claude-3-haiku"
        )
        
    monkeypatch.setattr(provider_router, "generate", mock_generate)
    
    session_id = session.id
    response = await client.post(f"/api/v1/sessions/{session_id}/essay", json=essay_request)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["title"] == "The Power of PLG"
    assert data["word_count"] >= 800
    assert "citations" in data
    
    # Check if messages were persisted
    msg_response = await client.get(f"/api/v1/sessions/{session_id}/messages")
    messages = msg_response.json()["items"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert "Ship 30 for 30" in messages[0]["content"]
    assert messages[1]["role"] == "assistant"
    assert messages[1]["metadata_"]["type"] == "essay"

@pytest.mark.asyncio
async def test_generate_essay_retry_on_length(client: AsyncClient, db_session, monkeypatch):
    # Setup session
    from app.services.session_service import SessionService
    from app.schemas.session import SessionCreate
    session = await SessionService.create_session(db_session, SessionCreate(title="Test 2"))
    
    essay_request = {
        "topic": "Short Essay",
    }
    
    # First response is too short. Second response is good.
    responses = [
        "<essay>\n# Short\n\nToo short.</essay>",
        "<essay>\n# Longer\n\n" + "Word " * 1250 + "</essay>"
    ]
    
    from app.providers.router import provider_router
    from app.providers.base import ProviderResponse
    
    async def mock_generate(*args, **kwargs):
        content = responses.pop(0) if responses else ""
        return ProviderResponse(
            content=content,
            provider="claude",
            model="claude-3-haiku"
        )
        
    monkeypatch.setattr(provider_router, "generate", mock_generate)
    
    session_id = session.id
    response = await client.post(f"/api/v1/sessions/{session_id}/essay", json=essay_request)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["title"] == "Longer"
    assert data["word_count"] >= 800
