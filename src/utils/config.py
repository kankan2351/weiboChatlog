# src/utils/config.py
import os
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from .logger import get_logger

logger = get_logger(__name__)

class Config:
    def __init__(self):
        """Initialize configuration"""
        # Load environment variables from .env file
        load_dotenv()
        
        # Set environment
        self.env = os.getenv('ENV', 'development')
        
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
        
        # Cache configs
        self.cache_config = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'db': int(os.getenv('REDIS_DB', '0')),
            'password': os.getenv('REDIS_PASSWORD', None)
        }
        
        # Logging configs
        self.log_config = {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'dir': os.getenv('LOG_DIR', './logs'),
            'max_size': int(os.getenv('LOG_MAX_SIZE', '10485760')),  # 10MB
            'backup_count': int(os.getenv('LOG_BACKUP_COUNT', '5'))
        }
        
        # Chat bot configs
        self.bot_config = {
            'name': os.getenv('BOT_NAME', '茧房爬楼王'),
            'response_timeout': int(os.getenv('BOT_RESPONSE_TIMEOUT', '30')),
            'max_retry': int(os.getenv('BOT_MAX_RETRY', '3')),
            'cache_ttl': int(os.getenv('BOT_CACHE_TTL', '3600'))
        }
        
        self._validate_config()
        self._setup_directories()
        
    def _validate_config(self):
        """Validate required configuration settings"""
        required_azure = [
            'openai_endpoint',
            'openai_key',
            'embedding_endpoint',
            'embedding_key'
        ]
        
        missing = []
        for key in required_azure:
            if not self.azure_config.get(key):
                missing.append(key)
                
        if missing:
            logger.error(f"Missing required Azure configurations: {', '.join(missing)}")
            raise ValueError(f"Missing required configurations: {', '.join(missing)}")
            
    def _setup_directories(self):
        """Create necessary directories"""
        dirs = [
            Path(self.log_config['dir']),
            Path(self.db_config['vector_db_path']).parent,
            Path(self.db_config['sqlite_db_path']).parent
        ]
        
        for dir_path in dirs:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {dir_path}: {str(e)}")
                
    def get_azure_config(self) -> Dict[str, str]:
        """Get Azure configurations"""
        return self.azure_config
        
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
        
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.env.lower() == 'production'
        
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.env.lower() == 'development'
        
# Create global config instance
config = Config()
