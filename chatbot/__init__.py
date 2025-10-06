"""Top level package for the chatbot project."""

__version__ = "1.0.0"

from chatbot.utils.config import config
from chatbot.utils.logger import get_logger

__all__ = [
    "__version__",
    "config",
    "get_logger",
    "get_ai_interface",
]


def get_ai_interface(*args, **kwargs):
    """Factory that defers importing heavy dependencies until needed."""
    from chatbot.handlers.ai_interface import AIInterface

    return AIInterface(*args, **kwargs)