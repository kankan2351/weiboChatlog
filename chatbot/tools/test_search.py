import asyncio
from typing import Dict, List, Optional
from chatbot.utils.config import Config
from chatbot.db.message_db import MessageDB
from chatbot.search.search_manager import SearchManager
from chatbot.utils.logger import get_logger
from datetime import datetime, timedelta

logger = get_logger(__name__)

class MockCache:
    """模拟缓存类，用于测试"""
    async def get(self, key):
        return None
        
    async def set(self, key, value, expire=None):
        pass

async def test_search():
    """测试搜索功能"""
    try:
        # 初始化组件
        config = Config()
        message_db = MessageDB(config)
        message_db.cache = MockCache()  # 添加 mock cache
        search_manager = SearchManager(message_db)
        
        # 测试场景
        test_cases = [
            {
                "name": "语义搜索测试",
                "type": "semantic",
                "params": {
                    "query": "AI",
                    "limit": 5,
                    "distance_threshold": 0.5
                }
            },
            {
                "name": "数据库搜索测试",
                "type": "db",
                "params": {
                    "user_name": "tqtq",
                    "limit": 10,
                    "order_by": "timestamp DESC"
                }
            },
            {
                "name": "最近24小时消息搜索",
                "type": "db",
                "params": {
                    "start_time": int((datetime.now() - timedelta(days=1)).timestamp()),
                    "end_time": int(datetime.now().timestamp()),
                    "limit": 10,
                    "order_by": "timestamp DESC"
                }
            },
            {
                "name": "组合搜索测试",
                "type": "combined",
                "params": {
                    "query": "AI",
                    "user_name": "tqtq",
                    "limit": 5
                }
            }
        ]
        
        # 执行测试
        for test in test_cases:
            print(f"\n=== {test['name']} ===")
            print(f"搜索类型: {test['type']}")
            print(f"参数: {test['params']}")
            
            if test['type'] == 'semantic':
                results = await search_manager.semantic_search(**test['params'])
                print(f"\n找到 {len(results)} 条语义搜索结果:")
                
            elif test['type'] == 'db':
                results = await search_manager.db_search(**test['params'])
                print(f"\n找到 {len(results)} 条数据库搜索结果:")
                
            else:  # combined
                results = await search_manager.combined_search(**test['params'])
                print(f"\n找到 {len(results['semantic_results'])} 条语义搜索结果:")
                print(f"找到 {len(results['db_results'])} 条数据库搜索结果:")
                
            # 打印结果
            if test['type'] == 'combined':
                for search_type, search_results in results.items():
                    print(f"\n{search_type}:")
                    for idx, result in enumerate(search_results, 1):
                        print_result(idx, result)
            else:
                for idx, result in enumerate(results, 1):
                    print_result(idx, result)
                    
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")

def print_result(idx: int, result: Dict):
    """格式化打印单条结果"""
    print(f"\n结果 {idx}:")
    print(f"ID: {result.get('id', 'N/A')}")
    print(f"时间: {result.get('time', 'N/A')}")
    print(f"用户: {result.get('user_name', 'N/A')}")
    print(f"内容: {result.get('content', 'N/A')}")
    if 'distance' in result:
        print(f"��似度: {1 - result['distance']:.4f}")
    print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_search()) 