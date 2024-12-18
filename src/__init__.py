# src/__init__.py
from .handlers.ai_interface import AIInterface
from .utils.config import config
from .utils.logger import get_logger

__version__ = "1.0.0"
__all__ = ['AIInterface', 'config', 'get_logger']