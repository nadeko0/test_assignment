"""Unit tests for analytics service functions."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
import json
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from app.services.analytics import AnalyticsService, simple_tokenize, self_analyze_text

@pytest.mark.asyncio
async def test_analytics_service_init():
    """Test the initialization of AnalyticsService."""
    # Test singleton pattern
    service1 = AnalyticsService()
    service2 = AnalyticsService()
    assert service1 is service2
    
    # Reset for other tests
    AnalyticsService._instance = None

def test_additional_tokenize_cases():
    """Test tokenization with more edge cases."""
    # Test with various punctuation
    text = "Hello, world! This is a test. With some punctuation: ; - _ ? !"
    tokens = simple_tokenize(text)
    assert "hello" in tokens
    assert "world" in tokens
    assert "punctuation" in tokens
    
    # Test with numbers and mixed case
    text = "Testing 123 MixedCase UPPERCASE lowercase"
    tokens = simple_tokenize(text)
    assert "testing" in tokens  # Lowercase conversion
    assert "123" in tokens      # Numbers preserved
    assert "mixedcase" in tokens  # Case normalized
    assert "uppercase" in tokens
    assert "lowercase" in tokens
    
    # Test with special characters
    text = "Email: test@example.com, URL: https://example.com"
    tokens = simple_tokenize(text)
    assert "email" in tokens
    assert "test@example.com" in tokens  # Email preserved
    assert "url" in tokens
    assert "https://example.com" in tokens  # URL preserved

def test_self_analyze_multiple_cases():
    """Test text self-analysis with more variations."""
    # Short text analysis
    short_text = "Short text for analysis."
    short_analysis = self_analyze_text(short_text)
    assert short_analysis["word_count"] == 4
    
    # Empty text
    empty_analysis = self_analyze_text("")
    assert empty_analysis["word_count"] == 0
    assert len(empty_analysis["common_words"]) == 0
    
    # Text with repeated words
    repeated_text = "test test test test other other other unique"
    repeated_analysis = self_analyze_text(repeated_text)
    common_words = {item["word"]: item["count"] for item in repeated_analysis["common_words"]}
    assert common_words["test"] == 4
    assert common_words["other"] == 3
    assert common_words["unique"] == 1

@pytest.mark.asyncio
async def test_analytics_service_caching():
    """Test analytics results caching."""
    # Create service with mock cache
    service = AnalyticsService()
    mock_cache = AsyncMock()
    mock_cache.get_value.return_value = json.dumps({"cached": True, "total_notes_count": 5})
    service._cache = mock_cache
    
    # Mock session
    mock_session = MagicMock()
    
    # Test with cache hit
    cached_result = await service.calculate_analytics(mock_session)
    assert cached_result["cached"] is True
    assert cached_result["total_notes_count"] == 5
    
    # Test force refresh
    with patch.object(service, "_get_notes_analytics") as mock_analytics:
        mock_analytics.return_value = {"fresh": True, "total_notes_count": 10}
        fresh_result = await service.calculate_analytics(mock_session, force_refresh=True)
        assert fresh_result["fresh"] is True
        assert fresh_result["total_notes_count"] == 10
        mock_analytics.assert_called_once()
    
    # Reset for other tests
    AnalyticsService._instance = None

@pytest.mark.asyncio
async def test_gemini_api_error_handling():
    """Test Gemini API error handling."""
    with patch("app.services.analytics.httpx.AsyncClient") as mock_client:
        # Create a mock client that raises an exception
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.post.side_effect = httpx.RequestError("Connection error")
        
        # Call function with error condition
        result = await analyze_text_with_gemini(["Test text"])
        
        # Should fall back to self-analysis
        assert "word_count" in result
        assert "common_words" in result
        
        # Verify it didn't just return empty results
        assert result["word_count"] > 0

@pytest.mark.asyncio
async def test_analytics_calculate_with_no_notes():
    """Test analytics calculation with no notes."""
    service = AnalyticsService()
    
    # Create a mock session that returns no notes
    mock_session = AsyncMock()
    mock_session.execute.return_value.scalars.return_value.all.return_value = []
    mock_session.execute.return_value.scalar.return_value = 0
    
    # Calculate analytics with no notes
    result = await service._get_notes_analytics(mock_session)
    
    # Verify results
    assert result["total_notes_count"] == 0
    assert result["active_notes_count"] == 0
    assert result["deleted_notes_count"] == 0
    assert result["total_word_count"] == 0
    assert len(result["top_common_words"]) == 0
    assert len(result["longest_notes"]) == 0
    assert len(result["shortest_notes"]) == 0
    
    # Reset for other tests
    AnalyticsService._instance = None

# Import at the end to avoid circular imports in the test
from app.services.analytics import analyze_text_with_gemini