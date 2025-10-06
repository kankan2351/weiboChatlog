# /data/chats/oqz4c/workspace/chatbot/utils/__init__.py
"""Light-weight exports for chatbot utility helpers."""

from chatbot.utils.config import config
from chatbot.utils.logger import get_logger

__all__ = [
    "config",
    "get_logger",
    "get_cache",
    "get_redis_client",
]


def get_cache(*args, **kwargs):
    from chatbot.utils.cache import Cache

    return Cache(*args, **kwargs)


def get_redis_client(*args, **kwargs):
    from chatbot.utils.redis_client import RedisClient

    return RedisClient(*args, **kwargs)
