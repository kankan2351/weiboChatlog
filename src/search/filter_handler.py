# src/search/filter_handler.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class FilterHandler:
    def __init__(self):
        self.default_filters = {
            'time_range': 'all',
            'user': None,
            'content_type': 'all'
        }
        
    def create_filter_dict(self, **kwargs) -> Dict:
        """Create filter dictionary for database queries"""
        filters = self.default_filters.copy()
        filters.update(kwargs)
        
        filter_dict = {}
        
        # Handle time range filter
        if filters['time_range'] != 'all':
            now = datetime.now()
            if filters['time_range'] == '24h':
                filter_dict['timestamp'] = {'$gte': now - timedelta(days=1)}
            elif filters['time_range'] == '7d':
                filter_dict['timestamp'] = {'$gte': now - timedelta(days=7)}
            elif filters['time_range'] == '30d':
                filter_dict['timestamp'] = {'$gte': now - timedelta(days=30)}
                
        # Handle user filter
        if filters['user']:
            filter_dict['from_name'] = filters['user']
            
        # Handle content type filter
        if filters['content_type'] != 'all':
            filter_dict['type'] = filters['content_type']
            
        return filter_dict
        
    def parse_query_filters(self, query: str) -> Dict:
        """Extract filter conditions from natural language query"""
        filters = {}
        
        # Time-related keywords
        if any(kw in query.lower() for kw in ['today', 'last 24h', 'yesterday']):
            filters['time_range'] = '24h'
        elif any(kw in query.lower() for kw in ['this week', 'last 7 days']):
            filters['time_range'] = '7d'
        elif any(kw in query.lower() for kw in ['this month', 'last 30 days']):
            filters['time_range'] = '30d'
            
        # TODO: Add more filter parsing logic based on requirements
            
        return filters
