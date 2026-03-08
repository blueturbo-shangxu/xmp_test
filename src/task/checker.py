"""
Task Checker
任务检查器，监控异常退出的任务
"""
import logging
import time
import threading
from typing import Optional

from src.sql.database import get_db_context
from src.sql.models import SyncTask
from src.task.base import TaskStatus
from src.task.queue_manager import RedisQueueManager
from src.task.notification import NotificationService

logger = logging.getLogger(__name__)

# 检查器分布式锁配置
CHECKER_LOCK_KEY = "task_checker_lock"


class TaskChecker:
    """
    任务检查器

    功能:
    1. 监控正在执行的任务集合
    2. 检查每个任务是否有对应的 Redis 锁
    3. 如果没有锁，说明任务异常退出
    4. 将异常任务重新加入队列
    """

    def __init__(self, check_interval: int = 30):
        """
        初始化检查器

        Args:
            check_interval: 检查间隔（秒），同时也是分布式锁的超时时间
        """
        self.queue_manager = RedisQueueManager()
        self.notification = NotificationService()
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._log_header = '[TaskChecker]'

    def start(self, daemon: bool = True):
        """
        启动检查器

        Args:
            daemon: 是否作为守护线程运行
        """
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=daemon)
        self._thread.start()
        logger.info(f"{self._log_header} Task checker started with interval {self.check_interval}s")

    def stop(self):
        """停止检查器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info(f"{self._log_header} Task checker stopped")

    def _acquire_checker_lock(self) -> bool:
        """
        获取检查器分布式锁

        Returns:
            bool: 是否获取成功
        """
        try:
            result = self.queue_manager.client.set(
                CHECKER_LOCK_KEY,
                str(time.time()),
                nx=True,
                ex=self.check_interval
            )
            if result:
                logger.debug(f"{self._log_header} Acquired checker lock")
            return result is not None
        except Exception as e:
            logger.error(f"{self._log_header} Failed to acquire checker lock: {e}")
            return False

    def _release_checker_lock(self):
        """释放检查器分布式锁"""
        try:
            self.queue_manager.client.delete(CHECKER_LOCK_KEY)
            logger.debug(f"{self._log_header} Released checker lock")
        except Exception as e:
            logger.error(f"{self._log_header} Failed to release checker lock: {e}")

    def _get_lock_ttl(self) -> int:
        """
        获取锁剩余过期时间

        Returns:
            int: 剩余秒数，-2表示key不存在，-1表示没有过期时间
        """
        try:
            return self.queue_manager.client.ttl(CHECKER_LOCK_KEY)
        except Exception as e:
            logger.error(f"{self._log_header} Failed to get lock TTL: {e}")
            return -2

    def _check_loop(self):
        """检查循环"""
        while self._running:
            try:
                # 尝试获取分布式锁
                if self._acquire_checker_lock():
                    self._check_running_tasks()
                    # 获取到锁并执行完成，等待下次检查
                    self._wait_interval()
                else:
                    # 未获取到锁，说明其他实例正在执行
                    # 等待锁过期时间后重试
                    ttl = self._get_lock_ttl()
                    if ttl > 0:
                        logger.debug(f"{self._log_header} Checker lock held by another instance, waiting {ttl}s")
                        self._wait_seconds(ttl + 1)
                    else:
                        # 锁不存在或无过期时间，短暂等待后重试
                        self._wait_seconds(10)

            except Exception as e:
                logger.error(f"{self._log_header} Error in task checker: {e}")
                self._wait_seconds(5)

    def _wait_interval(self):
        """等待检查间隔时间"""
        self._wait_seconds(self.check_interval)

    def _wait_seconds(self, seconds: int):
        """
        等待指定秒数，支持提前退出

        Args:
            seconds: 等待秒数
        """
        for _ in range(seconds):
            if not self._running:
                break
            time.sleep(1)

    def _check_running_tasks(self):
        """
        检查正在执行的任务

        检查逻辑:
        1. 获取正在执行的任务集合中的所有任务ID
        2. 对每个任务，检查是否有对应的执行锁
        3. 如果没有锁，说明任务异常退出
        4. 将任务重新加入队列，并从正在执行集合中移除
        """
        running_tasks = self.queue_manager.get_running_tasks()

        if not running_tasks:
            logger.debug(f"{self._log_header} No running tasks to check")
            return

        logger.debug(f"{self._log_header} Checking {len(running_tasks)} running tasks")

        for task_id in running_tasks:
            # 检查是否有执行锁
            if self.queue_manager.has_exec_lock(task_id):
                continue

            # 没有锁，说明任务异常退出
            logger.warning(f"{self._log_header} Task {task_id} has no exec lock, may have exited abnormally")

            # 检查数据库中的任务状态
            with get_db_context() as db:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if not task:
                    # 任务不存在，从运行集合中移除
                    logger.error(f"{self._log_header} Task {task_id} not found in database, but in running set, removing from running set")
                    self.queue_manager.remove_running_task(task_id)
                    continue

                # 检查任务是否已经完成
                if task.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                    # 任务已结束，从运行集合中移除
                    logger.error(f"{self._log_header} Task {task_id} has already completed, but still in running set, removing from running set")
                    self.queue_manager.remove_running_task(task_id)
                    continue

                # 检查是否超过最大重试次数
                if task.retry_count >= task.max_retry_count:
                    logger.warning(f"{self._log_header} Task {task_id} exceeded max retry count, marking as failed")
                    task.status = TaskStatus.FAILED.value
                    task.error_message = f"{self._log_header} Task exceeded max retry count after abnormal exit"
                    db.commit()
                    self.queue_manager.remove_running_task(task_id)
                    self.notification.notify_task_failed(task_id, task.error_message)
                    continue

                # 更新重试次数
                task.retry_count += 1
                task.status = TaskStatus.PENDING.value
                db.commit()

            # 重新加入队列
            if self.queue_manager.add_task(task_id):
                logger.info(f"{self._log_header} Task {task_id} re-added to queue due to abnormal exit")
            else:
                logger.error(f"{self._log_header} Failed to re-add task {task_id} to queue")

            # 从正在执行集合中移除
            self.queue_manager.remove_running_task(task_id)

    def check_once(self):
        """
        执行一次检查（用于手动触发）
        无需获取分布式锁，直接执行检查逻辑
        """
        self._check_running_tasks()
