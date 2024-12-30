"""
Enhanced Chatbot System with Summarization and Analytics
"""

__version__ = "1.0.0"

from chatbot.handlers.ai_interface import AIInterface
from chatbot.utils.config import config
from chatbot.utils.logger import get_logger

# Public API
__all__ = [
    'AIInterface',
    'config',
    'get_logger',
]

# Initialize configuration and logging
config.load()
logger = get_logger(__name__)