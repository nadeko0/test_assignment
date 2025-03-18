"""Additional tests for the Notes API to improve coverage."""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import Request, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.api.notes import (
    get_or_create_user_id,
    check_note_limit,
    get_user_note,
    get_user_id,
    check_user_limit,
    create_note_query,
    USER_ID_COOKIE,
    COOKIE_MAX_AGE
)
from app.models import Note

@pytest.mark.asyncio
async def test_check_note_limit_at_limit(db: AsyncSession):
    """Test the note limit check when user is at the limit."""
    # Create 10 notes (the limit)
    user_id = "test-limit-user"
    for i in range(10):
        note = Note(
            title=f"Limit Test {i+1}",
            content=f"Test content {i+1}",
            user_id=user_id,
            is_deleted=False
        )
        db.add(note)
    await db.commit()
    
    # Check the limit - should return True (at limit)
    result = await check_note_limit(user_id, db)
    assert result is True

@pytest.mark.asyncio
async def test_check_note_limit_below_limit(db: AsyncSession):
    """Test the note limit check when user is below the limit."""
    # Create 5 notes (below the limit)
    user_id = "test-below-limit-user"
    for i in range(5):
        note = Note(
            title=f"Below Limit Test {i+1}",
            content=f"Test content {i+1}",
            user_id=user_id,
            is_deleted=False
        )
        db.add(note)
    await db.commit()
    
    # Check the limit - should return False (below limit)
    result = await check_note_limit(user_id, db)
    assert result is False

@pytest.mark.asyncio
async def test_check_note_limit_with_deleted_notes(db: AsyncSession):
    """Test that deleted notes don't count towards the limit."""
    # Create 8 active notes and 5 deleted notes
    user_id = "test-deleted-notes-user"
    
    # Active notes
    for i in range(8):
        note = Note(
            title=f"Active Note {i+1}",
            content=f"Active content {i+1}",
            user_id=user_id,
            is_deleted=False
        )
        db.add(note)
    
    # Deleted notes
    for i in range(5):
        note = Note(
            title=f"Deleted Note {i+1}",
            content=f"Deleted content {i+1}",
            user_id=user_id,
            is_deleted=True
        )
        db.add(note)
    
    await db.commit()
    
    # Check the limit - should return False (below limit with 8 active notes)
    result = await check_note_limit(user_id, db)
    assert result is False

