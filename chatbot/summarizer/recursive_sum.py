# src/summarizer/recursive_sum.py
import asyncio
from typing import List, Dict, Optional
from .tokenizer import TokenManager
from .cache import SummaryCache
from ..utils.logger import get_logger
from chatbot.db.message_db import MessageDB
from datetime import datetime, timedelta
from chatbot.utils.config import Config
import tiktoken

logger = get_logger(__name__)

class RecursiveSummarizer:
    def __init__(self, cache: SummaryCache, message_db: MessageDB, openai_client, config: Config):
        """Initialize recursive summarizer"""
        self.cache = cache
        self.message_db = message_db
        self.client = openai_client
        self.config = config
        self.model_max_tokens = 4000
        
        # 初始化 tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model(
                self.config.get_azure_config()['model']
            )
        except KeyError:
            # 如果模型不在列表中，使用默认编码器
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
    def calculate_tokens(self, text: str) -> int:
        """计算文本的 token 数量"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.error(f"Error calculating tokens: {str(e)}")
            return len(text) // 2
            
    def check_token_limit(self, text: str, limit: int) -> bool:
        """检查文本是否超过 token 限制"""
        try:
            return self.calculate_tokens(text) <= limit
        except Exception as e:
            logger.error(f"Error checking token limit: {str(e)}")
            return False
        
    async def summarize(self, user_id: Optional[str] = None, time_range: str = '1d') -> Optional[str]:
        """总结指定时间范围内的消息"""
        try:
            # 1. 获取消息并分块
            chunks = await self._get_messages_chunks(user_id, time_range)
            if not chunks:
                return "指定时间范围内没有消息"
                
            # 2. 生成第一层摘要
            layer1_summaries = await self.summarize_layer1(chunks)
            if not layer1_summaries:
                return "无法生成摘要"
                
            # 3. 合并所有总结为最终结果
            final_summary = await self._merge_summaries(layer1_summaries)
            if not final_summary:
                return "无法生成最终摘要"
                
            return final_summary.get('content', "总结生成失败")
            
        except Exception as e:
            logger.error(f"Error in summarize: {str(e)}")
            return None
        
    async def summarize_layer1(self, chunks: List[List[Dict]]) -> List[Dict]:
        """Generate base summaries for chunks (Layer 1)"""
        try:
            summaries = []
            for chunk in chunks:
                cache_key = f"sum_l1_{hash(str(chunk))}"
                
                # 尝试从缓存获取
                if cached := await self.cache.get(cache_key):
                    summaries.append(cached)
                    continue
                    
                # 生成新的总结
                summary = await self._summarize_chunk(chunk, cache_key)
                if summary:
                    summaries.append(summary)
                    
            return summaries
            
        except Exception as e:
            logger.error(f"Error in layer 1 summarization: {str(e)}")
            return []
            
    async def _summarize_chunk(self, messages: List[Dict], cache_key: str) -> Optional[Dict]:
        """Summarize single chunk of messages"""
        try:
            # 从缓存获取
            if cached := await self.cache.get(cache_key):
                return cached
                
            # 准备内容
            content = "\n".join([
                f"[{msg.get('metadata', {}).get('user_name', '未知用户')} "
                f"在 {msg.get('metadata', {}).get('time', '')}]: "
                f"{msg.get('content', '')}"
                for msg in messages
            ])
            
            # 调用 OpenAI API
            response = self.client.chat.completions.create(
                model=self.config.get_azure_config()['model'],
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的对话总结助手。请分析对话内容，提取关键信息，"
                                 "生成简洁但信息完整的总结。关注重要的话题、决定和讨论要点。"
                                 "保持客观和准确。"
                    },
                    {
                        "role": "user",
                        "content": f"请总结以下聊天记录的主要内容：\n\n{content}"
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            summary = {
                "content": response.choices[0].message.content,
                "time_range": {
                    "start": messages[0].get('metadata', {}).get('time'),
                    "end": messages[-1].get('metadata', {}).get('time')
                },
                "message_count": len(messages)
            }
            
            # 缓存结果
            await self.cache.set(cache_key, summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error summarizing chunk: {str(e)}")
            return None
            
    async def _merge_summaries(self, summaries: List[Dict]) -> Optional[Dict]:
        """Merge all summaries into final result"""
        try:
            cache_key = f"sum_final_{hash(str(summaries))}"
            
            # Try cache first
            if cached := await self.cache.get(cache_key):
                return cached
                
            # Prepare content
            content = "\n\n".join([
                f"时间段 {i+1}：\n"
                f"时间范围：{s.get('time_range', {}).get('start')} - {s.get('time_range', {}).get('end')}\n"
                f"消息数量：{s.get('message_count', 0)}\n"
                f"内容：{s.get('content', '')}"
                for i, s in enumerate(summaries)
            ])
            
            # 调用 OpenAI API
            response = self.client.chat.completions.create(
                model=self.config.get_azure_config()['model'],
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的总结生成助手。请对这些时间段的总结进行整合，"
                                 "生成一个全面但简洁的总体总结。需要：\n"
                                 "1. 突出重要的主题和发展脉络\n"
                                 "2. 保持时间顺序\n"
                                 "3. 突出关键结论和决定\n"
                                 "4. 确保信息的连贯性和完整性\n"
                                 "5. 不要使用格式输出，使用纯文本，可以适当的在内容中加入 emoji"
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            merged = {
                "content": response.choices[0].message.content,
                "time_range": {
                    "start": summaries[0].get('time_range', {}).get('start'),
                    "end": summaries[-1].get('time_range', {}).get('end')
                },
                "message_count": sum(s.get('message_count', 0) for s in summaries)
            }
            
            # Cache result
            await self.cache.set(cache_key, merged)
            
            return merged
            
        except Exception as e:
            logger.error(f"Error merging summaries: {str(e)}")
            return None
            
    async def _get_messages_chunks(self, user_id: Optional[str] = None, time_range: str = '1d') -> List[List[Dict]]:
        """获取消息并分块"""
        try:
            # 构建时间过滤条件
            current_time = datetime.now()
            duration = self._parse_time_range(time_range)
            if duration and duration > timedelta(days=1):
                duration = timedelta(days=1)
            if not duration:
                logger.error(f"Invalid time range: {time_range}")
                return []
                
            start_time = current_time - duration
            filter_dict = {
                "timestamp": {
                    "$gte": int(start_time.timestamp())
                }
            }
            if user_id:
                filter_dict["user_id"] = user_id
                
            # 从数据库获取消息
            results = await self.message_db.query_messages(
                embeddings=None,
                filter_dict=filter_dict,
                n_results=1000,
                use_semantic_search=False
            )
            
            messages = results.get('results', [])
            if not messages:
                return []
                
            # 按token数量分块
            chunks = []
            current_chunk = []
            current_tokens = 0
            
            for msg in messages:
                msg_tokens = self.calculate_tokens(str(msg))
                
                # 如果当前块加上新消息会超限制，开始新的块
                if current_tokens + msg_tokens > self.model_max_tokens // 2:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = []
                    current_tokens = 0
                    
                current_chunk.append(msg)
                current_tokens += msg_tokens
                
            # 添加最后一个块
            if current_chunk:
                chunks.append(current_chunk)
                
            return chunks
            
        except Exception as e:
            logger.error(f"Error getting message chunks: {str(e)}")
            return []
            
    def _parse_time_range(self, time_range: str) -> Optional[timedelta]:
        """解析时间范围字符串, 限制最大值为 1d"""
        try:
            unit = time_range[-1].lower()
            value = int(time_range[:-1])
            
            if unit == 'd':
                if value > 1:
                    value = 1
                return timedelta(days=value)
            elif unit == 'h':
                if value > 24:
                    value = 24
                return timedelta(hours=value)
            elif unit == 'm' or unit == 'w':
                return timedelta(days=1)
            else:
                return timedelta(hours=1)
                
        except (ValueError, IndexError):
            return None
