"""
API routes for managing accounts and sync tasks
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.database import get_db
from src.models import Account, Campaign, AdGroup, SyncTask, OAuthToken
from src.services.google_ads_service import google_ads_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


# Pydantic模型
class AccountResponse(BaseModel):
    id: int
    customer_id: str
    account_name: str
    currency_code: Optional[str]
    timezone: Optional[str]
    account_type: str
    status: str
    has_valid_token: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SyncTaskRequest(BaseModel):
    account_id: int
    task_type: str  # CAMPAIGNS, AD_GROUPS, ADS, KEYWORDS, PERFORMANCE
    customer_id: str


class SyncTaskResponse(BaseModel):
    id: int
    account_id: int
    task_type: str
    status: str
    total_records: int
    processed_records: int
    failed_records: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True


@router.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    获取账户列表

    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        db: 数据库会话

    Returns:
        账户列表
    """
    try:
        accounts = db.query(Account).offset(skip).limit(limit).all()

        # 检查每个账户的token状态
        result = []
        for account in accounts:
            token = db.query(OAuthToken).filter(
                OAuthToken.account_id == account.id,
                OAuthToken.is_valid == True
            ).first()

            account_dict = {
                "id": account.id,
                "customer_id": account.customer_id,
                "account_name": account.account_name,
                "currency_code": account.currency_code,
                "timezone": account.timezone,
                "account_type": account.account_type,
                "status": account.status,
                "has_valid_token": token is not None and not token.is_expired,
                "created_at": account.created_at
            }
            result.append(account_dict)

        return result

    except Exception as e:
        logger.error(f"Failed to list accounts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个账户详情

    Args:
        account_id: 账户ID
        db: 数据库会话

    Returns:
        账户详情
    """
    try:
        account = db.query(Account).filter(Account.id == account_id).first()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        token = db.query(OAuthToken).filter(
            OAuthToken.account_id == account.id,
            OAuthToken.is_valid == True
        ).first()

        return {
            "id": account.id,
            "customer_id": account.customer_id,
            "account_name": account.account_name,
            "currency_code": account.currency_code,
            "timezone": account.timezone,
            "account_type": account.account_type,
            "status": account.status,
            "has_valid_token": token is not None and not token.is_expired,
            "created_at": account.created_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get account: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/campaigns", response_model=SyncTaskResponse)
async def sync_campaigns(
    request: SyncTaskRequest,
    db: Session = Depends(get_db)
):
    """
    同步推广活动数据

    Args:
        request: 同步任务请求
        db: 数据库会话

    Returns:
        同步任务信息
    """
    try:
        # 验证账户存在
        account = db.query(Account).filter(Account.id == request.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # 创建同步任务
        sync_task = SyncTask(
            account_id=request.account_id,
            task_type='CAMPAIGNS',
            status='RUNNING',
            started_at=datetime.now()
        )
        db.add(sync_task)
        db.commit()
        db.refresh(sync_task)

        # 执行同步
        success = google_ads_service.sync_campaigns(
            db,
            request.account_id,
            request.customer_id,
            sync_task.id
        )

        # 刷新任务状态
        db.refresh(sync_task)

        if not success:
            logger.error(f"Campaign sync failed for account {request.account_id}")

        return sync_task

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync campaigns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/ad-groups", response_model=SyncTaskResponse)
async def sync_ad_groups(
    request: SyncTaskRequest,
    db: Session = Depends(get_db)
):
    """
    同步广告组数据

    Args:
        request: 同步任务请求
        db: 数据库会话

    Returns:
        同步任务信息
    """
    try:
        # 验证账户存在
        account = db.query(Account).filter(Account.id == request.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # 创建同步任务
        sync_task = SyncTask(
            account_id=request.account_id,
            task_type='AD_GROUPS',
            status='RUNNING',
            started_at=datetime.now()
        )
        db.add(sync_task)
        db.commit()
        db.refresh(sync_task)

        # 执行同步
        success = google_ads_service.sync_ad_groups(
            db,
            request.account_id,
            request.customer_id,
            task_id=sync_task.id
        )

        # 刷新任务状态
        db.refresh(sync_task)

        if not success:
            logger.error(f"Ad group sync failed for account {request.account_id}")

        return sync_task

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync ad groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/tasks/{task_id}", response_model=SyncTaskResponse)
async def get_sync_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    获取同步任务状态

    Args:
        task_id: 任务ID
        db: 数据库会话

    Returns:
        同步任务信息
    """
    try:
        task = db.query(SyncTask).filter(SyncTask.id == task_id).first()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return task

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns")
async def list_campaigns(
    account_id: int = Query(..., description="账户ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    获取推广活动列表

    Args:
        account_id: 账户ID
        skip: 跳过的记录数
        limit: 返回的最大记录数
        db: 数据库会话

    Returns:
        推广活动列表
    """
    try:
        campaigns = db.query(Campaign).filter(
            Campaign.account_id == account_id
        ).offset(skip).limit(limit).all()

        result = []
        for campaign in campaigns:
            result.append({
                "id": campaign.id,
                "campaign_id": campaign.campaign_id,
                "campaign_name": campaign.campaign_name,
                "campaign_status": campaign.campaign_status,
                "campaign_type": campaign.campaign_type,
                "advertising_channel_type": campaign.advertising_channel_type,
                "budget_amount": str(campaign.budget_amount) if campaign.budget_amount else None,
                "bidding_strategy_type": campaign.bidding_strategy_type,
                "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
                "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
                "serving_status": campaign.serving_status,
                "last_synced_at": campaign.last_synced_at.isoformat() if campaign.last_synced_at else None
            })

        return result

    except Exception as e:
        logger.error(f"Failed to list campaigns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ad-groups")
async def list_ad_groups(
    account_id: int = Query(..., description="账户ID"),
    campaign_id: Optional[int] = Query(None, description="推广活动ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    获取广告组列表

    Args:
        account_id: 账户ID
        campaign_id: 可选的推广活动ID
        skip: 跳过的记录数
        limit: 返回的最大记录数
        db: 数据库会话

    Returns:
        广告组列表
    """
    try:
        query = db.query(AdGroup).filter(AdGroup.account_id == account_id)

        if campaign_id:
            query = query.filter(AdGroup.campaign_id == campaign_id)

        ad_groups = query.offset(skip).limit(limit).all()

        result = []
        for ad_group in ad_groups:
            result.append({
                "id": ad_group.id,
                "campaign_id": ad_group.campaign_id,
                "ad_group_id": ad_group.ad_group_id,
                "ad_group_name": ad_group.ad_group_name,
                "ad_group_status": ad_group.ad_group_status,
                "ad_group_type": ad_group.ad_group_type,
                "cpc_bid_micros": ad_group.cpc_bid_micros,
                "cpm_bid_micros": ad_group.cpm_bid_micros,
                "target_cpa_micros": ad_group.target_cpa_micros,
                "last_synced_at": ad_group.last_synced_at.isoformat() if ad_group.last_synced_at else None
            })

        return result

    except Exception as e:
        logger.error(f"Failed to list ad groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
