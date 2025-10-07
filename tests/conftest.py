import os
import sys
from pathlib import Path
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from dotenv import load_dotenv

from app.main import app
from app.models.models import Base

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment to test BEFORE loading dotenv
os.environ["ENV"] = "test"

# Load test environment variables
load_dotenv(dotenv_path=".env.test", override=True)

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env.test file")

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine for each test"""
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create a test database session for each test"""
    async_session = async_sessionmaker(
        db_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Create a test client with overridden database dependency"""
    from app.utils.db import get_db_session
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    # Use ASGITransport for httpx AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()