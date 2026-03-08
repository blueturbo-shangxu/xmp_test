"""
Sync Task API Router
数据同步任务 API 接口
"""
import logging
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.sql.database import get_db
from src.sql.models import SyncTask
from src.task.base import TaskType, InitiatorType, TaskStatus
from src.task.producer import TaskProducer
from src.task.queue_manager import RedisQueueManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["Sync Tasks"])


# ==================== Request/Response Models ====================

class CreateSyncTaskRequest(BaseModel):
    """创建同步任务请求"""
    platform: str = Field(..., description="平台标识: google, meta, tiktok")
    account_key: str = Field(..., description="账户标识")
    task_type: str = Field(..., description="任务类型")
    sync_params: Optional[dict] = Field(None, description="同步参数条件")
    priority: int = Field(5, ge=1, le=10, description="优先级(1-10)")
    start_date: Optional[date] = Field(None, description="数据开始日期")
    end_date: Optional[date] = Field(None, description="数据结束日期")
    max_retry_count: Optional[int] = Field(None, description="最大重试次数")
    retry_interval_seconds: Optional[int] = Field(None, description="重试间隔(秒)")
    initiator_type: str = Field(InitiatorType.USER.value, description="发起者类型")
    initiator_id: Optional[str] = Field(None, description="发起者ID")


class CreateGoogleSyncTaskRequest(BaseModel):
    """创建 Google 同步任务请求"""
    token_id: Optional[int] = Field(None, description="Token ID (账户同步时使用)")
    customer_id: Optional[str] = Field(None, description="Customer ID (其他同步时使用)")
    task_type: str = Field(..., description="任务类型")
    campaign_id: Optional[str] = Field(None, description="Campaign ID (可选过滤条件)")
    ad_group_id: Optional[str] = Field(None, description="AdGroup ID (可选过滤条件)")
    priority: int = Field(5, ge=1, le=10, description="优先级(1-10)")
    initiator_id: Optional[str] = Field(None, description="发起者ID")


class SyncTaskResponse(BaseModel):
    """同步任务响应"""
    id: int
    platform: str
    account_key: str
    task_type: str
    status: str
    priority: int
    sync_params: Optional[dict]
    initiator_type: str
    initiator_id: Optional[str]
    retry_count: int
    max_retry_count: int
    total_records: int
    processed_records: int
    failed_records: int
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[int]
    created_at: str

    class Config:
        from_attributes = True


class TaskQueueStatusResponse(BaseModel):
    """任务队列状态响应"""
    queue_length: int
    running_tasks: List[int]
    redis_healthy: bool


class CreateTaskResponse(BaseModel):
    """创建任务响应"""
    success: bool
    task_id: Optional[int]
    message: str


# ==================== API Endpoints ====================

@router.post("/task", response_model=CreateTaskResponse)
async def create_sync_task(request: CreateSyncTaskRequest):
    """
    创建同步任务

    通用接口，支持创建任意类型的同步任务
    """
    try:
        producer = TaskProducer()
        task_id = producer.create_task(
            platform=request.platform,
            account_key=request.account_key,
            task_type=request.task_type,
            sync_params=request.sync_params,
            priority=request.priority,
            start_date=request.start_date,
            end_date=request.end_date,
            max_retry_count=request.max_retry_count,
            retry_interval_seconds=request.retry_interval_seconds,
            initiator_type=request.initiator_type,
            initiator_id=request.initiator_id,
        )

        if task_id:
            return CreateTaskResponse(
                success=True,
                task_id=task_id,
                message=f"Task {task_id} created successfully"
            )
        else:
            return CreateTaskResponse(
                success=False,
                task_id=None,
                message="Failed to create task"
            )

    except Exception as e:
        logger.error(f"Failed to create sync task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google", response_model=CreateTaskResponse)
async def create_google_sync_task(request: CreateGoogleSyncTaskRequest):
    """
    创建 Google 同步任务

    便捷接口，简化 Google 平台的同步任务创建
    """
    try:
        producer = TaskProducer()

        # 根据任务类型选择合适的创建方法
        task_type = request.task_type

        if task_type == TaskType.SYNC_GOOGLE_ACCOUNTS.value:
            if not request.token_id:
                raise HTTPException(
                    status_code=400,
                    detail="token_id is required for account sync"
                )
            task_id = producer.create_google_account_sync_task(
                token_id=request.token_id,
                initiator_type=InitiatorType.USER.value,
                initiator_id=request.initiator_id,
                priority=request.priority,
            )

        elif task_type == TaskType.SYNC_GOOGLE_CAMPAIGNS.value:
            if not request.customer_id:
                raise HTTPException(
                    status_code=400,
                    detail="customer_id is required for campaign sync"
                )
            task_id = producer.create_google_campaign_sync_task(
                customer_id=request.customer_id,
                initiator_type=InitiatorType.USER.value,
                initiator_id=request.initiator_id,
                priority=request.priority,
            )

        elif task_type == TaskType.SYNC_GOOGLE_AD_GROUPS.value:
            if not request.customer_id:
                raise HTTPException(
                    status_code=400,
                    detail="customer_id is required for ad group sync"
                )
            task_id = producer.create_google_ad_group_sync_task(
                customer_id=request.customer_id,
                campaign_id=request.campaign_id,
                initiator_type=InitiatorType.USER.value,
                initiator_id=request.initiator_id,
                priority=request.priority,
            )

        elif task_type == TaskType.SYNC_GOOGLE_ADS.value:
            if not request.customer_id:
                raise HTTPException(
                    status_code=400,
                    detail="customer_id is required for ad sync"
                )
            task_id = producer.create_google_ad_sync_task(
                customer_id=request.customer_id,
                campaign_id=request.campaign_id,
                ad_group_id=request.ad_group_id,
                initiator_type=InitiatorType.USER.value,
                initiator_id=request.initiator_id,
                priority=request.priority,
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported task type: {task_type}"
            )

        if task_id:
            return CreateTaskResponse(
                success=True,
                task_id=task_id,
                message=f"Task {task_id} created successfully"
            )
        else:
            return CreateTaskResponse(
                success=False,
                task_id=None,
                message="Failed to create task"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create Google sync task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=SyncTaskResponse)
