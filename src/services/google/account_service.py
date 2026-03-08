"""
Google Ads Account Service
处理 Google Ads 账户级别的操作
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from google.ads.googleads.errors import GoogleAdsException
from sqlalchemy.orm import Session

from src.sql import OAuthToken, GoogleAdAccount
from src.services.google.base_service import GoogleAdsBaseService

logger = logging.getLogger(__name__)


class GoogleAdsAccountService(GoogleAdsBaseService):
    """
    Google Ads 账户服务类

    处理账户级别的查询、同步等操作
    """

    # ==================== 查询方法 ====================

    def get_accessible_customers(self) -> List[str]:
        """
        获取当前 token 可访问的客户ID列表

        Returns:
            List[str]: customer_id 列表
        """
        try:
            client = self._create_client(with_login_customer_id=False)
            customer_service = client.get_service("CustomerService")
            response = customer_service.list_accessible_customers()

            customer_ids = []
            for resource_name in response.resource_names:
                cid = resource_name.split('/')[-1]
                customer_ids.append(cid)

            logger.info(f"Found {len(customer_ids)} accessible customers")
            return customer_ids

        except GoogleAdsException as ex:
            self._handle_api_error(ex, "get_accessible_customers")
            return []
        except Exception as e:
            logger.error(f"Failed to get accessible customers: {e}")
            return []

    def get_account_info(self, customer_id: str) -> Optional[Dict]:
        """
        获取单个账户信息

        Args:
            customer_id: Google Ads Customer ID

        Returns:
            账户信息字典或 None
        """
        cid = customer_id.replace('-', '')
        query = f"""
            SELECT
                customer.id,
                customer.descriptive_name,
                customer.currency_code,
                customer.time_zone,
                customer.manager,
                customer.status
            FROM customer
            WHERE customer.id = '{cid}'
        """

        try:
            rows = self._execute_query(cid, query)
            if not rows:
                return None

            customer = rows[0].customer
            return {
                'customer_id': customer_id,
                'account_name': customer.descriptive_name,
                'currency_code': customer.currency_code,
                'timezone': customer.time_zone,
                'account_type': 'MANAGER' if customer.manager else 'CLIENT',
                'status': customer.status.name
            }

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"get_account_info({customer_id})")
            return None
        except Exception as e:
            logger.error(f"Failed to get account info for {customer_id}: {e}")
            return None

    def get_account_hierarchy(self, customer_id: str) -> List[Dict]:
        """
        获取账户层级结构（对于Manager账户）

        Args:
            customer_id: Manager账户的 Customer ID

        Returns:
            List[Dict]: 子账户列表
        """
        cid = customer_id.replace('-', '')
        query = """
            SELECT
                customer_client.client_customer,
                customer_client.level,
                customer_client.manager,
                customer_client.descriptive_name,
                customer_client.currency_code,
                customer_client.time_zone,
                customer_client.status
            FROM customer_client
            WHERE customer_client.level <= 1
        """

        try:
            rows = self._execute_query(cid, query)
            print(0)
            print(rows)
            clients = []
            for row in rows:
                client = row.customer_client
                client_id = client.client_customer.split('/')[-1]
                clients.append({
                    'customer_id': client_id,
                    'level': client.level,
                    'is_manager': client.manager,
                    'account_name': client.descriptive_name,
                    'currency_code': client.currency_code,
                    'timezone': client.time_zone,
                    'status': client.status.name
                })
            return clients

        except GoogleAdsException as ex:
            self._handle_api_error(ex, f"get_account_hierarchy({customer_id})")
            return []
        except Exception as e:
            logger.error(f"Failed to get account hierarchy for {customer_id}: {e}")
            return []

    # ==================== 同步方法 ====================

    def sync_all_accounts(self, db: Session) -> Dict:
        """
        同步当前 token 下所有可访问的广告账户（包含子账户）

        使用 get_account_hierarchy 获取账户层级信息，同步所有账户及子账户

        Args:
            db: 数据库会话

        Returns:
            Dict: 同步结果汇总
        """
        result = {
            "token_id": self.token_id,
            "total": 0,
            "synced": 0,
            "failed": 0,
            "accounts": [],
            "errors": []
        }

        # 获取可访问的顶级账户
        customer_ids = self.get_accessible_customers()

        if not customer_ids:
            logger.warning(f"No accessible customers for token {self.token_id}")
            return result

        # 用于去重和追踪所有已同步的账户
        synced_customer_ids = set()

        for customer_id in customer_ids:
            # 获取账户层级结构（包含自身和子账户）
            hierarchy = self.get_account_hierarchy(customer_id)

            if not hierarchy:
                # 如果获取层级失败，尝试直接获取单个账户信息
                account_info = self.get_account_info(customer_id)
                if account_info:
                    hierarchy = [{
                        'customer_id': customer_id,
                        'level': 0,
                        'is_manager': account_info.get('account_type') == 'MANAGER',
                        'account_name': account_info.get('account_name', ''),
                        'currency_code': account_info.get('currency_code', 'USD'),
                        'timezone': account_info.get('timezone', 'UTC'),
                        'status': account_info.get('status', 'ENABLED')
                    }]

            # 同步层级中的所有账户
            for client_info in hierarchy:
                client_customer_id = client_info['customer_id']
                cid = client_customer_id.replace('-', '')

                # 跳过已同步的账户
                if cid in synced_customer_ids:
                    continue

                result["total"] += 1

                # 确定 manager_customer_id
                # 如果是 manager 账户，manager_customer_id 填自己
                # 如果是子账户 (level > 0)，manager_customer_id 填父级 manager
                if client_info.get('is_manager'):
                    manager_cid = cid  # manager 账户的 manager_customer_id 填自己
                elif client_info.get('level', 0) > 0:
                    manager_cid = customer_id.replace('-', '')  # 子账户填父级
                else:
                    manager_cid = None

                sync_result = self._sync_single_account_from_hierarchy(
                    db, client_info, manager_cid
                )

                if sync_result["success"]:
                    result["synced"] += 1
                    synced_customer_ids.add(cid)
                    result["accounts"].append({
                        "customer_id": client_customer_id,
                        "account_name": sync_result.get("account_name"),
                        "account_type": sync_result.get("account_type"),
                        "manager_customer_id": manager_cid
                    })
                else:
                    result["failed"] += 1
                    result["errors"].append(sync_result.get("error"))

        # 更新 token 的 advertiser_ids
        if result["accounts"]:
            token = db.query(OAuthToken).filter(OAuthToken.id == self.token_id).first()
            if token:
                synced_ids = [acc["customer_id"] for acc in result["accounts"]]
                token.advertiser_ids = synced_ids
                token.updated_at = datetime.now()
                db.commit()

        logger.info(f"Sync completed: total={result['total']}, synced={result['synced']}, failed={result['failed']}")
        return result

    def _sync_single_account_from_hierarchy(self, db: Session, client_info: Dict, manager_cid: Optional[str]) -> Dict:
        """
        从层级数据同步单个账户信息到数据库

        Args:
            db: 数据库会话
            client_info: 从 get_account_hierarchy 获取的账户信息
            manager_cid: 管理账户ID（已格式化）

        Returns:
            Dict: 同步结果
        """
        customer_id = client_info['customer_id']
        cid = customer_id.replace('-', '')

        try:
            account = db.query(GoogleAdAccount).filter(
                GoogleAdAccount.customer_id == cid
            ).first()

            # 从 client_info 提取字段
            account_name = client_info.get('account_name', '')
            currency_code = client_info.get('currency_code', 'USD')
            timezone = client_info.get('timezone', 'UTC')
            is_manager = client_info.get('is_manager', False)
            account_type = 'MANAGER' if is_manager else 'CLIENT'
            status = client_info.get('status', 'ENABLED')

            if account:
                # 更新现有账户
                account.account_name = account_name
                account.descriptive_name = account_name
                account.currency_code = currency_code
                account.timezone = timezone
                account.account_type = account_type
                account.status = status
                account.manager_customer_id = manager_cid
                account.can_manage_clients = is_manager
                account.updated_at = datetime.now()
            else:
                # 创建新账户
                account = GoogleAdAccount(
                    customer_id=cid,
                    account_name=account_name,
                    descriptive_name=account_name,
                    currency_code=currency_code,
                    timezone=timezone,
                    account_type=account_type,
                    status=status,
                    manager_customer_id=manager_cid,
                    can_manage_clients=is_manager,
                    test_account=False,
                    sync_enabled=True
                )
                db.add(account)

            db.commit()

            return {
                "success": True,
                "customer_id": customer_id,
                "account_name": account_name,
                "account_type": account_type
            }

        except Exception as e:
            db.rollback()
            error_msg = f"Failed to sync account {customer_id}: {e}"
            logger.error(error_msg)
            return {"success": False, "customer_id": customer_id, "error": error_msg}

    def _sync_single_account(self, db: Session, customer_id: str) -> Dict:
        """同步单个客户账户信息到数据库（保留用于单独调用）"""
        cid = customer_id.replace('-', '')

        try:
            account_info = self.get_account_info(customer_id)
            if not account_info:
                return {"success": False, "customer_id": customer_id, "error": "Failed to get account info"}

            account = db.query(GoogleAdAccount).filter(
                GoogleAdAccount.customer_id == cid
            ).first()

            if account:
                account.account_name = account_info['account_name']
                account.currency_code = account_info['currency_code']
                account.timezone = account_info['timezone']
                account.account_type = account_info['account_type']
                account.status = account_info['status']
                account.updated_at = datetime.now()
            else:
                account = GoogleAdAccount(
                    customer_id=cid,
                    account_name=account_info['account_name'],
                    currency_code=account_info['currency_code'],
                    timezone=account_info['timezone'],
                    account_type=account_info['account_type'],
                    status=account_info['status'],
                    sync_enabled=True
                )
                db.add(account)

            db.commit()

            return {
                "success": True,
                "customer_id": customer_id,
                "account_name": account_info['account_name'],
                "account_type": account_info['account_type']
            }

        except Exception as e:
            db.rollback()
            error_msg = f"Failed to sync account {customer_id}: {e}"
            logger.error(error_msg)
            return {"success": False, "customer_id": customer_id, "error": error_msg}

    # ==================== 数据库查询方法 ====================

    def get_account_from_db(self, db: Session, customer_id: str) -> Optional[GoogleAdAccount]:
        """
        从数据库获取账户记录

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID

        Returns:
            GoogleAdAccount 或 None
        """
        cid = customer_id.replace('-', '')
        return db.query(GoogleAdAccount).filter(
            GoogleAdAccount.customer_id == cid
        ).first()

    def list_accounts_from_db(self, db: Session) -> List[GoogleAdAccount]:
        """
        从数据库获取所有账户列表

        Args:
            db: 数据库会话

        Returns:
            List[GoogleAdAccount]
        """
        return db.query(GoogleAdAccount).all()
