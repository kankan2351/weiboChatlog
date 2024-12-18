# src/summarizer/chunker.py
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .tokenizer import TokenManager
from .cache import SummaryCache
from ..utils.logger import get_logger

logger = get_logger(__name__)

class MessageChunker:
    def __init__(self, token_manager: TokenManager, cache: SummaryCache):
        """Initialize message chunker"""
        self.token_manager = token_manager
        self.cache = cache
        
    async def split_by_tokens(
        self,
        messages: List[Dict],
        max_tokens: int = 3000
    ) -> List[List[Dict]]:
        """Split messages into chunks based on token count"""
        try:
            chunks = []
            current_chunk = []
            current_tokens = 0
            
            for message in messages:
                content = message.get('content', '')
                msg_tokens = self.token_manager.calculate_tokens(content)
                
                # If single message exceeds max tokens, split it
                if msg_tokens > max_tokens:
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = []
                        current_tokens = 0
                        
                    # Split long message into smaller parts
                    parts = self._split_long_message(content, max_tokens)
                    for part in parts:
                        msg_copy = message.copy()
                        msg_copy['content'] = part
                        chunks.append([msg_copy])
                        
                # Add message to current chunk or start new chunk
                elif current_tokens + msg_tokens > max_tokens:
                    chunks.append(current_chunk)
                    current_chunk = [message]
                    current_tokens = msg_tokens
                else:
                    current_chunk.append(message)
                    current_tokens += msg_tokens
                    
            if current_chunk:
                chunks.append(current_chunk)
                
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting messages: {str(e)}")
            return [[]]
            
    async def split_by_time(
        self,
        messages: List[Dict],
        hours: int = 24
    ) -> List[List[Dict]]:
        """Split messages into chunks by time periods"""
        try:
            if not messages:
                return []
                
            chunks = []
            current_chunk = []
            current_time = None
            
            for message in messages:
                msg_time = datetime.fromtimestamp(message.get('timestamp', 0))
                
                if not current_time:
                    current_time = msg_time
                    
                # Start new chunk if time difference exceeds limit
                if (msg_time - current_time) > timedelta(hours=hours):
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = []
                    current_time = msg_time
                    
                current_chunk.append(message)
                
            if current_chunk:
                chunks.append(current_chunk)
                
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting by time: {str(e)}")
            return [[]]
            
    async def split_by_topic(self, messages: List[Dict]) -> List[List[Dict]]:
        """Split messages into chunks by topic similarity"""
        try:
            # First split by time to get manageable chunks
            time_chunks = await self.split_by_time(messages, hours=12)
            
            # Then analyze each time chunk for topic boundaries
            topic_chunks = []
            for chunk in time_chunks:
                boundaries = await self._analyze_topic_boundary(chunk)
                
                # Split chunk by detected boundaries
                start = 0
                for end in boundaries:
                    if end > start:
                        topic_chunks.append(chunk[start:end])
                    start = end
                    
                if start < len(chunk):
                    topic_chunks.append(chunk[start:])
                    
            return topic_chunks
            
        except Exception as e:
            logger.error(f"Error splitting by topic: {str(e)}")
            return [[]]
            
    async def _analyze_topic_boundary(self, messages: List[Dict]) -> List[int]:
        """Analyze topic boundaries in a chunk of messages"""
        try:
            boundaries = []
            
            if len(messages) < 3:
                return boundaries
                
            for i in range(1, len(messages)-1):
                prev_msg = messages[i-1].get('content', '')
                curr_msg = messages[i].get('content', '')
                next_msg = messages[i+1].get('content', '')
                
                # Check for topic shift indicators
                if any([
                    len(curr_msg) > 200,  # Long message often starts new topic
                    curr_msg.startswith('?') or curr_msg.startswith('？'),  # Question
                    self._is_topic_shift(prev_msg, curr_msg, next_msg)
                ]):
                    boundaries.append(i)
                    
            return boundaries
            
        except Exception as e:
            logger.error(f"Error analyzing topic boundary: {str(e)}")
            return []
            
    def _is_topic_shift(self, prev: str, curr: str, next: str) -> bool:
        """Detect if current message indicates topic shift"""
        topic_markers = ['主题', '话题', '说说', '讨论', '聊聊']
        return any(marker in curr for marker in topic_markers)
        
    def _split_long_message(self, content: str, max_tokens: int) -> List[str]:
        """Split long message into smaller parts"""
        try:
            parts = []
            current_part = ''
            
            # Split by sentences
            sentences = content.split('。')
            
            for sentence in sentences:
                if not sentence.strip():
                    continue
                    
                sentence = sentence + '。'
                sentence_tokens = self.token_manager.calculate_tokens(sentence)
                
                if sentence_tokens > max_tokens:
                    # Split very long sentence by punctuation
                    subparts = self._split_sentence(sentence, max_tokens)
                    parts.extend(subparts)
                    current_part = ''
                elif self.token_manager.calculate_tokens(current_part + sentence) > max_tokens:
                    if current_part:
                        parts.append(current_part)
                    current_part = sentence
                else:
                    current_part += sentence
                    
            if current_part:
                parts.append(current_part)
                
            return parts
            
        except Exception as e:
            logger.error(f"Error splitting long message: {str(e)}")
            return [content]
            
    def _split_sentence(self, sentence: str, max_tokens: int) -> List[str]:
        """Split long sentence by punctuation"""
        try:
            parts = []
            current_part = ''
            
            # Split by common punctuation
            for part in sentence.replace('，', ',').split(','):
                part = part.strip() + '，'
                
                if self.token_manager.calculate_tokens(part) > max_tokens:
                    # Last resort: split by fixed length
                    subparts = [part[i:i+100] for i in range(0, len(part), 100)]
                    parts.extend(subparts)
                elif self.token_manager.calculate_tokens(current_part + part) > max_tokens:
                    if current_part:
                        parts.append(current_part)
                    current_part = part
                else:
                    current_part += part
                    
            if current_part:
                parts.append(current_part)
                
            return parts
            
        except Exception as e:
            logger.error(f"Error splitting sentence: {str(e)}")
            return [sentence]