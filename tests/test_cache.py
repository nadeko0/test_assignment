"""Unit tests for Redis cache service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.services.cache import RedisService, DEFAULT_TTL, REDIS_PREFIX

@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    mock_client = AsyncMock()
    # Default success responses
    mock_client.ping.return_value = True
    mock_client.set.return_value = True
    mock_client.get.return_value = None
    mock_client.delete.return_value = 1  # Redis returns number of keys deleted
    return mock_client

@pytest.fixture
def redis_service(mock_redis_client):
    """Create a RedisService with mocked Redis client."""
    with patch('app.services.cache.redis.Redis', return_value=mock_redis_client):
        # Force new instance for clean testing
        RedisService._instance = None
        service = RedisService()
        service._redis_client = mock_redis_client
        return service

@pytest.mark.asyncio
async def test_is_connected(redis_service, mock_redis_client):
    """Test is_connected method."""
    # Test successful connection
    mock_redis_client.ping.return_value = True
    assert await redis_service.is_connected() is True
    
    # Test failed connection
    mock_redis_client.ping.side_effect = Exception("Connection error")
    assert await redis_service.is_connected() is False
    
    # Test with None client
    redis_service._redis_client = None
    assert await redis_service.is_connected() is False

@pytest.mark.asyncio
async def test_set_value(redis_service, mock_redis_client):
    """Test setting a value in Redis."""
    # Test successful set
    mock_redis_client.ping.return_value = True
    mock_redis_client.set.return_value = True
    
    test_key = "test_key"
    test_value = {"name": "test", "value": 123}
    
    result = await redis_service.set_value(test_key, test_value)
    assert result is True
    
    # Verify called with correct parameters
    mock_redis_client.set.assert_called_with(
        f"{REDIS_PREFIX}{test_key}", 
        json.dumps(test_value), 
        ex=DEFAULT_TTL
    )
    
    # Test with custom TTL
    custom_ttl = 7200
    await redis_service.set_value(test_key, test_value, ttl=custom_ttl)
    mock_redis_client.set.assert_called_with(
        f"{REDIS_PREFIX}{test_key}", 
        json.dumps(test_value), 
        ex=custom_ttl
    )
    
    # Test when Redis is not connected
    mock_redis_client.ping.return_value = False
    result = await redis_service.set_value(test_key, test_value)
    assert result is False
    
    # Test with exception
    mock_redis_client.ping.return_value = True
    mock_redis_client.set.side_effect = Exception("Redis error")
    result = await redis_service.set_value(test_key, test_value)
    assert result is False

@pytest.mark.asyncio
async def test_get_value(redis_service, mock_redis_client):
    """Test getting a value from Redis."""
    # Test when key exists
    test_key = "test_key"
    test_value = {"name": "test", "value": 123}
    serialized_value = json.dumps(test_value)
    
    mock_redis_client.ping.return_value = True
    mock_redis_client.get.return_value = serialized_value
    
    result = await redis_service.get_value(test_key)
    assert result == test_value
    mock_redis_client.get.assert_called_with(f"{REDIS_PREFIX}{test_key}")
    
    # Test when key doesn't exist
    mock_redis_client.get.return_value = None
    result = await redis_service.get_value(test_key)
    assert result is None
    
    # Test when Redis is not connected
    mock_redis_client.ping.return_value = False
    result = await redis_service.get_value(test_key)
    assert result is None
    
    # Test with exception
    mock_redis_client.ping.return_value = True
    mock_redis_client.get.side_effect = Exception("Redis error")
    result = await redis_service.get_value(test_key)
    assert result is None

@pytest.mark.asyncio
async def test_delete_value(redis_service, mock_redis_client):
    """Test deleting a value from Redis."""
    test_key = "test_key"
    
    # Test successful delete
    mock_redis_client.ping.return_value = True
    mock_redis_client.delete.return_value = 1
    
    result = await redis_service.delete_value(test_key)
    assert result is True
    mock_redis_client.delete.assert_called_with(f"{REDIS_PREFIX}{test_key}")
    
    # Test when Redis is not connected
    mock_redis_client.ping.return_value = False
    result = await redis_service.delete_value(test_key)
    assert result is False
    
    # Test with exception
    mock_redis_client.ping.return_value = True
    mock_redis_client.delete.side_effect = Exception("Redis error")
    result = await redis_service.delete_value(test_key)
    assert result is False

@pytest.mark.asyncio
async def test_note_summary_methods(redis_service, mock_redis_client):
    """Test note summary helper methods."""
    note_id = 42
    language = "en"
    summary_data = {
        "note_id": note_id,
        "summary": "This is a test summary",
        "language": language
    }
    
    # Setup mock
    mock_redis_client.ping.return_value = True
    mock_redis_client.get.return_value = json.dumps(summary_data)
    mock_redis_client.set.return_value = True
    mock_redis_client.delete.return_value = 1
    
    # Test get_note_summary
    result = await redis_service.get_note_summary(note_id, language)
    assert result == summary_data
    mock_redis_client.get.assert_called_with(f"{REDIS_PREFIX}summary:{note_id}:{language}")
    
    # Test with default language
    await redis_service.get_note_summary(note_id)
    mock_redis_client.get.assert_called_with(f"{REDIS_PREFIX}summary:{note_id}:en")
    
    # Test set_note_summary
    result = await redis_service.set_note_summary(note_id, summary_data, language)
    assert result is True
    mock_redis_client.set.assert_called_with(
        f"{REDIS_PREFIX}summary:{note_id}:{language}", 
        json.dumps(summary_data), 
        ex=DEFAULT_TTL
    )
    
    # Test invalidate_note_summary
    result = await redis_service.invalidate_note_summary(note_id, language)
    assert result is True
    mock_redis_client.delete.assert_called_with(f"{REDIS_PREFIX}summary:{note_id}:{language}")

@pytest.mark.asyncio
async def test_redis_singleton():
    """Test that RedisService is a singleton."""
    # Patch Redis to avoid actual connections
    with patch('app.services.cache.redis.Redis'):
        # Reset singleton for test
        RedisService._instance = None
        
        # Create two instances
        service1 = RedisService()
        service2 = RedisService()
        
        # They should be the same object
        assert service1 is service2

@pytest.mark.asyncio
async def test_initialization_error():
    """Test error handling during initialization."""
    # Patch Redis to raise an exception during initialization
    with patch('app.services.cache.redis.Redis', side_effect=Exception("Connection error")):
        # Reset singleton for test
        RedisService._instance = None
        
        # Create an instance (should not raise an exception)
        service = RedisService()
        
        # Redis client should be None
        assert service._redis_client is None
        
        # is_connected should return False
        assert await service.is_connected() is False