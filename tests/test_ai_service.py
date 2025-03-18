"""Tests for the AI service functionality with focus on error handling and edge cases."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, UTC
import httpx
import json

from app.services.ai import AIService, SUPPORTED_LANGUAGES
from app.services.cache import redis_service

@pytest.mark.asyncio
async def test_summarize_note_cache_hit():
    """Test that the AI service returns cached summaries when available."""
    # Create an AI service instance
    ai_service = AIService()
    
    # Mock data
    note_id = 123
    title = "Cache Test"
    content = "Testing the cache hit scenario."
    language = "en"
    
    # Mock cache data
    cached_summary = {
        "note_id": note_id,
        "original_title": title,
        "summary": "This is a cached summary",
        "generated_at": datetime.now(UTC).isoformat(),
        "language": language
    }
    
    # Mock the redis_service directly in AIService
    with patch('app.services.ai.redis_service.get_note_summary', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = cached_summary
        
        # Call the summarize function
        result = await ai_service.summarize_note(note_id, title, content, language)
        
        # Verify cache was checked
        mock_get.assert_called_once_with(note_id, language)
        
        # Verify we got the cached result
        assert result == cached_summary
        assert result["summary"] == "This is a cached summary"

@pytest.mark.asyncio
async def test_summarize_note_cache_miss():
    """Test that the AI service generates new summaries when not in cache."""
    # Create an AI service instance
    ai_service = AIService()
    
    # Mock data
    note_id = 123
    title = "Cache Miss Test"
    content = "Testing the cache miss scenario."
    language = "en"
    
    # Mock expected API response
    api_summary = "This is a generated summary"
    
    # Mock cache miss and successful API call
    with patch('app.services.ai.redis_service.get_note_summary', new_callable=AsyncMock) as mock_get, \
         patch.object(AIService, '_call_gemini_api', new_callable=AsyncMock) as mock_api, \
         patch('app.services.ai.redis_service.set_note_summary', new_callable=AsyncMock) as mock_set:
        
        # Setup mocks
        mock_get.return_value = None  # Cache miss
        mock_api.return_value = api_summary  # API returns summary
        mock_set.return_value = True  # Cache set succeeds
        
        # Call the summarize function
        result = await ai_service.summarize_note(note_id, title, content, language)
        
        # Verify cache was checked
        mock_get.assert_called_once_with(note_id, language)
        
        # Verify API was called
        mock_api.assert_called_once()
        
        # Verify result was cached
        mock_set.assert_called_once()
        
        # Verify we got the API result
        assert result is not None
        assert result["summary"] == api_summary
        assert result["note_id"] == note_id
        assert result["original_title"] == title
        assert result["language"] == language

@pytest.mark.asyncio
async def test_summarize_note_api_error():
    """Test behavior when API call fails."""
    # Create an AI service instance
    ai_service = AIService()
    
    # Mock data
    note_id = 123
    title = "API Error Test"
    content = "Testing the API error handling scenario."
    language = "en"
    
    # Mock cache miss and API error
    with patch('app.services.ai.redis_service.get_note_summary', new_callable=AsyncMock) as mock_get, \
         patch.object(AIService, '_call_gemini_api', new_callable=AsyncMock) as mock_api:
        
        # Setup mocks
        mock_get.return_value = None  # Cache miss
        mock_api.return_value = None  # API fails
        
        # Call the summarize function
        result = await ai_service.summarize_note(note_id, title, content, language)
        
        # Verify cache was checked
        mock_get.assert_called_once_with(note_id, language)
        
        # Verify API was called
        mock_api.assert_called_once()
        
        # Verify result is None on API failure
        assert result is None

@pytest.mark.asyncio
async def test_summarize_note_with_invalid_language():
    """Test language validation fallback to English."""
    # Create an AI service instance
    ai_service = AIService()
    
    # Mock data
    note_id = 123
    title = "Language Fallback Test"
    content = "Testing invalid language fallback."
    invalid_language = "invalid"  # Not in SUPPORTED_LANGUAGES
    
    # Mock expected API response for English (fallback)
    api_summary = "This is a summary in English (fallback)"
    
    # Mock cache miss and successful API call
    with patch('app.services.ai.redis_service.get_note_summary', new_callable=AsyncMock) as mock_get, \
         patch.object(AIService, '_call_gemini_api', new_callable=AsyncMock) as mock_api:
        
        # Setup mocks
        mock_get.return_value = None  # Cache miss
        mock_api.return_value = api_summary  # API returns summary
        
        # Call the summarize function with invalid language
        result = await ai_service.summarize_note(note_id, title, content, invalid_language)
        
        # Verify cache was checked with default language (en)
        mock_get.assert_called_once_with(note_id, "en")
        
        # Verify API was called
        mock_api.assert_called_once()
        
        # Verify result has fallback language
        assert result is not None
        assert result["language"] == "en"  # Should have fallen back to English

@pytest.mark.asyncio
async def test_call_gemini_api_error_response():
    """Test handling of error responses from Gemini API."""
    # Create an AI service instance
    ai_service = AIService()
    
    # Test data
    title = "Error Test"
    content = "Testing error response handling."
    
    # Mock httpx client for API error
    with patch('httpx.AsyncClient') as mock_client:
        # Create mock for the client context manager
        mock_cm = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_cm
        
        # Mock post method to return error status
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_cm.post.return_value = mock_response
        
        # Call the API method
        result = await ai_service._call_gemini_api(title, content)
        
        # Verify result is None on API error
        assert result is None

@pytest.mark.asyncio
async def test_call_gemini_api_malformed_response():
    """Test handling of malformed responses from Gemini API."""
    # Create an AI service instance
    ai_service = AIService()
    
    # Test data
    title = "Malformed Response Test"
    content = "Testing malformed response handling."
    
    # Mock httpx client for malformed response
    with patch('httpx.AsyncClient') as mock_client:
        # Create mock for the client context manager
        mock_cm = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_cm
        
        # Mock post method to return success but malformed response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            # Missing 'candidates' field
            "usage": {"promptTokens": 10, "candidatesTokens": 5}
        }
        mock_cm.post.return_value = mock_response
        
        # Call the API method
        result = await ai_service._call_gemini_api(title, content)
        
        # Verify result is None on malformed response
        assert result is None

@pytest.mark.asyncio
async def test_call_gemini_api_exception():
    """Test handling of exceptions during API call."""
    # Create an AI service instance
    ai_service = AIService()
    
    # Test data
    title = "Exception Test"
    content = "Testing exception handling."
    
    # Mock httpx client to raise exception
    with patch('httpx.AsyncClient') as mock_client:
        # Create mock for the client context manager
        mock_client.return_value.__aenter__.side_effect = Exception("Test exception")
        
        # Call the API method
        result = await ai_service._call_gemini_api(title, content)
        
        # Verify result is None on exception
        assert result is None

@pytest.mark.asyncio
async def test_call_gemini_api_success():
    """Test successful API call with proper response parsing."""
    # Create an AI service instance
    ai_service = AIService()
    
    # Test data
    title = "Success Test"
    content = "Testing successful API call."
    expected_summary = "This is a summarized version of the content."
    
    # Mock httpx client for success response
    with patch('httpx.AsyncClient') as mock_client:
        # Create mock for the client context manager
        mock_cm = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_cm
        
        # Mock post method to return success response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": expected_summary}
                        ]
                    }
                }
            ]
        }
        mock_cm.post.return_value = mock_response
        
        # Call the API method
        result = await ai_service._call_gemini_api(title, content)
        
        # Verify correct summary was extracted
        assert result == expected_summary