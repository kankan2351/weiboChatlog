# src/language/detector.py
import langdetect
from typing import Optional
from ..utils.logger import get_logger
from ..utils.cache import Cache

logger = get_logger(__name__)

class LanguageDetector:
    def __init__(self, cache: Cache):
        """Initialize language detector with cache"""
        self.cache = cache
        self.default_lang = 'zh'
        self.supported_langs = {'zh', 'en', 'ja', 'ko'}
        
    async def detect_language(self, text: str) -> str:
        """Detect text language with cache support"""
        try:
            # Use cache to avoid repeated detection
            cache_key = f"lang_{hash(text)}"
            if cached := await self.cache.get(cache_key):
                return cached
                
            # Default to Chinese for very short texts
            if len(text.strip()) < 5:
                return self.default_lang
                
            # Detect language
            lang = langdetect.detect(text)
            
            # Map to supported languages or default
            lang = lang if lang in self.supported_langs else self.default_lang
            
            # Cache result
            await self.cache.set(cache_key, lang)
            return lang
            
        except Exception as e:
            logger.error(f"Language detection error: {str(e)}")
            return self.default_lang
            
    def is_chinese(self, text: str) -> bool:
        """Quick check if text contains Chinese characters"""
        try:
            for char in text:
                if '\u4e00' <= char <= '\u9fff':
                    return True
            return False
        except Exception as e:
            logger.error(f"Chinese check error: {str(e)}")
            return False
