# /data/chats/oqz4c/workspace/chatbot/handlers/ai_interface.py
import os
import json
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import logging
from pathlib import Path
from openai import OpenAI

from chatbot.utils.config import Config
from chatbot.utils.logger import get_logger
from chatbot.db.message_db import MessageDB
from chatbot.utils.redis_client import RedisClient
from chatbot.summarizer.cache import SummaryCache
from chatbot.summarizer.recursive_sum import RecursiveSummarizer
from chatbot.language.templates import TemplateManager
from chatbot.search import SemanticSearch, FilterHandler
from chatbot.advisor import SuggestionEngine
from chatbot.analytics import DataAnalyzer
from chatbot.handlers.base_handler import BaseHandler
from chatbot.db.sqlite_db import SQLiteDB
from chatbot.utils.embeddings import generate_embeddings
from chatbot.search.search_manager import SearchManager

logger = get_logger(__name__)

class AIInterface(BaseHandler):
    def __init__(self, config: Config, openai_client, lang_detector, message_db):
        """Initialize AI interface with all components"""
        self.config = config
        self.client = openai_client
        self.lang_detector = lang_detector
        self.message_db = message_db
        self.sqlite_db = message_db.sqlite_db
        
        # 初始化搜索管理器
        self.search_manager = SearchManager(message_db)
        
        # Initialize OpenAI client
        # azure_config = config.get_azure_config()
        # self.client = AzureOpenAI(
        #     azure_endpoint=azure_config['openai_endpoint'],
        #     api_key=azure_config['openai_key'],
        #     api_version=azure_config['api_version']
        # )
        deepseek_config = config.get_deepseek_config()
        self.client = OpenAI(
            api_key=deepseek_config['api_key'], 
            base_url=deepseek_config['base_url']
        )
        
        # Initialize core components
        self.cache = SummaryCache(RedisClient(**config.get_cache_config()))
        
        # Initialize language processing
        self.templates = TemplateManager()
        
        # Initialize message processing
        self.summarizer = RecursiveSummarizer(self.cache, self.message_db, self.client, self.config)
        
        # Initialize other components
        self.search = SemanticSearch(self.message_db, self.cache)
        self.filter_handler = FilterHandler()
        self.suggestion_engine = SuggestionEngine(self.client, self.cache)
        self.data_analyzer = DataAnalyzer(self.message_db, self.cache)
        # Configure tools
        self.tools = self._setup_tools()

        # Rest of the class implementation remains the same...

    async def ai_process_message(self, content: str, user: str) -> Dict:
        """
        处理用户消息并返回响应
        
        Args:
            content (str): 用户消息内容
            user (str): 用户标识
            
        Returns:
            Dict: {
                'success': bool,
                'response': str,
                'detected_lang': str (optional)
            }
        """
        try:
            # 清理和预处理消息
            content = content.strip()
            detected_lang = await self.lang_detector.detect_language(content)
            
            # 处理空消息
            if not content:
                return await self._handle_empty_message(detected_lang)
                
            response = await self._generate_ai_response(content, user, detected_lang)
            
            # 处理工具调用
            if response.choices[0].message.tool_calls:
                return await self._handle_tool_calls(
                    response.choices[0].message.tool_calls,
                    user,
                    detected_lang
                )
            
            # 返回普通响应
            return {
                "success": True,
                "response": response.choices[0].message.content
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "success": False,
                "response": f"处理消息时出错: {str(e)}"
            }
            
    async def _handle_empty_message(self, detected_lang: str) -> Dict:
        """处理空消息"""
        welcome_msg = (
            "我可以帮你：\n"
            "- 总结聊天历史\n"
            "- 搜索历史消息\n"
            "- 提供智能建议\n"
            "- 分析聊天活动\n"
            "请问需要什么帮助？"
        )
        return {
            "success": True,
            "response": welcome_msg,
            "detected_lang": detected_lang
        }
        
    async def _generate_ai_response(self, content: str, user: str, detected_lang: str):
        """生成 AI 响应"""
        try:
            # 从 SQLite 获取最近的消息作为上下文
            recent_messages = await self.sqlite_db.get_recent_messages(50)
            
            # 添加日志以便调试
            logger.info(f"Retrieved {len(recent_messages)} messages from database")
            
            # 构建历史消息上下文
            context = "供参考的最近聊天记录：\n"
            if recent_messages:
                # 因为是倒序查询的，所以需要反转列表来展示
                for msg in reversed(recent_messages):
                    time_str = datetime.fromtimestamp(msg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    context += f"[{time_str}] {msg['user_name']}: {msg['content']}\n"
            else:
                context += "（暂无历史记录）\n"
            
            response = self.client.chat.completions.create(
                # model=self.config.get_azure_config()['model'],
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(detected_lang)
                    },
                    {
                        "role": "user",
                        "content": f"用户 '{user}' 通过@你说: '{content}'\n请针对这句话回复。\n{context}"
                    }
                ],
                tools=self.tools,
                tool_choice="auto",
                temperature=1.3,
                max_tokens=1000
            )
            return response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            raise
        
    def _get_system_prompt(self, detected_lang: str) -> str:
        """获取系统提示词"""
        return f"""你是一个智能助手，名字叫{self.config.bot_config['name']}，拥有以下功能：

1. 总结聊天历史 (summarize_chat)
   - 仅当用户明确要求总结或查看历史记录时使用
   - 例如："帮我总结一下聊天记录"、"看看之前聊了什么"

2. 消息搜索 (search_messages)
   - 仅当用户明确要求搜索或查找特定内容时使用
   - 当用户要查询某人的所有发言时，应该将 query 设置为 "*" 或空字符串，并设置 user_name
   - 当用户要搜索特定内容时，应该设置具体的 query，可选择性设置 user_name
   - 例如：
     * "查看张三的所有发言" → query: "*", user_name: "张三"
     * "搜索张三关于Python的发言" → query: "Python", user_name: "张三"
     * "查找关于数据库的讨论" → query: "数据库"

3. 活动分析 (analyze_activity)
   - 仅当用户要求分析聊天数据或统计信息时使用
   - 例如："分析一下今天的聊天活跃度"、"统计一下发言情况"

4. 隐私管理 (manage_privacy)
   - 仅当用户明确要求管理隐私设置或数据时使用
   - 支持的命令：停止记录信息、恢复记录信息

重要规则：
- 只在用户明确要求相关功能时才使用工具
- 对于普通对话和问题，直接回答，不要调用工具
- 如果不确定是否需要使用工具，优先选择直接回答
- 用户发出隐私管理命令时，直接执行，不需要确认
- 在搜索时要准确区分是搜索特定内容还是查看某人的所有发言
- 不要输出任何 Emoji

检测到用户语言：{detected_lang}
优先使用中文回复，如果是其他语言则使用相应语言。
保持友好、有趣的聊天风格，像朋友一样和用户互动。"""
        
    def _setup_tools(self) -> List[Dict]:
        """设置可用的工具"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_messages",
                    "description": "搜索历史消息。默认搜索所有用户的消息，可以通过指定用户名来查找特定用户的消息。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索关键词"
                            },
                            "user_name": {
                                "type": "string",
                                "description": "用户名（可选）。如果指定，则只搜索该用户的消息；如果不指定，则搜索所有用户的消息。例如：'张三'、'John'"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "返回结果数量限制，默认为5条",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 20
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_privacy",
                    "description": "管理用户隐私设置和数据",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "要执行的操作",
                                "enum": ["stop_recording", "delete_history", "resume_recording"]
                            },
                            "user_name": {
                                "type": "string",
                                "description": "用户名"
                            }
                        },
                        "required": ["action", "user_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "summarize_chat",
                    "description": "总结聊天历史",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "用户ID（可选）"
                            },
                            "time_range": {
                                "type": "string",
                                "description": "时间范围，例如 '1d'（1天）, '1w'（1周）等",
                                "default": "1d"
                            }
                        }
                    }
                }
            }
        ]
        
    def _setup_functions(self) -> Dict:
        """设置可用的函数"""
        # TODO: 实现函数配置
        return {}
        
    async def _check_user_status(self, user: str) -> bool:
        """检查用户状态"""
        try:
            user_status = await self.sqlite_db.get_user_status(user)
            
            if not user_status:
                # 如果用户不存在，创建新用户
                await self.sqlite_db.create_user(user)
                return True
            
            status = user_status.get('status')
            if status == 'blocked':
                logger.warning(f"Blocked user attempted access: {user}")
                return False
                
            if status == 'restricted':
                # 检查限制是否已过期
                if restricted_until := user_status.get('restricted_until'):
                    if datetime.now() > restricted_until:
                        await self.sqlite_db.update_user_status(user, 'active')
                        return True
                    return False
                    
            if status == 'no_record':
                # 允许访问，但不记录新消息
                return True
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking user status: {str(e)}")
            return True  # 如果出错，默认允许访问但记录错误
        
    async def _handle_tool_calls(self, tool_calls, user: str, detected_lang: str) -> Dict:
        """处理工具调用"""
        try:
            tool_results = []
            for tool_call in tool_calls:
                try:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # 记录函数调用日志
                    logger.info(f"Executing function: {function_name}")
                    logger.info(f"Function arguments: {json.dumps(function_args, ensure_ascii=False)}")
                    
                    # 直接执行工具调用，不需要确认
                    result = await self._execute_tool(function_name, function_args)
                    if result:
                        tool_results.append({
                            "tool": function_name,
                            "result": result
                        })
                        logger.info(f"Function {function_name} execution result: {result}")
                    
                except Exception as e:
                    logger.error(f"Error executing tool {function_name}: {str(e)}")
                    continue
            
            # 如果隐私管理工具被调用，直接返回结果
            if function_name == "manage_privacy":
                return {
                    "success": True,
                    "response": result
                }
            
            # 如果有工具执行结果，进行二次处理，隐私管理工具除外
            if tool_results and function_name != "manage_privacy":
                return await self._process_tool_results(tool_results, detected_lang)
            
            return {
                "success": False,
                "response": "无法处理请求"
            }
            
        except Exception as e:
            logger.error(f"Error handling tool calls: {str(e)}")
            return {
                "success": False,
                "response": f"处理工具调用时出错: {str(e)}"
            }

    async def _execute_tool(self, function_name: str, function_args: Dict) -> Optional[str]:
        """执行单个工具调用"""
        try:
            if function_name == "summarize_chat":
                result = await self.summarizer.summarize(
                    user_id=function_args.get('user_id'),
                    time_range=function_args.get('time_range', '1d')
                )
                return result
            
            elif function_name == "search_messages":
                query = function_args.get('query', '')
                user_name = function_args.get('user_name')
                limit = function_args.get('limit', 50)
                
                if user_name:
                    # 如果指定了用户名，使用数据库搜索
                    results = await self.search_manager.db_search(
                        user_name=user_name,
                        limit=limit,
                        order_by="timestamp DESC"
                    )
                else:
                    # 否则使用语义搜索
                    results = await self.search_manager.semantic_search(
                        query=query,
                        limit=limit
                    )
                
                if not results:
                    return "没有找到相关消息。"
                    
                # 格式化搜索结果
                formatted_results = []
                for msg in results:
                    get_time = msg.get('metadata', {}).get('time', '0')
                    time_str = self._parse_timestamp(get_time)
                    user_name = msg.get('metadata', {}).get('user_name', 'Unknown user')
                    content = msg.get('content', 'No content')
                    formatted_results.append(f"[{time_str}] {user_name}: {content}")
                    
                return "\n\n".join(formatted_results)
                
            elif function_name == "search_user_messages":
                user_name = function_args.get('user_name')
                limit = function_args.get('limit', 50)
                
                # 使用数据库搜索用户消息
                results = await self.search_manager.db_search(
                    user_name=user_name,
                    limit=limit,
                    order_by="timestamp DESC"
                )
                
                if not results:
                    return f"没有找到用户 {user_name} 的消息。"
                    
                # 格式化搜索结果
                formatted_results = []
                for msg in results:
                    time_str = msg.get('time', 'Unknown time')
                    content = msg.get('content', 'No content')
                    formatted_results.append(f"[{time_str}] {content}")
                    
                return "\n\n".join(formatted_results)
                
            elif function_name == "analyze_activity":
                # 功能还没实现，返回固定的回复
                return "抱歉，活跃度分析功能正在开发中，敬请期待。不要催我，催也没用。"
                analysis = await self.data_analyzer.analyze_activity(
                    user_id=function_args.get('user_id'),
                    analysis_type=function_args.get('analysis_type', 'daily')
                )
                if analysis:
                    return '\n'.join([f"{key}: {value}" for key, value in analysis.items()])
            
            elif function_name == "manage_privacy":
                action = function_args.get('action')
                user_name = function_args.get('user_name')
                if action == "stop_recording":
                    success = await self.sqlite_db.update_user_status(
                        user_name=user_name,
                        status='no_record'
                    )
                    if success:
                        return "已停止记录您的新消息。之前的消息仍然保留。"
                    return "操作失败，请稍后重试。"
                elif action == "resume_recording":
                    success = await self.sqlite_db.update_user_status(
                        user_name=user_name,
                        status='active'
                    )
                    if success:
                        return "已恢复记录您的新消息。"
                    return "操作失败，请稍后重试。"

            return None
            
        except Exception as e:
            logger.error(f"Error executing tool {function_name}: {str(e)}")
            return None

    async def _process_tool_results(self, tool_results: List[Dict], detected_lang: str) -> Dict:
        """处理工具执行结果"""
        try:
            # 根据工具类型获取相应的提示词
            prompts = []
            for result in tool_results:
                tool_prompt = self._get_tool_prompt(result["tool"], detected_lang)
                prompts.append(f"{tool_prompt}\n\n{result['result']}")
            
            # 组合所有结果和提示词
            combined_prompt = "\n\n".join(prompts)
            
            # 调用 AI 进行二次处理
            response = self.client.chat.completions.create(
                #model=self.config.get_azure_config()['model'],
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_result_processing_prompt(detected_lang)
                    },
                    {
                        "role": "user",
                        "content": combined_prompt
                    }
                ],
                temperature=1.3,
                max_tokens=1000
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content
            }
            
        except Exception as e:
            logger.error(f"Error processing tool results: {str(e)}")
            return {
                "success": False,
                "response": "处理结果时出错"
            }

    def _get_tool_prompt(self, tool_name: str, detected_lang: str) -> str:
        """获取工具特定的提示词"""
        prompts = {
            "summarize_chat": {
                "zh": "以下是聊天历史的总结。请分析这些内容，提取关键信息，并给出简洁的总结：",
                "en": "Here's a summary of chat history. Please analyze the content, extract key information, and provide a concise summary:"
            },
            "search_messages": {
                "zh": "以下是搜索到的相关信息。请分析这些消息，找出最相关的内容，并给出有见地的解读：",
                "en": "Here are the search results. Please analyze these messages, identify the most relevant content, and provide insightful interpretation:"
            },
            "analyze_activity": {
                "zh": "以下是聊天活动的分析数据。请解读这些数据，找出重要的模式和趋势：",
                "en": "Here's the chat activity analysis. Please interpret this data and identify important patterns and trends:"
            }
        }
        
        lang = "zh" if detected_lang == "zh" else "en"
        return prompts.get(tool_name, {}).get(lang, prompts[tool_name]["en"])

    def _get_result_processing_prompt(self, detected_lang: str) -> str:
        """获取结果处理的系统提示词"""
        prompts = {
            "zh": """作为AI助手，你的任务是：
