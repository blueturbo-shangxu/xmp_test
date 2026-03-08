"""
Core module - Configuration and settings
"""
from src.core.config import settings, setup_logging, Settings, BASE_DIR
from src.core.logging_config import (
    setup_api_logging,
    setup_worker_logging,
    LoggerType,
    get_logger,
)
from src.core.redis_client import (
    init_redis,
    get_redis_client,
    close_redis,
    redis_client,
    check_redis_connection
)

__all__ = [
    'settings',
    'setup_logging',
    'setup_api_logging',
    'setup_worker_logging',
    'LoggerType',
    'get_logger',
    'Settings',
    'BASE_DIR',
    'get_redis_client',
    'close_redis',
    'redis_client',
    'check_redis_connection',
]
