import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.services.retrieval_service import get_retrieval_service
from app.models.knowledge_base import TranscriptChunk, TranscriptDocument

async def main():
    rs = get_retrieval_service()
    
    async with AsyncSessionLocal() as db:
        q = "What is the smile curve of retention?"
        print(f"\nQuery: {q}")
        results = await rs.search(db, q, top_k=5, similarity_threshold=0.0)
        for r in results:
            print(f"Score: {r.similarity_score:.4f} | {r.episode_title} | {r.content[:50]}...")
            
        q = "How do you calculate retention rate?"
        print(f"\nQuery: {q}")
        results = await rs.search(db, q, top_k=5, similarity_threshold=0.0)
        for r in results:
            print(f"Score: {r.similarity_score:.4f} | {r.episode_title} | {r.content[:50]}...")

        q = "What is the best recipe for baking chocolate chip cookies?"
        print(f"\nQuery: {q}")
        results = await rs.search(db, q, top_k=5, similarity_threshold=0.0)
        for r in results:
            print(f"Score: {r.similarity_score:.4f} | {r.episode_title} | {r.content[:50]}...")

if __name__ == "__main__":
    asyncio.run(main())
