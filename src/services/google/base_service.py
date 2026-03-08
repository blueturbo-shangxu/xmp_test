"""
Google Ads API Base Service
基础服务类，提供通用的API调用和工具方法
"""
import logging
from typing import List, Dict, Optional, Any
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from sqlalchemy.orm import Session
from datetime import datetime

from src.core import settings
from src.sql import get_db_context, OAuthToken, SyncTask, GoogleAdAccount

logger = logging.getLogger(__name__)


class GoogleAdsBaseService:
    """
    Google Ads API 基础服务类

    提供通用的初始化、API调用、错误处理等功能
    """

    def __init__(self, token_id: int, login_customer_id: Optional[str] = None):
        """
        初始化基础服务

        Args:
            token_id: OAuthToken 的 ID
            login_customer_id: 可选的 Manager 账户 ID（用于访问子账户）

        Raises:
            ValueError: token_id 无效或 token 不存在/无效
        """
        self.token_id = token_id
        self.login_customer_id = login_customer_id
        self.developer_token = settings.GOOGLE_ADS_DEVELOPER_TOKEN
        self.api_version = settings.GOOGLE_ADS_API_VERSION

        # 当前设置的 customer_id（用于缓存判断）
        self._current_customer_id: Optional[str] = None

        # 从数据库加载 token 信息并缓存必要数据
        self._refresh_token: Optional[str] = None
        self._load_token_info()

        # 初始化 Google Ads Client
        self.client = self._create_client()

        logger.info(f"{self.__class__.__name__} initialized with token_id={token_id}, login_customer_id={login_customer_id}")

    # ==================== Token 和 Client 管理 ====================

    def _load_token_info(self):
        """从数据库加载 token 信息，缓存必要数据"""
        with get_db_context() as db:
            token = db.query(OAuthToken).filter(
                OAuthToken.id == self.token_id,
                OAuthToken.platform == 'google'
            ).first()

            if not token:
                raise ValueError(f"OAuthToken with id={self.token_id} not found")

            if not token.is_valid:
                raise ValueError(f"OAuthToken with id={self.token_id} is invalid")

            if not token.refresh_token:
                raise ValueError(f"OAuthToken with id={self.token_id} has no refresh_token")

            # 缓存 refresh_token（用于创建 client）
            self._refresh_token = token.refresh_token

    def _create_client(self, with_login_customer_id: bool = True) -> GoogleAdsClient:
        """创建 Google Ads Client"""
        config = {
            "developer_token": self.developer_token,
            "use_proto_plus": True,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": self._refresh_token,
        }

        if with_login_customer_id:
            # 优先使用实例指定的 login_customer_id，否则使用配置中的
            login_cid = self.login_customer_id or settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID
            if login_cid:
                config["login_customer_id"] = login_cid.replace('-', '')

        return GoogleAdsClient.load_from_dict(config, version=self.api_version)

    def refresh_client(self):
        """刷新 token 信息并重建 client（当 token 被更新时调用）"""
        self._load_token_info()
        self.client = self._create_client()

    def set_customer_id(self, customer_id: Optional[str] = None):
        """
        设置当前操作的 customer_id，并根据账户的 manager_customer_id 自动设置 login_customer_id

        Args:
            customer_id: Google Ads Customer ID，为空则清除 login_customer_id

        说明:
            - 如果 customer_id 与当前设置相同，跳过处理
            - 查询数据库获取账户信息
            - 如果账户有 manager_customer_id，则设置为 login_customer_id
            - 重新构建 client
        """
        cid = customer_id.replace('-', '') if customer_id else None

        # 如果 customer_id 没有变化，跳过处理
        if cid == self._current_customer_id:
            return

        if not cid:
            # 清除 login_customer_id 并重建 client
            self._current_customer_id = None
            self.login_customer_id = None
            self.client = self._create_client()
            logger.info("Cleared login_customer_id and rebuilt client")
            return

        # 更新当前 customer_id
        self._current_customer_id = cid

        with get_db_context() as db:
            account = db.query(GoogleAdAccount).filter(
                GoogleAdAccount.customer_id == cid
            ).first()

            if account and account.manager_customer_id:
                self.login_customer_id = account.manager_customer_id
                logger.info(f"Set login_customer_id to {account.manager_customer_id} for customer {cid}")
            else:
                self.login_customer_id = None
                logger.info(f"No manager_customer_id found for customer {cid}, cleared login_customer_id")

        # 重建 client
        self.client = self._create_client()

    # ==================== API 调用方法 ====================

    def _execute_query(self, customer_id: str, query: str) -> list:
        """执行 GAQL 查询"""
        ga_service = self.client.get_service("GoogleAdsService")
        return list(ga_service.search(customer_id=customer_id, query=query))

    def _execute_mutate(self, customer_id: str, operations: List[Any], service_name: str) -> Any:
        """
        执行 mutate 操作（创建/更新/删除）

        Args:
            customer_id: Google Ads Customer ID
            operations: 操作列表
            service_name: 服务名称（如 "CampaignService"）

        Returns:
            mutate 响应
        """
        service = self.client.get_service(service_name)
        return service.mutate(customer_id=customer_id, operations=operations)

    # ==================== 错误处理 ====================

    def _handle_api_error(self, ex: GoogleAdsException, context: str) -> str:
        """处理 Google Ads API 错误，返回错误信息"""
        error_details = [f"Google Ads API error in {context}: {ex}"]
        for error in ex.failure.errors:
            error_details.append(f"  Code: {error.error_code}, Message: {error.message}")
        error_msg = "\n".join(error_details)
        logger.error(error_msg)
        return error_msg

    # ==================== 同步任务管理 ====================

    def _update_sync_task(
        self,
        db: Session,
        task_id: int,
        status: str,
        start_time: datetime,
        total: int = 0,
        processed: int = 0,
        failed: int = 0,
        error_message: str = None
    ):
        """更新同步任务状态"""
        task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
        if task:
            task.status = status
            task.total_records = total
            task.processed_records = processed
            task.failed_records = failed
            task.completed_at = datetime.now()
            task.duration_seconds = int((datetime.now() - start_time).total_seconds())
            if error_message:
                task.error_message = error_message
            db.commit()

    def _create_sync_task(
        self,
        db: Session,
        customer_id: str,
        task_type: str,
        entity_id: Optional[str] = None
    ) -> SyncTask:
        """
        创建同步任务记录

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID
            task_type: 任务类型（ACCOUNT, CAMPAIGN, AD_GROUP, AD）
            entity_id: 可选的实体ID

        Returns:
            SyncTask: 创建的任务记录
        """
        task = SyncTask(
            customer_id=customer_id.replace('-', ''),
            task_type=task_type,
            entity_id=entity_id,
            status='RUNNING',
            started_at=datetime.now()
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
