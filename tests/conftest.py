"""Test configuration and fixtures for pytest."""

import os
import time
import gc
import asyncio
import pytest
import pytest_asyncio
import httpx
from typing import AsyncGenerator, Dict, Any
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base, get_session
from app.models import Note
from main import app

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create async engine for tests
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

# Create async session factory for tests
test_async_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Override the get_session dependency
async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async session for tests."""
    async with test_async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

# Set up the app with overridden dependencies
app.dependency_overrides[get_session] = override_get_session

# Mocks for external services
class MockRedisService:
    """Mock Redis service for testing."""
    
    async def is_connected(self) -> bool:
        return True
    
    async def set_value(self, key: str, value: Any, ttl: int = 3600) -> bool:
        return True
    
    async def get_value(self, key: str) -> Any:
        return None
    
    async def delete_value(self, key: str) -> bool:
        return True
    
    async def get_note_summary(self, note_id: int, language: str = "en") -> Dict[str, Any]:
        return None
    
    async def set_note_summary(self, note_id: int, summary_data: Dict[str, Any], language: str = "en") -> bool:
        return True
    
    async def invalidate_note_summary(self, note_id: int, language: str = "en") -> bool:
        return True

class MockAIService:
    """Mock AI service for testing."""
    
    async def summarize_note(self, note_id: int, title: str, content: str, language: str = "en") -> Dict[str, Any]:
        return {
            "note_id": note_id,
            "original_title": title,
            "summary": f"Mock summary of: {title}",
            "generated_at": "2025-03-15T12:00:00Z",
            "language": language
        }

# Create a fixture for initializing the database before tests
@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Set up the database before any tests run."""
    # Run setup synchronously to ensure it completes before any tests
    asyncio.run(_setup_database())
    yield
    # Cleanup after all tests
    try:
        # Force garbage collection to release file handles
        gc.collect()
        time.sleep(0.5)
        # Try to remove the test database file
        if os.path.exists("./test.db"):
            os.remove("./test.db")
    except Exception:
        pass  # Ignore cleanup errors

async def _setup_database():
    """Set up database tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for tests."""
    async with test_async_session_maker() as session:
        # Clear existing data for a clean test
        try:
            await session.execute(text("DELETE FROM notes"))
            await session.commit()
        except Exception:
            await session.rollback()
        
        yield session
        
        # Clean up after test
        await session.rollback()

# Use AsyncClient for async tests
@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Get an async test client for FastAPI app."""
    # Create transport for the FastAPI app
    transport = httpx.ASGITransport(app=app)
    
    # Create AsyncClient with the transport and testing header
    async with AsyncClient(
        transport=transport, 
        base_url="http://testserver",
        headers={"testing": "true"}  # Add testing header to ensure consistent user_id
    ) as ac:
        yield ac

@pytest_asyncio.fixture
async def sample_note(db: AsyncSession) -> Dict[str, Any]:
    """Create a sample note for testing."""
    note = Note(
        title="Test Note",
        content="This is a test note content.",
        user_id="test-user-id"
    )
    # Ensure version is added properly
    note.add_version()
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "user_id": note.user_id
    }

@pytest.fixture(scope="session", autouse=True)
def mock_services():
    """Mock external services for all tests."""
    import app.services.cache
    import app.services.ai
    
    # Save original services
    original_redis = app.services.cache.redis_service
    original_ai = app.services.ai.ai_service
    
    # Replace with mocks
    app.services.cache.redis_service = MockRedisService()
    app.services.ai.ai_service = MockAIService()
    
    yield
    
    # Restore original services
    app.services.cache.redis_service = original_redis
    app.services.ai.ai_service = original_ai