@pytest.mark.asyncio
async def test_check_user_limit_throws_exception(db: AsyncSession):
    """Test that check_user_limit throws an exception when at limit."""
    # Mock the check_note_limit to return True (at limit)
    with patch('app.api.notes.check_note_limit', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        
        # Try to pass the limit check (should raise exception)
        with pytest.raises(HTTPException) as excinfo:
            await check_user_limit(user_id="test-user", session=db)
        
        # Verify exception details
        assert excinfo.value.status_code == 403
        assert "limit" in excinfo.value.detail.lower()

@pytest.mark.asyncio
async def test_check_user_limit_passes(db: AsyncSession):
    """Test that check_user_limit passes when below limit."""
    # Mock the check_note_limit to return False (below limit)
    with patch('app.api.notes.check_note_limit', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False
        
        # Should pass without exception
        result = await check_user_limit(user_id="test-user", session=db)
        assert result is None

@pytest.mark.asyncio
async def test_create_note_with_version_history(client: AsyncClient, db: AsyncSession):
    """Test creating a note with version history."""
    # Create a new note
    note_data = {
        "title": "Version History Test",
        "content": "Testing version history creation"
    }
    
    response = await client.post("/api/notes", json=note_data)
    assert response.status_code == 201
    
    # Get the note ID
    note_id = response.json()["id"]
    
    # Get version history
    response = await client.get(f"/api/notes/{note_id}/versions")
    assert response.status_code == 200
    
    # Verify version history
    versions = response.json()
    assert len(versions) == 1  # Should have initial version
    assert "1" in versions  # Version 1 should exist
    assert versions["1"]["title"] == note_data["title"]
    assert versions["1"]["content"] == note_data["content"]

@pytest.mark.asyncio
async def test_delete_note_permanently(client: AsyncClient, db: AsyncSession):
    """Test permanently deleting a note."""
    # Create a note
    note_data = {
        "title": "Permanent Delete Test",
        "content": "This will be permanently deleted"
    }
    
    response = await client.post("/api/notes", json=note_data)
    assert response.status_code == 201
    note_id = response.json()["id"]
    
    # Permanently delete the note
    response = await client.delete(f"/api/notes/{note_id}?permanent=true")
    assert response.status_code == 204
    
    # Verify note is completely gone
    response = await client.get(f"/api/notes/{note_id}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_restore_note_at_limit(client: AsyncClient, db: AsyncSession):
    """Test restoring a note when user is at the limit."""
    # Create a deleted note
    deleted_note = Note(
        title="Restore At Limit",
        content="Test restoring at limit",
        user_id="test-user-id",
        is_deleted=True
    )
    db.add(deleted_note)
    await db.commit()
    await db.refresh(deleted_note)
    
    # Mock check_note_limit to return True (at limit)
    with patch('app.api.notes.check_note_limit', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        
        # Try to restore
        response = await client.post(f"/api/notes/{deleted_note.id}/restore")
        assert response.status_code == 403
        assert "limit" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_create_note_query_different_scenarios():
    """Test creating queries with different parameters."""
    # Basic query
    query1 = create_note_query(1, "test-user", include_deleted=False)
    query_str1 = str(query1)
    assert "notes.id = :id_1" in query_str1
    assert "notes.user_id = :user_id_1" in query_str1
    assert "notes.is_deleted = false" in query_str1.lower()
    
    # Query with deleted notes
    query2 = create_note_query(2, "test-user", include_deleted=True)
    query_str2 = str(query2)
    assert "notes.id = :id_1" in query_str2
    assert "notes.user_id = :user_id_1" in query_str2
    assert "notes.is_deleted = false" not in query_str2.lower()

@pytest.mark.asyncio
async def test_cookie_max_age():
    """Test that cookie has the correct max age set."""
    # Create mock request with no cookies
    request = MagicMock(spec=Request)
    request.cookies = {}
    request.headers = {}
    
    # Create mock response for cookie setting
    response = MagicMock(spec=Response)
    
    # Call the function
    user_id = await get_or_create_user_id(request, response)
    
    # Verify cookie max age is set correctly
    assert response.set_cookie.call_args[1]["max_age"] == COOKIE_MAX_AGE
    assert COOKIE_MAX_AGE == 60 * 60 * 24 * 30  # 30 days

@pytest.mark.asyncio
async def test_get_notes_with_invalid_params(client: AsyncClient):
    """Test get notes endpoint with invalid parameters."""
    # Test with negative skip value
    response = await client.get("/api/notes?skip=-1")
    assert response.status_code == 422  # Validation error
    
    # Test with limit outside allowed range
    response = await client.get("/api/notes?limit=0")
    assert response.status_code == 422  # Validation error
    
    response = await client.get("/api/notes?limit=101")
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_get_user_id_dependency(db: AsyncSession):
    """Test the get_user_id dependency."""
    # Create mocks
    request = MagicMock(spec=Request)
    request.cookies = {"notes_user_id": "test-dependency-id"}
    request.headers = {}
    
    response = MagicMock(spec=Response)
    
    # With patch to skip the full dependency resolution
    with patch('app.api.notes.get_or_create_user_id', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = "test-dependency-id"
        
        # Call the dependency
        user_id = await get_user_id(request, response)
        
        # Verify
        assert user_id == "test-dependency-id"
        mock_get.assert_called_once_with(request, response)

@pytest.mark.asyncio
async def test_update_note_with_version_history(client: AsyncClient, db: AsyncSession):
    """Test updating a note and verifying version history is created."""
    # Create a note
    note_data = {
        "title": "Version History Test",
        "content": "Initial content for version history testing"
    }
    
    # Create the note
    response = await client.post("/api/notes", json=note_data)
    assert response.status_code == 201
    note_id = response.json()["id"]
    
    # Verify initial version
    versions_response = await client.get(f"/api/notes/{note_id}/versions")
    assert versions_response.status_code == 200
    versions = versions_response.json()
    assert len(versions) == 1
    
    # Update the note
    update_data = {
        "title": "Updated Version Test",
        "content": "Updated content for version history testing"
    }
    update_response = await client.put(f"/api/notes/{note_id}", json=update_data)
    assert update_response.status_code == 200
    
    # Verify new version was added
    versions_response = await client.get(f"/api/notes/{note_id}/versions")
    assert versions_response.status_code == 200
    versions = versions_response.json()
    assert len(versions) == 2
    
    # Check that the version content is correct
    assert "1" in versions
    assert "2" in versions
    assert versions["1"]["content"] == note_data["content"]
    assert versions["2"]["content"] == update_data["content"]

@pytest.mark.asyncio
async def test_partial_note_update(client: AsyncClient, db: AsyncSession):
    """Test updating only title or only content of a note."""
    # Create a note
    note_data = {
        "title": "Partial Update Test",
        "content": "Initial content for partial update testing"
    }
    
    # Create the note
    response = await client.post("/api/notes", json=note_data)
    assert response.status_code == 201
    note_id = response.json()["id"]
    
    # Update only title
    title_update = {
        "title": "Updated Title Only"
    }
    title_response = await client.put(f"/api/notes/{note_id}", json=title_update)
    assert title_response.status_code == 200
    assert title_response.json()["title"] == "Updated Title Only"
    assert title_response.json()["content"] == note_data["content"]
    
    # Update only content
    content_update = {
        "content": "Updated content only"
    }
    content_response = await client.put(f"/api/notes/{note_id}", json=content_update)
    assert content_response.status_code == 200
    assert content_response.json()["title"] == "Updated Title Only"
    assert content_response.json()["content"] == "Updated content only"

@pytest.mark.asyncio
async def test_soft_delete_and_restore_flow(client: AsyncClient, db: AsyncSession):
    """Test the complete flow of creating, soft deleting, and restoring a note."""
    # Create a note
    note_data = {
        "title": "Delete Restore Flow Test",
        "content": "Testing the full delete-restore flow"
    }
    
    # Create the note
    response = await client.post("/api/notes", json=note_data)
    assert response.status_code == 201
    note_id = response.json()["id"]
    
    # Soft delete the note
    delete_response = await client.delete(f"/api/notes/{note_id}")
    assert delete_response.status_code == 204
    
    # Verify note is not found with regular query
    get_response = await client.get(f"/api/notes/{note_id}")
    assert get_response.status_code == 404
    
    # Verify note is included when querying deleted notes
    deleted_response = await client.get(f"/api/notes?include_deleted=true")
    deleted_notes = deleted_response.json()
    assert any(note["id"] == note_id for note in deleted_notes)
    
    # Restore the note
    restore_response = await client.post(f"/api/notes/{note_id}/restore")
    assert restore_response.status_code == 200
    
    # Verify note is accessible again
    get_response = await client.get(f"/api/notes/{note_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == note_id
    assert get_response.json()["is_deleted"] is False
    assert get_response.json()["deleted_at"] is None