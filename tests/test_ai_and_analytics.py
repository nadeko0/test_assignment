"""Integration tests for AI and Analytics API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import json
from unittest.mock import patch
from sqlalchemy import text, delete

from app.models import Note
from app.services.analytics import simple_tokenize, self_analyze_text, analyze_text_with_gemini

@pytest.mark.asyncio
async def test_get_supported_languages(client: AsyncClient):
    """Test getting the list of supported languages for AI summarization."""
    response = await client.get("/api/ai/languages")
    assert response.status_code == 200
    
    data = response.json()
    assert "supported_languages" in data
    assert "en" in data["supported_languages"]
    assert "ru" in data["supported_languages"]
    assert "uk" in data["supported_languages"]
    assert "sk" in data["supported_languages"]
    assert "de" in data["supported_languages"]
    assert "cs" in data["supported_languages"]

@pytest.mark.asyncio
async def test_summarize_note(client: AsyncClient, sample_note):
    """Test generating an AI summary for a note."""
    response = await client.get(f"/api/ai/summarize/{sample_note['id']}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["note_id"] == sample_note["id"]
    assert data["original_title"] == sample_note["title"]
    assert "summary" in data
    assert "generated_at" in data
    assert data["language"] == "en"  # Default language

@pytest.mark.asyncio
async def test_summarize_note_with_language(client: AsyncClient, sample_note):
    """Test generating an AI summary in a specific language."""
    response = await client.get(f"/api/ai/summarize/{sample_note['id']}?language=ru")
    assert response.status_code == 200
    
    data = response.json()
    assert data["language"] == "ru"

@pytest.mark.asyncio
async def test_summarize_nonexistent_note(client: AsyncClient):
    """Test attempting to summarize a note that doesn't exist."""
    response = await client.get("/api/ai/summarize/9999")
    assert response.status_code == 404
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_summarize_deleted_note(client: AsyncClient, db: AsyncSession):
    """Test attempting to summarize a deleted note."""
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
    
    # Try to summarize
    response = await client.get(f"/api/ai/summarize/{note.id}")
    assert response.status_code == 404
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_summarize_invalid_language(client: AsyncClient, sample_note):
    """Test attempting to summarize with an invalid language."""
    response = await client.get(f"/api/ai/summarize/{sample_note['id']}?language=invalid")
    assert response.status_code == 400
    assert "language" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_get_analytics_empty(client: AsyncClient, db: AsyncSession):
    """Test getting analytics with no notes."""
    # Delete all notes to ensure empty state - use SQLAlchemy delete()
    from sqlalchemy import delete
    from app.models import Note
    
    # Execute delete operation
    await db.execute(delete(Note))
    await db.commit()
    
    # Verify notes are deleted
    from sqlalchemy import select, func
    count_query = select(func.count()).select_from(Note)
    result = await db.execute(count_query)
    count = result.scalar()
    assert count == 0, f"Expected 0 notes, but found {count}"
    
    response = await client.get("/api/analytics")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total_notes_count"] == 0
    assert data["active_notes_count"] == 0
    assert data["total_word_count"] == 0
    assert "top_common_words" in data
    assert "longest_notes" in data
    assert "shortest_notes" in data
    assert "notes_by_date" in data

@pytest.mark.asyncio
async def test_get_analytics_with_notes(client: AsyncClient, db: AsyncSession):
    """Test getting analytics with notes in the database."""
    # Create some test notes
    for i in range(3):
        note = Note(
            title=f"Analytics Test {i+1}",
            content=f"This is test content for analytics testing. Sample text {i+1}.",
            user_id="test-user-id"
        )
        db.add(note)
    
    # Create a deleted note
    deleted_note = Note(
        title="Deleted Note",
        content="This is a deleted note.",
        user_id="test-user-id",
        is_deleted=True
    )
    db.add(deleted_note)
    
    await db.commit()
    
    # Get analytics
    response = await client.get("/api/analytics")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total_notes_count"] == 4  # 3 active + 1 deleted
    assert data["active_notes_count"] == 3
    assert data["deleted_notes_count"] == 1
    assert data["total_word_count"] > 0
    assert data["average_note_length"] > 0
    
    # Verify top words
    assert len(data["top_common_words"]) > 0
    for word_data in data["top_common_words"]:
        assert "word" in word_data
        assert "count" in word_data
    
    # Verify longest/shortest notes
    assert len(data["longest_notes"]) > 0
    assert len(data["shortest_notes"]) > 0
    
    # Verify date distribution
    assert len(data["notes_by_date"]) > 0

