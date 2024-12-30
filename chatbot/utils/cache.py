# src/utils/cache.py
from typing import Any, Dict, Optional
from .redis_client import RedisClient
from .logger import get_logger

logger = get_logger(__name__)

class Cache:
    def __init__(self, config: Dict):
        """Initialize cache with Redis config"""
        try:
            # 确保配置中的 host 是字符串类型
            redis_config = {
                'host': str(config.get('host', 'localhost')),
                'port': int(config.get('port', 6379)),
                'db': int(config.get('db', 0))
            }
            
            # 只有在密码存在时才添加到配置中
            if password := config.get('password'):
                redis_config['password'] = str(password)
                
            self.redis_client = RedisClient(**redis_config)
            
        except Exception as e:
            logger.error(f"Error initializing cache: {str(e)}")
            raise
            
    async def get(self, key: str) -> Any:
        """Get value from cache"""
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return None
            
    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """Set value in cache"""
        try:
            return await self.redis_client.set(key, value, expire)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
            return False
            
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            return await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False
            
    async def clear(self) -> bool:
        """Clear all cache entries"""
        try:
            return await self.redis_client.flushdb()
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
            return False