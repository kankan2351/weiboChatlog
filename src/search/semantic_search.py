# src/search/semantic_search.py
from typing import List, Dict, Optional
import numpy as np
from ..utils.cache import Cache
from ..utils.logger import get_logger
from ..embedding import generate_embeddings

logger = get_logger(__name__)

class SemanticSearch:
    def __init__(self, message_db, cache: Cache):
        self.message_db = message_db
        self.cache = cache
        
    async def search(self, query: str, 
                    filters: Optional[Dict] = None, 
                    limit: int = 5) -> List[Dict]:
        """Perform semantic search on messages"""
        try:
            # Generate query embedding
            query_embedding = generate_embeddings(query)
            
            # Search in vector database
            results = await self.message_db.query_messages(
                query_embedding=query_embedding,
                filter_dict=filters,
                n_results=limit
            )
            
            return results.get('results', [])
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
            
    async def similar_messages(self, message_id: str, 
                             limit: int = 5) -> List[Dict]:
        """Find messages similar to a given message"""
        try:
            # Get message embedding
            message = await self.message_db.get_message(message_id)
            if not message:
                return []
                
            # Search similar messages
            results = await self.message_db.query_messages(
                query_embedding=message['embedding'],
                n_results=limit + 1  # Add 1 to exclude the message itself
            )
            
            # Filter out the original message
            similar = [r for r in results.get('results', []) 
                      if r['id'] != message_id]
            return similar[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar messages: {str(e)}")
            return []