# Direct tests for analytics service functions to improve coverage

def test_simple_tokenize():
    """Test the tokenization function."""
    # Test basic tokenization
    text = "Hello, world! This is a test."
    tokens = simple_tokenize(text)
    assert "hello" in tokens
    assert "world" in tokens
    assert "this" in tokens
    assert "is" in tokens
    assert "a" in tokens
    assert "test" in tokens
    assert "," not in tokens  # Punctuation should be removed
    assert "!" not in tokens
    
    # Test empty text
    assert simple_tokenize("") == []
    
    # Test with numbers
    text_with_numbers = "I have 2 apples and 3 oranges."
    tokens = simple_tokenize(text_with_numbers)
    assert "2" in tokens
    assert "3" in tokens

def test_self_analyze_text():
    """Test the self_analyze_text function."""
    # Test with normal text
    text = "This is a test. This is only a test. Testing testing one two three."
    analysis = self_analyze_text(text)
    
    assert "word_count" in analysis
    assert analysis["word_count"] > 0
    assert "common_words" in analysis
    assert len(analysis["common_words"]) > 0
    
    # Verify common words format
    for word_data in analysis["common_words"]:
        assert "word" in word_data
        assert "count" in word_data
    
    # Verify stopwords are filtered
    common_words = [item["word"] for item in analysis["common_words"]]
    assert "a" not in common_words  # "a" should be filtered as stopword
    assert "is" not in common_words  # "is" should be filtered as stopword
    
    # Check if "test" is one of the most common words
    assert any(item["word"] == "test" for item in analysis["common_words"])
    
    # Test with empty text
    empty_analysis = self_analyze_text("")
    assert empty_analysis["word_count"] == 0
    assert len(empty_analysis["common_words"]) == 0

@pytest.mark.asyncio
async def test_analyze_text_with_gemini():
    """Test the Gemini API text analysis function."""
    # Test with valid text input
    text_content = ["Here is some sample text for analysis. It contains some repeated words for testing."]
    result = await analyze_text_with_gemini(text_content)
    
    assert "word_count" in result
    assert result["word_count"] > 0
    assert "common_words" in result
    
    # Test with empty content
    empty_result = await analyze_text_with_gemini([])
    assert empty_result["word_count"] == 0
    assert empty_result["common_words"] == []

@pytest.mark.asyncio
async def test_analyze_text_gemini_api_error():
    """Test behavior when Gemini API returns an error."""
    # Mock the httpx client to simulate API error
    with patch("app.services.analytics.httpx.AsyncClient") as mock_client:
        # Create mock for post method that returns error response
        mock_response = type('MockResponse', (), {'status_code': 500, 'text': 'Server error'})
        mock_client_instance = mock_client.return_value.__aenter__.return_value
        mock_client_instance.post.return_value = mock_response
        
        # Call the function with the mocked client
        text_content = ["Test content for error handling"]
        result = await analyze_text_with_gemini(text_content)
        
        # Should fall back to self_analyze_text
        assert "word_count" in result
        assert "common_words" in result

@pytest.mark.asyncio
async def test_analytics_service_error_handling(client: AsyncClient, db: AsyncSession):
    """Test error handling in analytics endpoint."""
    # Force an error in analytics calculation by using a patched method instead of DB manipulation
    with patch("app.services.analytics.AnalyticsService.calculate_analytics") as mock_calc:
        # Create a mock response with an error message
        mock_calc.return_value = {"error": "Test error", "message": "Error message for testing"}
        
        # Try to get analytics (this should respond with HTTP 500)
        response = await client.get("/api/analytics")
        assert response.status_code == 500
        assert "detail" in response.json()

@pytest.mark.asyncio
async def test_force_analytics_cache_refresh(client: AsyncClient):
    """Test forcing analytics cache refresh."""
    # Get analytics normally (cached)
    response1 = await client.get("/api/analytics")
    assert response1.status_code == 200
    
    # Force refresh
    response2 = await client.get("/api/analytics?force_refresh=true")
    assert response2.status_code == 200
    
    # Both should have the same structure
    data1 = response1.json()
    data2 = response2.json()
    
    # Check that both have the same keys
    assert set(data1.keys()) == set(data2.keys())