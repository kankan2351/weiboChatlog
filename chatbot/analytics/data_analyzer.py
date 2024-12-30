# src/analytics/data_analyzer.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from ..utils.logger import get_logger
from .metrics_calculator import MetricsCalculator

logger = get_logger(__name__)

class DataAnalyzer:
    def __init__(self, message_db, cache):
        self.message_db = message_db
        self.cache = cache
        self.metrics = MetricsCalculator()
        
    async def analyze_user_activity(self, user: str) -> Dict:
        """Analyze user's chat activity"""
        try:
            messages = await self.message_db.get_user_messages(user)
            
            if not messages:
                return {"error": "No data found for user"}
                
            df = pd.DataFrame(messages)
            
            return {
                "message_count": len(df),
                "avg_message_length": df["content"].str.len().mean(),
                "active_hours": self.metrics.calculate_active_hours(df),
                "topic_distribution": self.metrics.analyze_topics(df),
                "engagement_score": self.metrics.calculate_engagement(df),
                "response_patterns": self.metrics.analyze_response_patterns(df)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user activity: {str(e)}")
            return {"error": str(e)}
            
    async def generate_chat_insights(self, 
                                 time_range: str = "7d") -> Dict:
        """Generate insights from chat history"""
        try:
            # Get time filter based on range
            now = datetime.now()
            if time_range == "24h":
                start_time = now - timedelta(days=1)
            elif time_range == "7d":
                start_time = now - timedelta(days=7)
            else:
                start_time = now - timedelta(days=30)
                
            messages = await self.message_db.query_messages(
                filter_dict={"timestamp": {"$gte": start_time}},
                limit=1000
            )
            
            df = pd.DataFrame(messages.get("results", []))
            if df.empty:
                return {"error": "No data found for time range"}
                
            return {
                "total_messages": len(df),
                "active_users": len(df["from_name"].unique()),
                "peak_hours": self.metrics.get_peak_hours(df),
                "popular_topics": self.metrics.get_popular_topics(df),
                "sentiment_analysis": self.metrics.analyze_sentiment(df),
                "interaction_patterns": self.metrics.analyze_interactions(df)
            }
            
        except Exception as e:
            logger.error(f"Error generating chat insights: {str(e)}")
            return {"error": str(e)}
            
    async def get_trend_analysis(self, metric: str, 
                              days: int = 7) -> List[Dict]:
        """Get trend analysis for specific metric"""
        try:
            cache_key = f"trend:{metric}:{days}"
            if cached := await self.cache.get(cache_key):
                return cached
                
            start_time = datetime.now() - timedelta(days=days)
            messages = await self.message_db.query_messages(
                filter_dict={"timestamp": {"$gte": start_time}},
                limit=10000
            )
            
            df = pd.DataFrame(messages.get("results", []))
            if df.empty:
                return []
                
            trends = self.metrics.calculate_trends(df, metric)
            await self.cache.set(cache_key, trends, expire=3600)
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return []