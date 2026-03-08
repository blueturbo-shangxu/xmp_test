"""
Redis client initialization and management
全局 Redis 客户端初始化和管理
"""
import logging
from typing import Optional
import redis
from redis.exceptions import RedisError

from src.core.config import settings

logger = logging.getLogger(__name__)

# 全局 Redis 客户端实例
_redis_client: Optional[redis.Redis] = None


def init_redis() -> redis.Redis:
    """
    初始化全局 Redis 客户端

    Returns:
        redis.Redis: Redis 客户端实例

    Raises:
        RedisError: 连接失败时抛出
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        # 测试连接
        _redis_client.ping()
        logger.info(f"Redis connected successfully: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        return _redis_client
    except RedisError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


def get_redis_client() -> redis.Redis:
    """
    获取全局 Redis 客户端

    如果尚未初始化，会自动初始化

    Returns:
        redis.Redis: Redis 客户端实例
    """
    global _redis_client

    if _redis_client is None:
        return init_redis()

    return _redis_client


redis_client = get_redis_client()

def close_redis():
    """关闭全局 Redis 连接"""
    global _redis_client

    if _redis_client is not None:
        try:
            _redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None


def check_redis_connection() -> bool:
    """
    检查 Redis 连接状态

    Returns:
        bool: 连接是否正常
    """
    try:
        client = get_redis_client()
        return client.ping()
    except RedisError as e:
        logger.error(f"Redis health check failed: {e}")
        return False
