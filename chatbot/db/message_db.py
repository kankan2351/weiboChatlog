# /data/chats/oqz4c/workspace/chatbot/db/message_db.py
import logging
import chromadb
from chromadb.utils import embedding_functions
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path
import uuid
from chromadb.config import Settings
import json
import time

from chatbot.utils.embeddings import generate_embeddings
from chatbot.utils.logger import get_logger
from chatbot.db.sqlite_db import SQLiteDB

logger = get_logger(__name__)

class MessageDB:
    def __init__(self, config):
        """初始化消息数据库"""
        self.config = config
        
        # 初始化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(
            path="./data/chromadb",
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # 初始化或获取集合
        self.collection = self.client.get_or_create_collection(
            name="messages",
            metadata={"hnsw:space": "cosine"}
        )
        
        # 初始化 SQLite 数据库
        self.sqlite_db = SQLiteDB()
        
        # 初始化缓存
        self.cache = None  # 将在运行时设置
        
    async def add_message(self, message: Dict) -> bool:
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
                
            # Generate embedding for content
            try:
                embedding = generate_embeddings(content)
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
                return False
                
            # Prepare metadata with searchable fields
            metadata = {
                # 基本信息
                "id": message_id,
                "time": str(message.get('time', '')),
                "timestamp": int(message.get('timestamp', 0)),
                "type": message.get('type', ''),
                
                # 用户信息（用于标量搜索）
                "user_name": message.get('from', {}).get('name', ''),
                "user_id": message.get('from', {}).get('uid', ''),
                
                # 群组信息（用于标量搜索）
                "group_id": message.get('group', {}).get('gid', ''),
                
                # 消息属性
                "media_type": int(message.get('media_type', 0)),
                "is_reply": bool(message.get('reply_to', False)),
                "has_media": bool(message.get('media_type', 0) > 0),
                
                # 时间相关（方便按时间段查询）
                "year": datetime.fromtimestamp(int(message.get('timestamp', 0))).year,
                "month": datetime.fromtimestamp(int(message.get('timestamp', 0))).month,
                "day": datetime.fromtimestamp(int(message.get('timestamp', 0))).day,
                "hour": datetime.fromtimestamp(int(message.get('timestamp', 0))).hour,
                
                # 消息统计
                "content_length": len(content),
                "word_count": len(content.split())
            }
            
            # Add to database with embedding
            self.collection.add(
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[message_id]
            )
            
            # logger.info(f"Added message {message_id} with metadata")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            return False
            
    async def query_messages(self, 
                           embeddings: Optional[List[float]] = None,
                           filter_dict: Optional[Dict] = None,
                           n_results: int = 5,
                           distance_threshold: float = 0.5,
                           use_semantic_search: bool = True) -> Dict:
        """
        查询消息
        
        Args:
            embeddings: 查询向量，用于语义搜索
            filter_dict: 过滤条件
            n_results: 返回结果数量
            distance_threshold: 相似度距离阈值
            use_semantic_search: 是否使用语义搜索
            
        Returns:
            Dict: 查询结果
        """
        try:
            if use_semantic_search and embeddings is not None:
                # 语义搜索
                results = self.collection.query(
                    query_embeddings=[embeddings],
                    where=filter_dict,
                    n_results=n_results,
                    include=['documents', 'metadatas', 'distances']
                )
            else:
                # 直接获取消息（不使用向量搜索）
                results = self.collection.get(
                    where=filter_dict,
                    limit=n_results,
                    include=['documents', 'metadatas']
                )
                # 转换为与 query 结果相同的格式
                results = {
                    'ids': [results['ids']],
                    'documents': [results['documents']],
                    'metadatas': [results['metadatas']],
                    'distances': [[0.0] * len(results['ids'])]  # 填充虚拟距离
                }
            
            # 格式化结果
            messages = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    if not use_semantic_search or (
                        results['distances'] and 
                        results['distances'][0][i] <= distance_threshold
                    ):
                        message = {
                            'content': results['documents'][0][i],
                            'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                            'id': results['ids'][0][i] if results['ids'] else None,
                            'distance': results['distances'][0][i] if results['distances'] else 0.0
                        }
                        messages.append(message)
                
            return {'results': messages}
            
        except Exception as e:
            logger.error(f"Error querying messages: {str(e)}")
            return {'results': []}  
    # 查询总数据量
    async def count_messages(self) -> int:
        """查询总数据量"""
        return self.collection.count()
