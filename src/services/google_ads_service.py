"""
Google Ads API Service
处理Google Ads API调用
"""
import logging
from typing import List, Dict, Optional
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from sqlalchemy.orm import Session
from datetime import datetime

from src.config import settings
from src.services.oauth_service import oauth_service
from src.models import GoogleAdAccount, GoogleCampaign, GoogleAdGroup, SyncTask

logger = logging.getLogger(__name__)


class GoogleAdsAPIService:
    """Google Ads API服务类"""

    def __init__(self):
        """初始化API服务"""
        self.developer_token = settings.GOOGLE_ADS_DEVELOPER_TOKEN
        self.api_version = settings.GOOGLE_ADS_API_VERSION

    def get_client(self, db: Session, customer_id: str) -> Optional[GoogleAdsClient]:
        """
        获取Google Ads客户端实例

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID (格式: 123-456-7890)

        Returns:
            Optional[GoogleAdsClient]: Google Ads客户端,失败返回None
        """
        try:
            # 获取有效凭据 (使用新的接口,传入customer_id)
            credentials = oauth_service.get_valid_credentials(db, customer_id)
            if not credentials:
                logger.error(f"Failed to get valid credentials for customer {customer_id}")
                return None

            # 构建客户端配置
            client_config = {
                "developer_token": self.developer_token,
                "use_proto_plus": True,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": credentials.refresh_token,
            }

            # 如果有登录客户ID,添加到配置
            if settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID:
                client_config["login_customer_id"] = settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID

            # 创建客户端
            client = GoogleAdsClient.load_from_dict(client_config, version=self.api_version)

            logger.info(f"Successfully created Google Ads client for customer {customer_id}")
            return client

        except Exception as e:
            logger.error(f"Failed to create Google Ads client: {str(e)}")
            return None

    def get_account_info(self, db: Session, customer_id: str) -> Optional[Dict]:
        """
        获取账户信息

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID (格式: 123-456-7890)

        Returns:
            Optional[Dict]: 账户信息字典
        """
        try:
            client = self.get_client(db, customer_id)
            if not client:
                return None

            ga_service = client.get_service("GoogleAdsService")

            # 构建查询
            query = """
                SELECT
                    customer.id,
                    customer.descriptive_name,
                    customer.currency_code,
                    customer.time_zone,
                    customer.manager,
                    customer.status
                FROM customer
                WHERE customer.id = '{customer_id}'
            """.format(customer_id=customer_id.replace('-', ''))

            # 执行查询
            response = ga_service.search(customer_id=customer_id, query=query)

            for row in response:
                customer = row.customer
                return {
                    'customer_id': customer_id,
                    'account_name': customer.descriptive_name,
                    'currency_code': customer.currency_code,
                    'timezone': customer.time_zone,
                    'account_type': 'MANAGER' if customer.manager else 'CLIENT',
                    'status': customer.status.name
                }

            return None

        except GoogleAdsException as ex:
            logger.error(f"Google Ads API error: {ex}")
            for error in ex.failure.errors:
                logger.error(f"\tError code: {error.error_code}")
                logger.error(f"\tError message: {error.message}")
            return None
        except Exception as e:
            logger.error(f"Failed to get account info: {str(e)}")
            return None

    def sync_campaigns(
        self,
        db: Session,
        customer_id: str,
        task_id: Optional[int] = None
    ) -> bool:
        """
        同步推广活动数据

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID (格式: 123-456-7890)
            task_id: 同步任务ID

        Returns:
            bool: 同步是否成功
        """
        start_time = datetime.now()

        try:
            # 获取账户记录
            account = db.query(GoogleAdAccount).filter(
                GoogleAdAccount.customer_id == customer_id
            ).first()
            if not account:
                raise ValueError(f"Google account {customer_id} not found in database")

            client = self.get_client(db, customer_id)
            if not client:
                raise ValueError("Failed to create Google Ads client")

            ga_service = client.get_service("GoogleAdsService")

            # 构建查询
            query = """
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    campaign.bidding_strategy_type,
                    campaign.campaign_budget,
                    campaign.start_date,
                    campaign.end_date,
                    campaign.serving_status
                FROM campaign
                ORDER BY campaign.id
            """

            # 执行查询
            response = ga_service.search(customer_id=customer_id, query=query)

            total_count = 0
            processed_count = 0
            failed_count = 0

            for row in response:
                total_count += 1
                campaign_data = row.campaign

                try:
                    # 查找或创建推广活动记录
                    campaign = db.query(GoogleCampaign).filter(
                        GoogleCampaign.customer_id == customer_id,
                        GoogleCampaign.campaign_id == str(campaign_data.id)
                    ).first()

                    if campaign:
                        # 更新现有记录
                        campaign.campaign_name = campaign_data.name
                        campaign.campaign_status = campaign_data.status.name
                        campaign.advertising_channel_type = campaign_data.advertising_channel_type.name
                        campaign.bidding_strategy_type = campaign_data.bidding_strategy_type.name
                        campaign.serving_status = campaign_data.serving_status.name
                        campaign.start_date = campaign_data.start_date
                        campaign.end_date = campaign_data.end_date if campaign_data.end_date else None
                        campaign.last_synced_at = datetime.now()
                    else:
                        # 创建新记录
                        campaign = GoogleCampaign(
                            account_id=account.id,
                            customer_id=customer_id,
                            campaign_id=str(campaign_data.id),
                            campaign_name=campaign_data.name,
                            campaign_status=campaign_data.status.name,
                            advertising_channel_type=campaign_data.advertising_channel_type.name,
                            bidding_strategy_type=campaign_data.bidding_strategy_type.name,
                            serving_status=campaign_data.serving_status.name,
                            start_date=campaign_data.start_date,
                            end_date=campaign_data.end_date if campaign_data.end_date else None,
                            last_synced_at=datetime.now()
                        )
                        db.add(campaign)

                    processed_count += 1

                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to process campaign {campaign_data.id}: {str(e)}")

            # 提交所有更改
            db.commit()

            # 更新同步任务状态
            if task_id:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if task:
                    task.status = 'COMPLETED'
                    task.total_records = total_count
                    task.processed_records = processed_count
                    task.failed_records = failed_count
                    task.completed_at = datetime.now()
                    task.duration_seconds = int((datetime.now() - start_time).total_seconds())
                    db.commit()

            logger.info(
                f"Campaign sync completed for customer {customer_id}: "
                f"total={total_count}, processed={processed_count}, failed={failed_count}"
            )
            return True

        except GoogleAdsException as ex:
            db.rollback()
            error_message = f"Google Ads API error: {ex}"
            for error in ex.failure.errors:
                error_message += f"\n\tError code: {error.error_code}, Message: {error.message}"

            logger.error(error_message)

            # 更新任务状态为失败
            if task_id:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if task:
                    task.status = 'FAILED'
                    task.error_message = error_message
                    task.completed_at = datetime.now()
                    task.duration_seconds = int((datetime.now() - start_time).total_seconds())
                    db.commit()

            return False

        except Exception as e:
            db.rollback()
            error_message = f"Failed to sync campaigns: {str(e)}"
            logger.error(error_message)

            if task_id:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if task:
                    task.status = 'FAILED'
                    task.error_message = error_message
                    task.completed_at = datetime.now()
                    task.duration_seconds = int((datetime.now() - start_time).total_seconds())
                    db.commit()

            return False

    def sync_ad_groups(
        self,
        db: Session,
        customer_id: str,
        campaign_id: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> bool:
        """
        同步广告组数据

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID (格式: 123-456-7890)
            campaign_id: 可选的推广活动ID,如果指定则只同步该推广活动的广告组
            task_id: 同步任务ID

        Returns:
            bool: 同步是否成功
        """
        start_time = datetime.now()

        try:
            # 获取账户记录
            account = db.query(GoogleAdAccount).filter(
                GoogleAdAccount.customer_id == customer_id
            ).first()
            if not account:
                raise ValueError(f"Google account {customer_id} not found in database")

            client = self.get_client(db, customer_id)
            if not client:
                raise ValueError("Failed to create Google Ads client")

            ga_service = client.get_service("GoogleAdsService")

            # 构建查询
            query = """
                SELECT
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    ad_group.type,
                    ad_group.campaign,
                    ad_group.cpc_bid_micros,
                    ad_group.cpm_bid_micros,
                    ad_group.target_cpa_micros
                FROM ad_group
            """

            if campaign_id:
                query += f" WHERE ad_group.campaign = 'customers/{customer_id}/campaigns/{campaign_id}'"

            query += " ORDER BY ad_group.id"

            # 执行查询
            response = ga_service.search(customer_id=customer_id, query=query)

            total_count = 0
            processed_count = 0
            failed_count = 0

            for row in response:
                total_count += 1
                ad_group_data = row.ad_group

                try:
                    # 提取campaign ID
                    campaign_resource = ad_group_data.campaign
                    campaign_id_from_resource = campaign_resource.split('/')[-1]

                    # 查找对应的campaign记录
                    campaign_record = db.query(GoogleCampaign).filter(
                        GoogleCampaign.customer_id == customer_id,
                        GoogleCampaign.campaign_id == campaign_id_from_resource
                    ).first()

                    if not campaign_record:
                        logger.warning(f"Campaign {campaign_id_from_resource} not found for ad group {ad_group_data.id}")
                        failed_count += 1
                        continue

                    # 查找或创建广告组记录
                    ad_group = db.query(GoogleAdGroup).filter(
                        GoogleAdGroup.customer_id == customer_id,
                        GoogleAdGroup.ad_group_id == str(ad_group_data.id)
                    ).first()

                    if ad_group:
                        # 更新现有记录
                        ad_group.ad_group_name = ad_group_data.name
                        ad_group.ad_group_status = ad_group_data.status.name
                        ad_group.ad_group_type = ad_group_data.type_.name
                        ad_group.cpc_bid_micros = ad_group_data.cpc_bid_micros
                        ad_group.cpm_bid_micros = ad_group_data.cpm_bid_micros
                        ad_group.target_cpa_micros = ad_group_data.target_cpa_micros
                        ad_group.last_synced_at = datetime.now()
                    else:
                        # 创建新记录
                        ad_group = GoogleAdGroup(
                            account_id=account.id,
                            campaign_id=campaign_record.id,
                            customer_id=customer_id,
                            ad_group_id=str(ad_group_data.id),
                            ad_group_name=ad_group_data.name,
                            ad_group_status=ad_group_data.status.name,
                            ad_group_type=ad_group_data.type_.name,
                            cpc_bid_micros=ad_group_data.cpc_bid_micros,
                            cpm_bid_micros=ad_group_data.cpm_bid_micros,
                            target_cpa_micros=ad_group_data.target_cpa_micros,
                            last_synced_at=datetime.now()
                        )
                        db.add(ad_group)

                    processed_count += 1

                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to process ad group {ad_group_data.id}: {str(e)}")

            # 提交所有更改
            db.commit()

            # 更新同步任务状态
            if task_id:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if task:
                    task.status = 'COMPLETED'
                    task.total_records = total_count
                    task.processed_records = processed_count
                    task.failed_records = failed_count
                    task.completed_at = datetime.now()
                    task.duration_seconds = int((datetime.now() - start_time).total_seconds())
                    db.commit()

            logger.info(
                f"Ad group sync completed for customer {customer_id}: "
                f"total={total_count}, processed={processed_count}, failed={failed_count}"
            )
            return True

        except GoogleAdsException as ex:
            db.rollback()
            error_message = f"Google Ads API error: {ex}"
            for error in ex.failure.errors:
                error_message += f"\n\tError code: {error.error_code}, Message: {error.message}"

            logger.error(error_message)

            if task_id:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if task:
                    task.status = 'FAILED'
                    task.error_message = error_message
                    task.completed_at = datetime.now()
                    task.duration_seconds = int((datetime.now() - start_time).total_seconds())
                    db.commit()

            return False

        except Exception as e:
            db.rollback()
            error_message = f"Failed to sync ad groups: {str(e)}"
            logger.error(error_message)

            if task_id:
                task = db.query(SyncTask).filter(SyncTask.id == task_id).first()
                if task:
                    task.status = 'FAILED'
                    task.error_message = error_message
                    task.completed_at = datetime.now()
                    task.duration_seconds = int((datetime.now() - start_time).total_seconds())
                    db.commit()

            return False


# 创建全局服务实例
google_ads_service = GoogleAdsAPIService()
