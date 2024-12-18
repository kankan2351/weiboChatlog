# src/handlers/base_handler.py
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import logging

class BaseHandler:
    def __init__(self, db_path: str = "./data/handler.db"):
        """Initialize base handler with SQLite database"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create user tracking table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_tracking (
                        user_name TEXT PRIMARY KEY,
                        status TEXT,
                        updated_at TIMESTAMP,
                        updated_by TEXT,
                        reason TEXT
                    )
                """)
                
                # Create action logs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS action_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_type TEXT,
                        user_name TEXT,
                        timestamp TIMESTAMP,
                        details TEXT
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"Error initializing database: {str(e)}")
            
    def log_action(self, action_type: str, user_name: str, details: str):
        """Log user action"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO action_logs (action_type, user_name, timestamp, details) VALUES (?, ?, ?, ?)",
                    (action_type, user_name, datetime.now(), details)
                )
                conn.commit()
                
        except Exception as e:
            logging.error(f"Error logging action: {str(e)}")
            
    def update_user_status(
        self, 
        user_name: str,
        status: str,
        updated_by: str,
        reason: str
    ) -> bool:
        """Update user tracking status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO user_tracking 
                    (user_name, status, updated_at, updated_by, reason)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_name, status, datetime.now(), updated_by, reason))
                conn.commit()
                return True
                
        except Exception as e:
            logging.error(f"Error updating user status: {str(e)}")
            return False
            
    def get_user_status(self, user_name: str) -> Optional[Dict]:
        """Get user tracking status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM user_tracking WHERE user_name = ?",
                    (user_name,)
                )
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            logging.error(f"Error getting user status: {str(e)}")
            return None
