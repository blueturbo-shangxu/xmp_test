"""
Google Ads Service Facade
外观模式，整合所有 Google Ads 服务，提供统一的调用入口
"""
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from src.services.google.account_service import GoogleAdsAccountService
from src.services.google.campaign_service import GoogleAdsCampaignService
from src.services.google.ad_group_service import GoogleAdsAdGroupService
from src.services.google.ad_service import GoogleAdsAdService

logger = logging.getLogger(__name__)


class GoogleAdsServiceFacade:
    """
    Google Ads 服务外观类

    整合 Account、Campaign、AdGroup、Ad 等服务，提供统一的调用入口
    """

    def __init__(self, token_id: int, login_customer_id: Optional[str] = None):
        """
        初始化服务外观

        Args:
            token_id: OAuthToken 的 ID
            login_customer_id: 可选的 Manager 账户 ID（用于访问子账户）
        """
        self.token_id = token_id
        self.login_customer_id = login_customer_id

        # 初始化各级服务
        self._account_service: Optional[GoogleAdsAccountService] = None
        self._campaign_service: Optional[GoogleAdsCampaignService] = None
        self._ad_group_service: Optional[GoogleAdsAdGroupService] = None
        self._ad_service: Optional[GoogleAdsAdService] = None

        logger.info(f"GoogleAdsServiceFacade initialized with token_id={token_id}, login_customer_id={login_customer_id}")

    # ==================== 服务实例访问（延迟初始化）====================

    @property
    def account(self) -> GoogleAdsAccountService:
        """获取账户服务实例"""
        if self._account_service is None:
            self._account_service = GoogleAdsAccountService(self.token_id, self.login_customer_id)
        return self._account_service

    @property
    def campaign(self) -> GoogleAdsCampaignService:
        """获取 Campaign 服务实例"""
        if self._campaign_service is None:
            self._campaign_service = GoogleAdsCampaignService(self.token_id, self.login_customer_id)
        return self._campaign_service

    @property
    def ad_group(self) -> GoogleAdsAdGroupService:
        """获取 AdGroup 服务实例"""
        if self._ad_group_service is None:
            self._ad_group_service = GoogleAdsAdGroupService(self.token_id, self.login_customer_id)
        return self._ad_group_service

    @property
    def ad(self) -> GoogleAdsAdService:
        """获取 Ad 服务实例"""
        if self._ad_service is None:
            self._ad_service = GoogleAdsAdService(self.token_id, self.login_customer_id)
        return self._ad_service

    # ==================== 便捷方法：账户操作 ====================

    def get_accessible_customers(self) -> List[str]:
        """获取可访问的客户ID列表"""
        return self.account.get_accessible_customers()

    def get_account_info(self, customer_id: str) -> Optional[Dict]:
        """获取账户信息"""
        return self.account.get_account_info(customer_id)

    def sync_all_accounts(self, db: Session) -> Dict:
        """同步所有账户"""
        return self.account.sync_all_accounts(db)

    # ==================== 便捷方法：Campaign 操作 ====================

    def get_campaigns(
        self,
        customer_id: str,
        status_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """获取 Campaign 列表"""
        return self.campaign.get_campaigns(customer_id, status_filter)

    def sync_campaigns(
        self,
        db: Session,
        customer_id: str,
        task_id: Optional[int] = None
    ) -> bool:
        """同步 Campaign 数据"""
        return self.campaign.sync_campaigns(db, customer_id, task_id)

    def create_campaign(
        self,
        customer_id: str,
        name: str,
        budget_amount_micros: int,
        **kwargs
    ) -> Optional[str]:
        """创建 Campaign"""
        return self.campaign.create_campaign(customer_id, name, budget_amount_micros, **kwargs)

    # ==================== 便捷方法：AdGroup 操作 ====================

    def get_ad_groups(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        status_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """获取 AdGroup 列表"""
        return self.ad_group.get_ad_groups(customer_id, campaign_id, status_filter)

    def sync_ad_groups(
        self,
        db: Session,
        customer_id: str,
        campaign_id: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> bool:
        """同步 AdGroup 数据"""
        return self.ad_group.sync_ad_groups(db, customer_id, campaign_id, task_id)

    def create_ad_group(
        self,
        customer_id: str,
        campaign_id: str,
        name: str,
        **kwargs
    ) -> Optional[str]:
        """创建 AdGroup"""
        return self.ad_group.create_ad_group(customer_id, campaign_id, name, **kwargs)

    # ==================== 便捷方法：Ad 操作 ====================

    def get_ads(
        self,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        status_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """获取 Ad 列表"""
        return self.ad.get_ads(customer_id, ad_group_id, status_filter)

    def sync_ads(
        self,
        db: Session,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> bool:
        """同步 Ad 数据"""
        return self.ad.sync_ads(db, customer_id, ad_group_id, task_id)

    def create_responsive_search_ad(
        self,
        customer_id: str,
        ad_group_id: str,
        headlines: List[str],
        descriptions: List[str],
        final_urls: List[str],
        **kwargs
    ) -> Optional[str]:
        """创建响应式搜索广告"""
        return self.ad.create_responsive_search_ad(
            customer_id, ad_group_id, headlines, descriptions, final_urls, **kwargs
        )

    # ==================== 批量同步方法 ====================

    def sync_all(self, db: Session, customer_id: str) -> Dict:
        """
        完整同步：账户 -> Campaign -> AdGroup -> Ad

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID

        Returns:
            Dict: 同步结果汇总
        """
        result = {
            "customer_id": customer_id,
            "accounts": {"success": False, "error": None},
            "campaigns": {"success": False, "error": None},
            "ad_groups": {"success": False, "error": None},
            "ads": {"success": False, "error": None}
        }

        try:
            # 1. 同步账户
            account_result = self.account._sync_single_account(db, customer_id)
            result["accounts"]["success"] = account_result.get("success", False)
            if not result["accounts"]["success"]:
                result["accounts"]["error"] = account_result.get("error")
                return result

            # 2. 同步 Campaigns
            result["campaigns"]["success"] = self.campaign.sync_campaigns(db, customer_id)
            if not result["campaigns"]["success"]:
                result["campaigns"]["error"] = "Campaign sync failed"
                return result

            # 3. 同步 AdGroups
            result["ad_groups"]["success"] = self.ad_group.sync_ad_groups(db, customer_id)
            if not result["ad_groups"]["success"]:
                result["ad_groups"]["error"] = "AdGroup sync failed"
                return result

            # 4. 同步 Ads
            result["ads"]["success"] = self.ad.sync_ads(db, customer_id)
            if not result["ads"]["success"]:
                result["ads"]["error"] = "Ad sync failed"

            logger.info(f"Full sync completed for customer {customer_id}")
            return result

        except Exception as e:
            logger.error(f"Full sync failed for customer {customer_id}: {e}")
            return result

    def sync_campaign_tree(
        self,
        db: Session,
        customer_id: str,
        campaign_id: str
    ) -> Dict:
        """
        同步单个 Campaign 及其下的 AdGroup 和 Ad

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID
            campaign_id: Campaign ID

        Returns:
            Dict: 同步结果汇总
        """
        result = {
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "ad_groups": {"success": False, "error": None},
            "ads": {"success": False, "error": None}
        }

        try:
            # 1. 同步该 Campaign 下的 AdGroups
            result["ad_groups"]["success"] = self.ad_group.sync_ad_groups(
                db, customer_id, campaign_id
            )
            if not result["ad_groups"]["success"]:
                result["ad_groups"]["error"] = "AdGroup sync failed"
                return result

            # 2. 同步该 Campaign 下所有 AdGroup 的 Ads
            ad_groups = self.ad_group.get_ad_groups(customer_id, campaign_id)
            ads_success = True
            for ag in ad_groups:
                if not self.ad.sync_ads(db, customer_id, ag['ad_group_id']):
                    ads_success = False

            result["ads"]["success"] = ads_success
            if not ads_success:
                result["ads"]["error"] = "Some ads sync failed"

            logger.info(f"Campaign tree sync completed for campaign {campaign_id}")
            return result

        except Exception as e:
            logger.error(f"Campaign tree sync failed: {e}")
            return result

    # ==================== 状态更新便捷方法 ====================

    def update_campaign_status(
        self,
        customer_id: str,
        campaign_id: str,
        status: str
    ) -> bool:
        """更新 Campaign 状态"""
        return self.campaign.update_campaign_status(customer_id, campaign_id, status)

    def update_ad_group_status(
        self,
        customer_id: str,
        ad_group_id: str,
        status: str
    ) -> bool:
        """更新 AdGroup 状态"""
        return self.ad_group.update_ad_group_status(customer_id, ad_group_id, status)

    def update_ad_status(
        self,
        customer_id: str,
        ad_group_id: str,
        ad_id: str,
        status: str
    ) -> bool:
        """更新 Ad 状态"""
        return self.ad.update_ad_status(customer_id, ad_group_id, ad_id, status)

    def refresh_all_clients(self):
        """刷新所有服务的 client（token 更新后调用）"""
        if self._account_service:
            self._account_service.refresh_client()
        if self._campaign_service:
            self._campaign_service.refresh_client()
        if self._ad_group_service:
            self._ad_group_service.refresh_client()
        if self._ad_service:
            self._ad_service.refresh_client()


# 类型别名，方便导入
GoogleAdsService = GoogleAdsServiceFacade
