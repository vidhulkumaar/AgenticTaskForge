import asyncio
from app.db.session import engine
from sqlalchemy import text
import json

async def main():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT count(*) FROM transcript_chunks;"))
        count = res.scalar()
        print(f"Chunks count: {count}")
        
        res = await conn.execute(text("SELECT embedding FROM transcript_chunks LIMIT 1;"))
        embedding_str = res.scalar()
        if embedding_str:
            try:
                emb = json.loads(embedding_str)
                print(f"Embedding type: {type(emb)}, len: {len(emb)}")
                print(f"Sample values: {emb[:5]}")
            except Exception as e:
                print(f"Failed to parse embedding: {e}")

asyncio.run(main())