async def get_sync_task(task_id: int, db: Session = Depends(get_db)):
    """获取同步任务详情"""
    task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return SyncTaskResponse(
        id=task.id,
        platform=task.platform,
        account_key=task.account_key,
        task_type=task.task_type,
        status=task.status,
        priority=task.priority,
        sync_params=task.sync_params,
        initiator_type=task.initiator_type,
        initiator_id=task.initiator_id,
        retry_count=task.retry_count,
        max_retry_count=task.max_retry_count,
        total_records=task.total_records,
        processed_records=task.processed_records,
        failed_records=task.failed_records,
        error_message=task.error_message,
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        duration_seconds=task.duration_seconds,
        created_at=task.created_at.isoformat() if task.created_at else None,
    )


@router.get("/tasks", response_model=List[SyncTaskResponse])
async def list_sync_tasks(
    platform: Optional[str] = Query(None, description="平台过滤"),
    account_key: Optional[str] = Query(None, description="账户过滤"),
    task_type: Optional[str] = Query(None, description="任务类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """获取同步任务列表"""
    query = db.query(SyncTask)

    if platform:
        query = query.filter(SyncTask.platform == platform)
    if account_key:
        query = query.filter(SyncTask.account_key == account_key)
    if task_type:
        query = query.filter(SyncTask.task_type == task_type)
    if status:
        query = query.filter(SyncTask.status == status)

    tasks = query.order_by(SyncTask.created_at.desc()).offset(offset).limit(limit).all()

    return [
        SyncTaskResponse(
            id=task.id,
            platform=task.platform,
            account_key=task.account_key,
            task_type=task.task_type,
            status=task.status,
            priority=task.priority,
            sync_params=task.sync_params,
            initiator_type=task.initiator_type,
            initiator_id=task.initiator_id,
            retry_count=task.retry_count,
            max_retry_count=task.max_retry_count,
            total_records=task.total_records,
            processed_records=task.processed_records,
            failed_records=task.failed_records,
            error_message=task.error_message,
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            duration_seconds=task.duration_seconds,
            created_at=task.created_at.isoformat() if task.created_at else None,
        )
        for task in tasks
    ]


@router.post("/task/{task_id}/cancel")
async def cancel_sync_task(task_id: int, db: Session = Depends(get_db)):
    """取消同步任务"""
    task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status: {task.status}"
        )

    # 从队列中移除
    queue_manager = RedisQueueManager()
    queue_manager.remove_task(task_id)

    # 更新状态
    task.status = TaskStatus.CANCELLED.value
    db.commit()

    return {"success": True, "message": f"Task {task_id} cancelled"}


@router.post("/task/{task_id}/retry")
async def retry_sync_task(task_id: int, db: Session = Depends(get_db)):
    """重试同步任务"""
    task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in [TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry task with status: {task.status}"
        )

    # 创建重试任务
    producer = TaskProducer()
    success = producer.create_retry_task(task_id, retry_delay=0)

    if success:
        return {"success": True, "message": f"Task {task_id} queued for retry"}
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to queue task for retry"
        )


@router.get("/queue/status", response_model=TaskQueueStatusResponse)
async def get_queue_status():
    """获取任务队列状态"""
    try:
        queue_manager = RedisQueueManager()
        return TaskQueueStatusResponse(
            queue_length=queue_manager.get_queue_length(),
            running_tasks=queue_manager.get_running_tasks(),
            redis_healthy=queue_manager.health_check(),
        )
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return TaskQueueStatusResponse(
            queue_length=0,
            running_tasks=[],
            redis_healthy=False,
        )


@router.get("/task-types")
async def get_task_types():
    """获取支持的任务类型列表"""
    return {
        "task_types": [
            {"value": t.value, "name": t.name}
            for t in TaskType
        ],
        "initiator_types": [
            {"value": t.value, "name": t.name}
            for t in InitiatorType
        ],
        "task_statuses": [
            {"value": t.value, "name": t.name}
            for t in TaskStatus
        ],
    }
