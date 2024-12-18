# src/utils/redis_client.py
import redis
import json
from typing import Any, Optional
import asyncio
from .logger import get_logger

logger = get_logger(__name__)

class RedisClient:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        """Initialize Redis client"""
        try:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_timeout=5
            )
            self.redis.ping()  # Test connection
            logger.info("Redis client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {str(e)}")
            self.redis = None
            
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            if not self.redis:
                return None
                
            value = await asyncio.to_thread(self.redis.get, key)
            return json.loads(value) if value else None
            
        except Exception as e:
            logger.error(f"Redis get error: {str(e)}")
            return None
            
    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in Redis with expiration"""
        try:
            if not self.redis:
                return False
                
            serialized = json.dumps(value)
            return await asyncio.to_thread(
                self.redis.set, key, serialized, ex=expire
            )
            
        except Exception as e:
            logger.error(f"Redis set error: {str(e)}")
            return False
            
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            if not self.redis:
                return False
                
            return bool(await asyncio.to_thread(self.redis.delete, key))
            
        except Exception as e:
            logger.error(f"Redis delete error: {str(e)}")
            return False
            
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            if not self.redis:
                return False
                
            return bool(await asyncio.to_thread(self.redis.exists, key))
            
        except Exception as e:
            logger.error(f"Redis exists error: {str(e)}")
            return False
            
    def close(self):
        """Close Redis connection"""
        if self.redis:
            self.redis.close()