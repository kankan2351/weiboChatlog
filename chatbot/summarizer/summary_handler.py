# src/summarizer/summary_handler.py
from typing import List, Dict, Optional
import openai
from .summary_templates import SummaryTemplates
from ..utils.cache import Cache
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SummaryHandler:
    def __init__(self, openai_client, cache: Cache):
        self.openai_client = openai_client
        self.cache = cache
        self.templates = SummaryTemplates()
        
    async def summarize_messages(self, messages: List[Dict], 
                               summary_type: str = 'brief') -> str:
        """Generate summary for a list of messages"""
        cache_key = f"summary:{summary_type}:{hash(str(messages))}"
        
        # Try to get from cache first
        if cached := await self.cache.get(cache_key):
            return cached
            
        # Select template based on summary type
        template = self.templates.get_template(summary_type)
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": template},
                    {"role": "user", "content": str(messages)}
                ]
            )
            
            summary = response.choices[0].message.content
            await self.cache.set(cache_key, summary, expire=3600)
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return "Failed to generate summary"
            
    async def get_key_points(self, messages: List[Dict]) -> List[str]:
        """Extract key points from messages"""
        template = self.templates.get_template('key_points')
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[
                    {"role": "system", "content": template},
                    {"role": "user", "content": str(messages)}
                ]
            )
            
            points = response.choices[0].message.content.split('\n')
            return [p.strip('- ') for p in points if p.strip()]
            
        except Exception as e:
            logger.error(f"Error extracting key points: {str(e)}")
            return []