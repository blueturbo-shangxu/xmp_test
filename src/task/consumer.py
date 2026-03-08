"""
Task Consumer
任务消费者，负责从队列中获取任务并执行
"""
import logging
import time
import threading
import traceback
from typing import Dict, Type, Optional
from datetime import datetime

from src.sql.database import get_db_context
from src.sql.models import SyncTask
from src.task.base import BaseTask, TaskType, TaskResult, TaskStatus, TaskNonRetryableError
from src.task.queue_manager import RedisQueueManager
from src.task.producer import TaskProducer
from src.task.notification import NotificationService
from src.task.handlers import (
    GoogleAccountSyncHandler,
    GoogleCampaignSyncHandler,
    GoogleAdGroupSyncHandler,
    GoogleAdSyncHandler,
)
from src.core import settings

logger = logging.getLogger(__name__)

# 默认最大工作线程数
DEFAULT_MAX_WORKERS = 5

# 全局任务处理器映射表
TASK_HANDLERS: Dict[str, Type[BaseTask]] = {
    TaskType.SYNC_GOOGLE_ACCOUNTS.value: GoogleAccountSyncHandler,
    TaskType.SYNC_GOOGLE_CAMPAIGNS.value: GoogleCampaignSyncHandler,
    TaskType.SYNC_GOOGLE_AD_GROUPS.value: GoogleAdGroupSyncHandler,
    TaskType.SYNC_GOOGLE_ADS.value: GoogleAdSyncHandler,
}


def register_handler(task_type: str, handler_class: Type[BaseTask]):
    """
    注册任务处理器到全局映射表

    Args:
        task_type: 任务类型
        handler_class: 任务处理器类
    """
    TASK_HANDLERS[task_type] = handler_class
    logger.info(f"Registered handler for task type: {task_type}")


def get_handler(task_type: str) -> Optional[Type[BaseTask]]:
    """
    获取任务处理器

    Args:
        task_type: 任务类型

    Returns:
        Optional[Type[BaseTask]]: 处理器类或 None
    """
    return TASK_HANDLERS.get(task_type)


