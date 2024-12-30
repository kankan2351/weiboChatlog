import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json
from ..utils.logger import get_logger
import time
from chatbot.utils.config import Config

logger = get_logger(__name__)

class SQLiteDB:
    _instance = None
    
    def __new__(cls, db_path: str = "./data/chatbot.db"):
        if cls._instance is None:
            cls._instance = super(SQLiteDB, cls).__new__(cls)
            cls._instance._init_db(db_path)
        return cls._instance
        
    def _init_db(self, db_path: str):
        """初始化数据库（只在第一次创建实例时调用）"""
        try:
            # 确保目录存在
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.db_path = db_path
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            
            # 初始化配置
            self.config = Config()
            self.weibo_config = self.config.get_weibo_config()
            
            # 创建表
            self._create_tables()
            logger.info("SQLite database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {str(e)}")
            raise
            
    def _create_tables(self):
        """创建必要的数据表"""
        with self.conn:
            # 用户状态表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_status (
                    user_name TEXT PRIMARY KEY,
                    status TEXT DEFAULT 'active',
                    restricted_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 消息表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    time TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_name ON messages(user_name)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_group_id ON messages(group_id)")
            
    # 用户相关方法
    async def get_user_status(self, user_name: str) -> Optional[Dict]:
        """获取用户状态"""
        try:
            cursor = self.conn.execute(
                "SELECT * FROM user_status WHERE user_name = ?",
                (user_name,)
            )
            if row := cursor.fetchone():
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user status: {str(e)}")
            return None
            
    async def create_user(self, user_name: str) -> bool:
        """创建新用户"""
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO user_status (user_name) VALUES (?)",
                    (user_name,)
                )
            return True
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return False
            
    async def update_user_status(self, 
                               user_name: str, 
                               status: str,
                               restricted_until: Optional[datetime] = None) -> bool:
        """更新用户状态"""
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO user_status (user_name, status, restricted_until)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_name) DO UPDATE SET
                        status = excluded.status,
                        restricted_until = excluded.restricted_until,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (user_name, status, restricted_until)
                )
            return True
            
        except Exception as e:
            logger.error(f"Error updating user status: {str(e)}")
            return False
            
    # 消息相关方法
    async def add_message(self, message: Dict) -> bool:
        """添加消息到数据库（同步方法，方便调试）"""
        try:
            # 检查必要字段
            if not message.get('id'):
                logger.error("Message ID is empty")
                return False
                
            # 确保时间戳字段存在且为整数
            get_time = message.get('time')  
            timestamp = message.get('timestamp')
            if timestamp is None:
                timestamp = int(time.time())
            
            try:
                msg_id = int(message['id'].strip()) if isinstance(message['id'], str) else int(message['id'])
            except (ValueError, AttributeError) as e:
                logger.error(f"Invalid message ID format: {message.get('id')}")
                return False

            # 从配置中获取群组信息
            monitor_group = self.weibo_config.get('monitor_group', {})
            group_id = monitor_group.get('id')
            if not group_id:
                logger.error("Group ID is empty")
                return False
                
            # 构建 metadata
            metadata = {
                "user_id": message['metadata']['user_id'],
                "user_name": message['metadata']['user_name'],
                "timestamp": timestamp,
                "time": get_time,
                "group_id": group_id
            }
            
            # 准备数据
            data = {
                'id': msg_id,
                'content': message['content'],
                'user_id': message['metadata']['user_id'],
                'user_name': message['metadata']['user_name'],
                'timestamp': timestamp,
                'time': get_time,
                'group_id': group_id,
                'metadata': json.dumps(metadata)  # 将 metadata 转换为 JSON 字符串
            }
            # logger.info(data)
            # 执行插入
            await self.execute(
                """
                INSERT INTO messages (
                    id, content, user_id, user_name, timestamp, 
                    time, group_id, metadata
                ) VALUES (
                    :id, :content, :user_id, :user_name, :timestamp,
                    :time, :group_id, :metadata
                )
                """,
                data
            )
            # logger.info(f"Message added to SQLite, Message_id: {message['id']}")
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            raise
            
    async def query_messages(self, 
                            user_name: Optional[str] = None,
                            group_id: Optional[str] = None,
                            start_time: Optional[int] = None,
                            end_time: Optional[int] = None,
                            limit: int = 10,
                            offset: int = 0,
                            order_by: str = "timestamp DESC") -> List[Dict]:
        """
        查询消息
        
        Args:
            user_name: 用户名
            group_id: 群组ID
            start_time: 开始时间戳
            end_time: 结束时间戳
            limit: 返回记录数量限制
            offset: 分页偏移量
            order_by: 排序方式
            
        Returns:
            List[Dict]: 消息列表
        """
        try:
            conditions = []
            params = []
            
            # 构建查询条件
            if user_name:
                conditions.append("user_name = ?")
                params.append(user_name)
                
            if group_id:
                conditions.append("group_id = ?")
                params.append(group_id)
                
            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)
                
            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)
                
            # 构建完整的查询语句
            query = "SELECT * FROM messages"
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            # 添加排序
            query += f" ORDER BY {order_by}"
            
            # 添加分页
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # 执行查询
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()
            
            # 转换结果
            messages = []
            for row in rows:
                message = {
                    'id': row['id'],
                    'content': row['content'],
                    'user_id': row['user_id'],
                    'user_name': row['user_name'],
                    'timestamp': row['timestamp'],
                    'time': row['time'],
                    'group_id': row['group_id'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else None
                }
                messages.append(message)
                
            return messages
            
        except Exception as e:
            logger.error(f"Error querying messages: {str(e)}")
            return []
            
    async def execute(self, query: str, params: dict = None) -> None:
        """执行 SQL 查询"""
        try:
            with self.conn:
                if params:
                    self.conn.execute(query, params)
                else:
                    self.conn.execute(query)
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise
            
    async def get_recent_messages(self, limit: int = 50) -> List[Dict]:
        """获取最近的消息记录
        
        Args:
            limit: 返回的消息数量限制
            
        Returns:
            List[Dict]: 消息列表
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT content, timestamp, user_name 
                FROM messages 
                ORDER BY id DESC 
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting recent messages: {str(e)}")
            return []
            
    def __del__(self):
        """确保关闭数据库连接"""
        try:
            self.conn.close()
        except:
            pass