# src/summarizer/recursive_sum.py
import asyncio
from typing import List, Dict, Optional
from .tokenizer import TokenManager
from .cache import SummaryCache
from ..utils.logger import get_logger

logger = get_logger(__name__)

class RecursiveSummarizer:
    def __init__(self, token_manager: TokenManager, cache: SummaryCache):
        """Initialize recursive summarizer"""
        self.token_manager = token_manager
        self.cache = cache
        self.model_max_tokens = 4000
        
    async def summarize_layer1(self, chunks: List[List[Dict]]) -> List[Dict]:
        """Generate base summaries for chunks (Layer 1)"""
        try:
            summaries = []
            tasks = []
            
            for chunk in chunks:
                cache_key = f"sum_l1_{hash(str(chunk))}"
                
                # Try cache first
                if cached := await self.cache.get(cache_key):
                    summaries.append(cached)
                    continue
                    
                # Create summary task
                task = asyncio.create_task(self._summarize_chunk(
                    chunk,
                    prompt="请总结以下聊天记录的主要内容，包括关键话题和重要信息：",
                    cache_key=cache_key
                ))
                tasks.append(task)
                
            # Wait for all summaries
            if tasks:
                chunk_summaries = await asyncio.gather(*tasks)
                summaries.extend(chunk_summaries)
                
            return summaries
            
        except Exception as e:
            logger.error(f"Error in layer 1 summarization: {str(e)}")
            return []
            
    async def summarize_layer2(self, summaries: List[Dict]) -> List[Dict]:
        """Merge summaries by topic (Layer 2)"""
        try:
            topic_summaries = []
            current_topic = []
            current_tokens = 0
            
            for summary in summaries:
                summary_tokens = self.token_manager.calculate_tokens(str(summary))
                
                # Start new topic group if token limit reached
                if current_tokens + summary_tokens > self.model_max_tokens // 2:
                    if current_topic:
                        merged = await self._merge_topic_summaries(current_topic)
                        if merged:
                            topic_summaries.append(merged)
                    current_topic = []
                    current_tokens = 0
                    
                current_topic.append(summary)
                current_tokens += summary_tokens
                
            # Process remaining summaries
            if current_topic:
                merged = await self._merge_topic_summaries(current_topic)
                if merged:
                    topic_summaries.append(merged)
                    
            return topic_summaries
            
        except Exception as e:
            logger.error(f"Error in layer 2 summarization: {str(e)}")
            return []
            
    async def summarize_layer3(self, topic_summaries: List[Dict]) -> Optional[Dict]:
        """Generate final summary (Layer 3)"""
        try:
            if not topic_summaries:
                return None
                
            cache_key = f"sum_l3_{hash(str(topic_summaries))}"
            
            # Try cache first
            if cached := await self.cache.get(cache_key):
                return cached
                
            # Generate final summary
            summary = await self._generate_final_summary(topic_summaries)
            
            # Cache result
            if summary:
                await self.cache.set(cache_key, summary)
                
            return summary
            
        except Exception as e:
            logger.error(f"Error in layer 3 summarization: {str(e)}")
            return None
            
    async def _summarize_chunk(
        self,
        messages: List[Dict],
        prompt: str,
        cache_key: str
    ) -> Optional[Dict]:
        """Summarize single chunk of messages"""
        try:
            # Prepare content for summarization
            content = "\n".join([
                f"[{msg.get('time', '')}] {msg.get('from', {}).get('name', '')}: {msg.get('content', '')}"
                for msg in messages
            ])
            
            # Add prompt
            content = f"{prompt}\n\n{content}"
            
            # Ensure content fits token limit
            if not self.token_manager.check_limit(content, self.model_max_tokens):
                content = content[:int(len(content) * 0.8)]  # Truncate if too long
                
            # Generate summary using AI
            # Note: Actual AI call implementation would go here
            # For now, we'll use a placeholder
            summary = {
                "content": "这是一个测试总结",  # Would be replaced with actual AI response
                "time_range": {
                    "start": messages[0].get('time'),
                    "end": messages[-1].get('time')
                },
                "message_count": len(messages)
            }
            
            # Cache result
            await self.cache.set(cache_key, summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error summarizing chunk: {str(e)}")
            return None
            
    async def _merge_topic_summaries(self, summaries: List[Dict]) -> Optional[Dict]:
        """Merge summaries within same topic"""
        try:
            cache_key = f"sum_l2_{hash(str(summaries))}"
            
            # Try cache first
            if cached := await self.cache.get(cache_key):
                return cached
                
            # Prepare content for merging
            content = "\n\n".join([
                f"时间范围：{s.get('time_range', {}).get('start')} - {s.get('time_range', {}).get('end')}\n"
                f"消息数量：{s.get('message_count', 0)}\n"
                f"内容：{s.get('content', '')}"
                for s in summaries
            ])
            
            # Generate merged summary
            # Note: Actual AI call implementation would go here
            merged = {
                "content": "这是一个合并后的主题总结",  # Would be replaced with actual AI response
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
            
    async def _generate_final_summary(self, topic_summaries: List[Dict]) -> Optional[Dict]:
        """Generate final comprehensive summary"""
        try:
            # Prepare content for final summary
            content = "请生成一个总体摘要，包含以下主题的内容：\n\n" + "\n\n".join([
                f"主题 {i+1}：\n"
                f"时间范围：{s.get('time_range', {}).get('start')} - {s.get('time_range', {}).get('end')}\n"
                f"消息数量：{s.get('message_count', 0)}\n"
                f"内容：{s.get('content', '')}"
                for i, s in enumerate(topic_summaries)
            ])
            
            # Generate final summary
            # Note: Actual AI call implementation would go here
            final = {
                "content": "这是最终的综合总结",  # Would be replaced with actual AI response
                "time_range": {
                    "start": topic_summaries[0].get('time_range', {}).get('start'),
                    "end": topic_summaries[-1].get('time_range', {}).get('end')
                },
                "message_count": sum(s.get('message_count', 0) for s in topic_summaries),
                "topic_count": len(topic_summaries)
            }
            
            return final
            
        except Exception as e:
            logger.error(f"Error generating final summary: {str(e)}")
            return None
