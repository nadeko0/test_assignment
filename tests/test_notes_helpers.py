"""Tests for the helper functions in the Notes API."""

import pytest
import asyncio
from datetime import datetime, UTC, timedelta
from unittest.mock import patch
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.notes import get_user_note, create_note_query, get_current_time
from app.models import Note

@pytest.mark.asyncio
async def test_get_user_note_helper(db: AsyncSession, sample_note):
    """Test the get_user_note helper function."""
    # Test successful retrieval
    note = await get_user_note(sample_note["id"], sample_note["user_id"], db)
    assert note.id == sample_note["id"]
    
    # Test 404 for nonexistent note
    with pytest.raises(HTTPException) as excinfo:
        await get_user_note(9999, sample_note["user_id"], db)
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail.lower()

@pytest.mark.asyncio
async def test_create_note_query():
    """Test the create_note_query helper function."""
    # Test basic query creation
    query = create_note_query(1, "test-user", include_deleted=False)
    query_str = str(query)
    assert "notes.id" in query_str
    assert "notes.user_id" in query_str
    assert "notes.is_deleted = false" in query_str.lower()
    
    # Test query with include_deleted=True
    query = create_note_query(1, "test-user", include_deleted=True)
    query_str = str(query)
    assert "notes.id" in query_str
    assert "notes.user_id" in query_str
    assert "notes.is_deleted = false" not in query_str.lower()

@pytest.mark.asyncio
async def test_note_with_time_sequence(client: AsyncClient, db: AsyncSession):
    """Test note operations ensuring timestamps follow expected sequence."""
    # Create a note
    note_data = {"title": "Time Test", "content": "Testing with timestamp sequence"}
    response = await client.post("/api/notes", json=note_data)
    assert response.status_code == 201
    
    # Get note ID and creation time
    note_id = response.json()["id"]
    created_at = datetime.fromisoformat(response.json()["created_at"])
    
    # Ensure creation time exists
    assert created_at is not None
    
    # Short delay to ensure timestamps can be differentiated
    await asyncio.sleep(0.5)
    
    # Update the note
    update_data = {"title": "Updated with New Time"}
    response = await client.put(f"/api/notes/{note_id}", json=update_data)
    assert response.status_code == 200
    
    # Get updated timestamp
    updated_at = datetime.fromisoformat(response.json()["updated_at"])
    
    # Verify timestamps are in correct sequence (updated time is same or after created time)
    assert updated_at >= created_at
    
    # Delete the note
    await client.delete(f"/api/notes/{note_id}")
    
    # Get note directly from DB to check deleted_at
    query = select(Note).where(Note.id == note_id)
    result = await db.execute(query)
    note = result.scalar_one()
    
    # Verify note is marked as deleted
    assert note.is_deleted is True
    assert note.deleted_at is not None
    
    # Verify deletion timestamp is same or after update timestamp
    assert note.deleted_at >= updated_at

@pytest.mark.asyncio
async def test_get_current_time():
    """Test the get_current_time function returns a UTC datetime."""
    time = get_current_time()
    assert time.tzinfo is not None
    assert time.tzinfo.tzname(time) == 'UTC'