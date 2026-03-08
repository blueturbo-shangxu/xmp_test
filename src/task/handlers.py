"""
Task Handlers
具体的任务处理器实现
"""
import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

from src.task.base import BaseTask, TaskType, TaskResult, TaskNonRetryableError
from src.sql.database import get_db_context
from src.services.google.account_service import GoogleAdsAccountService
from src.services.google.campaign_service import GoogleAdsCampaignService
from src.services.google.ad_group_service import GoogleAdsAdGroupService
from src.services.google.ad_service import GoogleAdsAdService

logger = logging.getLogger(__name__)


class GoogleAccountSyncHandler(BaseTask):
    """
    Google 账户同步处理器
    """

    def __init__(self, task_type: TaskType = TaskType.SYNC_GOOGLE_ACCOUNTS):
        super().__init__(task_type)

    def execute(
        self,
        task_id: int,
        platform: str,
        account_key: str,
        sync_params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> TaskResult:
        """
        执行账户同步

        Args:
            task_id: 任务ID
            platform: 平台
            account_key: token_id
            sync_params: 同步参数

        Returns:
            TaskResult
        """
        self.logger.info(f"Starting Google account sync, token_id={account_key}")
        result = TaskResult(success=False, task_id=task_id)

        try:
            token_id = int(account_key)

            # 创建服务实例
            service = GoogleAdsAccountService(token_id=token_id)

            # 执行同步
            with get_db_context() as db:
                sync_result = service.sync_all_accounts(db)

            result.success = True
            result.total_records = sync_result.get("total", 0)
            result.processed_records = sync_result.get("synced", 0)
            result.failed_records = sync_result.get("failed", 0)
            result.data = sync_result

            if sync_result.get("errors"):
                result.error_message = "; ".join(sync_result["errors"][:5])

        except Exception as e:
            result.error_message = str(e)
            result.error_traceback = traceback.format_exc()
            self.logger.error(f"Google account sync failed: {e}")

        return result


class GoogleCampaignSyncHandler(BaseTask):
    """
    Google Campaign 同步处理器
    """

    def __init__(self, task_type: TaskType = TaskType.SYNC_GOOGLE_CAMPAIGNS):
        super().__init__(task_type)

    def execute(
        self,
        task_id: int,
        platform: str,
        account_key: str,
        sync_params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> TaskResult:
        """
        执行 Campaign 同步

        Args:
            task_id: 任务ID
            platform: 平台
            account_key: token_id
            sync_params: 同步参数 (必须包含 customer_id)

        Returns:
            TaskResult
        """
        self.logger.info(f"Starting Google campaign sync, token_id={account_key}")
        result = TaskResult(success=False, task_id=task_id)

        try:
            token_id = int(account_key)

            # 从 sync_params 获取 customer_id
            if not sync_params or not sync_params.get("customer_id"):
                raise TaskNonRetryableError("customer_id is required in sync_params")

            customer_id = sync_params["customer_id"]

            # 创建服务并执行同步
            service = GoogleAdsCampaignService(token_id=token_id)
            service.set_customer_id(customer_id)

            with get_db_context() as db:
                sync_result = service.sync_campaigns(db, customer_id)

            result.success = True
            result.total_records = sync_result.get("total", 0)
            result.processed_records = sync_result.get("synced", 0)
            result.failed_records = sync_result.get("failed", 0)
            result.data = sync_result

        except TaskNonRetryableError:
            raise
        except Exception as e:
            result.error_message = str(e)
            result.error_traceback = traceback.format_exc()
            self.logger.error(f"Google campaign sync failed: {e}")

        return result


class GoogleAdGroupSyncHandler(BaseTask):
    """
    Google AdGroup 同步处理器
    """

    def __init__(self, task_type: TaskType = TaskType.SYNC_GOOGLE_AD_GROUPS):
        super().__init__(task_type)

    def execute(
        self,
        task_id: int,
        platform: str,
        account_key: str,
        sync_params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> TaskResult:
        """
        执行 AdGroup 同步

        Args:
            task_id: 任务ID
            platform: 平台
            account_key: token_id
            sync_params: 同步参数 (必须包含 customer_id，可选 campaign_id)

        Returns:
            TaskResult
        """
        self.logger.info(f"Starting Google ad group sync, token_id={account_key}")
        result = TaskResult(success=False, task_id=task_id)

        try:
            token_id = int(account_key)

            # 从 sync_params 获取 customer_id
            if not sync_params or not sync_params.get("customer_id"):
                raise TaskNonRetryableError("customer_id is required in sync_params")

            customer_id = sync_params["customer_id"]
            campaign_id = sync_params.get("campaign_id")

            # 创建服务并执行同步
            service = GoogleAdsAdGroupService(token_id=token_id)
            service.set_customer_id(customer_id)

            with get_db_context() as db:
                if campaign_id:
                    sync_result = service.sync_ad_groups_by_campaign(
                        db, customer_id, campaign_id
                    )
                else:
                    sync_result = service.sync_all_ad_groups(db, customer_id)

            result.success = True
            result.total_records = sync_result.get("total", 0)
            result.processed_records = sync_result.get("synced", 0)
            result.failed_records = sync_result.get("failed", 0)
            result.data = sync_result

        except TaskNonRetryableError:
            raise
        except Exception as e:
            result.error_message = str(e)
            result.error_traceback = traceback.format_exc()
            self.logger.error(f"Google ad group sync failed: {e}")

        return result


class GoogleAdSyncHandler(BaseTask):
    """
    Google Ad 同步处理器
    """

    def __init__(self, task_type: TaskType = TaskType.SYNC_GOOGLE_ADS):
        super().__init__(task_type)

    def execute(
        self,
        task_id: int,
        platform: str,
        account_key: str,
        sync_params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> TaskResult:
        """
        执行 Ad 同步

        Args:
            task_id: 任务ID
            platform: 平台
            account_key: token_id
            sync_params: 同步参数 (必须包含 customer_id，可选 campaign_id, ad_group_id)

        Returns:
            TaskResult
        """
        self.logger.info(f"Starting Google ad sync, token_id={account_key}")
        result = TaskResult(success=False, task_id=task_id)

        try:
            token_id = int(account_key)

            # 从 sync_params 获取 customer_id
            if not sync_params or not sync_params.get("customer_id"):
                raise TaskNonRetryableError("customer_id is required in sync_params")

            customer_id = sync_params["customer_id"]
            campaign_id = sync_params.get("campaign_id")
            ad_group_id = sync_params.get("ad_group_id")

            # 创建服务并执行同步
            service = GoogleAdsAdService(token_id=token_id)
            service.set_customer_id(customer_id)

            with get_db_context() as db:
                if ad_group_id:
                    sync_result = service.sync_ads_by_ad_group(
                        db, customer_id, ad_group_id
                    )
                elif campaign_id:
                    sync_result = service.sync_ads_by_campaign(
                        db, customer_id, campaign_id
                    )
                else:
                    sync_result = service.sync_all_ads(db, customer_id)

            result.success = True
            result.total_records = sync_result.get("total", 0)
            result.processed_records = sync_result.get("synced", 0)
            result.failed_records = sync_result.get("failed", 0)
            result.data = sync_result

        except TaskNonRetryableError:
            raise
        except Exception as e:
            result.error_message = str(e)
            result.error_traceback = traceback.format_exc()
            self.logger.error(f"Google ad sync failed: {e}")

        return result
