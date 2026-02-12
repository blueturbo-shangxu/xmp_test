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
BASE_DIR = Path(__file__).resolve().parent.parent

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

    # Token加密配置
    TOKEN_ENCRYPTION_KEY: str = os.getenv('TOKEN_ENCRYPTION_KEY', 'default_key_change_me_32_chars!')
    TOKEN_ENCRYPTION_ALGORITHM: str = os.getenv('TOKEN_ENCRYPTION_ALGORITHM', 'AES256')

    # Session配置
    SESSION_SECRET: str = os.getenv('SESSION_SECRET', 'your_session_secret')
    SESSION_COOKIE_NAME: str = os.getenv('SESSION_COOKIE_NAME', 'xmp_session')
    SESSION_MAX_AGE: int = int(os.getenv('SESSION_MAX_AGE', 86400))

    # 日志配置
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES: int = int(os.getenv('LOG_MAX_BYTES', 10485760))
    LOG_BACKUP_COUNT: int = int(os.getenv('LOG_BACKUP_COUNT', 5))

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


# 日志配置
def setup_logging():
    """配置日志系统"""
    import logging
    from logging.handlers import RotatingFileHandler

    # 创建logs目录
    log_dir = BASE_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)

    # 配置根日志器
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_formatter = logging.Formatter(settings.LOG_FORMAT)
    console_handler.setFormatter(console_formatter)

    # 文件处理器
    file_handler = RotatingFileHandler(
        BASE_DIR / settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(settings.LOG_FORMAT)
    file_handler.setFormatter(file_formatter)

    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


if __name__ == '__main__':
    # 测试配置加载
    print(f"Environment: {settings.ENV}")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Google Scopes: {settings.GOOGLE_SCOPES_LIST}")
    print(f"CORS Origins: {settings.CORS_ORIGINS_LIST}")
