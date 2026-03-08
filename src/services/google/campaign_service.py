"""
Google Ads Campaign Service
处理 Google Ads Campaign 级别的操作
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from google.ads.googleads.errors import GoogleAdsException
from google.api_core import protobuf_helpers
from sqlalchemy.orm import Session

from src.sql import GoogleAdAccount, GoogleCampaign
from src.services.google.base_service import GoogleAdsBaseService

logger = logging.getLogger(__name__)


class GoogleAdsCampaignService(GoogleAdsBaseService):
    """
    Google Ads Campaign 服务类

    处理 Campaign 级别的查询、同步、创建、更新等操作
    """

    # ==================== 查询方法 ====================

    def get_campaigns(
        self,
        customer_id: str,
        status_filter: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取 Campaign 列表

        Args:
            customer_id: Google Ads Customer ID
            status_filter: 状态过滤（如 ['ENABLED', 'PAUSED']）
            limit: 返回数量限制

        Returns:
            List[Dict]: Campaign 列表
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.bidding_strategy_type,
                campaign.campaign_budget,
                campaign.serving_status
            FROM campaign
        """

        conditions = []
        if status_filter:
            status_str = ", ".join([f"'{s}'" for s in status_filter])
            conditions.append(f"campaign.status IN ({status_str})")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += f" ORDER BY campaign.id LIMIT {limit}"

        try:
            rows = self._execute_query(cid, query)
            campaigns = []
            for row in rows:
                campaign = row.campaign
                campaigns.append({
                    'campaign_id': str(campaign.id),
                    'campaign_name': campaign.name,
                    'status': campaign.status.name,
                    'channel_type': campaign.advertising_channel_type.name,
                    'bidding_strategy': campaign.bidding_strategy_type.name,
                    'serving_status': campaign.serving_status.name,
                })
            return campaigns

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"get_campaigns({customer_id})")
            return []
        except Exception as e:
            logger.error(f"Failed to get campaigns for {customer_id}: {e}")
            return []

    def get_campaign_by_id(self, customer_id: str, campaign_id: str) -> Optional[Dict]:
        """
        获取单个 Campaign 详情

        Args:
            customer_id: Google Ads Customer ID
            campaign_id: Campaign ID

        Returns:
            Campaign 信息字典或 None
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.bidding_strategy_type,
                campaign.campaign_budget,
                campaign.serving_status,
                campaign.optimization_score,
                campaign.url_custom_parameters
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """

        try:
            rows = self._execute_query(cid, query)
            if not rows:
                return None

            campaign = rows[0].campaign
            return {
                'campaign_id': str(campaign.id),
                'campaign_name': campaign.name,
                'status': campaign.status.name,
                'channel_type': campaign.advertising_channel_type.name,
                'bidding_strategy': campaign.bidding_strategy_type.name,
                'serving_status': campaign.serving_status.name,
            }

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"get_campaign_by_id({customer_id}, {campaign_id})")
            return None
        except Exception as e:
            logger.error(f"Failed to get campaign {campaign_id}: {e}")
            return None

    # ==================== 同步方法 ====================

    def sync_campaigns(
        self,
        db: Session,
        customer_id: str,
        task_id: Optional[int] = None
    ) -> bool:
        """
        同步 Campaign 数据到数据库

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID
            task_id: 可选的同步任务ID

        Returns:
            bool: 同步是否成功
        """
        start_time = datetime.now()
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        try:
            account = db.query(GoogleAdAccount).filter(
                GoogleAdAccount.customer_id == cid
            ).first()
            if not account:
                raise ValueError(f"Account {customer_id} not found in database")

            query = """
                SELECT
                    campaign.id, campaign.name, campaign.status,
                    campaign.advertising_channel_type, campaign.bidding_strategy_type,
                    campaign.campaign_budget, campaign.serving_status
                FROM campaign
                ORDER BY campaign.id
            """

            rows = self._execute_query(cid, query)
            total, processed, failed = len(rows), 0, 0

            for row in rows:
                try:
                    self._upsert_campaign(db, account.id, cid, row.campaign)
                    processed += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to process campaign {row.campaign.id}: {e}")
                    print(f"Failed to process campaign {row.campaign.id}: {e}")

            db.commit()

            if task_id:
                self._update_sync_task(db, task_id, 'COMPLETED', start_time, total, processed, failed)

            logger.info(f"Campaign sync for {customer_id}: total={total}, processed={processed}, failed={failed}")
            return True

        except GoogleAdsException as ex:
            db.rollback()
            error_msg = self._handle_api_error(ex, f"sync_campaigns({customer_id})")
            if task_id:
                self._update_sync_task(db, task_id, 'FAILED', start_time, error_message=error_msg)
            logger.error(f"Failed to sync campaigns for {customer_id}: {error_msg}")
            return False

        except Exception as e:
            db.rollback()
            error_msg = f"Failed to sync campaigns: {e}"
            logger.error(error_msg)
            if task_id:
                self._update_sync_task(db, task_id, 'FAILED', start_time, error_message=error_msg)
            return False

    def _upsert_campaign(
        self,
        db: Session,
        account_id: int,
        customer_id: str,
        campaign_data
    ) -> GoogleCampaign:
        """更新或插入 Campaign 记录"""
        campaign = db.query(GoogleCampaign).filter(
            GoogleCampaign.customer_id == customer_id,
            GoogleCampaign.campaign_id == str(campaign_data.id)
        ).first()

        data = {
            'campaign_name': campaign_data.name,
            'campaign_status': campaign_data.status.name,
            'advertising_channel_type': campaign_data.advertising_channel_type.name,
            'bidding_strategy_type': campaign_data.bidding_strategy_type.name,
            'serving_status': campaign_data.serving_status.name,
            'last_synced_at': datetime.now()
        }

        if campaign:
            for key, value in data.items():
                setattr(campaign, key, value)
        else:
            campaign = GoogleCampaign(
                account_id=account_id,
                customer_id=customer_id,
                campaign_id=str(campaign_data.id),
                **data
            )
            db.add(campaign)

        return campaign

    # ==================== 创建/更新方法 ====================

    def create_campaign(
        self,
        customer_id: str,
        name: str,
        budget_amount_micros: int,
        channel_type: str = "SEARCH",
        bidding_strategy: str = "MAXIMIZE_CONVERSIONS",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[str]:
        """
        创建新的 Campaign

        Args:
            customer_id: Google Ads Customer ID
            name: Campaign 名称
            budget_amount_micros: 预算金额（微单位，1元=1000000微单位）
            channel_type: 广告渠道类型
            bidding_strategy: 出价策略
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            str: 新创建的 Campaign ID 或 None
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        try:
            # 创建预算
            campaign_budget_service = self.client.get_service("CampaignBudgetService")
            campaign_budget_operation = self.client.get_type("CampaignBudgetOperation")
            campaign_budget = campaign_budget_operation.create
            campaign_budget.name = f"{name}_budget_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            campaign_budget.amount_micros = budget_amount_micros
            campaign_budget.delivery_method = self.client.enums.BudgetDeliveryMethodEnum.STANDARD

            budget_response = campaign_budget_service.mutate_campaign_budgets(
                customer_id=cid,
                operations=[campaign_budget_operation]
            )
            budget_resource_name = budget_response.results[0].resource_name

            # 创建 Campaign
            campaign_service = self.client.get_service("CampaignService")
            campaign_operation = self.client.get_type("CampaignOperation")
            campaign = campaign_operation.create
            campaign.name = name
            campaign.campaign_budget = budget_resource_name
            campaign.advertising_channel_type = getattr(
                self.client.enums.AdvertisingChannelTypeEnum, channel_type
            )
            campaign.status = self.client.enums.CampaignStatusEnum.PAUSED

            # 设置出价策略（参考官方示例，直接赋值类型对象）
            if bidding_strategy == "MAXIMIZE_CONVERSIONS":
                campaign.maximize_conversions = self.client.get_type("MaximizeConversions")
            elif bidding_strategy == "TARGET_CPA":
                target_cpa = self.client.get_type("TargetCpa")
                target_cpa.target_cpa_micros = budget_amount_micros // 10
                campaign.target_cpa = target_cpa
            elif bidding_strategy == "MANUAL_CPC":
                campaign.manual_cpc = self.client.get_type("ManualCpc")
            elif bidding_strategy == "TARGET_SPEND":
                campaign.target_spend = self.client.get_type("TargetSpend")

            # 网络设置
            campaign.network_settings.target_google_search = True
            campaign.network_settings.target_search_network = True
            campaign.network_settings.target_partner_search_network = False
            campaign.network_settings.target_content_network = False

            # 欧盟政治广告声明（必填字段，使用枚举值）
            campaign.contains_eu_political_advertising = (
                self.client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
            )

            # 设置日期（使用 start_date_time 格式）
            if start_date:
                campaign.start_date_time = f"{start_date.replace('-', '')} 00:00:00"
            if end_date:
                campaign.end_date_time = f"{end_date.replace('-', '')} 23:59:59"

            response = campaign_service.mutate_campaigns(
                customer_id=cid,
                operations=[campaign_operation]
            )

            campaign_resource_name = response.results[0].resource_name
            campaign_id = campaign_resource_name.split('/')[-1]

            logger.info(f"Created campaign {campaign_id} for customer {customer_id}")
            return campaign_id

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"create_campaign({customer_id})")
            return None
        except Exception as e:
            logger.error(f"Failed to create campaign: {e}")
            return None

    def update_campaign_status(
        self,
        customer_id: str,
        campaign_id: str,
        status: str
    ) -> bool:
        """
        更新 Campaign 状态

        Args:
            customer_id: Google Ads Customer ID
            campaign_id: Campaign ID
            status: 新状态 (ENABLED, PAUSED, REMOVED)

        Returns:
            bool: 是否更新成功
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        try:
            campaign_service = self.client.get_service("CampaignService")
            campaign_operation = self.client.get_type("CampaignOperation")
            campaign = campaign_operation.update

            campaign.resource_name = campaign_service.campaign_path(cid, campaign_id)
            campaign.status = getattr(self.client.enums.CampaignStatusEnum, status)

            # 使用 protobuf_helpers 生成 FieldMask
            self.client.copy_from(
                campaign_operation.update_mask,
                protobuf_helpers.field_mask(None, campaign._pb),
            )

            campaign_service.mutate_campaigns(
                customer_id=cid,
                operations=[campaign_operation]
            )

            logger.info(f"Updated campaign {campaign_id} status to {status}")
            return True

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"update_campaign_status({customer_id}, {campaign_id})")
            return False
        except Exception as e:
            logger.error(f"Failed to update campaign status: {e}")
            return False

    def update_campaign_name(
        self,
        customer_id: str,
        campaign_id: str,
        name: str
    ) -> bool:
        """
        更新 Campaign 名称

        Args:
            customer_id: Google Ads Customer ID
            campaign_id: Campaign ID
            name: 新名称

        Returns:
            bool: 是否更新成功
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        try:
            campaign_service = self.client.get_service("CampaignService")
            campaign_operation = self.client.get_type("CampaignOperation")
            campaign = campaign_operation.update

            campaign.resource_name = campaign_service.campaign_path(cid, campaign_id)
            campaign.name = name

            # 使用 protobuf_helpers 生成 FieldMask
            self.client.copy_from(
                campaign_operation.update_mask,
                protobuf_helpers.field_mask(None, campaign._pb),
            )

            campaign_service.mutate_campaigns(
                customer_id=cid,
                operations=[campaign_operation]
            )

            logger.info(f"Updated campaign {campaign_id} name to {name}")
            return True

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"update_campaign_name({customer_id}, {campaign_id})")
            return False
        except Exception as e:
            logger.error(f"Failed to update campaign name: {e}")
            return False

    # ==================== 数据库查询方法 ====================

    def get_campaigns_from_db(
        self,
        db: Session,
        customer_id: str,
        status_filter: Optional[List[str]] = None
    ) -> List[GoogleCampaign]:
        """
        从数据库获取 Campaign 列表

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID
            status_filter: 状态过滤

        Returns:
            List[GoogleCampaign]
        """
        cid = customer_id.replace('-', '')
        query = db.query(GoogleCampaign).filter(GoogleCampaign.customer_id == cid)

        if status_filter:
            query = query.filter(GoogleCampaign.campaign_status.in_(status_filter))

        return query.all()

    def get_campaign_from_db(
        self,
        db: Session,
        customer_id: str,
        campaign_id: str
    ) -> Optional[GoogleCampaign]:
        """
        从数据库获取单个 Campaign

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID
            campaign_id: Campaign ID

        Returns:
            GoogleCampaign 或 None
        """
        cid = customer_id.replace('-', '')
        return db.query(GoogleCampaign).filter(
            GoogleCampaign.customer_id == cid,
            GoogleCampaign.campaign_id == campaign_id
        ).first()
