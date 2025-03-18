"""Unit tests for database module."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from app.database import get_session, engine

@pytest.mark.asyncio
async def test_get_session():
    """Test the session dependency works correctly."""
    # Get a session
    session_gen = get_session()
    session = await anext(session_gen)
    
    assert isinstance(session, AsyncSession)
    
    # Test basic database operation with session
    result = await session.execute(select(1))
    assert result.scalar_one() == 1
    
    # Make sure we can close the session
    try:
        await session.close()
        await anext(session_gen, None)
    except StopAsyncIteration:
        pass  # Expected behavior

@pytest.mark.asyncio
async def test_engine_connection():
    """Test that the database engine can connect."""
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar_one() == 1

@pytest.mark.asyncio
async def test_session_transaction_commit():
    """Test session with transaction commit."""
    async with AsyncSession(engine) as session:
        async with session.begin():
            # Just a read-only query to test transaction
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
            # Transaction will be committed automatically

@pytest.mark.asyncio
async def test_session_transaction_rollback():
    """Test session with transaction rollback."""
    async with AsyncSession(engine) as session:
        # Start transaction explicitly
        trans = await session.begin()
        
        try:
            # Read-only query
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
            
            # Rollback transaction
            await trans.rollback()
            
            # Can start a new transaction after rollback
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
        finally:
            # Make sure transaction is cleaned up
            if trans.is_active:
                await trans.rollback()