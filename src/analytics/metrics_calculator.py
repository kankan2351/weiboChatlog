# src/analytics/metrics_calculator.py
from typing import Dict, List
import pandas as pd
from datetime import datetime
import numpy as np
from textblob import TextBlob
from collections import Counter
from ..utils.logger import get_logger

logger = get_logger(__name__)

class MetricsCalculator:
    def calculate_active_hours(self, df: pd.DataFrame) -> Dict[str, int]:
        """Calculate distribution of active hours"""
        try:
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            hour_counts = df['hour'].value_counts().to_dict()
            return {str(h): int(c) for h, c in hour_counts.items()}
        except Exception as e:
            logger.error(f"Error calculating active hours: {str(e)}")
            return {}
            
    def analyze_topics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analyze topic distribution in messages"""
        try:
            # Simple keyword-based topic analysis
            topics = {
                'question': ['what', 'how', 'why', 'when', 'where'],
                'discussion': ['think', 'believe', 'opinion', 'agree'],
                'suggestion': ['should', 'could', 'recommend', 'suggest'],
                'problem': ['issue', 'problem', 'error', 'bug', 'wrong'],
                'solution': ['solve', 'fixed', 'resolved', 'solution']
            }
            
            results = {}
            total = len(df)
            
            for topic, keywords in topics.items():
                count = df['content'].str.lower().str.contains(
                    '|'.join(keywords)).sum()
                results[topic] = round(count / total * 100, 2)
                
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing topics: {str(e)}")
            return {}
            
    def calculate_engagement(self, df: pd.DataFrame) -> float:
        """Calculate user engagement score"""
        try:
            # Factors considered:
            # 1. Message frequency
            # 2. Message length
            # 3. Response rate
            # 4. Topic variety
            
            freq_score = min(len(df) / 100, 1.0)
            
            avg_len = df['content'].str.len().mean()
            len_score = min(avg_len / 200, 1.0)
            
            response_rate = df['sub_type'].str.contains('reply').mean()
            
            topic_count = len(self.analyze_topics(df))
            topic_score = min(topic_count / 5, 1.0)
            
            # Weighted average
            engagement = (freq_score * 0.3 + 
                        len_score * 0.2 + 
                        response_rate * 0.3 + 
                        topic_score * 0.2)
                        
            return round(engagement * 100, 2)
            
        except Exception as e:
            logger.error(f"Error calculating engagement: {str(e)}")
            return 0.0
            
    def analyze_response_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze user response patterns"""
        try:
            patterns = {
                'avg_response_time': self._calculate_response_time(df),
                'response_rate': self._calculate_response_rate(df),
                'conversation_length': self._calculate_conv_length(df)
            }
            return patterns
        except Exception as e:
            logger.error(f"Error analyzing response patterns: {str(e)}")
            return {}
            
    def get_peak_hours(self, df: pd.DataFrame) -> List[Dict]:
        """Get peak activity hours"""
        try:
            hourly = self.calculate_active_hours(df)
            sorted_hours = sorted(hourly.items(), 
                               key=lambda x: x[1], 
                               reverse=True)
            return [{"hour": h, "count": c} for h, c in sorted_hours[:5]]
        except Exception as e:
            logger.error(f"Error getting peak hours: {str(e)}")
            return []
            
    def analyze_sentiment(self, df: pd.DataFrame) -> Dict:
        """Analyze sentiment of messages"""
        try:
            sentiments = df['content'].apply(lambda x: TextBlob(x).sentiment)
            return {
                'average_polarity': float(np.mean([s.polarity for s in sentiments])),
                'average_subjectivity': float(np.mean([s.subjectivity for s in sentiments])),
                'positive_ratio': float(sum(1 for s in sentiments if s.polarity > 0) / len(df)),
                'negative_ratio': float(sum(1 for s in sentiments if s.polarity < 0) / len(df))
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {}
            
    def _calculate_response_time(self, df: pd.DataFrame) -> float:
        """Calculate average response time"""
        try:
            df = df.sort_values('timestamp')
            response_times = []
            
            for i in range(1, len(df)):
                if df.iloc[i]['sub_type'] == 'reply':
                    time_diff = (df.iloc[i]['timestamp'] - 
                               df.iloc[i-1]['timestamp'])
                    response_times.append(time_diff)
                    
            return float(np.mean(response_times)) if response_times else 0
            
        except Exception as e:
            logger.error(f"Error calculating response time: {str(e)}")
            return 0.0