1. 仔细分析工具返回的结果
2. 提取最重要和最相关的信息
3. 用清晰、自然的语言总结这些信息
4. 如果发现有趣的模式或见解，请指出
5. 保持回答简洁

请用对话式的语言回应，避免机械式的复述。""",
            
            "en": """As an AI assistant, your task is to:
1. Carefully analyze the tool results
2. Extract the most important and relevant information
3. Summarize this information in clear, natural language
4. Point out interesting patterns or insights if found
5. Keep responses concise but informative

Please respond in a conversational tone, avoiding mechanical repetition."""
        }
        
        return prompts.get(detected_lang, prompts["en"])

    async def generate_summary(self, messages: List[Dict], prompt: str) -> Optional[Dict]:
        """
        生成消息总结
        
        Args:
            messages: 要总结的消息列表
            prompt: 总结提示词
            
        Returns:
            Optional[Dict]: 总结结果
        """
        try:
            # 准备内容用于总结
            content = "\n".join([
                f"[{msg.get('metadata', {}).get('user_name', '未知用户')} "
                f"在 {msg.get('metadata', {}).get('time', '')}]: "
                f"{msg.get('content', '')}"
                for msg in messages
            ])
            
            # 添加提示词
            content = f"{prompt}\n\n{content}"
            
            response = await self.client.chat.completions.create(
                #model=self.config.get_azure_config()['model'],
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的对话总结助手。请分析对话内容，提取关键信息，生成简洁但信息完整的总结。"
                                    "关注重要的话题、决定和讨论要点。保持客观和准确。"
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=1.3,
                max_tokens=500
            )
            
            # 构建总结结果
            return {
                "content": response.choices[0].message.content,
                "time_range": {
                    "start": messages[0].get('metadata', {}).get('time'),
                    "end": messages[-1].get('metadata', {}).get('time')
                },
                "message_count": len(messages)
            }
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return None

    def _parse_timestamp(self, time_value: Any) -> str:
        """安全地解析时间戳或时间字符串
        
        Args:
            time_value: 可能是时间戳(int/str)或格式化的时间字符串
            
        Returns:
            str: 格式化的时间字符串 ('%Y-%m-%d %H:%M:%S')
        """
        try:
            # 如果是数字字符串，转换为整数
            if isinstance(time_value, str) and time_value.isdigit():
                return datetime.fromtimestamp(int(time_value)).strftime('%Y-%m-%d %H:%M:%S')
            
            # 如果是整数，直接转换
            if isinstance(time_value, (int, float)):
                return datetime.fromtimestamp(time_value).strftime('%Y-%m-%d %H:%M:%S')
            
            # 如果已经是格式化的时间字符串，尝试解析并重新格式化
            if isinstance(time_value, str):
                # 尝试多种常见的时间格式
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d']:
                    try:
                        return datetime.strptime(time_value, fmt).strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        continue
                        
            # 如果都失败了，返回默认值
            return "Unknown time"
            
        except Exception as e:
            logger.error(f"Error parsing timestamp {time_value}: {str(e)}")
            return "Unknown time"