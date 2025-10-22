"""
Redis client configuration for event bus
"""
import redis.asyncio as redis
from config.settings import settings
from typing import Optional


class RedisClient:
    """
    Singleton Redis client for event publishing and caching.

    Uses async Redis client for non-blocking I/O with FastAPI.
    """

    _instance: Optional[redis.Redis] = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        """Get or create Redis client instance"""
        if cls._instance is None:
            # Parse Redis URL from settings or use default
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')

            cls._instance = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )

        return cls._instance

    @classmethod
    async def close(cls):
        """Close Redis connection"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None


# Convenience function for dependency injection
async def get_redis() -> redis.Redis:
    """FastAPI dependency for Redis client"""
    return await RedisClient.get_client()
