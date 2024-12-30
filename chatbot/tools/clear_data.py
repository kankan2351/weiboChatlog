import os
import json
import shutil
import asyncio
import logging
from pathlib import Path
from chatbot.utils.config import Config
from chatbot.db.message_db import MessageDB

logger = logging.getLogger(__name__)

async def clear_all_data():
    """清空所有数据"""
    try:
        config = Config()
        # 1. 清空 processed_messages.json
        processed_messages_file = "./data/processed_messages.json"
        os.makedirs(os.path.dirname(processed_messages_file), exist_ok=True)
        with open(processed_messages_file, 'w') as f:
            json.dump([], f)
        logger.info("Reset processed_messages.json to empty array")

        # 2. 清空向量数据库
        config = Config()
        message_db = MessageDB(config)
        # 清空向量数据库
        all_ids = message_db.collection.get()['ids']  # 获取所有文档的 ID
        if all_ids:  # 如果有数据才执行删除
            message_db.collection.delete(ids=all_ids)  # 删除所有数据
        logger.info("Cleared vector database")

        # 3. 清空 SQLite 数据库
        db = message_db.sqlite_db
        await db.execute("DELETE FROM messages")
        await db.execute("VACUUM")  # 回收空间
        logger.info("Cleared SQLite database")
        

        
        logger.info("All data cleared successfully")
        
    except Exception as e:
        logger.error(f"Error clearing data: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(clear_all_data()) 