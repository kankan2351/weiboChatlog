# src/advisor/solution_generator.py
from typing import List, Dict, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SolutionGenerator:
    def __init__(self, openai_client):
        self.openai_client = openai_client
        
    async def generate_solution(self, 
                              question: str,
                              context: Optional[Dict] = None) -> Dict:
        """Generate specific solution for a question"""
        try:
            messages = [
                {"role": "system", "content": "Generate specific solutions to help users."}
            ]
            
            if context:
                messages.append({
                    "role": "user",
                    "content": f"Context: {context}\nQuestion: {question}"
                })
            else:
                messages.append({
                    "role": "user",
                    "content": question
                })
                
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            
            return {
                'solution': response.choices[0].message.content,
                'confidence': self._calculate_confidence(response)
            }
            
        except Exception as e:
            logger.error(f"Error generating solution: {str(e)}")
            return {'solution': "Unable to generate solution", 'confidence': 0}
            
    def _calculate_confidence(self, response) -> float:
        """Calculate confidence score for the generated solution"""
        try:
            # Use response metadata to calculate confidence
            # This is a simplified implementation
            if hasattr(response, 'model_confidence'):
                return float(response.model_confidence)
            return 0.7  # Default confidence score
        except:
            return 0.5
