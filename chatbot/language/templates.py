# src/language/templates.py
from typing import Dict, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TemplateManager:
    def __init__(self):
        """Initialize template manager with multilingual templates"""
        self.templates = {
            'default': {
                'zh': '{content}',
                'en': '{content}',
                'ja': '{content}',
                'ko': '{content}'
            },
            'greeting': {
                'zh': '你好！{content}',
                'en': 'Hello! {content}',
                'ja': 'こんにちは！{content}',
                'ko': '안녕하세요! {content}'
            },
            'error': {
                'zh': '抱歉，出现了错误：{content}',
                'en': 'Sorry, an error occurred: {content}',
                'ja': '申し訳ありません、エラーが発生しました：{content}',
                'ko': '죄송합니다. 오류가 발생했습니다: {content}'
            },
            'summary': {
                'zh': '聊天记录总结：\n{content}',
                'en': 'Chat Summary:\n{content}',
                'ja': 'チャット履歴のまとめ：\n{content}',
                'ko': '채팅 기록 요약:\n{content}'
            },
            'suggestion': {
                'zh': '建议：\n{content}',
                'en': 'Suggestion:\n{content}',
                'ja': '提案：\n{content}',
                'ko': '제안:\n{content}'
            },
            'search_result': {
                'zh': '搜索结果：\n{content}',
                'en': 'Search Results:\n{content}',
                'ja': '検索結果：\n{content}',
                'ko': '검색 결과:\n{content}'
            }
        }
        
    def get_template(
        self,
        key: str,
        lang: str = 'zh',
        fallback: bool = True
    ) -> str:
        """Get template by key and language"""
        try:
            # Get language templates
            lang_templates = self.templates.get(key, self.templates['default'])
            
            # Get specific language template
            template = lang_templates.get(lang)
            
            # Fallback to Chinese if template not found
            if not template and fallback:
                template = lang_templates.get('zh', '{content}')
                
            return template or '{content}'
            
        except Exception as e:
            logger.error(f"Error getting template: {str(e)}")
            return '{content}'
            
    def add_template(self, key: str, templates: Dict[str, str]) -> bool:
        """Add new template"""
        try:
            if key not in self.templates:
                self.templates[key] = {}
                
            self.templates[key].update(templates)
            return True
            
        except Exception as e:
            logger.error(f"Error adding template: {str(e)}")
            return False
