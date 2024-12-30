# src/summarizer/cache.py
from typing import Dict, Any, Optional
import time
from collections import OrderedDict
from ..utils.redis_client import RedisClient
from ..utils.logger import get_logger
import json
from redis.asyncio import Redis

logger = get_logger(__name__)

class SummaryCache:
    PREFIX = "summary:"  # 使用类变量而不是实例变量
    EXPIRE_TIME = 3600  # 1小时过期

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        
    async def get(self, key: str) -> Optional[Dict]:
        """从缓存获取数据"""
        try:
            full_key = f"{self.PREFIX}{key}"
            data = await self.redis.get(full_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
            
    async def set(self, key: str, value: Dict) -> bool:
        """将数据存入缓存"""
        try:
            full_key = f"{self.PREFIX}{key}"
            # 将字典序列化为 JSON 字符串
            serialized_value = json.dumps(value)
            # 只执行 SET 操作
            await self.redis.set(full_key, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
            
    async def delete(self, key: str) -> bool:
        """Delete from both cache levels"""
        try:
            # Remove from L1 cache
            self.memory_cache.pop(key, None)
            self.memory_timestamps.pop(key, None)
            
            # Remove from L2 cache
            if self.redis:
                return await self.redis.delete(key)
                
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False
            
    async def _add_to_memory(self, key: str, value: Any):
        """Add item to memory cache with LRU eviction"""
        try:
            # Evict oldest items if cache is full
            while len(self.memory_cache) >= self.max_memory_items:
                oldest_key, _ = self.memory_cache.popitem(last=False)
                self.memory_timestamps.pop(oldest_key, None)
            
            # Add new item
            self.memory_cache[key] = value
            self.memory_timestamps[key] = time.time()
            self.memory_cache.move_to_end(key)
            
        except Exception as e:
            logger.error(f"Error adding to memory cache: {str(e)}")
            
    def clear_memory_cache(self):
        """Clear L1 (memory) cache"""
        self.memory_cache.clear()
        self.memory_timestamps.clear()