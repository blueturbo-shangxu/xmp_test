"""
Task module for XMP Server
异步任务处理系统
"""
from src.task.base import BaseTask, TaskType
from src.task.queue_manager import RedisQueueManager
from src.task.producer import TaskProducer
from src.task.consumer import (
    TaskConsumer,
    TASK_HANDLERS,
    register_handler,
    get_handler,
    DEFAULT_MAX_WORKERS,
)
from src.task.checker import TaskChecker
from src.task.notification import NotificationService

__all__ = [
    'BaseTask',
    'TaskType',
    'RedisQueueManager',
    'TaskProducer',
    'TaskConsumer',
    'TaskChecker',
    'NotificationService',
    'TASK_HANDLERS',
    'register_handler',
    'get_handler',
    'DEFAULT_MAX_WORKERS',
]
