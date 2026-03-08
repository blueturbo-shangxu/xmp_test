"""
Configuration module for XMP Auth Server
Loads environment variables and provides configuration settings
"""
import os
from typing import List
from pathlib import Path
from urllib import parse
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 获取项目根目录
# __file__ = src/core/config.py
# .parent = src/core/
# .parent.parent = src/
# .parent.parent.parent = 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 加载环境变量
env_file = BASE_DIR / 'conf' / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv(BASE_DIR / 'conf' / '.env.example')


class Settings(BaseSettings):
    """应用配置类"""

    # 服务器配置
    ENV: str = os.getenv('ENV', 'development')
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', 8000))
    DEBUG: bool = os.getenv('DEBUG', 'True').lower() == 'true'

    # 数据库配置
    DB_HOST: str = os.getenv('DB_HOST', 'db.office.pg.domob-inc.cn')
    DB_PORT: int = int(os.getenv('DB_PORT', 5433))
    DB_USER: str = os.getenv('DB_USER', 'socialbooster')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'B<JRsi3.lI')
    DB_NAME: str = os.getenv('DB_NAME', 'socialbooster')
    DB_POOL_SIZE: int = int(os.getenv('DB_POOL_SIZE', 10))
    DB_MAX_OVERFLOW: int = int(os.getenv('DB_MAX_OVERFLOW', 20))

    @property
    def DATABASE_URL(self) -> str:
        """生成数据库连接URL"""
        return (
            f"postgresql://{self.DB_USER}:{parse.quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Google OAuth2 配置
    GOOGLE_CLIENT_ID: str = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET: str = os.getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI: str = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/callback')
    GOOGLE_AUTH_SCOPES: str = os.getenv('GOOGLE_AUTH_SCOPES', 'https://www.googleapis.com/auth/adwords')

    @property
    def GOOGLE_SCOPES_LIST(self) -> List[str]:
        """获取Google授权范围列表"""
        return self.GOOGLE_AUTH_SCOPES.split(',')

    # Google Ads API 配置
    GOOGLE_ADS_DEVELOPER_TOKEN: str = os.getenv('GOOGLE_ADS_DEVELOPER_TOKEN', '')
    GOOGLE_ADS_API_VERSION: str = os.getenv('GOOGLE_ADS_API_VERSION', 'v16')
    GOOGLE_ADS_LOGIN_CUSTOMER_ID: str = os.getenv('GOOGLE_ADS_LOGIN_CUSTOMER_ID', '')

    # Session配置
    SESSION_SECRET: str = os.getenv('SESSION_SECRET', 'your_session_secret')
    SESSION_COOKIE_NAME: str = os.getenv('SESSION_COOKIE_NAME', 'xmp_session')
    SESSION_MAX_AGE: int = int(os.getenv('SESSION_MAX_AGE', 86400))

    # JWT配置
    JWT_SECRET: str = os.getenv('JWT_SECRET', 'default_jwt_secret_please_change_in_production')
    JWT_TOKEN_EXPIRE_DAYS: int = int(os.getenv('JWT_TOKEN_EXPIRE_DAYS', 180))

    # 飞书配置
    FEISHU_APP_ID: str = os.getenv('FEISHU_APP_ID', '')
    FEISHU_APP_SECRET: str = os.getenv('FEISHU_APP_SECRET', '')
    FEISHU_TOMATO_APP_ID: str = os.getenv('FEISHU_TOMATO_APP_ID', '')
    FEISHU_TOMATO_APP_SECRET: str = os.getenv('FEISHU_TOMATO_APP_SECRET', '')
    FEISHU_TOKEN_URL: str = os.getenv('FEISHU_TOKEN_URL', 'https://passport.feishu.cn/suite/passport/oauth/token')
    FEISHU_USER_URL: str = os.getenv('FEISHU_USER_URL', 'https://passport.feishu.cn/suite/passport/oauth/userinfo')

    # 日志配置（保留用于向后兼容）
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_MAX_BYTES: int = int(os.getenv('LOG_MAX_BYTES', 10485760))
    LOG_BACKUP_COUNT: int = int(os.getenv('LOG_BACKUP_COUNT', 5))

    # Redis配置
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', 6379))
    REDIS_PASSWORD: str = os.getenv('REDIS_PASSWORD', '')
    REDIS_DB: int = int(os.getenv('REDIS_DB', 0))

    @property
    def REDIS_URL(self) -> str:
        """生成Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # 任务队列配置
    TASK_QUEUE_NAME: str = os.getenv('TASK_QUEUE_NAME', 'sync_task_queue')
    TASK_RUNNING_SET: str = os.getenv('TASK_RUNNING_SET', 'sync_task_running')
    TASK_LOCK_PREFIX: str = os.getenv('TASK_LOCK_PREFIX', 'sync_task_lock:')
    TASK_EXEC_LOCK_PREFIX: str = os.getenv('TASK_EXEC_LOCK_PREFIX', 'sync_task_exec_lock:')
    TASK_LOCK_TIMEOUT: int = int(os.getenv('TASK_LOCK_TIMEOUT', 30))
    TASK_LOCK_RENEW_INTERVAL: int = int(os.getenv('TASK_LOCK_RENEW_INTERVAL', 10))

    # 同步任务配置
    SYNC_INTERVAL_MINUTES: int = int(os.getenv('SYNC_INTERVAL_MINUTES', 60))
    SYNC_BATCH_SIZE: int = int(os.getenv('SYNC_BATCH_SIZE', 1000))
    MAX_RETRY_COUNT: int = int(os.getenv('MAX_RETRY_COUNT', 3))
    RETRY_DELAY_SECONDS: int = int(os.getenv('RETRY_DELAY_SECONDS', 60))

    # API速率限制配置
    RATE_LIMIT_REQUESTS: int = int(os.getenv('RATE_LIMIT_REQUESTS', 100))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv('RATE_LIMIT_WINDOW_SECONDS', 60))

    # CORS配置
    CORS_ORIGINS: str = os.getenv('CORS_ORIGINS', 'http://localhost:8000,http://localhost:3000')
    CORS_ALLOW_CREDENTIALS: bool = os.getenv('CORS_ALLOW_CREDENTIALS', 'True').lower() == 'true'

    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """获取CORS允许的源列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]

    # 安全配置
    ALLOWED_HOSTS: str = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
    SECURE_COOKIES: bool = os.getenv('SECURE_COOKIES', 'False').lower() == 'true'

    class Config:
        case_sensitive = True


# 创建全局配置实例
settings = Settings()


# 向后兼容：从 logging_config 模块导入日志配置函数
from src.core.logging_config import (
    setup_logging,
    setup_api_logging,
    setup_worker_logging,
    LoggerType,
)


if __name__ == '__main__':
    # 测试配置加载
    print(f"Environment: {settings.ENV}")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Google Scopes: {settings.GOOGLE_SCOPES_LIST}")
    print(f"CORS Origins: {settings.CORS_ORIGINS_LIST}")
