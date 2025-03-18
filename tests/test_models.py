"""Unit tests for database models."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Note

@pytest.mark.asyncio
async def test_note_creation(db: AsyncSession):
    """Test creating a note with basic fields."""
    # Create a note
    note = Note(
        title="Test Note",
        content="This is a test note content.",
        user_id="test-user-id"
    )
    
    # Add to session and commit
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    # Verify fields
    assert note.id is not None
    assert note.title == "Test Note"
    assert note.content == "This is a test note content."
    assert note.user_id == "test-user-id"
    assert note.is_deleted is False
    assert note.deleted_at is None
    assert isinstance(note.created_at, datetime)
    assert isinstance(note.updated_at, datetime)
    assert note.versions == {}

@pytest.mark.asyncio
async def test_note_version_history(db: AsyncSession):
    """Test adding versions to note history."""
    # Create a note
    note = Note(
        title="Original Title",
        content="Original content.",
        user_id="test-user-id"
    )
    
    # Add initial version
    note.add_version()
    
    # Add to session and commit
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    # Verify initial version
    assert len(note.versions) == 1
    assert "1" in note.versions
    assert note.versions["1"]["title"] == "Original Title"
    assert note.versions["1"]["content"] == "Original content."
    
    # Update note and add another version
    note.title = "Updated Title"
    note.content = "Updated content."
    note.add_version()
    await db.commit()
    await db.refresh(note)
    
    # Verify both versions exist
    assert len(note.versions) == 2
    assert "1" in note.versions
    assert "2" in note.versions
    assert note.versions["1"]["title"] == "Original Title"
    assert note.versions["2"]["title"] == "Updated Title"

@pytest.mark.asyncio
async def test_version_limit(db: AsyncSession):
    """Test that version history is limited to 5 versions."""
    # Create a note
    note = Note(
        title="Version Test",
        content="Testing version limits.",
        user_id="test-user-id"
    )
    
    # Add to session and commit
    db.add(note)
    await db.commit()
    
    # Add 6 versions (initial + 5 updates)
    for i in range(6):
        note.title = f"Version {i+1}"
        note.content = f"Content version {i+1}"
        note.add_version()
        await db.commit()
        await db.refresh(note)
    
    # Verify only 5 versions are kept (oldest is removed)
    assert len(note.versions) == 5
    assert "1" not in note.versions  # The first version should be removed
    assert "2" in note.versions
    assert "3" in note.versions
    assert "4" in note.versions
    assert "5" in note.versions
    assert "6" in note.versions

@pytest.mark.asyncio
async def test_soft_delete(db: AsyncSession):
    """Test soft delete functionality."""
    # Create a note
    note = Note(
        title="Delete Test",
        content="Testing soft deletion.",
        user_id="test-user-id"
    )
    
    # Add to session and commit
    db.add(note)
    await db.commit()
    await db.refresh(note)
    
    # Verify not deleted initially
    assert note.is_deleted is False
    assert note.deleted_at is None
    
    # Soft delete the note
    note.is_deleted = True
    note.deleted_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(note)
    
    # Verify deletion state
    assert note.is_deleted is True
    assert note.deleted_at is not None
    
    # Restore the note
    note.is_deleted = False
    note.deleted_at = None
    await db.commit()
    await db.refresh(note)
    
    # Verify restored state
    assert note.is_deleted is False
    assert note.deleted_at is None