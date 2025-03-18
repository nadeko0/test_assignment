"""Integration tests for Notes API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete

from app.models import Note

@pytest.mark.asyncio
async def test_get_empty_notes(client: AsyncClient, db: AsyncSession):
    """Test getting empty notes list."""
    response = await client.get("/api/notes")
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_create_note(client: AsyncClient):
    """Test creating a new note."""
    note_data = {
        "title": "Test Note",
        "content": "This is a test note content."
    }
    
    response = await client.post("/api/notes", json=note_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["title"] == note_data["title"]
    assert data["content"] == note_data["content"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "versions" in data
    assert data["is_deleted"] is False

@pytest.mark.asyncio
async def test_get_notes_list(client: AsyncClient):
    """Test getting a list of notes after creation."""
    # Create a test note first
    note_data = {
        "title": "List Test",
        "content": "Testing notes list."
    }
    await client.post("/api/notes", json=note_data)
    
    # Get notes list
    response = await client.get("/api/notes")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) > 0
    assert any(note["title"] == "List Test" for note in data)

@pytest.mark.asyncio
async def test_get_note_by_id(client: AsyncClient, sample_note):
    """Test getting a specific note by ID."""
    response = await client.get(f"/api/notes/{sample_note['id']}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == sample_note["id"]
    assert data["title"] == sample_note["title"]
    assert data["content"] == sample_note["content"]

@pytest.mark.asyncio
async def test_get_nonexistent_note(client: AsyncClient):
    """Test getting a note that doesn't exist."""
    response = await client.get("/api/notes/9999")
    assert response.status_code == 404
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_update_note(client: AsyncClient, sample_note):
    """Test updating an existing note."""
    update_data = {
        "title": "Updated Title",
        "content": "Updated content for testing."
    }
    
    response = await client.put(f"/api/notes/{sample_note['id']}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == sample_note["id"]
    assert data["title"] == update_data["title"]
    assert data["content"] == update_data["content"]
    assert len(data["versions"]) > 0  # Should have version history

@pytest.mark.asyncio
async def test_partial_update_note(client: AsyncClient, sample_note):
    """Test partially updating a note (only title)."""
    update_data = {
        "title": "Partial Update"
    }
    
    response = await client.put(f"/api/notes/{sample_note['id']}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == sample_note["id"]
    assert data["title"] == update_data["title"]
    assert data["content"] == sample_note["content"]  # Content should be unchanged

@pytest.mark.asyncio
async def test_delete_note(client: AsyncClient, db: AsyncSession):
    """Test soft deleting a note."""
    # Create a note to delete
    note = Note(
        title="Delete Me",
        content="This note will be deleted.",
        user_id="test-user-id"
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    # Delete the note
    response = await client.delete(f"/api/notes/{note.id}")
    assert response.status_code == 204
    
    # Verify note is soft deleted in database
    await db.refresh(note)
    assert note.is_deleted is True
    assert note.deleted_at is not None

@pytest.mark.asyncio
async def test_restore_note(client: AsyncClient, db: AsyncSession):
    """Test restoring a deleted note."""
    # Create a deleted note
    note = Note(
        title="Restore Me",
        content="This note will be restored.",
        user_id="test-user-id",
        is_deleted=True
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    # Restore the note
    response = await client.post(f"/api/notes/{note.id}/restore")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == note.id
    assert data["is_deleted"] is False
    assert data["deleted_at"] is None
    
    # Verify in database too
    await db.refresh(note)
    assert note.is_deleted is False
    assert note.deleted_at is None

@pytest.mark.asyncio
async def test_get_versions(client: AsyncClient, db: AsyncSession):
    """Test getting version history for a note."""
    # Create a note with version history
    note = Note(
        title="Version Test",
        content="Initial content.",
        user_id="test-user-id"
    )
    note.add_version()
    db.add(note)
    await db.commit()
    
    # Update and add another version
    note.title = "Updated Version Test"
    note.content = "Updated content."
    note.add_version()
    await db.commit()
    
    # Get versions
    response = await client.get(f"/api/notes/{note.id}/versions")
    assert response.status_code == 200
    
    versions = response.json()
    assert len(versions) == 2
    assert "1" in versions
    assert "2" in versions
    assert versions["1"]["title"] == "Version Test"
    assert versions["2"]["title"] == "Updated Version Test"

@pytest.mark.asyncio
async def test_note_limit(client: AsyncClient):
    """Test that users are limited to 10 notes."""
    # Create 10 notes (note that sample_note fixture creates one already, so we need 9 more)
    for i in range(9):
        note_data = {
            "title": f"Note {i+1}",
            "content": f"Content for note {i+1}"
        }
        response = await client.post("/api/notes", json=note_data)
        assert response.status_code == 201
    
    # Try to create an 11th note, should fail
    note_data = {
        "title": "Over Limit",
        "content": "This note should not be created."
    }
    response = await client.post("/api/notes", json=note_data)
    assert response.status_code == 403
    assert "limit" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_permanent_delete_note(client: AsyncClient, db: AsyncSession):
    """Test permanently deleting a note."""
    # Create a note to delete
    note = Note(
        title="Delete Permanently",
        content="This note will be permanently deleted.",
        user_id="test-user-id"
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    note_id = note.id
    
    # Permanently delete the note
    response = await client.delete(f"/api/notes/{note_id}?permanent=true")
    assert response.status_code == 204
    
    # Verify note is completely deleted from database
    result = await db.execute(select(Note).where(Note.id == note_id))
    assert result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_get_notes_include_deleted(client: AsyncClient, db: AsyncSession):
    """Test getting all notes including deleted ones."""
    # Create a regular note
    note1 = Note(
        title="Regular Note",
        content="This is a regular note.",
        user_id="test-user-id"
    )
    db.add(note1)
    
    # Create a deleted note
    note2 = Note(
        title="Deleted Note",
        content="This note is deleted.",
        user_id="test-user-id",
        is_deleted=True
    )
    db.add(note2)
    await db.commit()
    
    # Get only active notes (default)
    response = await client.get("/api/notes")
    regular_notes = response.json()
    assert all(not note.get("is_deleted") for note in regular_notes)
    
    # Get all notes including deleted
    response = await client.get("/api/notes?include_deleted=true")
    all_notes = response.json()
    assert len(all_notes) > len(regular_notes)
    assert any(note.get("is_deleted") for note in all_notes)

@pytest.mark.asyncio
async def test_update_nonexistent_note(client: AsyncClient):
    """Test updating a note that doesn't exist."""
    update_data = {
        "title": "Updated Title",
        "content": "Updated content"
    }
    
    response = await client.put("/api/notes/99999", json=update_data)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_update_deleted_note(client: AsyncClient, db: AsyncSession):
    """Test updating a soft-deleted note (should fail)."""
    # Create a deleted note
    note = Note(
        title="Deleted Note",
        content="This note is deleted.",
        user_id="test-user-id",
        is_deleted=True
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    # Try to update it
    update_data = {
        "title": "Try Update Deleted",
        "content": "This should fail"
    }
    
    response = await client.put(f"/api/notes/{note.id}", json=update_data)
    assert response.status_code == 404
    assert "deleted" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_restore_nonexistent_note(client: AsyncClient):
    """Test restoring a note that doesn't exist."""
    response = await client.post("/api/notes/99999/restore")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_restore_at_limit(client: AsyncClient, db: AsyncSession):
    """Test restoring when at note limit."""
    # Create 10 active notes
    for i in range(10):
        note = Note(
            title=f"Active Note {i}",
            content=f"Active content {i}",
            user_id="test-user-id"
        )
        db.add(note)
    
    # Create a deleted note
    deleted_note = Note(
        title="Deleted Note",
        content="This note is deleted.",
        user_id="test-user-id",
        is_deleted=True
    )
    db.add(deleted_note)
    await db.commit()
    await db.refresh(deleted_note)
    
    # Try to restore while at limit
    response = await client.post(f"/api/notes/{deleted_note.id}/restore")
    assert response.status_code == 403
    assert "limit" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_pagination(client: AsyncClient, db: AsyncSession):
    """Test note pagination."""
    # Clear existing notes
    await db.execute(delete(Note).where(Note.user_id == "test-user-id"))
    await db.commit()
    
    # Create 15 notes
    for i in range(15):
        note = Note(
            title=f"Paginated Note {i}",
            content=f"Paginated content {i}",
            user_id="test-user-id"
        )
        db.add(note)
    await db.commit()
    
    # Test pagination - first page
    response = await client.get("/api/notes?skip=0&limit=5")
    page1_notes = response.json()
    assert len(page1_notes) == 5
    
    # Test pagination - second page
    response = await client.get("/api/notes?skip=5&limit=5")
    page2_notes = response.json()
    assert len(page2_notes) == 5
    
    # Verify different notes on different pages
    page1_ids = [note["id"] for note in page1_notes]
    page2_ids = [note["id"] for note in page2_notes]
    assert not set(page1_ids).intersection(set(page2_ids))