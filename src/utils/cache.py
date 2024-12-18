# src/utils/cache.py
from typing import Any, Optional
import redis
import json
import asyncio
from .logger import get_logger

logger = get_logger(__name__)

class Cache:
    def __init__(self, host='localhost', port=6379, db=0):
        try:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True
            )
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {str(e)}")
            self.redis = None
            
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if not self.redis:
                return None
                
            value = await asyncio.to_thread(self.redis.get, key)
            return json.loads(value) if value else None
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return None
            
    async def set(self, key: str, value: Any, 
                expire: int = 3600) -> bool:
        """Set value in cache with expiration"""
        try:
            if not self.redis:
                return False
                
            serialized = json.dumps(value)
            success = await asyncio.to_thread(
                self.redis.set, key, serialized, ex=expire
            )
            return bool(success)
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
            return False
            
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if not self.redis:
                return False
                
            return bool(await asyncio.to_thread(self.redis.delete, key))
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False
            
    async def clear(self) -> bool:
        """Clear all cache entries"""
        try:
            if not self.redis:
                return False
                
            return bool(await asyncio.to_thread(self.redis.flushdb))
            
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
            return False