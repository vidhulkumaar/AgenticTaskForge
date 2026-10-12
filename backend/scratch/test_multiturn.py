import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        # Create a session
        resp = await client.post("/api/v1/sessions", json={"title": "Multi-turn Test"})
        session_id = resp.json()["id"]

        queries = [
            "How does Superhuman measure product-market fit?",
            "What example did the guest give?",
            "Explain that in simpler terms.",
            "Can you tell me how to bake a cake?"
        ]

        for q in queries:
            print(f"\nUser: {q}")
            resp = await client.post(f"/api/v1/sessions/{session_id}/chat", json={
                "content": q,
                "provider": "ollama"
            })
            if resp.status_code != 200:
                print(f"Error: {resp.status_code} {resp.text}")
                continue
            data = resp.json()
            print(f"Assistant: {data['content']}\n")
            print(f"Citations: {[c['episode_title'] for c in data.get('citations', [])]}")

if __name__ == "__main__":
    asyncio.run(main())
