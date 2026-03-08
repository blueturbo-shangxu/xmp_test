"""
Task Producer
任务生产者，负责创建任务并发送到队列
"""
import logging
import time
from typing import Dict, Any, Optional
from datetime import date

from src.sql.database import get_db_context
from src.sql.models import SyncTask
from src.task.base import TaskType, InitiatorType, TaskStatus
from src.task.queue_manager import RedisQueueManager
from src.core import settings

logger = logging.getLogger(__name__)


class TaskProducer:
    """
    任务生产者

    负责创建 SyncTask 数据库记录并将任务ID发送到 Redis 队列
    """

    def __init__(self):
        self.queue_manager = RedisQueueManager()

    def create_task(
        self,
        platform: str,
        account_key: str,
        task_type: str,
        sync_params: Optional[Dict[str, Any]] = None,
        initiator_type: str = InitiatorType.PROGRAM.value,
        initiator_id: Optional[str] = None,
        priority: int = 5,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_retry_count: Optional[int] = None,
        retry_interval_seconds: Optional[int] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        ext_info: Optional[Dict[str, Any]] = None,
        schedule_time: Optional[float] = None,
    ) -> Optional[int]:
        """
        创建同步任务

        Args:
            platform: 平台标识 (google, meta, tiktok)
            account_key: 账户标识
            task_type: 任务类型
            sync_params: 同步参数条件 (如: {"ad_group_id": "123"})
            initiator_type: 发起者类型 (USER, PROGRAM)
            initiator_id: 发起者ID
            priority: 优先级 (1-10, 10最高)
            start_date: 数据开始日期
            end_date: 数据结束日期
            max_retry_count: 最大重试次数
            retry_interval_seconds: 重试间隔秒数
            raw_data: 原始任务数据
            ext_info: 扩展信息
            schedule_time: 调度时间戳（用于延迟执行），默认为当前时间

        Returns:
            Optional[int]: 任务ID，失败返回 None
        """
        try:
            # 设置默认值
            if max_retry_count is None:
                max_retry_count = settings.MAX_RETRY_COUNT
            if retry_interval_seconds is None:
                retry_interval_seconds = settings.RETRY_DELAY_SECONDS
            if schedule_time is None:
                schedule_time = time.time()

            # 创建数据库记录
            with get_db_context() as db:
                task = SyncTask(
                    platform=platform,
                    account_key=account_key,
                    task_type=task_type,
                    status=TaskStatus.PENDING.value,
                    priority=priority,
                    start_date=start_date,
                    end_date=end_date,
                    sync_params=sync_params or {},
                    initiator_type=initiator_type,
                    initiator_id=initiator_id,
                    max_retry_count=max_retry_count,
                    retry_interval_seconds=retry_interval_seconds,
                    raw_data=raw_data or {},
                    ext_info=ext_info or {},
                )
                db.add(task)
                db.commit()
                db.refresh(task)
                task_id = task.id

            logger.info(
                f"Created task {task_id}: platform={platform}, "
                f"account_key={account_key}, task_type={task_type}"
            )

            # 发送任务ID到Redis队列
            # 使用当前时间戳作为权重（用于延迟执行的任务，可以使用未来时间戳）
            if self.queue_manager.add_task(task_id, score=schedule_time):
                logger.info(f"Task {task_id} added to queue with score {schedule_time}")
                return task_id
            else:
                logger.error(f"Failed to add task {task_id} to queue")
                # 回滚数据库状态
                self._mark_task_failed(task_id, "Failed to add task to Redis queue")
                return None

        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return None

    def create_retry_task(
        self,
        task_id: int,
        retry_delay: Optional[int] = None,
    ) -> bool:
        """
        创建重试任务（将已有任务重新加入队列）

        Args:
            task_id: 原任务ID
            retry_delay: 重试延迟秒数，默认从数据库读取

        Returns:
            bool: 是否成功
        """
        try:
            with get_db_context() as db:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return False

                # 检查是否超过最大重试次数
                if task.retry_count >= task.max_retry_count:
                    logger.warning(
                        f"Task {task_id} exceeded max retry count "
                        f"({task.retry_count}/{task.max_retry_count})"
                    )
                    return False

                # 更新重试次数
                task.retry_count += 1
                task.status = TaskStatus.PENDING.value
                db.commit()

                # 计算重试时间
                if retry_delay is None:
                    retry_delay = task.retry_interval_seconds

                schedule_time = time.time() + retry_delay

            # 重新加入队列
            if self.queue_manager.add_task(task_id, score=schedule_time):
                logger.info(
                    f"Retry task {task_id} added to queue, "
                    f"will execute after {retry_delay}s"
                )
                return True
            else:
                logger.error(f"Failed to add retry task {task_id} to queue")
                return False

        except Exception as e:
            logger.error(f"Failed to create retry task {task_id}: {e}")
            return False

    def _mark_task_failed(self, task_id: int, error_message: str):
        """标记任务失败"""
        try:
            with get_db_context() as db:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if task:
                    task.status = TaskStatus.FAILED.value
                    task.error_message = error_message
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to mark task {task_id} as failed: {e}")

    # ==================== 便捷方法 ====================

    def create_google_account_sync_task(
        self,
        token_id: int,
        initiator_type: str = InitiatorType.PROGRAM.value,
        initiator_id: Optional[str] = None,
        **kwargs
    ) -> Optional[int]:
        """创建 Google 账户同步任务"""
        return self.create_task(
            platform="google",
            account_key=str(token_id),
            task_type=TaskType.SYNC_GOOGLE_ACCOUNTS.value,
            initiator_type=initiator_type,
            initiator_id=initiator_id,
            **kwargs
        )

    def create_google_campaign_sync_task(
        self,
        customer_id: str,
        initiator_type: str = InitiatorType.PROGRAM.value,
        initiator_id: Optional[str] = None,
        sync_params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[int]:
        """创建 Google Campaign 同步任务"""
        return self.create_task(
            platform="google",
            account_key=customer_id,
            task_type=TaskType.SYNC_GOOGLE_CAMPAIGNS.value,
            sync_params=sync_params,
            initiator_type=initiator_type,
            initiator_id=initiator_id,
            **kwargs
        )

    def create_google_ad_group_sync_task(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        initiator_type: str = InitiatorType.PROGRAM.value,
        initiator_id: Optional[str] = None,
        **kwargs
    ) -> Optional[int]:
        """创建 Google AdGroup 同步任务"""
        sync_params = {}
        if campaign_id:
            sync_params["campaign_id"] = campaign_id

        return self.create_task(
            platform="google",
            account_key=customer_id,
            task_type=TaskType.SYNC_GOOGLE_AD_GROUPS.value,
            sync_params=sync_params if sync_params else None,
            initiator_type=initiator_type,
            initiator_id=initiator_id,
            **kwargs
        )

    def create_google_ad_sync_task(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        ad_group_id: Optional[str] = None,
        initiator_type: str = InitiatorType.PROGRAM.value,
        initiator_id: Optional[str] = None,
        **kwargs
    ) -> Optional[int]:
        """创建 Google Ad 同步任务"""
        sync_params = {}
        if campaign_id:
            sync_params["campaign_id"] = campaign_id
        if ad_group_id:
            sync_params["ad_group_id"] = ad_group_id

        return self.create_task(
            platform="google",
            account_key=customer_id,
            task_type=TaskType.SYNC_GOOGLE_ADS.value,
            sync_params=sync_params if sync_params else None,
            initiator_type=initiator_type,
            initiator_id=initiator_id,
            **kwargs
        )
