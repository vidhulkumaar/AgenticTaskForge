import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.retrieval_service import get_retrieval_service

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///alembic.db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    retrieval_service = get_retrieval_service()
    
    async with async_session() as session:
        try:
            results = await retrieval_service.search(session, "test query")
            print(f"Success, found {len(results)} results")
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
