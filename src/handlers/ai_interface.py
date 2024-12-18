# src/handlers/ai_interface.py
import os
import json
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
from pathlib import Path
from openai import AzureOpenAI

from .base_handler import BaseHandler
from ..db.message_db import MessageDB
from ..utils.logger import get_logger
from ..utils.redis_client import RedisClient
from ..summarizer.tokenizer import TokenManager
from ..summarizer.cache import SummaryCache
from ..summarizer.chunker import MessageChunker
from ..summarizer.recursive_sum import RecursiveSummarizer
from ..language.detector import LanguageDetector
from ..language.formatter import ResponseFormatter
from ..language.templates import TemplateManager
from ..search import SemanticSearch, FilterHandler
from ..advisor import SuggestionEngine
from ..analytics import DataAnalyzer

logger = get_logger(__name__)

class AIInterface(BaseHandler):
    def __init__(self, config):
        """初始化 AI 接口及所有组件"""
        super().__init__(db_path=config.get_db_config()['sqlite_db_path'])
        
        # 初始化 OpenAI 客户端
        azure_config = config.get_azure_config()
        self.client = AzureOpenAI(
            azure_endpoint=azure_config['openai_endpoint'],
            api_key=azure_config['openai_key'],
            api_version=azure_config['api_version']
        )
        
        # 初始化核心组件
        self.message_db = MessageDB(config.get_db_config()['vector_db_path'])
        self.token_manager = TokenManager()
        self.cache = SummaryCache(RedisClient(**config.get_cache_config()))
        
        # 初始化语言处理
        self.lang_detector = LanguageDetector(self.cache)
        self.templates = TemplateManager()
        self.formatter = ResponseFormatter(self.lang_detector, self.templates)
        
        # 初始化消息处理
        self.chunker = MessageChunker(self.token_manager, self.cache)
        self.summarizer = RecursiveSummarizer(self.token_manager, self.cache)
        
        # Initialize components
        self.message_db = MessageDB(config.get_db_config()['vector_db_path'])
        self.summarizer = SummaryHandler(self.client, config.cache)
        self.search = SemanticSearch(self.message_db, config.cache)
        self.filter_handler = FilterHandler()
        self.suggestion_engine = SuggestionEngine(self.client, config.cache)
        self.data_analyzer = DataAnalyzer(self.message_db, config.cache)
        
        # Configure tools
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "stop_tracking",
                    "description": "Stop tracking user's messages",
                    "parameters": {
                        "type": "object",
                        "required": ["user"],
                        "properties": {
                            "user": {
                                "type": "string",
                                "description": "Username to stop tracking"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_messages",
                    "description": "Delete user's messages",
                    "parameters": {
                        "type": "object",
                        "required": ["user"],
                        "properties": {
                            "user": {
                                "type": "string",
                                "description": "Username whose messages to delete"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "summarize_history",
                    "description": "Summarize chat history",
                    "parameters": {
                        "type": "object",
                        "required": ["time_range"],
                        "properties": {
                            "time_range": {
                                "type": "string",
                                "description": "Time range (24h, 7d, 30d)",
                                "enum": ["24h", "7d", "30d"]
                            },
                            "summary_type": {
                                "type": "string",
                                "description": "Type of summary",
                                "enum": ["brief", "detailed", "topics"]
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_messages",
                    "description": "Search for messages",
                    "parameters": {
                        "type": "object",
                        "required": ["query"],
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "time_range": {
                                "type": "string",
                                "description": "Time range for search",
                                "enum": ["24h", "7d", "30d", "all"]
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_suggestions",
                    "description": "Get contextual suggestions",
                    "parameters": {
                        "type": "object",
                        "required": ["question"],
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "User question"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_activity",
                    "description": "Analyze chat activity",
                    "parameters": {
                        "type": "object",
                        "required": ["time_range"],
                        "properties": {
                            "time_range": {
                                "type": "string",
                                "description": "Time range for analysis",
                                "enum": ["24h", "7d", "30d"]
                            }
                        }
                    }
                }
            }
        ]
        
        # Map available functions
        self.available_functions = {
            'stop_tracking': self.stop_tracking,
            'delete_messages': self.delete_messages,
            'summarize_history': self.summarize_history,
            'search_messages': self.search_messages,
            'get_suggestions': self.get_suggestions,
            'analyze_activity': self.analyze_activity
        }
        
    async def process_message(self, content: str, user: str) -> Dict:
        """Process user messages"""
        try:
            content = content.replace('@茧房爬楼王', '').strip()
            
            # 检测消息语言
            detected_lang = await self.lang_detector.detect_language(content)
            
            if not content:
                # 根据检测到的语言返回欢迎消息
                welcome_msg = await self.formatter.format_response(
                    content="我可以帮你：\n- 总结聊天历史\n- 搜索历史消息\n- 提供智能建议\n- 分析聊天活动\n请问需要什么帮助？",
                    template_key='greeting',
                    detected_lang=detected_lang
                )
                return {
                    "success": True,
                    "response": welcome_msg,
                    "detected_lang": detected_lang
                }
                
            # 检查用户状态
            if status := self.get_user_status(user):
                if status['status'] == 'blocked':
                    return {
                        "success": False,
                        "response": await self.formatter.format_response(
                            content=f"用户 {user} 已被禁止访问",
                            template_key='error',
                            detected_lang=detected_lang
                        )
                    }
                    
            # 生成回复
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an AI assistant with these capabilities:
                        1. Summarize chat history
                        2. Search messages
                        3. Provide suggestions
                        4. Analyze chat activity
                        5. Manage user tracking
                        
                        Understand user needs and use appropriate functions.
                        Respond in a friendly and helpful manner."""
                    },
                    {
                        "role": "user",
                        "content": f"User: {user}\nMessage: {content}"
                    }
                ],
                tools=self.tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Handle function calls
            if message.tool_calls:
                responses = []
                for tool_call in message.tool_calls:
                    try:
                        function_name = tool_call.function.name
                        function = self.available_functions.get(function_name)
                        if function:
                            args = json.loads(tool_call.function.arguments)
                            result = await function(**args)
                            
                            if result.get('success'):
                                self.log_action(
                                    action_type=function_name,
                                    user_name=user,
                                    details=str(result)
                                )
                                
                                # Format response based on function
                                if 'summary' in result:
                                    responses.append(f"Summary:\n{result['summary']}")
                                elif 'suggestions' in result:
                                    responses.append("Suggestions:")
                                    for i, sugg in enumerate(result['suggestions'], 1):
                                        responses.append(f"{i}. {sugg['suggestion']}")
                                elif 'insights' in result:
                                    responses.append("Analysis Results:")
                                    for key, value in result['insights'].items():
                                        responses.append(f"{key}: {value}")
                                elif 'results' in result:
                                    responses.append(f"Found {len(result['results'])} messages:")
                                    for msg in result['results'][:5]:
                                        responses.append(f"- {msg['content']}")
                                else:
                                    responses.append(result.get('message', 'Operation completed'))
                            else:
                                responses.append(f"Error: {result.get('message', 'Operation failed')}")
                                
                    except Exception as e:
                        logger.error(f"Error executing {function_name}: {str(e)}")
                        responses.append(f"Error executing {function_name}")
                        
                return {
                    "success": True,
                    "response": "\n".join(responses)
                }
                
            return {
                "success": True,
                "response": message.content
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "success": False,
                "response": f"Error processing message: {str(e)}"
            }
            
    async def stop_tracking(self, user: str) -> Dict:
        """Stop tracking user messages"""
        try:
            if self.update_user_status(
                user_name=user,
                status='blocked',
                updated_by='system',
                reason='User requested'
            ):
                return {
                    "success": True,
                    "message": f"Stopped tracking messages from {user}"
                }
            return {
                "success": False,
                "message": f"Failed to stop tracking {user}"
            }
        except Exception as e:
            logger.error(f"Error stopping user tracking: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
            
    async def delete_messages(self, user: str) -> Dict:
        """Delete user messages"""
        try:
            result = self.message_db.delete_messages(
                filter_dict={"from_user": user}
            )
            if result['success']:
                self.log_action(
                    action_type='delete_messages',
                    user_name=user,
                    details=f"Deleted {result['deleted_count']} messages"
                )
            return result
        except Exception as e:
            logger.error(f"Error deleting messages: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
            
    async def summarize_history(
        self,
        time_range: str,
        summary_type: str = 'brief'
    ) -> Dict:
        """使用三层递归架构总结聊天历史"""
        try:
            # 获取消息
            messages = await self.message_db.query_messages(
                filter_dict=self.filter_handler.create_filter_dict(time_range=time_range)
            )
            
            if not messages.get('results'):
                return {
                    "success": False,
                    "message": "指定时间范围内未找到消息记录"
                }
            
            # 1. 基于token限制分块
            chunks = await self.chunker.split_by_tokens(
                messages=messages['results'],
                max_tokens=3000
            )
            
            # 2. 第一层：基础块总结
            base_summaries = await self.summarizer.summarize_layer1(chunks)
            if not base_summaries:
                return {
                    "success": False,
                    "message": "生成基础总结失败"
                }
            
            # 3. 第二层：主题合并总结
            topic_summaries = await self.summarizer.summarize_layer2(base_summaries)
            if not topic_summaries:
                return {
                    "success": False,
                    "message": "生成主题总结失败"
                }
            
            # 4. 第三层：最终总结
            final_summary = await self.summarizer.summarize_layer3(topic_summaries)
            if not final_summary:
                return {
                    "success": False,
                    "message": "生成最终总结失败"
                }
            
            # 5. 格式化响应
            formatted_summary = await self.formatter.format_response(
                content=final_summary['content'],
                template_key='summary',
                time_range=time_range,
                message_count=final_summary['message_count'],
                topic_count=final_summary.get('topic_count', 1)
            )
            
            return {
                "success": True,
                "summary": formatted_summary,
                "stats": {
                    "chunks": len(chunks),
                    "base_summaries": len(base_summaries),
                    "topic_summaries": len(topic_summaries),
                    "total_messages": final_summary['message_count'],
                    "time_range": final_summary['time_range']
                }
            }
            
        except Exception as e:
            logger.error(f"Error summarizing history: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
            
    async def search_messages(
        self,
        query: str,
        time_range: str = 'all'
    ) -> Dict:
        """Search messages"""
        try:
            filters = self.filter_handler.create_filter_dict(time_range=time_range)
            return await self.search.search(
                query=query,
                filters=filters
            )
        except Exception as e:
            logger.error(f"Error searching messages: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
            
    async def get_suggestions(self, question: str) -> Dict:
        """Get contextual suggestions"""
        try:
            # Get recent context
            context = await self.message_db.query_messages(
                filter_dict={
                    "timestamp": {
                        "$gte": datetime.now() - timedelta(hours=24)
                    }
                },
                limit=10
            )
            
            return await self.suggestion_engine.get_suggestions(
                context=context.get('results', []),
                question=question
            )
            
        except Exception as e:
            logger.error(f"Error getting suggestions: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
            
    async def analyze_activity(self, time_range: str) -> Dict:
        """Analyze chat activity"""
        try:
            return await self.data_analyzer.generate_chat_insights(time_range)
        except Exception as e:
            logger.error(f"Error analyzing activity: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
[
    {
        "command_name": "Editor.edit_file_by_replace",
        "args": {
            "file_name": "src/cli.py",
            "to_replace": "from ai_handler import AIHandler",
            "new_content": "from handlers.ai_interface import AIInterface\nfrom utils.config import config"
        }
    }
]
