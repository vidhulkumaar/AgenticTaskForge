import asyncio
from app.db.session import AsyncSessionLocal
from app.services.retrieval_service import get_retrieval_service

async def main():
    rs = get_retrieval_service()
    
    async with AsyncSessionLocal() as db:
        q = "Why is retention more important than acquisition?"
        print(f"\nQuery: {q}")
        results = await rs.search(db, q, top_k=5, similarity_threshold=0.0)
        for r in results:
            print(f"Score: {r.similarity_score:.4f} | {r.episode_title} | {r.content[:50]}...")

if __name__ == "__main__":
    asyncio.run(main())
