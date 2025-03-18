import json
import os
from typing import Any, Optional
import redis.asyncio as redis
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PREFIX = "notes_app:"

# Default TTL (1 hour in seconds)
DEFAULT_TTL = 3600

class RedisService:
    """Service for Redis caching with TTL."""
    
    _instance = None
    _redis_client = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one Redis connection."""
        if cls._instance is None:
            cls._instance = super(RedisService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Redis connection."""
        try:
            self._redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True,
                encoding="utf-8"
            )
            logger.info("Redis connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            self._redis_client = None
    
    async def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self._redis_client:
            return False
        try:
            return await self._redis_client.ping()
        except Exception:
            return False
    
    async def set_value(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """Set a value in Redis with TTL."""
        if not await self.is_connected():
            logger.warning("Redis not connected, skipping cache operation")
            return False
        
        try:
            full_key = f"{REDIS_PREFIX}{key}"
            serialized_value = json.dumps(value)
            await self._redis_client.set(full_key, serialized_value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Error setting Redis value: {e}")
            return False
    
    async def get_value(self, key: str) -> Optional[Any]:
        """Get a value from Redis."""
        if not await self.is_connected():
            logger.warning("Redis not connected, skipping cache operation")
            return None
        
        try:
            full_key = f"{REDIS_PREFIX}{key}"
            value = await self._redis_client.get(full_key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting Redis value: {e}")
            return None
    
    async def delete_value(self, key: str) -> bool:
        """Delete a value from Redis."""
        if not await self.is_connected():
            logger.warning("Redis not connected, skipping cache operation")
            return False
        
        try:
            full_key = f"{REDIS_PREFIX}{key}"
            await self._redis_client.delete(full_key)
            return True
        except Exception as e:
            logger.error(f"Error deleting Redis value: {e}")
            return False
    
    # Helper methods for note summary caching
    
    async def get_note_summary(self, note_id: int, language: str = "en") -> Optional[dict]:
        """Get cached summary for a note."""
        cache_key = f"summary:{note_id}:{language}"
        return await self.get_value(cache_key)
    
    async def set_note_summary(self, note_id: int, summary_data: dict, language: str = "en") -> bool:
        """Cache a note summary with TTL."""
        cache_key = f"summary:{note_id}:{language}"
        return await self.set_value(cache_key, summary_data, ttl=DEFAULT_TTL)
    
    async def invalidate_note_summary(self, note_id: int, language: str = "en") -> bool:
        """Invalidate cached summary for a note."""
        cache_key = f"summary:{note_id}:{language}"
        return await self.delete_value(cache_key)

# Singleton instance
redis_service = RedisService()