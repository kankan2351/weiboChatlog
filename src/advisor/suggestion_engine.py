# src/advisor/suggestion_engine.py
from typing import List, Dict, Optional
from .solution_generator import SolutionGenerator
from ..utils.cache import Cache
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SuggestionEngine:
    def __init__(self, openai_client, cache: Cache):
        self.openai_client = openai_client
        self.cache = cache
        self.solution_generator = SolutionGenerator(openai_client)
        
    async def get_suggestions(self, 
                            context: Dict,
                            question: str) -> List[Dict]:
        """Get contextual suggestions based on question"""
        cache_key = f"suggestion:{hash(str(context))}{hash(question)}"
        
        if cached := await self.cache.get(cache_key):
            return cached
            
        try:
            # Generate context-aware suggestions
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Generate helpful suggestions based on the context and question."},
                    {"role": "user", "content": f"Context: {context}\nQuestion: {question}"}
                ]
            )
            
            suggestions = response.choices[0].message.content.split('\n')
            result = [{'suggestion': s.strip('- ')} for s in suggestions if s.strip()]
            
            # Cache results
            await self.cache.set(cache_key, result, expire=1800)
            return result
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            return []
            
    async def analyze_question(self, question: str) -> Dict:
        """Analyze question to determine best response approach"""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Analyze the question and determine the best way to help."},
                    {"role": "user", "content": question}
                ]
            )
            
            return {
                'type': response.choices[0].message.content,
                'needs_context': 'context' in response.choices[0].message.content.lower(),
                'is_specific': 'specific' in response.choices[0].message.content.lower()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing question: {str(e)}")
            return {'type': 'general', 'needs_context': False, 'is_specific': False}
