"""Tests for the AI API endpoints with focus on error handling."""

import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import status

from app.api.ai import summarize_note
from app.services.ai import ai_service

@pytest.mark.asyncio
async def test_summarize_note_service_failure(client: AsyncClient, sample_note):
    """Test handling of AI service failure in the summarize endpoint."""
    # Mock the AI service to return None (failure)
    with patch('app.services.ai.AIService.summarize_note', new_callable=AsyncMock) as mock_summarize:
        # Setup the mock to return None (simulating failure)
        mock_summarize.return_value = None
        
        # Call the endpoint
        response = await client.get(f"/api/ai/summarize/{sample_note['id']}")
        
        # Verify we get a 500 error
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "failed to generate summary" in response.json()["detail"].lower()
        
        # Verify AI service was called with correct parameters
        mock_summarize.assert_called_once()
        call_args = mock_summarize.call_args[1]
        assert call_args["note_id"] == sample_note["id"]
        assert call_args["title"] == sample_note["title"]
        assert call_args["content"] == sample_note["content"]
        assert call_args["language"] == "en"  # Default language

@pytest.mark.asyncio
async def test_summarize_note_with_multiple_languages(client: AsyncClient, sample_note):
    """Test summarization with multiple different languages."""
    # Try different languages
    for language in ["ru", "de", "uk", "cs", "sk"]:
        response = await client.get(f"/api/ai/summarize/{sample_note['id']}?language={language}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["language"] == language

@pytest.mark.asyncio
async def test_summarize_note_unsupported_language_detailed(client: AsyncClient, sample_note):
    """Test detailed error response for unsupported language."""
    # Try with a clearly unsupported language
    unsupported_language = "xyz"
    response = await client.get(f"/api/ai/summarize/{sample_note['id']}?language={unsupported_language}")
    
    # Verify error response
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error_detail = response.json()["detail"]
    
    # Verify error message contains the unsupported language
    assert unsupported_language in error_detail
    
    # Verify error message lists supported languages
    assert "supported languages" in error_detail.lower()
    assert "en" in error_detail  # Should list English as supported
    assert "ru" in error_detail  # Should list Russian as supported

@pytest.mark.asyncio
async def test_get_supported_languages_detailed(client: AsyncClient):
    """Test that all expected languages are returned by the languages endpoint."""
    response = await client.get("/api/ai/languages")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "supported_languages" in data
    
    languages = data["supported_languages"]
    
    # Verify expected structure: code -> language name
    assert languages["en"] == "English"
    assert languages["ru"] == "Russian"
    assert languages["de"] == "German"
    assert languages["uk"] == "Ukrainian"
    assert languages["sk"] == "Slovak"
    assert languages["cs"] == "Czech"
    
    # Verify the total count of languages
    assert len(languages) == 6  # As of current implementation