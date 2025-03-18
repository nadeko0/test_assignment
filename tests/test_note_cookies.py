"""Tests for cookie handling and user ID management in Notes API."""

import pytest
import httpx
from httpx import AsyncClient, ASGITransport
from fastapi import Response, Request
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.notes import get_or_create_user_id, USER_ID_COOKIE
from main import app

@pytest.mark.asyncio
async def test_get_user_id_with_new_cookie():
    """Test that a new user ID is created when no cookie exists."""
    # Create mock request with no cookies
    request = MagicMock(spec=Request)
    request.cookies = {}
    request.headers = {}
    
    # Create mock response for cookie setting
    response = MagicMock(spec=Response)
    
    # Call the function
    user_id = await get_or_create_user_id(request, response)
    
    # Verify a user ID was generated (UUID format)
    assert user_id is not None
    assert len(user_id) > 0
    
    # Verify a cookie was set with the user ID
    response.set_cookie.assert_called_once()
    # Check the cookie name is correct
    assert response.set_cookie.call_args[1]["key"] == USER_ID_COOKIE
    # Check the value matches the returned user ID
    assert response.set_cookie.call_args[1]["value"] == user_id
    # Verify cookie is httponly for security
    assert response.set_cookie.call_args[1]["httponly"] is True

@pytest.mark.asyncio
async def test_get_user_id_with_existing_cookie():
    """Test that an existing user ID is retrieved from cookies."""
    # Create mock request with existing cookie
    existing_id = "existing-user-id-12345"
    request = MagicMock(spec=Request)
    request.cookies = {USER_ID_COOKIE: existing_id}
    request.headers = {}
    
    # Create mock response
    response = MagicMock(spec=Response)
    
    # Call the function
    user_id = await get_or_create_user_id(request, response)
    
    # Verify the existing ID is returned
    assert user_id == existing_id
    
    # Verify no cookie was set (existing one preserved)
    response.set_cookie.assert_not_called()

@pytest.mark.asyncio
async def test_get_user_id_with_testing_header():
    """Test that a test user ID is returned when testing header is present."""
    # Create mock request with testing header
    request = MagicMock(spec=Request)
    request.cookies = {}  # No cookies
    request.headers = {"testing": "true"}
    
    # Create mock response
    response = MagicMock(spec=Response)
    
    # Call the function
    user_id = await get_or_create_user_id(request, response)
    
    # Verify the test user ID is returned
    assert user_id == "test-user-id"
    
    # Verify no cookie was set (not needed for testing)
    response.set_cookie.assert_not_called()

@pytest.mark.asyncio
async def test_client_without_testing_header():
    """Test that the user ID cookie works as expected."""
    # Generate a specific test user ID to use
    test_user_id = "test-client-user-id-123456"
    
    # Use ASGITransport to connect to the app
    transport = httpx.ASGITransport(app=app)
    
    # First, test without a cookie - should generate a new ID
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver"
    ) as client:
        response = await client.get("/api/notes")
        
        # Should get a cookie back
        assert USER_ID_COOKIE in response.cookies
        
        # Remember this auto-generated ID
        generated_id = response.cookies[USER_ID_COOKIE]
        assert len(generated_id) > 0
    
    # Now test with an existing cookie - server should use this ID
    cookies = {USER_ID_COOKIE: test_user_id}
    
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        cookies=cookies
    ) as client:
        # Mock the get_or_create_user_id function to verify it receives the cookie
        with patch('app.api.notes.get_or_create_user_id', side_effect=get_or_create_user_id) as mock_get:
            response = await client.get("/api/notes")
            
            # The function should be called with a request containing our cookie
            call_args = mock_get.call_args[0]
            request = call_args[0]
            
            # Verify the cookie we sent is in the request
            assert USER_ID_COOKIE in request.cookies
            assert request.cookies[USER_ID_COOKIE] == test_user_id

@pytest.mark.asyncio
async def test_restore_note_not_in_trash(client: AsyncClient, db: AsyncSession):
    """Test that restoring a note that isn't in trash returns an error."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models import Note
    
    # Create a note that is NOT deleted
    note = Note(
        title="Not In Trash",
        content="This note is not in trash",
        user_id="test-user-id",
        is_deleted=False  # Note is not in trash
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    # Try to restore it (should fail because it's not in trash)
    response = await client.post(f"/api/notes/{note.id}/restore")
    assert response.status_code == 404
    assert "not found in trash" in response.json()["detail"].lower()