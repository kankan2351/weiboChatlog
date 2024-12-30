import asyncio
from typing import Optional, List, Dict
from chatbot.utils.config import Config
from chatbot.db.message_db import MessageDB
from chatbot.search.semantic_search import SemanticSearch
from chatbot.utils.logger import get_logger

logger = get_logger(__name__)

class MockCache:
    """模拟缓存类，用于测试"""
    async def get(self, key):
        return None
        
    async def set(self, key, value, expire=None):
        pass

async def test_semantic_search():
    """测试语义搜索功能"""
    try:
        # 初始化必要组件
        config = Config()
        message_db = MessageDB(config)
        mock_cache = MockCache()
        semantic_search = SemanticSearch(message_db, mock_cache)
        
        # 测试查询场景
        test_queries = [
            {
                "query": "*",  # 使用特殊查询触发标量搜索
                "filters": {
                    "user_name": "tqtq"  # 直接使用字段名
                },
                "limit": 10,
                "distance_threshold": 0.1
            }
        ]
        
        # 执行测试查询
        for test in test_queries:
            print(f"\n=== 测试查询: {test['query']} ===")
            print(f"过滤条件: {test['filters']}")
            print(f"限制数量: {test['limit']}")
            print(f"距离阈值: {test['distance_threshold']}")
            
            results = await semantic_search.search(
                query=test['query'],
                filters=test['filters'],
                limit=test['limit'],
                distance_threshold=test['distance_threshold']
            )
            
            print(f"\n找到 {len(results)} 条结果:")
            for idx, result in enumerate(results, 1):
                print(result)
                print(f"\n结果 {idx}:")
                print(f"ID: {result.get('id', 'N/A')}")
                print(f"时间: {result['metadata'].get('time', 'N/A')}")
                print(f"发言人: {result['metadata'].get('user_name', 'N/A')}")
                print(f"内容: {result.get('content', 'N/A')}")
                if 'distance' in result:
                    print(f"相似度: {1 - result['distance']:.4f}")
                print("-" * 50)
                
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_semantic_search())