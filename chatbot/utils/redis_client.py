# src/utils/redis_client.py
import redis
import json
from typing import Any, Optional
import asyncio
from .logger import get_logger

logger = get_logger(__name__)

class RedisClient:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None):
        """Initialize Redis client"""
        # 确保 host 是字符串类型
        if not isinstance(host, str):
            host = str(host)
            
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        
    async def get(self, key: str) -> Any:
        """Get value from Redis"""
        try:
            return self.redis_client.get(key)
        except Exception as e:
            raise Exception(f"Redis get error: {str(e)}")
            
    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """Set value in Redis"""
        try:
            return self.redis_client.set(key, value, ex=expire)
        except Exception as e:
            raise Exception(f"Redis set error: {str(e)}")
            
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            raise Exception(f"Redis delete error: {str(e)}")
            
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            raise Exception(f"Redis exists error: {str(e)}")
            
    def close(self):
        """Close Redis connection"""
        if self.redis_client:
            self.redis_client.close()