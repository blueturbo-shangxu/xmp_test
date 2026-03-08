"""
API routes for managing accounts and sync tasks
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.sql import get_db
from src.sql import GoogleAdAccount, GoogleCampaign, GoogleAdGroup, SyncTask, OAuthToken
from src.services import GoogleAdsService
from src.middleware.token_verify import JWTBearer
from src.middleware import get_request_uuid_dependency

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
    sync_enabled: bool
    has_valid_token: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SyncTaskResponse(BaseModel):
    id: int
    platform: str
    account_key: str
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
    db: Session = Depends(get_db),
    user_id: str = Depends(JWTBearer()),  # JWT认证
    req_uuid: str = Depends(get_request_uuid_dependency)
):
    """
    获取账户列表 (需要JWT认证)

    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        db: 数据库会话
        user_id: 用户ID
        req_uuid: 请求UUID

    Returns:
        账户列表
    """
    try:
        logger.info(f"[{req_uuid}] User {user_id} is listing accounts")

        accounts = db.query(GoogleAdAccount).offset(skip).limit(limit).all()

        # 检查每个账户的token状态
        result = []
        for account in accounts:
            token = db.query(OAuthToken).filter(
                OAuthToken.platform == 'google',
                OAuthToken.account_key == account.customer_id,
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
                "sync_enabled": account.sync_enabled,
                "has_valid_token": token is not None and not token.is_expired,
                "created_at": account.created_at
            }
            result.append(account_dict)

        return result

    except Exception as e:
        logger.error(f"[{req_uuid}] Failed to list accounts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{customer_id}", response_model=AccountResponse)
async def get_account(
    customer_id: str,
    db: Session = Depends(get_db),
    req_uuid: str = Depends(get_request_uuid_dependency)
):
    """
    获取单个账户详情

    Args:
        customer_id: Google Ads Customer ID
        db: 数据库会话
        req_uuid: 请求UUID

    Returns:
        账户详情
    """
    try:
        account = db.query(GoogleAdAccount).filter(
            GoogleAdAccount.customer_id == customer_id
        ).first()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        token = db.query(OAuthToken).filter(
            OAuthToken.platform == 'google',
            OAuthToken.account_key == account.customer_id,
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
            "sync_enabled": account.sync_enabled,
            "has_valid_token": token is not None and not token.is_expired,
            "created_at": account.created_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{req_uuid}] Failed to get account: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class SyncAccountsByTokenRequest(BaseModel):
    token_id: int


class SyncAccountsByTokenResponse(BaseModel):
    token_id: int
    total_accounts: int
    synced_accounts: int
    failed_accounts: int
    accounts: List[dict]
    errors: List[str]


@router.post("/sync/accounts-by-token", response_model=SyncAccountsByTokenResponse)
async def sync_accounts_by_token(
    request: SyncAccountsByTokenRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(JWTBearer()),  # JWT认证
    req_uuid: str = Depends(get_request_uuid_dependency)
):
    """
    根据OAuth Token ID同步该授权账号下的所有可访问广告账号 (需要JWT认证)

    Args:
        request: 同步请求，包含token_id
        db: 数据库会话
        user_id: 用户ID
        req_uuid: 请求UUID

    Returns:
        同步结果，包含成功和失败的账号信息
    """
    try:
        logger.info(f"[{req_uuid}] User {user_id} is syncing accounts by token {request.token_id}")

        # 创建服务实例并执行同步
        service = GoogleAdsService(request.token_id)
        result = service.sync_all_accounts(db)

        # 转换结果格式以匹配响应模型
        response = {
            "token_id": result["token_id"],
            "total_accounts": result["total"],
            "synced_accounts": result["synced"],
            "failed_accounts": result["failed"],
            "accounts": result["accounts"],
            "errors": result["errors"]
        }

        if result["failed"] > 0:
            logger.warning(
                f"[{req_uuid}] Account sync completed with errors: "
                f"synced={result['synced']}, failed={result['failed']}"
            )
        else:
            logger.info(
                f"[{req_uuid}] Account sync completed successfully: "
                f"synced={result['synced']}"
            )

        return response

    except ValueError as e:
        logger.error(f"[{req_uuid}] Invalid token: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[{req_uuid}] Failed to sync accounts by token: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class SyncWithTokenRequest(BaseModel):
    token_id: int
    customer_id: str
    task_type: str = "CAMPAIGNS"  # CAMPAIGNS, AD_GROUPS


@router.post("/sync/campaigns", response_model=SyncTaskResponse)
async def sync_campaigns(
    request: SyncWithTokenRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(JWTBearer()),  # JWT认证
    req_uuid: str = Depends(get_request_uuid_dependency)
):
    """
    同步推广活动数据 (需要JWT认证)

    Args:
        request: 同步任务请求，包含 token_id 和 customer_id
        db: 数据库会话
        user_id: 用户ID
        req_uuid: 请求UUID

    Returns:
        同步任务信息
    """
    try:
        logger.info(f"[{req_uuid}] User {user_id} is syncing campaigns for {request.customer_id}")

        # 验证账户存在
        account = db.query(GoogleAdAccount).filter(
            GoogleAdAccount.customer_id == request.customer_id
        ).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # 创建同步任务
        sync_task = SyncTask(
            platform='google',
            account_key=request.customer_id,
            task_type='CAMPAIGNS',
            status='RUNNING',
            started_at=datetime.now()
        )
        db.add(sync_task)
        db.commit()
        db.refresh(sync_task)

        # 创建服务实例并执行同步
        service = GoogleAdsService(request.token_id)
        success = service.sync_campaigns(db, request.customer_id, sync_task.id)

        # 刷新任务状态
        db.refresh(sync_task)

        if not success:
            logger.error(f"[{req_uuid}] Campaign sync failed for account {request.customer_id}")

        return sync_task

    except ValueError as e:
        logger.error(f"[{req_uuid}] Invalid token: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{req_uuid}] Failed to sync campaigns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/ad-groups", response_model=SyncTaskResponse)
async def sync_ad_groups(
    request: SyncWithTokenRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(JWTBearer()),  # JWT认证
    req_uuid: str = Depends(get_request_uuid_dependency)
):
    """
    同步广告组数据 (需要JWT认证)

    Args:
        request: 同步任务请求，包含 token_id 和 customer_id
        db: 数据库会话
        user_id: 用户ID
        req_uuid: 请求UUID

    Returns:
        同步任务信息
    """
    try:
        logger.info(f"[{req_uuid}] User {user_id} is syncing ad groups for {request.customer_id}")

        # 验证账户存在
        account = db.query(GoogleAdAccount).filter(
            GoogleAdAccount.customer_id == request.customer_id
        ).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # 创建同步任务
        sync_task = SyncTask(
            platform='google',
            account_key=request.customer_id,
            task_type='AD_GROUPS',
            status='RUNNING',
            started_at=datetime.now()
        )
        db.add(sync_task)
        db.commit()
        db.refresh(sync_task)

        # 创建服务实例并执行同步
        service = GoogleAdsService(request.token_id)
        success = service.sync_ad_groups(db, request.customer_id, task_id=sync_task.id)

        # 刷新任务状态
        db.refresh(sync_task)

        if not success:
            logger.error(f"[{req_uuid}] Ad group sync failed for account {request.customer_id}")

        return sync_task

    except ValueError as e:
        logger.error(f"[{req_uuid}] Invalid token: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{req_uuid}] Failed to sync ad groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/tasks/{task_id}", response_model=SyncTaskResponse)
async def get_sync_task(
    task_id: int,
    db: Session = Depends(get_db),
    req_uuid: str = Depends(get_request_uuid_dependency)
):
    """
    获取同步任务状态

    Args:
        task_id: 任务ID
        db: 数据库会话
        req_uuid: 请求UUID

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
        logger.error(f"[{req_uuid}] Failed to get sync task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns")
