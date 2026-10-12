import pytest
from httpx import AsyncClient
from uuid import uuid4

pytestmark = pytest.mark.asyncio

async def test_health_live(client: AsyncClient):
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

async def test_health_ready(client: AsyncClient):
    response = await client.get("/health/ready")
    data = response.json()
    # In test environment with SQLite, DB check passes. Ollama may or may not be available.
    if response.status_code == 200:
        assert data["status"] == "ok"
        assert "checks" in data
        assert data["checks"]["database"] == "ok"
    else:
        # 503 means Ollama is unreachable but DB is fine
        assert response.status_code == 503
        assert "checks" in data.get("detail", {})

async def test_create_session(client: AsyncClient):
    response = await client.post("/api/v1/sessions", json={"title": "Test Session"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Session"
    assert "id" in data

async def test_get_session(client: AsyncClient):
    # Create first
    create_resp = await client.post("/api/v1/sessions", json={"title": "Session 2"})
    session_id = create_resp.json()["id"]

    # Get
    get_resp = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == session_id

async def test_get_unknown_session(client: AsyncClient):
    random_id = str(uuid4())
    get_resp = await client.get(f"/api/v1/sessions/{random_id}")
    assert get_resp.status_code == 404

async def test_list_sessions(client: AsyncClient):
    await client.post("/api/v1/sessions", json={"title": "Session A"})
    await client.post("/api/v1/sessions", json={"title": "Session B"})
    
    resp = await client.get("/api/v1/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 2
    assert "total" in data

async def test_create_and_list_messages(client: AsyncClient):
    # Create session
    create_resp = await client.post("/api/v1/sessions", json={"title": "Session for Messages"})
    session_id = create_resp.json()["id"]

    # Add message
    msg_resp = await client.post(f"/api/v1/sessions/{session_id}/messages", json={
        "role": "user",
        "content": "Hello!"
    })
    assert msg_resp.status_code == 201
    msg_data = msg_resp.json()
    assert msg_data["role"] == "user"
    assert msg_data["content"] == "Hello!"

    # List messages
    list_resp = await client.get(f"/api/v1/sessions/{session_id}/messages")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert list_data["items"][0]["content"] == "Hello!"

async def test_delete_session(client: AsyncClient):
    create_resp = await client.post("/api/v1/sessions", json={"title": "To be deleted"})
    session_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/sessions/{session_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 404
