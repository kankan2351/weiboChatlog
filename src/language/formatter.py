# src/language/formatter.py
from typing import Dict, Optional
from .detector import LanguageDetector
from .templates import TemplateManager
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ResponseFormatter:
    def __init__(self, detector: LanguageDetector, templates: TemplateManager):
        """Initialize response formatter"""
        self.detector = detector
        self.templates = templates
        
    async def format_response(
        self,
        content: str,
        template_key: Optional[str] = None,
        detected_lang: Optional[str] = None,
        **kwargs
    ) -> str:
        """Format response with appropriate language and template"""
        try:
            # Detect language if not provided
            if not detected_lang:
                detected_lang = await self.detector.detect_language(content)
                
            # Get template if specified
            if template_key:
                template = self.templates.get_template(template_key, detected_lang)
                content = template.format(content=content, **kwargs)
                
            # Special formatting for different languages
            if detected_lang == 'zh':
                content = self._format_chinese(content)
            elif detected_lang == 'en':
                content = self._format_english(content)
            elif detected_lang == 'ja':
                content = self._format_japanese(content)
            elif detected_lang == 'ko':
                content = self._format_korean(content)
                
            return content
            
        except Exception as e:
            logger.error(f"Response formatting error: {str(e)}")
            return content
            
    def _format_chinese(self, text: str) -> str:
        """Format Chinese text"""
        try:
            # Remove extra whitespace between Chinese characters
            text = ''.join(text.split())
            # Add spaces around English words and numbers
            text = self._add_spaces_around_foreign(text)
            return text
        except Exception as e:
            logger.error(f"Chinese formatting error: {str(e)}")
            return text
            
    def _format_english(self, text: str) -> str:
        """Format English text"""
        try:
            # Ensure proper spacing
            text = ' '.join(text.split())
            # Capitalize sentences
            text = '. '.join(s.strip().capitalize() for s in text.split('.'))
            return text
        except Exception as e:
            logger.error(f"English formatting error: {str(e)}")
            return text
            
    def _format_japanese(self, text: str) -> str:
        """Format Japanese text"""
        try:
            # Remove spaces between Japanese characters
            text = ''.join(text.split())
            return text
        except Exception as e:
            logger.error(f"Japanese formatting error: {str(e)}")
            return text
            
    def _format_korean(self, text: str) -> str:
        """Format Korean text"""
        try:
            # Remove spaces between Korean characters
            text = ''.join(text.split())
            return text
        except Exception as e:
            logger.error(f"Korean formatting error: {str(e)}")
            return text
            
    def _add_spaces_around_foreign(self, text: str) -> str:
        """Add spaces around non-Chinese characters"""
        result = []
        in_foreign = False
        
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                if in_foreign:
                    result.append(' ')
                    in_foreign = False
            else:
                if not in_foreign and result and result[-1] != ' ':
                    result.append(' ')
                in_foreign = True
            result.append(char)
            
        return ''.join(result).strip()