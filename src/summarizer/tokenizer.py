# src/summarizer/tokenizer.py
import tiktoken
import langdetect
import regex as re
from typing import Dict, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TokenManager:
    def __init__(self, model_name: str = "gpt-4"):
        """Initialize token manager with specific model encoding"""
        self.encoder = tiktoken.encoding_for_model(model_name)
        self.chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
        self.cache = {}
        
    def calculate_tokens(self, text: str) -> int:
        """Calculate exact token count for text"""
        try:
            # Check cache first
            cache_key = hash(text)
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Calculate tokens
            tokens = len(self.encoder.encode(text))
            
            # Cache result
            self.cache[cache_key] = tokens
            return tokens
            
        except Exception as e:
            logger.error(f"Error calculating tokens: {str(e)}")
            # Fallback to estimation
            return self.estimate_chinese_tokens(text)
            
    def estimate_chinese_tokens(self, text: str) -> int:
        """Estimate token count for Chinese text"""
        try:
            char_count = self._count_chars(text)
            
            # Chinese characters typically use 1.5 tokens
            chinese_tokens = int(char_count['chinese'] * 1.5)
            # Other characters typically use 0.25 tokens
            other_tokens = int(char_count['other'] * 0.25)
            
            return chinese_tokens + other_tokens
            
        except Exception as e:
            logger.error(f"Error estimating tokens: {str(e)}")
            # Super safe fallback: 2 tokens per character
            return len(text) * 2
            
    def check_limit(self, text: str, limit: int) -> bool:
        """Check if text is within token limit"""
        return self.calculate_tokens(text) <= limit
        
    def _count_chars(self, text: str) -> Dict[str, int]:
        """Count Chinese and other characters"""
        chinese_chars = len(self.chinese_pattern.findall(text))
        return {
            'chinese': chinese_chars,
            'other': len(text) - chinese_chars
        }
        
    def clear_cache(self):
        """Clear token calculation cache"""
        self.cache.clear()
