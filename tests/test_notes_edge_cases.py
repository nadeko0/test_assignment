"""Edge case tests for the Notes API to complete coverage."""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import Request, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from sqlalchemy import select, func

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
    delete_note
)
from app.models import Note

@pytest.mark.asyncio
async def test_get_notes_pagination_and_sorting(client: AsyncClient, db: AsyncSession):
    """Test note pagination and sorting by updated_at."""
    # Clear any existing notes
    for note in await db.execute(select(Note).where(Note.user_id == "test-user-id")):
        await db.delete(note.scalar())
    await db.commit()
    
    # Create notes with different timestamps
    for i in range(5):
        note = Note(
            title=f"Pagination Test {i+1}",
            content=f"Content {i+1}",
            user_id="test-user-id"
        )
        # Set created_at to different times
        offset = timedelta(minutes=i)
        note.created_at = datetime.now(UTC) - offset
        note.updated_at = datetime.now(UTC) - offset
        db.add(note)
    
    await db.commit()
    
    # Test basic pagination (skip=0, limit=3)
    response = await client.get("/api/notes?skip=0&limit=3")
    assert response.status_code == 200
    page1 = response.json()
    assert len(page1) == 3
    
    # Test second page (skip=3, limit=3)
    response = await client.get("/api/notes?skip=3&limit=3")
    assert response.status_code == 200
    page2 = response.json()
    assert len(page2) > 0
    
    # Verify no overlap between pages
    page1_ids = [note["id"] for note in page1]
    page2_ids = [note["id"] for note in page2]
    assert not any(note_id in page1_ids for note_id in page2_ids)
    
    # Verify sorting by updated_at (most recent first)
    for i in range(1, len(page1)):
        assert page1[i-1]["updated_at"] >= page1[i]["updated_at"]

@pytest.mark.asyncio
async def test_missing_cookie_and_header(db: AsyncSession):
    """Test user ID generation with no cookie and no testing header."""
    # Create request with no cookies and no testing header
    request = MagicMock(spec=Request)
    request.cookies = {}
    request.headers = {}
    
    # Create response for cookie setting
    response = MagicMock(spec=Response)
    
    # Call function
    user_id = await get_or_create_user_id(request, response)
    
    # Verify UUID was generated (36 chars with hyphens)
    assert len(user_id) == 36
    assert "-" in user_id
    
    # Verify cookie was set with correct parameters
    response.set_cookie.assert_called_once()
    cookie_params = response.set_cookie.call_args[1]
    assert cookie_params["key"] == USER_ID_COOKIE
    assert cookie_params["value"] == user_id
    assert cookie_params["httponly"] is True
    assert cookie_params["samesite"] == "lax"

@pytest.mark.asyncio
async def test_get_nonexistent_note_with_include_deleted(client: AsyncClient):
    """Test fetching a nonexistent note with include_deleted=True."""
    # Use a note ID that definitely doesn't exist
    nonexistent_id = 9999
    
    # Test get_note for nonexistent note with include_deleted=True
    # This is a direct API test for the get_user_note function with include_deleted=True
    with patch('app.api.notes.get_user_note') as mock_get:
        # Set up mock to raise 404
        mock_get.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {nonexistent_id} not found"
        )
        
        # Call the endpoint
        response = await client.get(f"/api/notes/{nonexistent_id}?include_deleted=true")
        
        # Verify 404 response
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_update_nonexistent_note_detailed(client: AsyncClient):
    """Test updating a nonexistent note with detailed error checking."""
    # Use a note ID that definitely doesn't exist
    nonexistent_id = 9999
    
    # Prepare update data
    update_data = {
        "title": "Updated Title",
        "content": "Updated content"
    }
    
    # Call update endpoint
    response = await client.put(f"/api/notes/{nonexistent_id}", json=update_data)
    
    # Verify 404 response with correct error message
    assert response.status_code == 404
    assert "note with id 9999 not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_delete_already_deleted_note(client: AsyncClient, db: AsyncSession):
    """Test deleting a note that's already deleted."""
    # Create a deleted note
    note = Note(
        title="Already Deleted",
        content="This note is already deleted",
        user_id="test-user-id",
        is_deleted=True,
        deleted_at=datetime.now(UTC) - timedelta(days=1)
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    # Try to delete it again
    response = await client.delete(f"/api/notes/{note.id}")
    
    # Should still return 204 (success) even though it was already deleted
    assert response.status_code == 204
    
    # Verify in database that it's still deleted
    await db.refresh(note)
    assert note.is_deleted is True

@pytest.mark.asyncio
async def test_permanent_delete_nonexistent_note(client: AsyncClient):
    """Test permanently deleting a nonexistent note."""
    # Use a note ID that definitely doesn't exist
    nonexistent_id = 9999
    
    # Try to permanently delete
    response = await client.delete(f"/api/notes/{nonexistent_id}?permanent=true")
    
    # Should return 404
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_restore_nonexistent_note(client: AsyncClient):
    """Test restoring a nonexistent note."""
    # Use a note ID that definitely doesn't exist
    nonexistent_id = 9999
    
    # Try to restore
    response = await client.post(f"/api/notes/{nonexistent_id}/restore")
    
    # Verify 404 response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_get_notes_order_by_updated(client: AsyncClient, db: AsyncSession):
    """Test that notes are ordered by updated_at in descending order."""
    # Create a note with an old timestamp
    old_note = Note(
        title="Old Note",
        content="This note has an old timestamp",
        user_id="test-user-id"
    )
    old_note.updated_at = datetime.now(UTC) - timedelta(days=7)
    db.add(old_note)
    
    # Create a note with a recent timestamp
    new_note = Note(
        title="New Note",
        content="This note has a recent timestamp",
        user_id="test-user-id"
    )
    new_note.updated_at = datetime.now(UTC)
    db.add(new_note)
    
    await db.commit()
    
    # Get notes list
    response = await client.get("/api/notes")
    assert response.status_code == 200
    
    notes = response.json()
    
    # Verify order (newest first)
    if len(notes) >= 2:
        # Find our test notes by title
        old_note_idx = next((i for i, n in enumerate(notes) if n["title"] == "Old Note"), -1)
        new_note_idx = next((i for i, n in enumerate(notes) if n["title"] == "New Note"), -1)
        
        # If both test notes are found, verify their order
        if old_note_idx != -1 and new_note_idx != -1:
            assert new_note_idx < old_note_idx, "Newer note should come before older note"

@pytest.mark.asyncio
async def test_get_user_id_caching(db: AsyncSession):
    """Test that get_user_id properly returns and caches the user ID."""
    # Create request with an existing cookie
    user_id = "cached-user-id-test"
    request = MagicMock(spec=Request)
    request.cookies = {USER_ID_COOKIE: user_id}
    request.headers = {}
    
    response = MagicMock(spec=Response)
    
    # Call function
    result = await get_user_id(request, response)
    
    # Verify the existing ID was returned and not changed
    assert result == user_id
    response.set_cookie.assert_not_called()
    
    # Create a request without cookie to test ID generation
    request_no_cookie = MagicMock(spec=Request)
    request_no_cookie.cookies = {}
    request_no_cookie.headers = {}
    
    # Call function again
    result2 = await get_user_id(request_no_cookie, response)
    
    # Verify a new ID was generated and cookie was set
    assert result2 is not None
    assert len(result2) > 0
    assert result2 != user_id
    response.set_cookie.assert_called_once()