async def list_campaigns(
    customer_id: str = Query(..., description="Google Ads Customer ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    req_uuid: str = Depends(get_request_uuid_dependency)
):
    """
    获取推广活动列表

    Args:
        customer_id: Google Ads Customer ID
        skip: 跳过的记录数
        limit: 返回的最大记录数
        db: 数据库会话
        req_uuid: 请求UUID

    Returns:
        推广活动列表
    """
    try:
        logger.info(f"[{req_uuid}] Listing campaigns for customer {customer_id}")

        campaigns = db.query(GoogleCampaign).filter(
            GoogleCampaign.customer_id == customer_id
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
        logger.error(f"[{req_uuid}] Failed to list campaigns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ad-groups")
async def list_ad_groups(
    customer_id: str = Query(..., description="Google Ads Customer ID"),
    campaign_id: Optional[int] = Query(None, description="推广活动ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    req_uuid: str = Depends(get_request_uuid_dependency)
):
    """
    获取广告组列表

    Args:
        customer_id: Google Ads Customer ID
        campaign_id: 可选的推广活动ID
        skip: 跳过的记录数
        limit: 返回的最大记录数
        db: 数据库会话
        req_uuid: 请求UUID

    Returns:
        广告组列表
    """
    try:
        logger.info(f"[{req_uuid}] Listing ad groups for customer {customer_id}")

        query = db.query(GoogleAdGroup).filter(
            GoogleAdGroup.customer_id == customer_id
        )

        if campaign_id:
            query = query.filter(GoogleAdGroup.campaign_id == campaign_id)

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
        logger.error(f"[{req_uuid}] Failed to list ad groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
