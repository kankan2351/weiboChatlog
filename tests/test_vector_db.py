import asyncio
from typing import List, Dict
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot.utils.config import Config
from chatbot.db.message_db import MessageDB
from chatbot.utils.embeddings import generate_embeddings
from chatbot.utils.logger import get_logger

logger = get_logger(__name__)

async def test_insert_messages(message_db: MessageDB):
    """测试消息插入"""
    current_time = datetime.now()
    test_messages = [
        {
            "id": f"test_msg_1_{int(current_time.timestamp())}",
            "content": "这是一条测试消息",
            "time": current_time.isoformat(),
            "timestamp": int(current_time.timestamp()),
            "type": "text",
            "from": {
                "name": "测试用户1",
                "uid": "u001"
            },
            "group": {
                "gid": "g001"
            },
            "media_type": 0
        },
        {
            "id": f"test_msg_2_{int(current_time.timestamp())}",
            "content": "Python是一种优雅的编程语言",
            "time": current_time.isoformat(),
            "timestamp": int(current_time.timestamp()),
            "type": "text",
            "from": {
                "name": "测试用户2",
                "uid": "u002"
            },
            "group": {
                "gid": "g001"
            },
            "media_type": 0
        },
        {
            "id": f"test_msg_3_{int(current_time.timestamp())}",
            "content": "向量数据库可以进行语义搜索",
            "time": current_time.isoformat(),
            "timestamp": int(current_time.timestamp()),
            "type": "text",
            "from": {
                "name": "测试用户1",
                "uid": "u001"
            },
            "group": {
                "gid": "g001"
            },
            "media_type": 0
        }
    ]
    
    for msg in test_messages:
        try:
            # 直接传入整个消息字典
            success = await message_db.add_message(message=msg)
            if success:
                logger.info(f"Successfully inserted message: {msg['content']}")
            else:
                logger.error(f"Failed to insert message: {msg['content']}")
            
        except Exception as e:
            logger.error(f"Error inserting message: {str(e)}")

async def test_query_messages(message_db: MessageDB):
    """测试消息查询"""
    test_queries = [
        {
            "query": "python优雅",
            "description": "基本查询测试"
        }
    ]
    
    for test in test_queries:
        try:
            # 生成查询向量
            query_embedding = generate_embeddings(test["query"])
            
            # 执行查询
            results = await message_db.query_messages(
                embeddings=query_embedding,
                n_results=5
            )
            
            logger.info(f"\n--- {test['description']} ---")
            logger.info(f"Query: {test['query']}")
            
            if results and results.get('results'):
                for i, msg in enumerate(results['results'], 1):
                    logger.info(f"{i}. Content: {msg.get('content')}")
                    logger.info(f"   Distance: {msg.get('distance')}")
                    logger.info(f"   Metadata: {msg.get('metadata')}\n")
            else:
                logger.info("No results found")
                
        except Exception as e:
            logger.error(f"Error querying messages: {str(e)}")

async def test_filtered_query(message_db: MessageDB):
    """测试带过滤条件的查询"""
    try:
        # 使用用户ID过滤
        filter_dict = {"user_id": "test_user_1"}
        query_embedding = generate_embeddings("测试消息")
        
        results = await message_db.query_messages(
            embeddings=query_embedding,
            filter_dict=filter_dict,
            n_results=5
        )
        
        logger.info("\n--- Filtered Query Test ---")
        logger.info(f"Filter: {filter_dict}")
        
        if results and results.get('results'):
            for i, msg in enumerate(results['results'], 1):
                logger.info(f"{i}. Content: {msg.get('content')}")
                logger.info(f"   User: {msg.get('metadata', {}).get('user_id')}")
                logger.info(f"   Distance: {msg.get('distance')}\n")
        else:
            logger.info("No results found")
            
    except Exception as e:
        logger.error(f"Error in filtered query: {str(e)}")

async def test_scalar_query(message_db: MessageDB):
    """测试标量查询"""
    try:
        # 测试各种标量查询条件
        test_cases = [
            {
                "description": "按用户ID查询",
                "where": {"user_id": "u001"}
            },
            {
                "description": "按群组查询",
                "where": {"group_id": "g001"}
            },
            {
                "description": "按时间范围查询",
                "where": {
                    "timestamp": {"$gte": int((datetime.now() - timedelta(days=1)).timestamp())}
                }
            },
            {
                "description": "复合条件查询",
                "where": {
                    "$and": [
                        {"user_id": "u001"},
                        {"media_type": 0},
                        {"has_media": False}
                    ]
                }
            }
        ]
        
        for test in test_cases:
            logger.info(f"\n--- {test['description']} ---")
            
            # 执行查询
            results = await message_db.query_messages(
                embeddings=generate_embeddings("测试查询"),
                filter_dict=test["where"],
                n_results=5
            )
            
            if results and results.get('results'):
                for i, msg in enumerate(results['results'], 1):
                    logger.info(f"{i}. Content: {msg.get('content')}")
                    logger.info(f"   User: {msg.get('metadata', {}).get('user_name')}")
                    logger.info(f"   Group: {msg.get('metadata', {}).get('group_id')}")
                    logger.info(f"   Time: {msg.get('metadata', {}).get('time')}\n")
            else:
                logger.info("No results found")
                
    except Exception as e:
        logger.error(f"Error in scalar query test: {str(e)}")

# 查询总数据量
async def test_count_messages(message_db: MessageDB):
    """测试查询总数据量"""
    count = await message_db.count_messages()
    logger.info(f"Total messages: {count}")

async def main():
    """主测试函数"""
    try:
        config = Config()
        message_db = MessageDB(config)
        
        # 运行测试
        # await test_insert_messages(message_db)
        await test_query_messages(message_db)
        # await test_filtered_query(message_db)
        # await test_scalar_query(message_db)
        #await test_count_messages(message_db)
        
    except Exception as e:
        logger.error(f"Test error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())