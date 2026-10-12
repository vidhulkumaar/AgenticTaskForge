import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db

# Use an in-memory SQLite database for testing, but since we use Postgres specific features (like UUID), 
# we should ideally use a test Postgres DB.
# For simplicity in this assessment, we'll try to use a test sqlite if it works with UUID, 
# but postgres UUID might fail in sqlite. Let's assume the user will run tests against a local test postgres,
# or we use an asyncpg URL.
# Let's override DATABASE_URL for tests.

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine_test, class_=AsyncSession)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine_test.dispose()

@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
