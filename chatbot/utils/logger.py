# /data/chats/oqz4c/workspace/chatbot/utils/logger.py
import logging
import sys
from datetime import datetime
from pathlib import Path
import os
from typing import Optional

# 保存已创建的日志器
_loggers = {}

def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器，避免重复创建
    """
    if name in _loggers:
        return _loggers[name]
        
    # 创建新的日志器
    logger = logging.getLogger(name)
    
    # 如果日志器还没有处理器，才添加处理器
    if not logger.handlers:
        # 设置日志级别
        logger.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # 添加处理器到日志器
        logger.addHandler(console_handler)
        
        # 阻止日志向上层传递
        logger.propagate = False
    
    # 保存日志器以供复用
    _loggers[name] = logger
    return logger

# Configure root logger
root_logger = get_logger("chatbot")

def log_error(error: Exception, context: str = "") -> None:
    """Log error with context"""
    root_logger.error(f"{context}: {str(error)}", exc_info=True)

def log_warning(message: str) -> None:
    """Log warning message"""
    root_logger.warning(message)

def log_info(message: str) -> None:
    """Log info message"""
    root_logger.info(message)