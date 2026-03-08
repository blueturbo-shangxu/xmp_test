"""
Google Ads Ad Service
处理 Google Ads Ad 级别的操作
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from google.ads.googleads.errors import GoogleAdsException
from sqlalchemy.orm import Session

from src.sql import GoogleAdAccount, GoogleCampaign, GoogleAdGroup, GoogleAd
from src.services.google.base_service import GoogleAdsBaseService

logger = logging.getLogger(__name__)


class GoogleAdsAdService(GoogleAdsBaseService):
    """
    Google Ads Ad 服务类

    处理 Ad 级别的查询、同步、创建、更新等操作
    """

    # ==================== 查询方法 ====================

    def get_ads(
        self,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        status_filter: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取 Ad 列表

        Args:
            customer_id: Google Ads Customer ID
            ad_group_id: 可选的 AdGroup ID 过滤
            status_filter: 状态过滤（如 ['ENABLED', 'PAUSED']）
            limit: 返回数量限制

        Returns:
            List[Dict]: Ad 列表
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        query = """
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.name,
                ad_group_ad.ad.type,
                ad_group_ad.ad.final_urls,
                ad_group_ad.status,
                ad_group_ad.policy_summary.approval_status,
                ad_group_ad.ad_group,
                ad_group.campaign
            FROM ad_group_ad
        """

        conditions = []
        if ad_group_id:
            conditions.append(f"ad_group_ad.ad_group = 'customers/{cid}/adGroups/{ad_group_id}'")
        if status_filter:
            status_str = ", ".join([f"'{s}'" for s in status_filter])
            conditions.append(f"ad_group_ad.status IN ({status_str})")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += f" ORDER BY ad_group_ad.ad.id LIMIT {limit}"

        try:
            rows = self._execute_query(cid, query)
            ads = []
            for row in rows:
                ad = row.ad_group_ad.ad
                ad_group_ad = row.ad_group_ad
                ad_group_id_str = ad_group_ad.ad_group.split('/')[-1]
                campaign_id_str = row.ad_group.campaign.split('/')[-1]

                ads.append({
                    'ad_id': str(ad.id),
                    'ad_name': ad.name if ad.name else None,
                    'ad_type': ad.type_.name,
                    'status': ad_group_ad.status.name,
                    'approval_status': ad_group_ad.policy_summary.approval_status.name if ad_group_ad.policy_summary else None,
                    'final_urls': list(ad.final_urls) if ad.final_urls else [],
                    'ad_group_id': ad_group_id_str,
                    'campaign_id': campaign_id_str
                })
            return ads

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"get_ads({customer_id})")
            return []
        except Exception as e:
            logger.error(f"Failed to get ads for {customer_id}: {e}")
            return []

    def get_ad_by_id(
        self,
        customer_id: str,
        ad_group_id: str,
        ad_id: str
    ) -> Optional[Dict]:
        """
        获取单个 Ad 详情

        Args:
            customer_id: Google Ads Customer ID
            ad_group_id: AdGroup ID
            ad_id: Ad ID

        Returns:
            Ad 信息字典或 None
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        query = f"""
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.name,
                ad_group_ad.ad.type,
                ad_group_ad.ad.final_urls,
                ad_group_ad.ad.final_mobile_urls,
                ad_group_ad.ad.tracking_url_template,
                ad_group_ad.ad.display_url,
                ad_group_ad.status,
                ad_group_ad.policy_summary.approval_status,
                ad_group_ad.policy_summary.review_status,
                ad_group_ad.ad_group,
                ad_group.campaign,
                ad_group_ad.ad.responsive_search_ad.headlines,
                ad_group_ad.ad.responsive_search_ad.descriptions
            FROM ad_group_ad
            WHERE ad_group_ad.ad_group = 'customers/{cid}/adGroups/{ad_group_id}'
                AND ad_group_ad.ad.id = {ad_id}
        """

        try:
            rows = self._execute_query(cid, query)
            if not rows:
                return None

            row = rows[0]
            ad = row.ad_group_ad.ad
            ad_group_ad = row.ad_group_ad

            # 处理 RSA 数据
            headlines = None
            descriptions = None
            if hasattr(ad, 'responsive_search_ad') and ad.responsive_search_ad:
                rsa = ad.responsive_search_ad
                if rsa.headlines:
                    headlines = [{'text': h.text, 'pinned_field': h.pinned_field.name if h.pinned_field else None}
                                 for h in rsa.headlines]
                if rsa.descriptions:
                    descriptions = [{'text': d.text, 'pinned_field': d.pinned_field.name if d.pinned_field else None}
                                    for d in rsa.descriptions]

            return {
                'ad_id': str(ad.id),
                'ad_name': ad.name if ad.name else None,
                'ad_type': ad.type_.name,
                'status': ad_group_ad.status.name,
                'approval_status': ad_group_ad.policy_summary.approval_status.name if ad_group_ad.policy_summary else None,
                'review_status': ad_group_ad.policy_summary.review_status.name if ad_group_ad.policy_summary else None,
                'final_urls': list(ad.final_urls) if ad.final_urls else [],
                'final_mobile_urls': list(ad.final_mobile_urls) if ad.final_mobile_urls else [],
                'display_url': ad.display_url if ad.display_url else None,
                'tracking_url_template': ad.tracking_url_template if ad.tracking_url_template else None,
                'headlines': headlines,
                'descriptions': descriptions,
                'ad_group_id': ad_group_id,
                'campaign_id': row.ad_group.campaign.split('/')[-1]
            }

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"get_ad_by_id({customer_id}, {ad_group_id}, {ad_id})")
            return None
        except Exception as e:
            logger.error(f"Failed to get ad {ad_id}: {e}")
            return None

    # ==================== 同步方法 ====================

    def sync_ads(
        self,
        db: Session,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> bool:
        """
        同步 Ad 数据到数据库

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID
            ad_group_id: 可选的 AdGroup ID
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
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.ad.type,
                    ad_group_ad.ad.final_urls,
                    ad_group_ad.ad.final_mobile_urls,
                    ad_group_ad.ad.tracking_url_template,
                    ad_group_ad.ad.display_url,
                    ad_group_ad.status,
                    ad_group_ad.policy_summary.approval_status,
                    ad_group_ad.policy_summary.review_status,
                    ad_group_ad.ad_group,
                    ad_group.campaign,
                    ad_group_ad.ad.responsive_search_ad.headlines,
                    ad_group_ad.ad.responsive_search_ad.descriptions
                FROM ad_group_ad
            """

            if ad_group_id:
                query += f" WHERE ad_group_ad.ad_group = 'customers/{cid}/adGroups/{ad_group_id}'"
            query += " ORDER BY ad_group_ad.ad.id"

            rows = self._execute_query(cid, query)
            total, processed, failed = len(rows), 0, 0
            print(rows)

            for row in rows:
                try:
                    self._upsert_ad(db, account.id, cid, row)
                    processed += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to process ad {row.ad_group_ad.ad.id}: {e}")

            db.commit()

            if task_id:
                self._update_sync_task(db, task_id, 'COMPLETED', start_time, total, processed, failed)

            logger.info(f"Ad sync for {customer_id}: total={total}, processed={processed}, failed={failed}")
            return True

        except GoogleAdsException as ex:
            print(ex)
            db.rollback()
            error_msg = self._handle_api_error(ex, f"sync_ads({customer_id})")
            if task_id:
                self._update_sync_task(db, task_id, 'FAILED', start_time, error_message=error_msg)
            return False

        except Exception as e:
            print(e)
            db.rollback()
            error_msg = f"Failed to sync ads: {e}"
            logger.error(error_msg)
            if task_id:
                self._update_sync_task(db, task_id, 'FAILED', start_time, error_message=error_msg)
            return False

    def _upsert_ad(
        self,
        db: Session,
        account_id: int,
        customer_id: str,
        row
    ) -> Optional[GoogleAd]:
        """更新或插入 Ad 记录"""
        ad_data = row.ad_group_ad.ad
        ad_group_ad_data = row.ad_group_ad

        # 解析 ad_group_id 和 campaign_id
        ad_group_resource = ad_group_ad_data.ad_group
        ad_group_id_str = ad_group_resource.split('/')[-1]

        campaign_resource = row.ad_group.campaign
        campaign_id_str = campaign_resource.split('/')[-1]

        # 查找关联的 Campaign 记录
        campaign_record = db.query(GoogleCampaign).filter(
            GoogleCampaign.customer_id == customer_id,
            GoogleCampaign.campaign_id == campaign_id_str
        ).first()

        if not campaign_record:
            logger.warning(f"Campaign {campaign_id_str} not found for ad {ad_data.id}")
            return None

        # 查找关联的 AdGroup 记录
        ad_group_record = db.query(GoogleAdGroup).filter(
            GoogleAdGroup.customer_id == customer_id,
            GoogleAdGroup.ad_group_id == ad_group_id_str
        ).first()

        if not ad_group_record:
            logger.warning(f"AdGroup {ad_group_id_str} not found for ad {ad_data.id}")
            return None

        # 查找现有的 Ad 记录
        ad = db.query(GoogleAd).filter(
            GoogleAd.customer_id == customer_id,
            GoogleAd.ad_id == str(ad_data.id)
        ).first()

        # 处理 headlines 和 descriptions (响应式搜索广告)
        headlines = None
        descriptions = None
        if hasattr(ad_data, 'responsive_search_ad') and ad_data.responsive_search_ad:
            rsa = ad_data.responsive_search_ad
            if rsa.headlines:
                headlines = [{'text': h.text, 'pinned_field': h.pinned_field.name if h.pinned_field else None}
                             for h in rsa.headlines]
            if rsa.descriptions:
                descriptions = [{'text': d.text, 'pinned_field': d.pinned_field.name if d.pinned_field else None}
                                for d in rsa.descriptions]

        # 处理 policy_summary
        policy_summary = None
        if ad_group_ad_data.policy_summary:
            ps = ad_group_ad_data.policy_summary
            policy_summary = {
                'approval_status': ps.approval_status.name if ps.approval_status else None,
                'review_status': ps.review_status.name if ps.review_status else None
            }

        data = {
            'ad_name': ad_data.name if ad_data.name else None,
            'ad_status': ad_group_ad_data.status.name,
            'ad_type': ad_data.type_.name,
            'headlines': headlines,
            'descriptions': descriptions,
            'final_urls': list(ad_data.final_urls) if ad_data.final_urls else None,
            'final_mobile_urls': list(ad_data.final_mobile_urls) if ad_data.final_mobile_urls else None,
            'tracking_url_template': ad_data.tracking_url_template if ad_data.tracking_url_template else None,
            'display_url': ad_data.display_url if ad_data.display_url else None,
            'policy_summary': policy_summary,
            'last_synced_at': datetime.now()
        }

        if ad:
            for key, value in data.items():
                setattr(ad, key, value)
        else:
            ad = GoogleAd(
                account_id=account_id,
                campaign_id=campaign_record.id,
                ad_group_id=ad_group_record.id,
                customer_id=customer_id,
                ad_id=str(ad_data.id),
                **data
            )
            db.add(ad)

        return ad

    # ==================== 创建/更新方法 ====================

    def create_responsive_search_ad(
        self,
        customer_id: str,
        ad_group_id: str,
        headlines: List[str],
        descriptions: List[str],
        final_urls: List[str],
        path1: Optional[str] = None,
        path2: Optional[str] = None
    ) -> Optional[str]:
        """
        创建响应式搜索广告 (RSA)

        Args:
            customer_id: Google Ads Customer ID
            ad_group_id: AdGroup ID
            headlines: 标题列表（3-15个）
            descriptions: 描述列表（2-4个）
            final_urls: 最终到达URL列表
            path1: 显示路径1
            path2: 显示路径2

        Returns:
            str: 新创建的 Ad ID 或 None
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        try:
            ad_group_ad_service = self.client.get_service("AdGroupAdService")
            ad_group_ad_operation = self.client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.create

            ad_group_ad.ad_group = f"customers/{cid}/adGroups/{ad_group_id}"
            ad_group_ad.status = self.client.enums.AdGroupAdStatusEnum.PAUSED

            # 设置 RSA
            ad = ad_group_ad.ad
            ad.final_urls.extend(final_urls)

            # 添加标题
            for headline_text in headlines:
                headline = self.client.get_type("AdTextAsset")
                headline.text = headline_text
                ad.responsive_search_ad.headlines.append(headline)

            # 添加描述
            for description_text in descriptions:
                description = self.client.get_type("AdTextAsset")
                description.text = description_text
                ad.responsive_search_ad.descriptions.append(description)

            # 设置路径
            if path1:
                ad.responsive_search_ad.path1 = path1
            if path2:
                ad.responsive_search_ad.path2 = path2

            response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=cid,
                operations=[ad_group_ad_operation]
            )

            ad_resource_name = response.results[0].resource_name
            # 资源名格式: customers/{customer_id}/adGroupAds/{ad_group_id}~{ad_id}
            ad_id = ad_resource_name.split('~')[-1]

            logger.info(f"Created RSA {ad_id} for ad group {ad_group_id}")
            return ad_id

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"create_responsive_search_ad({customer_id}, {ad_group_id})")
            return None
        except Exception as e:
            logger.error(f"Failed to create RSA: {e}")
            return None

    def update_ad_status(
        self,
        customer_id: str,
        ad_group_id: str,
        ad_id: str,
        status: str
    ) -> bool:
        """
        更新 Ad 状态

        Args:
            customer_id: Google Ads Customer ID
            ad_group_id: AdGroup ID
            ad_id: Ad ID
            status: 新状态 (ENABLED, PAUSED, REMOVED)

        Returns:
            bool: 是否更新成功
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        try:
            ad_group_ad_service = self.client.get_service("AdGroupAdService")
            ad_group_ad_operation = self.client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.update

            ad_group_ad.resource_name = f"customers/{cid}/adGroupAds/{ad_group_id}~{ad_id}"
            ad_group_ad.status = getattr(self.client.enums.AdGroupAdStatusEnum, status)

            self.client.copy_from(
                ad_group_ad_operation.update_mask,
                self.client.get_type("FieldMask")(paths=["status"])
            )

            ad_group_ad_service.mutate_ad_group_ads(
                customer_id=cid,
                operations=[ad_group_ad_operation]
            )

            logger.info(f"Updated ad {ad_id} status to {status}")
            return True

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"update_ad_status({customer_id}, {ad_group_id}, {ad_id})")
            return False
        except Exception as e:
            logger.error(f"Failed to update ad status: {e}")
            return False

    def update_ad_urls(
        self,
        customer_id: str,
        ad_group_id: str,
        ad_id: str,
        final_urls: Optional[List[str]] = None,
        final_mobile_urls: Optional[List[str]] = None,
        tracking_url_template: Optional[str] = None
    ) -> bool:
        """
        更新 Ad URL

        Args:
            customer_id: Google Ads Customer ID
            ad_group_id: AdGroup ID
            ad_id: Ad ID
            final_urls: 最终到达URL列表
            final_mobile_urls: 移动端最终到达URL列表
            tracking_url_template: 跟踪URL模板

        Returns:
            bool: 是否更新成功
        """
        cid = customer_id.replace('-', '')

        # 设置 customer_id 以自动配置 login_customer_id
        self.set_customer_id(customer_id)

        try:
            ad_group_ad_service = self.client.get_service("AdGroupAdService")
            ad_group_ad_operation = self.client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.update

            ad_group_ad.resource_name = f"customers/{cid}/adGroupAds/{ad_group_id}~{ad_id}"

            paths = []
            if final_urls is not None:
                ad_group_ad.ad.final_urls.extend(final_urls)
                paths.append("ad.final_urls")
            if final_mobile_urls is not None:
                ad_group_ad.ad.final_mobile_urls.extend(final_mobile_urls)
                paths.append("ad.final_mobile_urls")
            if tracking_url_template is not None:
                ad_group_ad.ad.tracking_url_template = tracking_url_template
                paths.append("ad.tracking_url_template")

            if not paths:
                logger.warning("No URL values provided to update")
                return False

            self.client.copy_from(
                ad_group_ad_operation.update_mask,
                self.client.get_type("FieldMask")(paths=paths)
            )

            ad_group_ad_service.mutate_ad_group_ads(
                customer_id=cid,
                operations=[ad_group_ad_operation]
            )

            logger.info(f"Updated ad {ad_id} URLs")
            return True

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"update_ad_urls({customer_id}, {ad_group_id}, {ad_id})")
            return False
        except Exception as e:
            logger.error(f"Failed to update ad URLs: {e}")
            return False

    # ==================== 数据库查询方法 ====================

    def get_ads_from_db(
        self,
        db: Session,
        customer_id: str,
        ad_group_id: Optional[str] = None,
        status_filter: Optional[List[str]] = None
    ) -> List[GoogleAd]:
        """
        从数据库获取 Ad 列表

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID
            ad_group_id: 可选的 AdGroup ID
            status_filter: 状态过滤

        Returns:
            List[GoogleAd]
        """
        cid = customer_id.replace('-', '')
        query = db.query(GoogleAd).filter(GoogleAd.customer_id == cid)

        if ad_group_id:
            ad_group = db.query(GoogleAdGroup).filter(
                GoogleAdGroup.customer_id == cid,
                GoogleAdGroup.ad_group_id == ad_group_id
            ).first()
            if ad_group:
                query = query.filter(GoogleAd.ad_group_id == ad_group.id)

        if status_filter:
            query = query.filter(GoogleAd.ad_status.in_(status_filter))

        return query.all()

    def get_ad_from_db(
        self,
        db: Session,
        customer_id: str,
        ad_id: str
    ) -> Optional[GoogleAd]:
        """
        从数据库获取单个 Ad

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID
            ad_id: Ad ID

        Returns:
            GoogleAd 或 None
        """
        cid = customer_id.replace('-', '')
        return db.query(GoogleAd).filter(
            GoogleAd.customer_id == cid,
            GoogleAd.ad_id == ad_id
        ).first()
