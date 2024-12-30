from typing import Dict, List, Optional
from ..db.message_db import MessageDB
from ..db.sqlite_db import SQLiteDB
from .semantic_search import SemanticSearch
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SearchManager:
    def __init__(self, message_db: MessageDB):
        self.message_db = message_db
        self.sqlite_db = message_db.sqlite_db
        self.semantic_searcher = SemanticSearch(message_db, message_db.cache)

    async def semantic_search(self, 
                            query: str,
                            filters: Optional[Dict] = None,
                            limit: int = 5,
                            distance_threshold: float = 0.5) -> List[Dict]:
        """
        执行语义搜索
        
        Args:
            query: 搜索查询文本
            filters: 过滤条件
            limit: 返回结果数量
            distance_threshold: 相似度阈值
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            results = await self.semantic_searcher.search(
                query=query,
                filters=filters,
                limit=limit,
                distance_threshold=distance_threshold
            )
            logger.info(f"Semantic search for '{query}' found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []

    async def db_search(self,
                       user_name: Optional[str] = None,
                       group_id: Optional[str] = None,
                       start_time: Optional[int] = None,
                       end_time: Optional[int] = None,
                       limit: int = 10,
                       offset: int = 0,
                       order_by: str = "timestamp DESC") -> List[Dict]:
        """
        执行数据库搜索
        
        Args:
            user_name: 用户名
            group_id: 群组ID
            start_time: 开始时间戳
            end_time: 结束时间戳
            limit: 返回记录数量
            offset: 分页偏移量
            order_by: 排序方式
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            results = await self.sqlite_db.query_messages(
                user_name=user_name,
                group_id=group_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                offset=offset,
                order_by=order_by
            )
            logger.info(f"Database search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in database search: {str(e)}")
            return []

    async def combined_search(self,
                            query: str,
                            user_name: Optional[str] = None,
                            group_id: Optional[str] = None,
                            start_time: Optional[int] = None,
                            end_time: Optional[int] = None,
                            limit: int = 5) -> Dict[str, List[Dict]]:
        """
        执行组合搜索（同时进行语义搜索和数据库搜索）
        
        Args:
            query: 搜索查询文本
            user_name: 用户名过滤
            group_id: 群组ID过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 每种搜索的结果数量
            
        Returns:
            Dict[str, List[Dict]]: 包含两种搜索结果的字典
        """
        try:
            # 构建过滤条件
            filters = {}
            if user_name:
                filters['user_name'] = user_name
            if group_id:
                filters['group_id'] = group_id
            if start_time:
                filters['timestamp'] = {'$gte': start_time}
            if end_time:
                filters['timestamp'] = {'$lte': end_time}

            # 并行执行两种搜索
            semantic_results = await self.semantic_search(
                query=query,
                filters=filters,
                limit=limit
            )
            
            db_results = await self.db_search(
                user_name=user_name,
                group_id=group_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            
            return {
                'semantic_results': semantic_results,
                'db_results': db_results
            }
            
        except Exception as e:
            logger.error(f"Error in combined search: {str(e)}")
            return {
                'semantic_results': [],
                'db_results': []
            }