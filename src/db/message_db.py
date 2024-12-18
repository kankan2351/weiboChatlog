# src/db/message_db.py
import logging
import chromadb
from chromadb.utils import embedding_functions
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path
from ..utils.embeddings import generate_embeddings

logging.getLogger('chromadb').setLevel(logging.ERROR)

class MessageDB:
    def __init__(self, db_path: str = "./chroma_db"):
        """Initialize vector database"""
        try:
            settings = chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
            
            self.chroma_client = chromadb.PersistentClient(
                path=db_path,
                settings=settings
            )
            
            class CustomEmbeddingFunction(embedding_functions.EmbeddingFunction):
                def __call__(self, texts):
                    return [generate_embeddings(text) for text in texts]
            
            self.embedding_function = CustomEmbeddingFunction()
            self.collection = self.chroma_client.get_or_create_collection(
                name="chat_messages",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            
        except Exception as e:
            logging.error(f"Error initializing vector database: {str(e)}")
            self.chroma_client = None
            self.collection = None
            
    def add_message(self, message: Dict) -> bool:
        """Add message to vector database"""
        try:
            if not self.collection:
                return False
                
            message_id = str(message.get('id', ''))
            content = message.get('content', '')
            
            if not content:
                return False
                
            # Check for existing message
            existing = self.collection.get(
                ids=[message_id],
                include=["metadatas"]
            )
            
            if existing["ids"]:
                return True
                
            # Prepare metadata
            metadata = {
                "id": message_id,
                "time": str(message.get('time', '')),
                "timestamp": int(message.get('timestamp', 0)),
                "type": message.get('type', ''),
                "from_user": message.get('from', {}).get('name', ''),
                "from_id": message.get('from', {}).get('uid', ''),
                "group_id": message.get('group', {}).get('gid', ''),
                "media_type": message.get('media_type', 0)
            }
            
            # Add to database
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[message_id]
            )
            return True
            
        except Exception as e:
            logging.error(f"Error adding message: {str(e)}")
            return False
            
    def query_messages(
        self, 
        query_text: str = "", 
        limit: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> Dict:
        """Query messages from vector database"""
        try:
            if not self.collection:
                return {"success": False, "error": "Database not initialized"}
                
            if not query_text and filter_dict:
                results = self.collection.get(
                    where=filter_dict,
                    limit=limit,
                    include=["documents", "metadatas"]
                )
            else:
                results = self.collection.query(
                    query_texts=[query_text],
                    n_results=limit,
                    where=filter_dict,
                    include=["documents", "metadatas", "distances"]
                )
                
            formatted_results = []
            if results.get("ids"):
                for i in range(len(results["ids"])):
                    result = {
                        "id": results["ids"][i],
                        "content": results["documents"][i],
                        "metadata": results["metadatas"][i],
                        "similarity": 1.0 / (1.0 + float(results.get("distances", [[0]])[0][i]))
                    }
                    formatted_results.append(result)
                    
            return {
                "success": True,
                "results": formatted_results,
                "total": len(formatted_results)
            }
            
        except Exception as e:
            logging.error(f"Error querying messages: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def delete_messages(self, filter_dict: Dict) -> Dict:
        """Delete messages based on filter"""
        try:
            if not self.collection:
                return {
                    "success": False,
                    "error": "Database not initialized"
                }
                
            results = self.collection.get(
                where=filter_dict,
                include=["metadatas"]
            )
            
            if not results["ids"]:
                return {
                    "success": True,
                    "message": "No messages found to delete",
                    "deleted_count": 0
                }
                
            self.collection.delete(ids=results["ids"])
            
            return {
                "success": True,
                "message": f"Deleted {len(results['ids'])} messages",
                "deleted_count": len(results["ids"])
            }
            
        except Exception as e:
            logging.error(f"Error deleting messages: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
