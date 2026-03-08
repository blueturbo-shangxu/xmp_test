"""
Base Task definitions and types
任务基础定义和类型
"""
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """任务类型枚举"""
    # Google Ads 同步任务
    SYNC_GOOGLE_ACCOUNTS = "sync_google_accounts"
    SYNC_GOOGLE_CAMPAIGNS = "sync_google_campaigns"
    SYNC_GOOGLE_AD_GROUPS = "sync_google_ad_groups"
    SYNC_GOOGLE_ADS = "sync_google_ads"

    # Meta 同步任务 (预留)
    SYNC_META_ACCOUNTS = "sync_meta_accounts"
    SYNC_META_CAMPAIGNS = "sync_meta_campaigns"

    # TikTok 同步任务 (预留)
    SYNC_TIKTOK_ACCOUNTS = "sync_tiktok_accounts"
    SYNC_TIKTOK_CAMPAIGNS = "sync_tiktok_campaigns"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class InitiatorType(str, Enum):
    """发起者类型枚举"""
    USER = "USER"
    PROGRAM = "PROGRAM"


class TaskNonRetryableError(Exception):
    """
    不需要重试的任务异常

    当任务因参数错误、配置缺失等原因失败时，抛出此异常。
    这类错误即使重试也不会成功，所以直接标记失败，不创建重试任务。
    """
    pass


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    task_id: int
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> Optional[int]:
        """计算执行时长"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None


class BaseTask(ABC):
    """
    任务基类
    所有具体任务类型需要继承此类并实现 execute 方法
    """

    def __init__(self, task_type: TaskType):
        self.task_type = task_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def execute(
        self,
        task_id: int,
        platform: str,
        account_key: str,
        sync_params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> TaskResult:
        """
        执行任务的抽象方法

        Args:
            task_id: 任务ID
            platform: 平台标识
            account_key: 账户标识
            sync_params: 同步参数条件
            **kwargs: 额外参数

        Returns:
            TaskResult: 任务执行结果
        """
        pass

    def on_success(self, result: TaskResult):
        """
        任务成功时的回调（可覆盖）

        Args:
            result: 任务结果
        """
        self.logger.info(
            f"Task {result.task_id} completed successfully. "
            f"Processed: {result.processed_records}/{result.total_records}"
        )

    def on_failure(self, result: TaskResult):
        """
        任务失败时的回调（可覆盖）

        Args:
            result: 任务结果
        """
        self.logger.error(
            f"Task {result.task_id} failed: {result.error_message}"
        )

    def on_retry(self, task_id: int, retry_count: int, max_retry: int):
        """
        任务重试时的回调（可覆盖）

        Args:
            task_id: 任务ID
            retry_count: 当前重试次数
            max_retry: 最大重试次数
        """
        self.logger.warning(
            f"Task {task_id} will retry ({retry_count}/{max_retry})"
        )