class TaskConsumer:
    """
    任务消费者

    循环从 Redis 队列中获取任务并执行
    支持多线程并发执行任务，可配置最大工作线程数
    """

    def __init__(self, max_workers: int = DEFAULT_MAX_WORKERS):
        """
        初始化任务消费者

        Args:
            max_workers: 最大工作线程数
        """
        self.queue_manager = RedisQueueManager()
        self.producer = TaskProducer()
        self.notification = NotificationService()
        self._running = False
        self._lock_renewal_threads: Dict[int, threading.Event] = {}

        # 线程池管理
        self._max_workers = max_workers
        self._active_workers = 0
        self._workers_lock = threading.Lock()
        self._workers_condition = threading.Condition(self._workers_lock)

    @property
    def active_workers(self) -> int:
        """获取当前活跃工作线程数"""
        with self._workers_lock:
            return self._active_workers

    @property
    def max_workers(self) -> int:
        """获取最大工作线程数"""
        return self._max_workers

    def set_max_workers(self, max_workers: int):
        """
        设置最大工作线程数

        Args:
            max_workers: 新的最大工作线程数
        """
        with self._workers_lock:
            self._max_workers = max_workers
            # 如果新的最大值大于当前活跃数，通知等待的线程
            self._workers_condition.notify_all()

    def start(self):
        """启动消费者"""
        self._running = True
        logger.info(f"Task consumer started with max_workers={self._max_workers}")
        self._consume_loop()

    def stop(self):
        """停止消费者"""
        self._running = False
        # 通知所有等待的线程
        with self._workers_condition:
            self._workers_condition.notify_all()
        # 停止所有锁续期线程
        for stop_event in self._lock_renewal_threads.values():
            stop_event.set()
        logger.info("Task consumer stopped")

    def _acquire_worker_slot(self) -> bool:
        """
        获取工作线程槽位

        如果当前活跃线程数 >= 最大线程数，则等待
        返回 False 表示消费者已停止

        Returns:
            bool: 是否成功获取槽位
        """
        with self._workers_condition:
            while self._running and self._active_workers >= self._max_workers:
                logger.debug(
                    f"Worker slots full ({self._active_workers}/{self._max_workers}), waiting..."
                )
                # 等待直到有线程完成或消费者停止
                self._workers_condition.wait(timeout=1)

            if not self._running:
                return False

            self._active_workers += 1
            logger.debug(f"Acquired worker slot ({self._active_workers}/{self._max_workers})")
            return True

    def _release_worker_slot(self):
        """释放工作线程槽位"""
        with self._workers_condition:
            self._active_workers -= 1
            logger.debug(f"Released worker slot ({self._active_workers}/{self._max_workers})")
            # 通知等待的线程
            self._workers_condition.notify()

    def _consume_loop(self):
        """
        消费循环

        逻辑:
        1. 检查是否有可用的工作线程槽位
        2. 循环轮询优先级队列
        3. 如果最优先的元素的权重小于等于当前时间戳则往下执行
        4. 否则计算等待时间，小于5秒则等待差值，大于5秒则等待5秒
        5. 获取消费锁成功后删除队列元素并启动线程处理
        6. 队列为空则等待10秒
        """
        while self._running:
            try:
                # 检查是否有可用的工作线程槽位
                if self._active_workers >= self._max_workers:
                    # 等待槽位释放
                    with self._workers_condition:
                        while self._running and self._active_workers >= self._max_workers:
                            self._workers_condition.wait(timeout=1)
                    if not self._running:
                        break
                    continue

                # 获取队列中优先级最高的任务
                first_task = self.queue_manager.get_first_task()

                if first_task is None:
                    # 队列为空，等待10秒
                    logger.debug("Queue is empty, waiting 10 seconds")
                    time.sleep(10)
                    continue

                task_id, score = first_task
                current_time = time.time()

                # 检查是否到达执行时间
                if score > current_time:
                    # 未到执行时间，计算等待时间
                    wait_time = min(score - current_time, 5)
                    logger.debug(
                        f"Task {task_id} not ready, waiting {wait_time:.2f}s"
                    )
                    time.sleep(wait_time)
                    continue

                # 尝试获取消费锁
                if not self.queue_manager.acquire_consume_lock(task_id):
                    # 获取锁失败，可能其他消费者正在处理，继续下一轮
                    logger.debug(f"Failed to acquire consume lock for task {task_id}")
                    time.sleep(0.1)
                    continue

                try:
                    # 从队列中删除任务
                    self.queue_manager.remove_task(task_id)

                    # 获取工作线程槽位
                    if not self._acquire_worker_slot():
                        # 消费者已停止，将任务重新加入队列
                        self.queue_manager.add_task(task_id, score)
                        break

                    # 启动工作线程处理任务
                    worker_thread = threading.Thread(
                        target=self._worker_wrapper,
                        args=(task_id,),
                        daemon=True,
                        name=f"TaskWorker-{task_id}"
                    )
                    worker_thread.start()

                finally:
                    # 释放消费锁
                    self.queue_manager.release_consume_lock(task_id)

            except Exception as e:
                logger.error(f"Error in consume loop: {e}")
                logger.error(traceback.format_exc())
                time.sleep(1)

    def _worker_wrapper(self, task_id: int):
        """
        工作线程包装器

        负责执行任务并在完成后释放槽位

        Args:
            task_id: 任务ID
        """
        try:
            self._process_task(task_id)
        finally:
            self._release_worker_slot()

    def _process_task(self, task_id: int):
        """
        处理单个任务

        Args:
            task_id: 任务ID
        """
        logger.info(f"Processing task {task_id}")
        start_time = datetime.now()

        # 获取执行锁
        if not self.queue_manager.acquire_exec_lock(task_id):
            logger.warning(f"Failed to acquire exec lock for task {task_id}")
            return

        # 启动锁续期线程
        stop_event = threading.Event()
        self._lock_renewal_threads[task_id] = stop_event
        renewal_thread = threading.Thread(
            target=self._lock_renewal_loop,
            args=(task_id, stop_event),
            daemon=True
        )
        renewal_thread.start()

        try:
            # 添加到正在执行集合
            self.queue_manager.add_running_task(task_id)
            # 从数据库获取任务详情
            with get_db_context() as db:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if not task:
                    logger.error(f"Task {task_id} not found in database")
                    return

                # 检查任务状态，避免重复处理
                if task.status == TaskStatus.RUNNING.value:
                    logger.warning(f"Task {task_id} is already running")
                    return

                # 更新任务状态为运行中
                task.status = TaskStatus.RUNNING.value
                task.started_at = start_time
                db.commit()

                # 获取任务信息
                task_type = task.task_type
                platform = task.platform
                account_key = task.account_key
                sync_params = task.sync_params or {}
                retry_count = task.retry_count
                max_retry_count = task.max_retry_count
                retry_interval = task.retry_interval_seconds


            # 获取处理器并执行
            handler_class = get_handler(task_type)
            if not handler_class:
                raise ValueError(f"No handler registered for task type: {task_type}")

            handler = handler_class(TaskType(task_type))
            result = handler.execute(
                task_id=task_id,
                platform=platform,
                account_key=account_key,
                sync_params=sync_params,
            )
            result.started_at = start_time
            result.completed_at = datetime.now()

            # 更新数据库
            self._update_task_result(task_id, result)

            # 调用回调
            if result.success:
                handler.on_success(result)
            else:
                handler.on_failure(result)
                # 检查是否需要重试
                if retry_count < max_retry_count:
                    handler.on_retry(task_id, retry_count + 1, max_retry_count)
                    self.producer.create_retry_task(task_id, retry_interval)
                else:
                    # 超过最大重试次数，发送通知
                    self.notification.notify_task_failed(task_id, result.error_message)

        except TaskNonRetryableError as e:
            # 不需要重试的异常，直接标记失败并通知
            error_msg = str(e)
            error_tb = traceback.format_exc()
            logger.error(f"Task {task_id} failed with non-retryable error: {error_msg}")

            # 更新数据库
            self._update_task_error(task_id, error_msg, error_tb, start_time)

            # 直接发送通知，不创建重试任务
            self.notification.notify_task_failed(task_id, error_msg)

        except Exception as e:
            error_msg = str(e)
            error_tb = traceback.format_exc()
            logger.error(f"Task {task_id} execution failed: {error_msg}")
            logger.error(error_tb)

            # 更新数据库
            self._update_task_error(task_id, error_msg, error_tb, start_time)

            # 检查重试
            with get_db_context() as db:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if task and task.retry_count < task.max_retry_count:
                    self.producer.create_retry_task(task_id, task.retry_interval_seconds)
                else:
                    self.notification.notify_task_failed(task_id, error_msg)

        finally:
            # 从正在执行集合移除
            self.queue_manager.remove_running_task(task_id)

            # 停止锁续期线程
            stop_event.set()
            if task_id in self._lock_renewal_threads:
                del self._lock_renewal_threads[task_id]

            # 释放执行锁
            self.queue_manager.release_exec_lock(task_id)

    def _lock_renewal_loop(self, task_id: int, stop_event: threading.Event):
        """
        锁续期循环

        Args:
            task_id: 任务ID
            stop_event: 停止事件
        """
        interval = settings.TASK_LOCK_RENEW_INTERVAL
        while not stop_event.is_set():
            if stop_event.wait(interval):
                break
            if not self.queue_manager.renew_exec_lock(task_id):
                logger.warning(f"Failed to renew exec lock for task {task_id}")

    def _update_task_result(self, task_id: int, result: TaskResult):
        """更新任务执行结果"""
        try:
            with get_db_context() as db:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if task:
                    task.status = TaskStatus.COMPLETED.value if result.success else TaskStatus.FAILED.value
                    task.total_records = result.total_records
                    task.processed_records = result.processed_records
                    task.failed_records = result.failed_records
                    task.completed_at = result.completed_at
                    task.duration_seconds = result.duration_seconds
                    if result.error_message:
                        task.error_message = result.error_message
                    if result.error_traceback:
                        task.error_traceback = result.error_traceback
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to update task {task_id} result: {e}")

    def _update_task_error(
        self,
        task_id: int,
        error_message: str,
        error_traceback: str,
        start_time: datetime
    ):
        """更新任务错误信息"""
        try:
            with get_db_context() as db:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if task:
                    task.status = TaskStatus.FAILED.value
                    task.error_message = error_message
                    task.error_traceback = error_traceback
                    task.completed_at = datetime.now()
                    task.duration_seconds = int((datetime.now() - start_time).total_seconds())
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to update task {task_id} error: {e}")
