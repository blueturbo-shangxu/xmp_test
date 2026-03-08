"""
Redis Queue Manager
Redis 队列管理器，处理任务队列和锁操作
"""
import logging
import time
from typing import Optional, List, Tuple
import redis
from redis.exceptions import RedisError

from src.core import settings, get_redis_client

logger = logging.getLogger(__name__)


class RedisQueueManager:
    """
    Redis 队列管理器

    管理任务队列、分布式锁、正在执行任务集合
    """

    _instance: Optional['RedisQueueManager'] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> redis.Redis:
        """获取全局 Redis 客户端"""
        return get_redis_client()

    # ==================== 任务队列操作 ====================

    def add_task(self, task_id: int, score: Optional[float] = None) -> bool:
        """
        添加任务到优先级队列

        Args:
            task_id: 任务ID
            score: 权重（时间戳），默认为当前时间戳

        Returns:
            bool: 是否添加成功
        """
        try:
            if score is None:
                score = time.time()

            result = self.client.zadd(
                settings.TASK_QUEUE_NAME,
                {str(task_id): score}
            )
            logger.debug(f"Task {task_id} added to queue with score {score}")
            return result >= 0
        except RedisError as e:
            logger.error(f"Failed to add task {task_id} to queue: {e}")
            return False

    def get_first_task(self) -> Optional[Tuple[int, float]]:
        """
        获取队列中优先级最高的任务（不删除）

        Returns:
            Optional[Tuple[int, float]]: (task_id, score) 或 None
        """
        try:
            result = self.client.zrange(
                settings.TASK_QUEUE_NAME,
                0, 0,
                withscores=True
            )
            if result:
                task_id_str, score = result[0]
                return int(task_id_str), score
            return None
        except RedisError as e:
            logger.error(f"Failed to get first task from queue: {e}")
            return None

    def get_tasks_batch(self, count: int = 10) -> List[Tuple[int, float]]:
        """
        批量获取队列中的任务

        Args:
            count: 获取数量

        Returns:
            List[Tuple[int, float]]: [(task_id, score), ...]
        """
        try:
            result = self.client.zrange(
                settings.TASK_QUEUE_NAME,
                0, count - 1,
                withscores=True
            )
            return [(int(task_id_str), score) for task_id_str, score in result]
        except RedisError as e:
            logger.error(f"Failed to get tasks batch from queue: {e}")
            return []

    def remove_task(self, task_id: int) -> bool:
        """
        从队列中删除任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否删除成功
        """
        try:
            result = self.client.zrem(settings.TASK_QUEUE_NAME, str(task_id))
            logger.debug(f"Task {task_id} removed from queue: {result}")
            return result > 0
        except RedisError as e:
            logger.error(f"Failed to remove task {task_id} from queue: {e}")
            return False

    def get_queue_length(self) -> int:
        """获取队列长度"""
        try:
            return self.client.zcard(settings.TASK_QUEUE_NAME)
        except RedisError as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0

    # ==================== 分布式锁操作 ====================

    def acquire_consume_lock(self, task_id: int, timeout: int = 10) -> bool:
        """
        获取任务消费锁（用于从队列取出任务时）

        Args:
            task_id: 任务ID
            timeout: 锁超时时间（秒）

        Returns:
            bool: 是否获取成功
        """
        lock_key = f"{settings.TASK_LOCK_PREFIX}{task_id}"
        try:
            result = self.client.set(
                lock_key,
                "1",
                nx=True,
                ex=timeout
            )
            if result:
                logger.debug(f"Acquired consume lock for task {task_id}")
            return result is not None
        except RedisError as e:
            logger.error(f"Failed to acquire consume lock for task {task_id}: {e}")
            return False

    def release_consume_lock(self, task_id: int) -> bool:
        """释放任务消费锁"""
        lock_key = f"{settings.TASK_LOCK_PREFIX}{task_id}"
        try:
            result = self.client.delete(lock_key)
            logger.debug(f"Released consume lock for task {task_id}")
            return result > 0
        except RedisError as e:
            logger.error(f"Failed to release consume lock for task {task_id}: {e}")
            return False

    def acquire_exec_lock(self, task_id: int, timeout: Optional[int] = None) -> bool:
        """
        获取任务执行锁（用于执行任务时）

        Args:
            task_id: 任务ID
            timeout: 锁超时时间（秒），默认使用配置值

        Returns:
            bool: 是否获取成功
        """
        if timeout is None:
            timeout = settings.TASK_LOCK_TIMEOUT

        lock_key = f"{settings.TASK_EXEC_LOCK_PREFIX}{task_id}"
        try:
            result = self.client.set(
                lock_key,
                str(time.time()),
                nx=True,
                ex=timeout
            )
            if result:
                logger.debug(f"Acquired exec lock for task {task_id}")
            return result is not None
        except RedisError as e:
            logger.error(f"Failed to acquire exec lock for task {task_id}: {e}")
            return False

    def renew_exec_lock(self, task_id: int, timeout: Optional[int] = None) -> bool:
        """
        续期任务执行锁

        Args:
            task_id: 任务ID
            timeout: 新的超时时间

        Returns:
            bool: 是否续期成功
        """
        if timeout is None:
            timeout = settings.TASK_LOCK_TIMEOUT

        lock_key = f"{settings.TASK_EXEC_LOCK_PREFIX}{task_id}"
        try:
            result = self.client.expire(lock_key, timeout)
            logger.debug(f"Renewed exec lock for task {task_id}: {result}")
            return result
        except RedisError as e:
            logger.error(f"Failed to renew exec lock for task {task_id}: {e}")
            return False

    def release_exec_lock(self, task_id: int) -> bool:
        """释放任务执行锁"""
        lock_key = f"{settings.TASK_EXEC_LOCK_PREFIX}{task_id}"
        try:
            result = self.client.delete(lock_key)
            logger.debug(f"Released exec lock for task {task_id}")
            return result > 0
        except RedisError as e:
            logger.error(f"Failed to release exec lock for task {task_id}: {e}")
            return False

    def has_exec_lock(self, task_id: int) -> bool:
        """检查任务是否有执行锁"""
        lock_key = f"{settings.TASK_EXEC_LOCK_PREFIX}{task_id}"
        try:
            return self.client.exists(lock_key) > 0
        except RedisError as e:
            logger.error(f"Failed to check exec lock for task {task_id}: {e}")
            return False

    # ==================== 正在执行任务集合操作 ====================

    def add_running_task(self, task_id: int) -> bool:
        """添加到正在执行的任务集合"""
        try:
            result = self.client.sadd(settings.TASK_RUNNING_SET, str(task_id))
            logger.debug(f"Task {task_id} added to running set")
            return result > 0
        except RedisError as e:
            logger.error(f"Failed to add task {task_id} to running set: {e}")
            return False

    def remove_running_task(self, task_id: int) -> bool:
        """从正在执行的任务集合中移除"""
        try:
            result = self.client.srem(settings.TASK_RUNNING_SET, str(task_id))
            logger.debug(f"Task {task_id} removed from running set")
            return result > 0
        except RedisError as e:
            logger.error(f"Failed to remove task {task_id} from running set: {e}")
            return False

    def get_running_tasks(self) -> List[int]:
        """获取所有正在执行的任务ID"""
        try:
            result = self.client.smembers(settings.TASK_RUNNING_SET)
            return [int(task_id) for task_id in result]
        except RedisError as e:
            logger.error(f"Failed to get running tasks: {e}")
            return []

    def is_task_running(self, task_id: int) -> bool:
        """检查任务是否在执行中"""
        try:
            return self.client.sismember(settings.TASK_RUNNING_SET, str(task_id))
        except RedisError as e:
            logger.error(f"Failed to check if task {task_id} is running: {e}")
            return False

    # ==================== 工具方法 ====================

    def health_check(self) -> bool:
        """健康检查"""
        try:
            return self.client.ping()
        except RedisError as e:
            logger.error(f"Redis health check failed: {e}")
            return False
