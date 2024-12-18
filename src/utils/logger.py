# src/utils/logger.py
import logging
import sys
from datetime import datetime
from pathlib import Path

def get_logger(name: str) -> logging.Logger:
    """Create and configure logger"""
    logger = logging.getLogger(name)
    
    # Skip if logger is already configured
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # File handler
    file_handler = logging.FileHandler(
        log_dir / f"{datetime.now():%Y-%m-%d}.log"
    )
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Configure root logger
root_logger = get_logger("root")

def log_error(error: Exception, context: str = ""):
    """Log error with context"""
    root_logger.error(f"{context}: {str(error)}", 
                     exc_info=True)

def log_warning(message: str):
    """Log warning message"""
    root_logger.warning(message)

def log_info(message: str):
    """Log info message"""
    root_logger.info(message)
