# src/summarizer/cache.py
from typing import Dict, Any, Optional
import time
from collections import OrderedDict
from ..utils.redis_client import RedisClient
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SummaryCache:
    def __init__(
        self,
        redis_client: RedisClient,
        max_memory_items: int = 1000,
        redis_ttl: int = 3600
    ):
        """Initialize multi-level cache system"""
        self.redis = redis_client
        self.max_memory_items = max_memory_items
        self.redis_ttl = redis_ttl
        
        # L1 cache (memory)
        self.memory_cache: OrderedDict = OrderedDict()
        self.memory_timestamps: Dict[str, float] = {}
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 -> L2)"""
        try:
            # Try L1 (memory) cache first
            if key in self.memory_cache:
                self.memory_cache.move_to_end(key)
                return self.memory_cache[key]
            
            # Try L2 (Redis) cache
            if self.redis:
                value = await self.redis.get(key)
                if value:
                    # Promote to L1 cache
                    await self._add_to_memory(key, value)
                    return value
                    
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
            
    async def set(self, key: str, value: Any) -> bool:
        """Set value in both cache levels"""
        try:
            # Set in L1 (memory) cache
            await self._add_to_memory(key, value)
            
            # Set in L2 (Redis) cache
            if self.redis:
                return await self.redis.set(key, value, expire=self.redis_ttl)
                
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