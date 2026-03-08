"""
Google Ads AdGroup Service
处理 Google Ads AdGroup 级别的操作
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from google.ads.googleads.errors import GoogleAdsException
from sqlalchemy.orm import Session

from src.sql import GoogleAdAccount, GoogleCampaign, GoogleAdGroup
from src.services.google.base_service import GoogleAdsBaseService

logger = logging.getLogger(__name__)


class GoogleAdsAdGroupService(GoogleAdsBaseService):
    """
    Google Ads AdGroup 服务类

    处理 AdGroup 级别的查询、同步、创建、更新等操作
    """

    # ==================== 查询方法 ====================

    def get_ad_groups(
        self,
        customer_id: str,
        campaign_id: Optional[str] = None,
        status_filter: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取 AdGroup 列表

        Args:
            customer_id: Google Ads Customer ID
            campaign_id: 可选的 Campaign ID 过滤
            status_filter: 状态过滤（如 ['ENABLED', 'PAUSED']）
            limit: 返回数量限制

        Returns:
            List[Dict]: AdGroup 列表
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

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

        conditions = []
        if campaign_id:
            conditions.append(f"ad_group.campaign = 'customers/{cid}/campaigns/{campaign_id}'")
        if status_filter:
            status_str = ", ".join([f"'{s}'" for s in status_filter])
            conditions.append(f"ad_group.status IN ({status_str})")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += f" ORDER BY ad_group.id LIMIT {limit}"

        try:
            rows = self._execute_query(cid, query)
            ad_groups = []
            for row in rows:
                ag = row.ad_group
                campaign_id_str = ag.campaign.split('/')[-1]
                ad_groups.append({
                    'ad_group_id': str(ag.id),
                    'ad_group_name': ag.name,
                    'status': ag.status.name,
                    'type': ag.type_.name,
                    'campaign_id': campaign_id_str,
                    'cpc_bid_micros': ag.cpc_bid_micros,
                    'cpm_bid_micros': ag.cpm_bid_micros,
                    'target_cpa_micros': ag.target_cpa_micros
                })
            return ad_groups

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"get_ad_groups({customer_id})")
            return []
        except Exception as e:
            logger.error(f"Failed to get ad groups for {customer_id}: {e}")
            return []

    def get_ad_group_by_id(
        self,
        customer_id: str,
        ad_group_id: str
    ) -> Optional[Dict]:
        """
        获取单个 AdGroup 详情

        Args:
            customer_id: Google Ads Customer ID
            ad_group_id: AdGroup ID

        Returns:
            AdGroup 信息字典或 None
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.type,
                ad_group.campaign,
                ad_group.cpc_bid_micros,
                ad_group.cpm_bid_micros,
                ad_group.target_cpa_micros,
                ad_group.effective_target_cpa_micros,
                ad_group.effective_target_roas
            FROM ad_group
            WHERE ad_group.id = {ad_group_id}
        """

        try:
            rows = self._execute_query(cid, query)
            if not rows:
                return None

            ag = rows[0].ad_group
            campaign_id_str = ag.campaign.split('/')[-1]
            return {
                'ad_group_id': str(ag.id),
                'ad_group_name': ag.name,
                'status': ag.status.name,
                'type': ag.type_.name,
                'campaign_id': campaign_id_str,
                'cpc_bid_micros': ag.cpc_bid_micros,
                'cpm_bid_micros': ag.cpm_bid_micros,
                'target_cpa_micros': ag.target_cpa_micros
            }

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"get_ad_group_by_id({customer_id}, {ad_group_id})")
            return None
        except Exception as e:
            logger.error(f"Failed to get ad group {ad_group_id}: {e}")
            return None

    # ==================== 同步方法 ====================

    def sync_ad_groups(
        self,
        db: Session,
        customer_id: str,
        campaign_id: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> bool:
        """
        同步 AdGroup 数据到数据库

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID
            campaign_id: 可选的 Campaign ID
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
                    ad_group.id, ad_group.name, ad_group.status,
                    ad_group.type, ad_group.campaign,
                    ad_group.cpc_bid_micros, ad_group.cpm_bid_micros,
                    ad_group.target_cpa_micros
                FROM ad_group
            """

            if campaign_id:
                query += f" WHERE ad_group.campaign = 'customers/{cid}/campaigns/{campaign_id}'"
            query += " ORDER BY ad_group.id"

            rows = self._execute_query(cid, query)
            total, processed, failed = len(rows), 0, 0

            for row in rows:
                try:
                    self._upsert_ad_group(db, account.id, cid, row.ad_group)
                    processed += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to process ad group {row.ad_group.id}: {e}")

            db.commit()

            if task_id:
                self._update_sync_task(db, task_id, 'COMPLETED', start_time, total, processed, failed)

            logger.info(f"AdGroup sync for {customer_id}: total={total}, processed={processed}, failed={failed}")
            return True

        except GoogleAdsException as ex:
            db.rollback()
            error_msg = self._handle_api_error(ex, f"sync_ad_groups({customer_id})")
            if task_id:
                self._update_sync_task(db, task_id, 'FAILED', start_time, error_message=error_msg)
            return False

        except Exception as e:
            print(e)
            db.rollback()
            error_msg = f"Failed to sync ad groups: {e}"
            logger.error(error_msg)
            if task_id:
                self._update_sync_task(db, task_id, 'FAILED', start_time, error_message=error_msg)
            return False

    def _upsert_ad_group(
        self,
        db: Session,
        account_id: int,
        customer_id: str,
        ad_group_data
    ) -> Optional[GoogleAdGroup]:
        """更新或插入 AdGroup 记录"""
        campaign_id_str = ad_group_data.campaign.split('/')[-1]

        campaign_record = db.query(GoogleCampaign).filter(
            GoogleCampaign.customer_id == customer_id,
            GoogleCampaign.campaign_id == campaign_id_str
        ).first()

        if not campaign_record:
            logger.warning(f"Campaign {campaign_id_str} not found for ad group {ad_group_data.id}")
            return None

        ad_group = db.query(GoogleAdGroup).filter(
            GoogleAdGroup.customer_id == customer_id,
            GoogleAdGroup.ad_group_id == str(ad_group_data.id)
        ).first()

        data = {
            'ad_group_name': ad_group_data.name,
            'ad_group_status': ad_group_data.status.name,
            'ad_group_type': ad_group_data.type_.name,
            'cpc_bid_micros': ad_group_data.cpc_bid_micros,
            'cpm_bid_micros': ad_group_data.cpm_bid_micros,
            'target_cpa_micros': ad_group_data.target_cpa_micros,
            'last_synced_at': datetime.now()
        }

        if ad_group:
            for key, value in data.items():
                setattr(ad_group, key, value)
        else:
            ad_group = GoogleAdGroup(
                account_id=account_id,
                campaign_id=campaign_record.id,
                customer_id=customer_id,
                ad_group_id=str(ad_group_data.id),
                **data
            )
            db.add(ad_group)

        return ad_group

    # ==================== 创建/更新方法 ====================

    def create_ad_group(
        self,
        customer_id: str,
        campaign_id: str,
        name: str,
        ad_group_type: str = "SEARCH_STANDARD",
        cpc_bid_micros: Optional[int] = 10000000,
        status: str = "ENABLED"
    ) -> Optional[str]:
        """
        创建新的 AdGroup

        Args:
            customer_id: Google Ads Customer ID
            campaign_id: Campaign ID
            name: AdGroup 名称
            ad_group_type: AdGroup 类型
            cpc_bid_micros: CPC 出价（微单位），默认 10000000 (10元)
            status: 状态，默认 ENABLED

        Returns:
            str: 新创建的 AdGroup ID 或 None
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        try:
            ad_group_service = self.client.get_service("AdGroupService")
            campaign_service = self.client.get_service("CampaignService")
            ad_group_operation = self.client.get_type("AdGroupOperation")
            ad_group = ad_group_operation.create

            ad_group.name = name
            # 使用 campaign_service.campaign_path 生成路径
            ad_group.campaign = campaign_service.campaign_path(cid, campaign_id)
            ad_group.type_ = getattr(self.client.enums.AdGroupTypeEnum, ad_group_type)
            ad_group.status = getattr(self.client.enums.AdGroupStatusEnum, status)

            if cpc_bid_micros:
                ad_group.cpc_bid_micros = cpc_bid_micros

            response = ad_group_service.mutate_ad_groups(
                customer_id=cid,
                operations=[ad_group_operation]
            )

            ad_group_resource_name = response.results[0].resource_name
            ad_group_id = ad_group_resource_name.split('/')[-1]

            logger.info(f"Created ad group {ad_group_id} for campaign {campaign_id}")
            return ad_group_id

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"create_ad_group({customer_id}, {campaign_id})")
            return None
        except Exception as e:
            logger.error(f"Failed to create ad group: {e}")
            return None

    def update_ad_group_status(
        self,
        customer_id: str,
        ad_group_id: str,
        status: str
    ) -> bool:
        """
        更新 AdGroup 状态

        Args:
            customer_id: Google Ads Customer ID
            ad_group_id: AdGroup ID
            status: 新状态 (ENABLED, PAUSED, REMOVED)

        Returns:
            bool: 是否更新成功
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        try:
            ad_group_service = self.client.get_service("AdGroupService")
            ad_group_operation = self.client.get_type("AdGroupOperation")
            ad_group = ad_group_operation.update

            ad_group.resource_name = f"customers/{cid}/adGroups/{ad_group_id}"
            ad_group.status = getattr(self.client.enums.AdGroupStatusEnum, status)

            self.client.copy_from(
                ad_group_operation.update_mask,
                self.client.get_type("FieldMask")(paths=["status"])
            )

            ad_group_service.mutate_ad_groups(
                customer_id=cid,
                operations=[ad_group_operation]
            )

            logger.info(f"Updated ad group {ad_group_id} status to {status}")
            return True

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"update_ad_group_status({customer_id}, {ad_group_id})")
            return False
        except Exception as e:
            logger.error(f"Failed to update ad group status: {e}")
            return False

    def update_ad_group_bid(
        self,
        customer_id: str,
        ad_group_id: str,
        cpc_bid_micros: Optional[int] = None,
        cpm_bid_micros: Optional[int] = None,
        target_cpa_micros: Optional[int] = None
    ) -> bool:
        """
        更新 AdGroup 出价

        Args:
            customer_id: Google Ads Customer ID
            ad_group_id: AdGroup ID
            cpc_bid_micros: CPC 出价（微单位）
            cpm_bid_micros: CPM 出价（微单位）
            target_cpa_micros: Target CPA（微单位）

        Returns:
            bool: 是否更新成功
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        try:
            ad_group_service = self.client.get_service("AdGroupService")
            ad_group_operation = self.client.get_type("AdGroupOperation")
            ad_group = ad_group_operation.update

            ad_group.resource_name = f"customers/{cid}/adGroups/{ad_group_id}"

            paths = []
            if cpc_bid_micros is not None:
                ad_group.cpc_bid_micros = cpc_bid_micros
                paths.append("cpc_bid_micros")
            if cpm_bid_micros is not None:
                ad_group.cpm_bid_micros = cpm_bid_micros
                paths.append("cpm_bid_micros")
            if target_cpa_micros is not None:
                ad_group.target_cpa_micros = target_cpa_micros
                paths.append("target_cpa_micros")

            if not paths:
                logger.warning("No bid values provided to update")
                return False

            self.client.copy_from(
                ad_group_operation.update_mask,
                self.client.get_type("FieldMask")(paths=paths)
            )

            ad_group_service.mutate_ad_groups(
                customer_id=cid,
                operations=[ad_group_operation]
            )

            logger.info(f"Updated ad group {ad_group_id} bids")
            return True

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"update_ad_group_bid({customer_id}, {ad_group_id})")
            return False
        except Exception as e:
            logger.error(f"Failed to update ad group bid: {e}")
            return False

    # ==================== 数据库查询方法 ====================

    def get_ad_groups_from_db(
        self,
        db: Session,
        customer_id: str,
        campaign_id: Optional[str] = None,
        status_filter: Optional[List[str]] = None
    ) -> List[GoogleAdGroup]:
        """
        从数据库获取 AdGroup 列表

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID
            campaign_id: 可选的 Campaign ID
            status_filter: 状态过滤

        Returns:
            List[GoogleAdGroup]
        """
        cid = customer_id.replace('-', '')
        query = db.query(GoogleAdGroup).filter(GoogleAdGroup.customer_id == cid)

        if campaign_id:
            # 需要先查找 campaign 记录获取其 id
            campaign = db.query(GoogleCampaign).filter(
                GoogleCampaign.customer_id == cid,
                GoogleCampaign.campaign_id == campaign_id
            ).first()
            if campaign:
                query = query.filter(GoogleAdGroup.campaign_id == campaign.id)

        if status_filter:
            query = query.filter(GoogleAdGroup.ad_group_status.in_(status_filter))

        return query.all()

    def get_ad_group_from_db(
        self,
        db: Session,
        customer_id: str,
        ad_group_id: str
    ) -> Optional[GoogleAdGroup]:
        """
        从数据库获取单个 AdGroup

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID
            ad_group_id: AdGroup ID

        Returns:
            GoogleAdGroup 或 None
        """
        cid = customer_id.replace('-', '')
        return db.query(GoogleAdGroup).filter(
            GoogleAdGroup.customer_id == cid,
            GoogleAdGroup.ad_group_id == ad_group_id
        ).first()
