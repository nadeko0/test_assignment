"""Final targeted tests for the Notes API to achieve 80% coverage."""

import pytest
import asyncio
from datetime import datetime, UTC, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import Request, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from sqlalchemy import select, func, delete

from app.api.notes import (
    get_or_create_user_id,
    check_note_limit,
    get_user_note,
    get_user_id,
    check_user_limit,
    create_note_query,
    USER_ID_COOKIE,
    COOKIE_MAX_AGE,
    get_notes,
    update_note,
    delete_note,
    restore_note
)
from app.models import Note

@pytest.mark.asyncio
async def test_direct_update_note(client: AsyncClient, db: AsyncSession):
    """Test update_note function directly to improve coverage."""
    # Create a note
    note = Note(
        title="Direct Update Test",
        content="Testing direct update function",
        user_id="test-user-id"
    )
    note.add_version()
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    # Create update data
    update_data = {
        "title": "Updated Direct Title",
        "content": "Updated direct content"
    }
    
    # Create mock request
    mock_request = MagicMock()
    mock_request.path_params = {"note_id": note.id}
    
    # Create update dependencies
    class MockData:
        title = update_data["title"]
        content = update_data["content"]
    
    # Get the initial note version count
    initial_version_count = len(note.versions)
    
    # Call update_note directly
    result = await update_note(
        note_id=note.id,
        note_data=MockData(),
        user_id="test-user-id",
        session=db,
        current_time=datetime.now(UTC)
    )
    
    # Assert result is correct
    assert result.id == note.id
    assert result.title == update_data["title"]
    assert result.content == update_data["content"]
    
    # Assert version was added
    assert len(result.versions) > initial_version_count

@pytest.mark.asyncio
async def test_direct_delete_note_permanent(db: AsyncSession):
    """Test delete_note function directly with permanent=True."""
    # Create a note
    note = Note(
        title="Direct Delete Test",
        content="Testing direct delete function",
        user_id="test-user-id"
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    note_id = note.id
    
    # Call delete_note directly with permanent=True
    await delete_note(
        note_id=note_id,
        permanent=True,
        user_id="test-user-id",
        session=db,
        current_time=datetime.now(UTC)
    )
    
    # Verify note is completely gone
    result = await db.execute(select(Note).where(Note.id == note_id))
    assert result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_direct_delete_note_soft(db: AsyncSession):
    """Test delete_note function directly with permanent=False."""
    # Create a note
    note = Note(
        title="Soft Delete Test",
        content="Testing soft delete function",
        user_id="test-user-id"
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    note_id = note.id
    
    # Call delete_note directly with permanent=False
    await delete_note(
        note_id=note_id,
        permanent=False,
        user_id="test-user-id",
        session=db,
        current_time=datetime.now(UTC)
    )
    
    # Verify note is marked as deleted
    result = await db.execute(select(Note).where(Note.id == note_id))
    deleted_note = result.scalar_one()
    assert deleted_note.is_deleted is True
    assert deleted_note.deleted_at is not None

@pytest.mark.asyncio
async def test_direct_restore_note(db: AsyncSession):
    """Test restore_note function directly."""
    # Create a deleted note
    note = Note(
        title="Direct Restore Test",
        content="Testing direct restore function",
        user_id="test-user-id",
        is_deleted=True,
        deleted_at=datetime.now(UTC)
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    note_id = note.id
    
    # Mock check_note_limit to return False (below limit)
    with patch('app.api.notes.check_note_limit', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False  # Below limit
        
        # Call restore_note directly
        result = await restore_note(
            note_id=note_id,
            user_id="test-user-id",
            session=db
        )
        
        # Verify note is restored
        assert result.is_deleted is False
        assert result.deleted_at is None

@pytest.mark.asyncio
async def test_get_notes_include_deleted_direct(db: AsyncSession):
    """Test get_notes function directly with include_deleted=True."""
    # Clear any existing notes
    await db.execute(delete(Note).where(Note.user_id == "test-user-id"))
    await db.commit()
    
    # Create a regular note
    note1 = Note(
        title="Regular Note",
        content="This is a regular note",
        user_id="test-user-id",
        is_deleted=False
    )
    db.add(note1)
    
    # Create a deleted note
    note2 = Note(
        title="Deleted Note",
        content="This is a deleted note",
        user_id="test-user-id",
        is_deleted=True,
        deleted_at=datetime.now(UTC)
    )
    db.add(note2)
    await db.commit()
    
    # Call get_notes directly with include_deleted=True
    notes = await get_notes(
        skip=0,
        limit=100,
        include_deleted=True,
        user_id="test-user-id",
        session=db
    )
    
    # Verify both notes are returned
    assert len(notes) == 2
    assert any(note.is_deleted for note in notes)
    assert any(not note.is_deleted for note in notes)
    
    # Call get_notes directly with include_deleted=False
    regular_notes = await get_notes(
        skip=0,
        limit=100,
        include_deleted=False,
        user_id="test-user-id",
        session=db
    )
    
    # Verify only regular notes are returned
    assert len(regular_notes) == 1
    assert all(not note.is_deleted for note in regular_notes)

@pytest.mark.asyncio
async def test_exception_handling_in_api_routes(client: AsyncClient, db: AsyncSession):
    """Test exception handling in API routes using direct calls to get_user_note."""
    # Create a path where get_user_note throws an exception
    with patch('app.api.notes.get_user_note', side_effect=HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error"
    )):
        # Call the notes API that uses get_user_note
        response = await client.get("/api/notes/1")
        
        # Verify the exception is propagated correctly
        assert response.status_code == 500
        assert "internal server error" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_cookie_security_settings():
    """Test the cookie security settings in get_or_create_user_id."""
    # Create request with no cookies
    request = MagicMock(spec=Request)
    request.cookies = {}
    request.headers = {}
    
    # Create response for cookie setting
    response = MagicMock(spec=Response)
    
    # Call function
    await get_or_create_user_id(request, response)
    
    # Verify security settings of cookie
    call_args = response.set_cookie.call_args[1]
    assert call_args["httponly"] is True  # Ensure httponly is set
    assert call_args["samesite"] == "lax"  # Ensure samesite policy is set
    assert call_args["max_age"] == COOKIE_MAX_AGE  # Verify correct max age