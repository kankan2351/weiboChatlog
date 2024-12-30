import asyncio
from typing import Dict, List, Optional
from chatbot.utils.config import Config
from chatbot.db.message_db import MessageDB
from chatbot.handlers.ai_interface import AIInterface
from chatbot.utils.logger import get_logger
from chatbot.language.detector import LanguageDetector
from openai import AzureOpenAI

logger = get_logger(__name__)

class MockCache:
    """模拟缓存类"""
    async def get(self, key):
        return None
    async def set(self, key, value, expire=None):
        pass

async def test_ai_handler():
    """测试 AI Handler 的工具调用功能"""
    try:
        # 初始化必要组件
        config = Config()
        message_db = MessageDB(config)
        message_db.cache = MockCache()
        lang_detector = LanguageDetector(MockCache())
        
        # 初始化真实的 OpenAI 客户端
        azure_config = config.get_azure_config()
        openai_client = AzureOpenAI(
            azure_endpoint=azure_config['openai_endpoint'],
            api_key=azure_config['openai_key'],
            api_version=azure_config['api_version']
        )
        
        # 初始化 AI Handler
        ai_handler = AIInterface(
            config=config,
            openai_client=openai_client,
            lang_detector=lang_detector,
            message_db=message_db
        )
        
        # 测试场景
        test_cases = [
            {
                "name": "搜索用户消息",
                "query": "查找用户 tqtq 最近说过什么",
                "expected_tool": "search_user_messages",
                "expected_args": {
                    "user_name": "tqtq",
                    "limit": 5
                }
            },
            {
                "name": "语义搜索",
                "query": "有人讨论过 AI 相关的话题吗",
                "expected_tool": "search_messages",
                "expected_args": {
                    "query": "AI",
                    "limit": 5
                }
            },
            {
                "name": "隐私设置",
                "query": "我不想被记录发言",
                "expected_tool": "manage_privacy",
                "expected_args": {
                    "action": "stop_recording",
                    "user_name": "test_user"
                }
            },
            {
                "name": "帮助信息",
                "query": "你能做什么",
                "expected_tool": "get_help",
                "expected_args": {}
            },
            {
                "name": "复杂查询",
                "query": "最近一周有人讨论过 Python 编程相关的话题吗？",
                "expected_tool": "search_messages",
                "expected_args": {
                    "query": "Python programming",
                    "limit": 5
                }
            },
            {
                "name": "特定时间段查询",
                "query": "昨天下午有人聊天吗？",
                "expected_tool": "search_messages",
                "expected_args": {
                    "query": "",
                    "limit": 5
                }
            }
        ]
        
        # 执行测试
        for test in test_cases:
            print(f"\n{'='*50}")
            print(f"测试场景: {test['name']}")
            print(f"输入查询: {test['query']}")
            print(f"期望工具: {test['expected_tool']}")
            print(f"期望参数: {test['expected_args']}")
            print(f"{'-'*50}")
            
            try:
                # 构建用户信息
                user = {
                    "uid": "test_user_id",
                    "name": "test_user",
                    "verified": False,
                    "verified_type": None,
                    "avatar": None
                }
                
                # 直接使用查询文本作为消息内容
                response = await ai_handler.ai_process_message(test['query'], user)
                
                print("\n实际响应:")
                print(response)
                
                # 添加延迟以避免 API 限制
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"测试场景 '{test['name']}' 执行失败: {str(e)}")
                continue
            
            print(f"{'='*50}\n")
                
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_ai_handler()) 