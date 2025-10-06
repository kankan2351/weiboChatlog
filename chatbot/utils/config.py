# /data/chats/oqz4c/workspace/chatbot/utils/config.py
import os
from typing import Dict, Any
from pathlib import Path
import importlib.util
import json

_dotenv_spec = importlib.util.find_spec("dotenv")
if _dotenv_spec is not None:
    from dotenv import load_dotenv  # type: ignore
else:
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False

from chatbot.utils.logger import get_logger

logger = get_logger(__name__)

class Config:
    def __init__(self):
        """Initialize configuration"""
        # Load environment variables
        load_dotenv()

        # Set environment
        self.env = os.getenv('ENV', 'development')

        # Configuration directories
        self.config_dir = Path(os.getenv('CHATBOT_CONFIG_DIR', './config'))

        # Database configs
        self.db_config = {
            'vector_db_path': os.getenv('VECTOR_DB_PATH', './chroma_db'),
            'sqlite_db_path': os.getenv('SQLITE_DB_PATH', './data/ai_handler.db')
        }

        # Azure OpenAI configs
        self.azure_config = {
            'openai_endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
            'openai_key': os.getenv('AZURE_OPENAI_KEY'),
            'embedding_endpoint': os.getenv('AZURE_EMBEDDING_ENDPOINT'),
            'embedding_key': os.getenv('AZURE_EMBEDDING_KEY'),
            'api_version': os.getenv('AZURE_API_VERSION', '2024-02-15-preview'),
            'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        }
        # deepseek configs
        self.deepseek_config = {
            'base_url': os.getenv('DEEPSEEK_BASE_URL'),
            'api_key': os.getenv('DEEPSEEK_API_KEY')
        }

        # Cache configs
        self.cache_config = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'db': int(os.getenv('REDIS_DB', '0')),
            'password': os.getenv('REDIS_PASSWORD')
        }

        # Logging configs
        self.log_config = {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'dir': os.getenv('LOG_DIR', './logs'),
            'max_size': int(os.getenv('LOG_MAX_SIZE', '10485760')),  # 10MB
            'backup_count': int(os.getenv('LOG_BACKUP_COUNT', '5'))
        }

        # Bot configs
        self.bot_config = {
            'name': os.getenv('BOT_NAME', 'BOT_NAME'),
            'response_timeout': int(os.getenv('BOT_RESPONSE_TIMEOUT', '30')),
            'max_retry': int(os.getenv('BOT_MAX_RETRY', '3')),
            'cache_ttl': int(os.getenv('BOT_CACHE_TTL', '3600'))
        }

        # weibo configs
        self.weibo_config = {
            'chat_url': 'https://api.weibo.com/chat#/chat',
            'monitor_group': {
                'name': os.getenv('WEIBO_GROUP_NAME', '默认群组名'),
                'id': os.getenv('WEIBO_GROUP_ID', '')
            },
            'send_group': {
                'name': '茧房建筑师协会',
                'id': '4761715839862414'
            },
            'client_id': os.getenv('WEIBO_CLIENT_ID', 'mted01pk63unikuvoli0sc8kusswwo'),
            'source': os.getenv('WEIBO_SOURCE', '209678993'),
            'api_base': os.getenv('WEIBO_API_BASE', 'https://api.weibo.com'),
            'cookies': []  # 初始化空的 cookies 列表
        }

        # Validate and setup
        self._ensure_defaults()
        self._setup_directories()
        
    def _ensure_defaults(self) -> None:
        """Populate essential configuration entries with safe defaults."""
        default_azure = {
            'openai_endpoint': 'https://example-openai-endpoint.test',
            'openai_key': 'dummy-openai-key',
            'embedding_endpoint': 'https://example-embedding-endpoint.test',
            'embedding_key': 'dummy-embedding-key'
        }

        for key, default in default_azure.items():
            if not self.azure_config.get(key):
                logger.warning("Missing Azure config '%s'; using default placeholder", key)
                self.azure_config[key] = default

        default_deepseek = {
            'base_url': 'https://example-deepseek-endpoint.test',
            'api_key': 'dummy-deepseek-key'
        }

        for key, default in default_deepseek.items():
            if not self.deepseek_config.get(key):
                logger.warning("Missing Deepseek config '%s'; using default placeholder", key)
                self.deepseek_config[key] = default
            
    def _setup_directories(self) -> None:
        """Create necessary directories"""
        dirs = [
            Path(self.log_config['dir']),
            Path(self.db_config['vector_db_path']).parent,
            Path(self.db_config['sqlite_db_path']).parent,
            self.config_dir
        ]
        
        for dir_path in dirs:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {dir_path}: {str(e)}")
                
    def get_azure_config(self) -> Dict[str, str]:
        """Get Azure configurations"""
        return self.azure_config
    
    def get_deepseek_config(self)-> Dict[str, str]:
        """Get Deepseek configurations"""
        return self.deepseek_config
        
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configurations"""
        return self.cache_config
        
    def get_db_config(self) -> Dict[str, str]:
        """Get database configurations"""
        return self.db_config
        
    def get_log_config(self) -> Dict[str, Any]:
        """Get logging configurations"""
        return self.log_config
        
    def get_bot_config(self) -> Dict[str, Any]:
        """Get chat bot configurations"""
        return self.bot_config
    
    def get_weibo_config(self):
        """获取微博相关配置"""
        return self.weibo_config
        
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.env.lower() == 'production'
        
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.env.lower() == 'development'
        
    def load(self) -> None:
        """Reload configuration from environment"""
        self.__init__()

    def _load_config(self, filename: str) -> dict:
        """Load configuration from file"""
        config_file = self.config_dir / filename
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_config(self, filename: str, config: dict):
        """Save configuration to file"""
        config_file = self.config_dir / filename
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    def update_weibo_config(self, new_config: dict):
        """Update Weibo configuration"""
        self.weibo_config.update(new_config)  # 使用 update 方法更新配置

# Create global config instance
config = Config()