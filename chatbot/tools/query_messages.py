import asyncio
from typing import Optional, List, Dict
from chatbot.utils.config import Config
from chatbot.db.message_db import MessageDB
from chatbot.utils.logger import get_logger
from chatbot.utils.embeddings import generate_embeddings

logger = get_logger(__name__)

class MessageQuery:
    def __init__(self):
        self.config = Config()
        self.message_db = MessageDB(self.config)
        
    async def search_by_content(self, query: str, limit: int = 5) -> List[Dict]:
        """根据内容搜索消息"""
        try:
            # 生成查询文本的嵌入向量
            embeddings = generate_embeddings(query)
            
            # 使用 query_messages 进行语义搜索
            results = await self.message_db.query_messages(
                embeddings=embeddings,
                n_results=limit,
                use_semantic_search=True
            )
            return results.get('results', [])
        except Exception as e:
            logger.error(f"Error searching messages: {str(e)}")
            return []
            
    async def get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """获取最近的消息"""
        try:
            # 使用 query_messages 获取消息，按时间戳排序
            results = await self.message_db.query_messages(
                n_results=limit,
                use_semantic_search=False,
                filter_dict={"timestamp": {"$gt": 0}}  # 使用有效的过滤条件
            )
            return results.get('results', [])
        except Exception as e:
            logger.error(f"Error getting recent messages: {str(e)}")
            return []
            
    async def get_user_messages(self, user_name: str, limit: int = 10) -> List[Dict]:
        """获取特定用户的消息"""
        try:
            # 使用 query_messages 获取特定用户的消息
            results = await self.message_db.query_messages(
                filter_dict={"user_name": {"$eq": user_name}},  # 使用 $eq 操作符
                n_results=limit,
                use_semantic_search=False
            )
            return results.get('results', [])
        except Exception as e:
            logger.error(f"Error getting user messages: {str(e)}")
            return []

    def format_message(self, content: str) -> str:
        """格式化消息内容，处理多层分割的回复"""
        # 使用分隔符分割消息
        parts = content.split("\n- - - - - - - - - - - - - - -\n")
        
        # 获取最后一个部分作为实际发言
        actual_content = parts[-1].strip()
        
        # 如果有引用内容（多于一个部分）
        if len(parts) > 1:
            # 获取倒数第二个部分作为被回复的内容
            quoted_content = parts[-2].strip()
            
            # 如果被引用的内容以 @ 开头，提取用户名
            if quoted_content.startswith('@'):
                user_end = quoted_content.find(' ')
                if user_end != -1:
                    replied_user = quoted_content[1:user_end]
                    quoted_text = quoted_content[user_end:].strip()
                    return f"对 '{replied_user}' 的「{quoted_text}」回复：{actual_content}"
        
        return actual_content

    async def delete_messages(self, ids: List[str]) -> bool:
        """删除指定 ID 的消息"""
        try:
            # ChromaDB 的删除方法
            self.message_db.collection.delete(
                ids=ids
            )
            logger.info(f"Successfully deleted messages with IDs: {ids}")
            return True
        except Exception as e:
            logger.error(f"Error deleting messages: {str(e)}")
            return False

    async def get_total_messages(self) -> int:
        """获取向量数据库中的总消息数量"""
        try:
            # 直接使用 ChromaDB 的 count 方法获取总数
            total_count = self.message_db.collection.count()
            return total_count
        except Exception as e:
            logger.error(f"Error getting total message count: {str(e)}")
            return 0

async def main():
    query = MessageQuery()
    
    # ids_to_delete = ["test_msg_1_1734574070"]
    # success = await query.delete_messages(ids_to_delete)
    # if success:
    #     print(f"Successfully deleted messages: {ids_to_delete}")
    # else:
    #     print("Failed to delete messages")

    # 0. 获取总消息数量
    total_messages = await query.get_total_messages()
    print(f"Total messages: {total_messages}")

    # 1. 获取最近消息
    # print("\n=== 最近消息 ===")
    # recent_messages = await query.get_recent_messages(20)
    # for msg in recent_messages:
    #     print(f"ID: {msg['metadata'].get('id', 'N/A')}")
    #     print(f"Time: {msg['metadata']['time']}")
    #     print(f"User: {msg['metadata']['user_name']}")
    #     print(f"Content: {query.format_message(msg['content'])}")
    #     print("-" * 50)
    
    # # 2. 搜索特定内容
    # search_term = "你好"  # 可以修改搜索词
    # print(f"\n=== 搜索 '{search_term}' ===")
    # search_results = await query.search_by_content(search_term)
    # for msg in search_results:
    #     print(f"ID: {msg['metadata'].get('id', 'N/A')}")
    #     print(f"Time: {msg['metadata']['time']}")
    #     print(f"User: {msg['metadata']['user_name']}")
    #     print(f"Content: {query.format_message(msg['content'])}")
    #     print(f"Similarity: {1 - msg['distance']:.4f}")
    #     print("-" * 50)
    
    # # 3. 获取特定用户的消息
    # user_name = "张三"  # 可以修改用户名
    # print(f"\n=== 用户 '{user_name}' 的消息 ===")
    # user_messages = await query.get_user_messages(user_name)
    # for msg in user_messages:
    #     print(f"ID: {msg['metadata'].get('id', 'N/A')}")
    #     print(f"Time: {msg['metadata']['time']}")
    #     print(f"Content: {query.format_message(msg['content'])}")
    #     print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())