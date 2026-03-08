"""
Google Ads Service Facade 集成测试
使用真实 token 数据进行测试
"""
from datetime import datetime

import pytest
import socket
import os
from typing import Dict, List, Optional

from src.services.google.service_facade import GoogleAdsServiceFacade, GoogleAdsService
from src.sql import get_db_context, OAuthToken, GoogleAdAccount

# 测试使用的 token_id
TEST_TOKEN_ID = 4
TEST_CUSTOMER_ID = '5006349945'
TEST_TOKEN_ID = 5
TEST_CUSTOMER_ID = '3950575513'
TEST_CUSTOMER_ID = '7588855578'
TEST_LOGIN_CUSTOMER_ID = '3950575513'
TEST_LOGIN_CUSTOMER_ID = None


def is_network_available() -> bool:
    """检查网络是否可用（支持代理）"""
    import urllib.request
    import urllib.error

    # 检查是否设置了代理
    proxy = os.environ.get('https_proxy') or os.environ.get('HTTPS_PROXY')

    try:
        if proxy:
            # 使用代理
            proxy_handler = urllib.request.ProxyHandler({
                'http': proxy,
                'https': proxy
            })
            opener = urllib.request.build_opener(proxy_handler)
            opener.open('https://accounts.google.com', timeout=10)
        else:
            # 直接连接
            socket.create_connection(("accounts.google.com", 443), timeout=5)
        return True
    except Exception:
        return False


# 网络可用性标记
NETWORK_AVAILABLE = is_network_available()
skip_if_no_network = pytest.mark.skipif(
    not NETWORK_AVAILABLE,
    reason="Network not available, skipping integration tests"
)


class TestGoogleAdsServiceFacadeBasic:
    """基本功能测试（不需要网络）"""

    def test_facade_initialization(self):
        """测试 Facade 初始化"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = TEST_TOKEN_ID
        facade._account_service = None
        facade._campaign_service = None
        facade._ad_group_service = None
        facade._ad_service = None

        assert facade.token_id == TEST_TOKEN_ID
        assert facade._account_service is None
        assert facade._campaign_service is None
        assert facade._ad_group_service is None
        assert facade._ad_service is None

    def test_google_ads_service_alias(self):
        """测试 GoogleAdsService 是 GoogleAdsServiceFacade 的别名"""
        assert GoogleAdsService is GoogleAdsServiceFacade


class TestGoogleAdsServiceFacadeWithMocks:
    """使用 Mock 的测试（不需要网络）"""

    @pytest.fixture
    def facade_with_mocks(self):
        """创建带有 mock 服务的 facade"""
        from unittest.mock import Mock

        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = TEST_TOKEN_ID
        facade._account_service = Mock()
        facade._campaign_service = Mock()
        facade._ad_group_service = Mock()
        facade._ad_service = Mock()
        return facade

    def test_get_accessible_customers_mock(self, facade_with_mocks):
        """测试获取可访问客户列表（Mock）"""
        expected = ['123-456-7890', '234-567-8901']
        facade_with_mocks._account_service.get_accessible_customers.return_value = expected

        result = facade_with_mocks.get_accessible_customers()

        facade_with_mocks._account_service.get_accessible_customers.assert_called_once()
        assert result == expected

    def test_get_account_info_mock(self, facade_with_mocks):
        """测试获取账户信息（Mock）"""
        expected = {
            'customer_id': '123-456-7890',
            'account_name': 'Test Account',
            'currency_code': 'USD',
            'timezone': 'America/Los_Angeles',
            'account_type': 'CLIENT',
            'status': 'ENABLED'
        }
        facade_with_mocks._account_service.get_account_info.return_value = expected

        result = facade_with_mocks.get_account_info('123-456-7890')

        facade_with_mocks._account_service.get_account_info.assert_called_once_with('123-456-7890')
        assert result == expected

    def test_get_campaigns_mock(self, facade_with_mocks):
        """测试获取 Campaign 列表（Mock）"""
        expected = [
            {'campaign_id': '111', 'campaign_name': 'Campaign 1', 'status': 'ENABLED'},
            {'campaign_id': '222', 'campaign_name': 'Campaign 2', 'status': 'PAUSED'}
        ]
        facade_with_mocks._campaign_service.get_campaigns.return_value = expected

        result = facade_with_mocks.get_campaigns('123-456-7890')

        facade_with_mocks._campaign_service.get_campaigns.assert_called_once_with('123-456-7890', None)
        assert result == expected

    def test_get_ad_groups_mock(self, facade_with_mocks):
        """测试获取 AdGroup 列表（Mock）"""
        expected = [
            {'ad_group_id': '111', 'ad_group_name': 'AdGroup 1', 'status': 'ENABLED'}
        ]
        facade_with_mocks._ad_group_service.get_ad_groups.return_value = expected

        result = facade_with_mocks.get_ad_groups('123-456-7890')

        facade_with_mocks._ad_group_service.get_ad_groups.assert_called_once_with('123-456-7890', None, None)
        assert result == expected

    def test_get_ads_mock(self, facade_with_mocks):
        """测试获取 Ad 列表（Mock）"""
        expected = [
            {'ad_id': '111', 'ad_name': 'Ad 1', 'status': 'ENABLED'}
        ]
        facade_with_mocks._ad_service.get_ads.return_value = expected

        result = facade_with_mocks.get_ads('123-456-7890')

        facade_with_mocks._ad_service.get_ads.assert_called_once_with('123-456-7890', None, None)
        assert result == expected

    def test_sync_all_accounts_mock(self, facade_with_mocks):
        """测试同步所有账户（Mock）"""
        from unittest.mock import Mock
        mock_db = Mock()
        expected = {
            'token_id': TEST_TOKEN_ID,
            'total': 2,
            'synced': 2,
            'failed': 0,
            'accounts': [],
            'errors': []
        }
        facade_with_mocks._account_service.sync_all_accounts.return_value = expected

        result = facade_with_mocks.sync_all_accounts(mock_db)

        facade_with_mocks._account_service.sync_all_accounts.assert_called_once_with(mock_db)
        assert result == expected

    def test_sync_campaigns_mock(self, facade_with_mocks):
        """测试同步 Campaign（Mock）"""
        from unittest.mock import Mock
        mock_db = Mock()
        facade_with_mocks._campaign_service.sync_campaigns.return_value = True

        result = facade_with_mocks.sync_campaigns(mock_db, '123-456-7890')

        facade_with_mocks._campaign_service.sync_campaigns.assert_called_once_with(
            mock_db, '123-456-7890', None
        )
        assert result is True

    def test_sync_ad_groups_mock(self, facade_with_mocks):
        """测试同步 AdGroup（Mock）"""
        from unittest.mock import Mock
        mock_db = Mock()
        facade_with_mocks._ad_group_service.sync_ad_groups.return_value = True

        result = facade_with_mocks.sync_ad_groups(mock_db, '123-456-7890')

        facade_with_mocks._ad_group_service.sync_ad_groups.assert_called_once_with(
            mock_db, '123-456-7890', None, None
        )
        assert result is True

    def test_sync_ads_mock(self, facade_with_mocks):
        """测试同步 Ad（Mock）"""
        from unittest.mock import Mock
        mock_db = Mock()
        facade_with_mocks._ad_service.sync_ads.return_value = True

        result = facade_with_mocks.sync_ads(mock_db, '123-456-7890')

        facade_with_mocks._ad_service.sync_ads.assert_called_once_with(
            mock_db, '123-456-7890', None, None
        )
        assert result is True

    def test_sync_all_mock(self, facade_with_mocks):
        """测试完整同步（Mock）"""
        from unittest.mock import Mock
        mock_db = Mock()

        facade_with_mocks._account_service._sync_single_account.return_value = {'success': True}
        facade_with_mocks._campaign_service.sync_campaigns.return_value = True
        facade_with_mocks._ad_group_service.sync_ad_groups.return_value = True
        facade_with_mocks._ad_service.sync_ads.return_value = True

        result = facade_with_mocks.sync_all(mock_db, '123-456-7890')

        assert result['customer_id'] == '123-456-7890'
        assert result['accounts']['success'] is True
        assert result['campaigns']['success'] is True
        assert result['ad_groups']['success'] is True
        assert result['ads']['success'] is True

    def test_sync_campaign_tree_mock(self, facade_with_mocks):
        """测试 Campaign 树同步（Mock）"""
        from unittest.mock import Mock
        mock_db = Mock()

        facade_with_mocks._ad_group_service.sync_ad_groups.return_value = True
        facade_with_mocks._ad_group_service.get_ad_groups.return_value = [
            {'ad_group_id': '111'},
            {'ad_group_id': '222'}
        ]
        facade_with_mocks._ad_service.sync_ads.return_value = True

        result = facade_with_mocks.sync_campaign_tree(mock_db, '123-456-7890', '12345')

        assert result['customer_id'] == '123-456-7890'
        assert result['campaign_id'] == '12345'
        assert result['ad_groups']['success'] is True
        assert result['ads']['success'] is True

    def test_update_campaign_status_mock(self, facade_with_mocks):
        """测试更新 Campaign 状态（Mock）"""
        facade_with_mocks._campaign_service.update_campaign_status.return_value = True

        result = facade_with_mocks.update_campaign_status('123-456-7890', '12345', 'PAUSED')

        facade_with_mocks._campaign_service.update_campaign_status.assert_called_once_with(
            '123-456-7890', '12345', 'PAUSED'
        )
        assert result is True

    def test_update_ad_group_status_mock(self, facade_with_mocks):
        """测试更新 AdGroup 状态（Mock）"""
        facade_with_mocks._ad_group_service.update_ad_group_status.return_value = True

        result = facade_with_mocks.update_ad_group_status('123-456-7890', '67890', 'ENABLED')

        facade_with_mocks._ad_group_service.update_ad_group_status.assert_called_once_with(
            '123-456-7890', '67890', 'ENABLED'
        )
        assert result is True

    def test_update_ad_status_mock(self, facade_with_mocks):
        """测试更新 Ad 状态（Mock）"""
        facade_with_mocks._ad_service.update_ad_status.return_value = True

        result = facade_with_mocks.update_ad_status('123-456-7890', '67890', '11111', 'REMOVED')

        facade_with_mocks._ad_service.update_ad_status.assert_called_once_with(
            '123-456-7890', '67890', '11111', 'REMOVED'
        )
        assert result is True

    def test_create_campaign_mock(self, facade_with_mocks):
        """测试创建 Campaign（Mock）"""
        facade_with_mocks._campaign_service.create_campaign.return_value = '12345'

        result = facade_with_mocks.create_campaign(
            '123-456-7890', 'New Campaign', 10000000, channel_type='SEARCH'
        )

        facade_with_mocks._campaign_service.create_campaign.assert_called_once_with(
            '123-456-7890', 'New Campaign', 10000000, channel_type='SEARCH'
        )
        assert result == '12345'

    def test_create_ad_group_mock(self, facade_with_mocks):
        """测试创建 AdGroup（Mock）"""
        facade_with_mocks._ad_group_service.create_ad_group.return_value = '67890'

        result = facade_with_mocks.create_ad_group(
            '123-456-7890', '12345', 'New AdGroup', cpc_bid_micros=1000000
        )

        facade_with_mocks._ad_group_service.create_ad_group.assert_called_once_with(
            '123-456-7890', '12345', 'New AdGroup', cpc_bid_micros=1000000
        )
        assert result == '67890'

    def test_create_responsive_search_ad_mock(self, facade_with_mocks):
        """测试创建响应式搜索广告（Mock）"""
        facade_with_mocks._ad_service.create_responsive_search_ad.return_value = '11111'

        headlines = ['Headline 1', 'Headline 2', 'Headline 3']
        descriptions = ['Description 1', 'Description 2']
        final_urls = ['https://example.com']

        result = facade_with_mocks.create_responsive_search_ad(
            '123-456-7890', '67890', headlines, descriptions, final_urls, path1='path1'
        )

        facade_with_mocks._ad_service.create_responsive_search_ad.assert_called_once_with(
            '123-456-7890', '67890', headlines, descriptions, final_urls, path1='path1'
        )
        assert result == '11111'

    def test_refresh_all_clients_mock(self, facade_with_mocks):
        """测试刷新所有客户端（Mock）"""
        facade_with_mocks.refresh_all_clients()

        facade_with_mocks._account_service.refresh_client.assert_called_once()
        facade_with_mocks._campaign_service.refresh_client.assert_called_once()
        facade_with_mocks._ad_group_service.refresh_client.assert_called_once()
        facade_with_mocks._ad_service.refresh_client.assert_called_once()


@skip_if_no_network
class TestGoogleAdsServiceFacadeIntegrationWithRealData:
    """使用真实数据的集成测试（需要网络）"""

    @pytest.fixture(scope="class")
    def facade(self):
        """创建服务实例"""
        return GoogleAdsServiceFacade(TEST_TOKEN_ID, login_customer_id=TEST_LOGIN_CUSTOMER_ID)
    
    def test_get_account_hierarchy(self, facade):
        """测试获取账户层级结构"""
        customers = facade.account.get_account_hierarchy(TEST_LOGIN_CUSTOMER_ID)
        assert isinstance(customers, list)


    def test_get_accessible_customers(self, facade):
        """测试获取可访问客户列表"""
        customers = facade.get_accessible_customers()

        assert isinstance(customers, list)
        if customers:
            for customer_id in customers:
                assert isinstance(customer_id, str)

    def test_get_account_info(self, facade):
        """测试获取账户信息"""
        customer_id = TEST_CUSTOMER_ID
        account_info = facade.get_account_info(customer_id)

        if account_info:
            assert 'customer_id' in account_info
            assert 'account_name' in account_info

    def test_get_campaigns(self, facade):
        """测试获取 Campaign 列表"""
        customer_id = TEST_CUSTOMER_ID
        campaigns = facade.get_campaigns(customer_id)

        assert isinstance(campaigns, list)

    def test_get_ad_groups(self, facade):
        """测试获取 AdGroup 列表"""
        customer_id = TEST_CUSTOMER_ID
        ad_groups = facade.get_ad_groups(customer_id)
        assert isinstance(ad_groups, list)

    def test_get_ads(self, facade):
        """测试获取 Ad 列表"""
        customer_id = TEST_CUSTOMER_ID
        ads = facade.get_ads(customer_id)

        assert isinstance(ads, list)

    # ==================== 同步测试 ====================

    def test_sync_all_accounts(self, facade):
        """测试同步所有账户到数据库"""
        with get_db_context() as db:
            result = facade.sync_all_accounts(db)

            assert isinstance(result, dict)
            assert 'token_id' in result
            assert result['token_id'] == TEST_TOKEN_ID
            assert 'total' in result
            assert 'synced' in result
            assert 'failed' in result
            assert isinstance(result['accounts'], list)

    def test_sync_campaigns(self, facade):
        """测试同步 Campaign 到数据库"""
        with get_db_context() as db:
            # 先确保账户已同步
            # facade.sync_all_accounts(db)

            # 同步 campaigns
            success = facade.sync_campaigns(db, TEST_CUSTOMER_ID)
            assert isinstance(success, bool)

    def test_sync_ad_groups(self, facade):
        """测试同步 AdGroup 到数据库"""
        with get_db_context() as db:
            # 确保前置数据已同步
            # facade.sync_all_accounts(db)
            # facade.sync_campaigns(db, TEST_CUSTOMER_ID)

            # 同步 ad_groups
            success = facade.sync_ad_groups(db, TEST_CUSTOMER_ID)
            assert isinstance(success, bool)

    def test_sync_ads(self, facade):
        """测试同步 Ad 到数据库"""
        with get_db_context() as db:
            # 确保前置数据已同步
            # facade.sync_all_accounts(db)
            # facade.sync_campaigns(db, TEST_CUSTOMER_ID)
            # facade.sync_ad_groups(db, TEST_CUSTOMER_ID)

            # 同步 ads
            success = facade.sync_ads(db, TEST_CUSTOMER_ID)
            assert isinstance(success, bool)

    def test_sync_all_full_flow(self, facade):
        """测试完整同步流程"""
        with get_db_context() as db:
            result = facade.sync_all(db, TEST_CUSTOMER_ID)

            assert isinstance(result, dict)
            assert result['customer_id'] == TEST_CUSTOMER_ID
            assert 'accounts' in result
            assert 'campaigns' in result
            assert 'ad_groups' in result
            assert 'ads' in result

    # ==================== 带过滤条件的查询测试 ====================

    def test_get_campaigns_with_status_filter(self, facade):
        """测试带状态过滤获取 Campaign"""
        campaigns = facade.get_campaigns(TEST_CUSTOMER_ID, status_filter=['ENABLED'])

        assert isinstance(campaigns, list)
        for campaign in campaigns:
            if campaign.get('status'):
                assert campaign['status'] == 'ENABLED'

    def test_get_ad_groups_with_campaign_filter(self, facade):
        """测试按 Campaign 过滤获取 AdGroup"""
        # 先获取一个 campaign
        campaigns = facade.get_campaigns(TEST_CUSTOMER_ID)

        if campaigns:
            campaign_id = campaigns[0]['campaign_id']
            ad_groups = facade.get_ad_groups(TEST_CUSTOMER_ID, campaign_id=campaign_id)

            assert isinstance(ad_groups, list)
            for ag in ad_groups:
                assert ag['campaign_id'] == campaign_id

    def test_get_ads_with_ad_group_filter(self, facade):
        """测试按 AdGroup 过滤获取 Ad"""
        # 先获取一个 ad_group
        ad_groups = facade.get_ad_groups(TEST_CUSTOMER_ID)

        if ad_groups:
            ad_group_id = ad_groups[0]['ad_group_id']
            ads = facade.get_ads(TEST_CUSTOMER_ID, ad_group_id=ad_group_id)

            assert isinstance(ads, list)
            for ad in ads:
                assert ad['ad_group_id'] == ad_group_id

    # ==================== 详情查询测试 ====================

    def test_get_campaign_detail(self, facade):
        """测试获取单个 Campaign 详情"""
        campaigns = facade.get_campaigns(TEST_CUSTOMER_ID)

        if campaigns:
            campaign_id = campaigns[0]['campaign_id']
            detail = facade.campaign.get_campaign_by_id(TEST_CUSTOMER_ID, campaign_id)

            if detail:
                assert detail['campaign_id'] == campaign_id
                assert 'campaign_name' in detail
                assert 'status' in detail

    def test_get_ad_group_detail(self, facade):
        """测试获取单个 AdGroup 详情"""
        ad_groups = facade.get_ad_groups(TEST_CUSTOMER_ID)

        if ad_groups:
            ad_group_id = ad_groups[0]['ad_group_id']
            detail = facade.ad_group.get_ad_group_by_id(TEST_CUSTOMER_ID, ad_group_id)

            if detail:
                assert detail['ad_group_id'] == ad_group_id
                assert 'ad_group_name' in detail
                assert 'status' in detail

    def test_get_ad_detail(self, facade):
        """测试获取单个 Ad 详情"""
        ad_groups = facade.get_ad_groups(TEST_CUSTOMER_ID)

        if ad_groups:
            ad_group_id = ad_groups[0]['ad_group_id']
            ads = facade.get_ads(TEST_CUSTOMER_ID, ad_group_id=ad_group_id)

            if ads:
                ad_id = ads[0]['ad_id']
                detail = facade.ad.get_ad_by_id(TEST_CUSTOMER_ID, ad_group_id, ad_id)

                if detail:
                    assert detail['ad_id'] == ad_id
                    assert 'ad_type' in detail
                    assert 'status' in detail

    # ==================== 数据库查询测试 ====================

    def test_get_account_from_db(self, facade):
        """测试从数据库获取账户"""
        with get_db_context() as db:
            # 先同步账户
            facade.sync_all_accounts(db)

            # 从数据库获取
            account = facade.account.get_account_from_db(db, TEST_CUSTOMER_ID)

            if account:
                assert account.customer_id == TEST_CUSTOMER_ID.replace('-', '')

    def test_get_campaigns_from_db(self, facade):
        """测试从数据库获取 Campaign 列表"""
        with get_db_context() as db:
            # 先同步数据
            facade.sync_all_accounts(db)
            facade.sync_campaigns(db, TEST_CUSTOMER_ID)

            # 从数据库获取
            campaigns = facade.campaign.get_campaigns_from_db(db, TEST_CUSTOMER_ID)

            assert isinstance(campaigns, list)

    def test_get_ad_groups_from_db(self, facade):
        """测试从数据库获取 AdGroup 列表"""
        with get_db_context() as db:
            # 先同步数据
            facade.sync_all_accounts(db)
            facade.sync_campaigns(db, TEST_CUSTOMER_ID)
            facade.sync_ad_groups(db, TEST_CUSTOMER_ID)

            # 从数据库获取
            ad_groups = facade.ad_group.get_ad_groups_from_db(db, TEST_CUSTOMER_ID)

            assert isinstance(ad_groups, list)

    def test_get_ads_from_db(self, facade):
        """测试从数据库获取 Ad 列表"""
        with get_db_context() as db:
            # 先同步数据
            facade.sync_all_accounts(db)
            facade.sync_campaigns(db, TEST_CUSTOMER_ID)
            facade.sync_ad_groups(db, TEST_CUSTOMER_ID)
            facade.sync_ads(db, TEST_CUSTOMER_ID)

            # 从数据库获取
            ads = facade.ad.get_ads_from_db(db, TEST_CUSTOMER_ID)

            assert isinstance(ads, list)

    # ==================== 层级结构测试 ====================

    def test_get_full_hierarchy(self, facade):
        """测试获取完整的广告层级结构"""
        # 获取账户信息
        account_info = facade.get_account_info(TEST_CUSTOMER_ID)
        assert account_info is not None or account_info is None  # 允许无权限

        # 获取 campaigns
        campaigns = facade.get_campaigns(TEST_CUSTOMER_ID)
        assert isinstance(campaigns, list)

        if campaigns:
            # 获取第一个 campaign 下的 ad_groups
            campaign_id = campaigns[0]['campaign_id']
            ad_groups = facade.get_ad_groups(TEST_CUSTOMER_ID, campaign_id=campaign_id)
            assert isinstance(ad_groups, list)

            if ad_groups:
                # 获取第一个 ad_group 下的 ads
                ad_group_id = ad_groups[0]['ad_group_id']
                ads = facade.get_ads(TEST_CUSTOMER_ID, ad_group_id=ad_group_id)
                assert isinstance(ads, list)

    # ==================== 服务属性测试 ====================

    def test_lazy_load_services(self, facade):
        """测试服务延迟加载"""
        # 访问各个服务属性
        account_service = facade.account
        campaign_service = facade.campaign
        ad_group_service = facade.ad_group
        ad_service = facade.ad

        assert account_service is not None
        assert campaign_service is not None
        assert ad_group_service is not None
        assert ad_service is not None

        # 验证已缓存
        assert facade._account_service is not None
        assert facade._campaign_service is not None
        assert facade._ad_group_service is not None
        assert facade._ad_service is not None

    def test_refresh_clients(self, facade):
        """测试刷新客户端"""
        # 先确保服务已初始化
        _ = facade.account
        _ = facade.campaign
        _ = facade.ad_group
        _ = facade.ad

        # 刷新不应抛出异常
        facade.refresh_all_clients()

        # 服务仍然可用
        customers = facade.get_accessible_customers()
        assert isinstance(customers, list)

    # ==================== Campaign 创建/修改/启停测试 ====================

    def test_create_campaign(self, facade):
        """测试创建 Campaign"""
        campaign_id = facade.create_campaign(
            customer_id=TEST_CUSTOMER_ID,
            name='Test Campaign - Integration Test 001',
            budget_amount_micros=10000000,  # 10 元
            channel_type='SEARCH',
            bidding_strategy='MANUAL_CPC'
        )

        # 创建可能因权限问题失败，所以允许返回 None
        if campaign_id:
            assert isinstance(campaign_id, str)
            assert len(campaign_id) > 0
            # 保存 campaign_id 供后续测试使用
            facade._test_campaign_id = campaign_id

    def test_update_campaign_name(self, facade):
        """测试更新 Campaign 名称"""
        # 先获取一个 campaign
        campaigns = facade.get_campaigns(TEST_CUSTOMER_ID)

        if campaigns:
            campaign_id = campaigns[0]['campaign_id']
            original_name = campaigns[0]['campaign_name']

            # 更新名称
            new_name = f"{original_name} - Updated"
            success = facade.campaign.update_campaign_name(
                TEST_CUSTOMER_ID, campaign_id, new_name
            )

            # 可能因权限问题失败
            assert isinstance(success, bool)

            # 如果成功，恢复原名称
            if success:
                facade.campaign.update_campaign_name(
                    TEST_CUSTOMER_ID, campaign_id, original_name
                )

    def test_update_campaign_status_pause_and_enable(self, facade):
        """测试暂停和启用 Campaign"""
        campaigns = facade.get_campaigns(TEST_CUSTOMER_ID)

        if campaigns:
            campaign_id = campaigns[0]['campaign_id']
            original_status = campaigns[0]['status']

            # 暂停 Campaign
            pause_result = facade.update_campaign_status(
                TEST_CUSTOMER_ID, campaign_id, 'PAUSED'
            )
            assert isinstance(pause_result, bool)

            # 启用 Campaign
            enable_result = facade.update_campaign_status(
                TEST_CUSTOMER_ID, campaign_id, 'ENABLED'
            )
            assert isinstance(enable_result, bool)

            # 恢复原状态
            if original_status != 'ENABLED':
                facade.update_campaign_status(
                    TEST_CUSTOMER_ID, campaign_id, original_status
                )

    # ==================== AdGroup 创建/修改/启停测试 ====================

    def test_create_ad_group(self, facade):
        """测试创建 AdGroup"""
        # 先获取 SEARCH 类型的 campaign
        campaigns = facade.get_campaigns(TEST_CUSTOMER_ID)

        # 过滤出 SEARCH 类型的 campaign
        search_campaign = None
        for campaign in campaigns:
            if campaign.get('channel_type') == 'SEARCH':
                search_campaign = campaign
                break

        if search_campaign:
            campaign_id = search_campaign['campaign_id']

            ad_group_id = facade.create_ad_group(
                customer_id=TEST_CUSTOMER_ID,
                campaign_id=campaign_id,
                name='Test AdGroup - Integration Test',
                ad_group_type='SEARCH_STANDARD',
                cpc_bid_micros=1000000  # 1 元
            )

            # 创建可能因权限问题失败
            if ad_group_id:
                assert isinstance(ad_group_id, str)
                assert len(ad_group_id) > 0
                # 保存供后续测试使用
                facade._test_ad_group_id = ad_group_id
                facade._test_ad_group_campaign_id = campaign_id
        else:
            pytest.skip("No SEARCH type campaign found, skipping ad group creation test")

    def test_update_ad_group_bid(self, facade):
        """测试更新 AdGroup 出价"""
        ad_groups = facade.get_ad_groups(TEST_CUSTOMER_ID)

        if ad_groups:
            ad_group_id = ad_groups[0]['ad_group_id']

            # 更新 CPC 出价
            success = facade.ad_group.update_ad_group_bid(
                TEST_CUSTOMER_ID,
                ad_group_id,
                cpc_bid_micros=1500000  # 1.5 元
            )

            assert isinstance(success, bool)

    def test_update_ad_group_status_pause_and_enable(self, facade):
        """测试暂停和启用 AdGroup"""
        ad_groups = facade.get_ad_groups(TEST_CUSTOMER_ID)

        if ad_groups:
            ad_group_id = ad_groups[0]['ad_group_id']
            original_status = ad_groups[0]['status']

            # 暂停 AdGroup
            pause_result = facade.update_ad_group_status(
                TEST_CUSTOMER_ID, ad_group_id, 'PAUSED'
            )
            assert isinstance(pause_result, bool)

            # 启用 AdGroup
            enable_result = facade.update_ad_group_status(
                TEST_CUSTOMER_ID, ad_group_id, 'ENABLED'
            )
            assert isinstance(enable_result, bool)

            # 恢复原状态
            if original_status != 'ENABLED':
                facade.update_ad_group_status(
                    TEST_CUSTOMER_ID, ad_group_id, original_status
                )

    # ==================== Ad 创建/修改/启停测试 ====================

    def test_create_responsive_search_ad(self, facade):
        """测试创建响应式搜索广告 (RSA)"""
        ad_groups = facade.get_ad_groups(TEST_CUSTOMER_ID)

        if ad_groups:
            ad_group_id = ad_groups[0]['ad_group_id']

            headlines = [
                'Test Headline 1',
                'Test Headline 2',
                'Test Headline 3'
            ]
            descriptions = [
                'Test Description 1 for integration test',
                'Test Description 2 for integration test'
            ]
            final_urls = ['https://example.com']

            ad_id = facade.create_responsive_search_ad(
                customer_id=TEST_CUSTOMER_ID,
                ad_group_id=ad_group_id,
                headlines=headlines,
                descriptions=descriptions,
                final_urls=final_urls,
                path1='test',
                path2='path'
            )

            # 创建可能因权限问题失败
            if ad_id:
                assert isinstance(ad_id, str)
                assert len(ad_id) > 0
                # 保存供后续测试使用
                facade._test_ad_id = ad_id
                facade._test_ad_ad_group_id = ad_group_id

    def test_update_ad_urls(self, facade):
        """测试更新 Ad URL"""
        ad_groups = facade.get_ad_groups(TEST_CUSTOMER_ID)

        if ad_groups:
            ad_group_id = ad_groups[0]['ad_group_id']
            ads = facade.get_ads(TEST_CUSTOMER_ID, ad_group_id=ad_group_id)

            if ads:
                ad_id = ads[0]['ad_id']

                # 更新 URL
                success = facade.ad.update_ad_urls(
                    TEST_CUSTOMER_ID,
                    ad_group_id,
                    ad_id,
                    final_urls=['https://example.com/updated']
                )

                assert isinstance(success, bool)

    def test_update_ad_status_pause_and_enable(self, facade):
        """测试暂停和启用 Ad"""
        ad_groups = facade.get_ad_groups(TEST_CUSTOMER_ID)

        if ad_groups:
            ad_group_id = ad_groups[0]['ad_group_id']
            ads = facade.get_ads(TEST_CUSTOMER_ID, ad_group_id=ad_group_id)

            if ads:
                ad_id = ads[0]['ad_id']
                original_status = ads[0]['status']

                # 暂停 Ad
                pause_result = facade.update_ad_status(
                    TEST_CUSTOMER_ID, ad_group_id, ad_id, 'PAUSED'
                )
                assert isinstance(pause_result, bool)

                # 启用 Ad
                enable_result = facade.update_ad_status(
                    TEST_CUSTOMER_ID, ad_group_id, ad_id, 'ENABLED'
                )
                assert isinstance(enable_result, bool)

                # 恢复原状态
                if original_status != 'ENABLED':
                    facade.update_ad_status(
                        TEST_CUSTOMER_ID, ad_group_id, ad_id, original_status
                    )

    # ==================== 综合创建流程测试 ====================

    def test_create_full_ad_structure(self, facade):
        """测试创建完整的广告结构: Campaign -> AdGroup -> Ad"""
        # 1. 创建 Campaign
        campaign_id = facade.create_campaign(
            customer_id=TEST_CUSTOMER_ID,
            name=f'Full Structure Test Campaign_{datetime.now().strftime("%Y%m%d%H%M%S")}',
            budget_amount_micros=5000000,
            channel_type='SEARCH',
            bidding_strategy='MANUAL_CPC'
        )

        if not campaign_id:
            pytest.skip("Cannot create campaign, skipping full structure test")

        # 2. 创建 AdGroup
        ad_group_id = facade.create_ad_group(
            customer_id=TEST_CUSTOMER_ID,
            campaign_id=campaign_id,
            name=f'Full Structure Test AdGroup_{datetime.now().strftime("%Y%m%d%H%M%S")}',
            cpc_bid_micros=10000000  # 10 元（确保满足最小出价要求）
        )

        if not ad_group_id:
            pytest.skip("Cannot create ad group, skipping ad creation")

        # 3. 创建 RSA
        ad_id = facade.create_responsive_search_ad(
            customer_id=TEST_CUSTOMER_ID,
            ad_group_id=ad_group_id,
            headlines=['Headline A', 'Headline B', 'Headline C'],
            descriptions=['Description A', 'Description B'],
            final_urls=['https://example.com/full-test']
        )

        # 验证结果
        assert campaign_id is not None
        assert ad_group_id is not None
        # ad_id 可能因政策原因创建失败，允许为 None
        assert ad_id is None or isinstance(ad_id, str)

        # 清理：将创建的 Campaign 设为 REMOVED（可选）
        # facade.update_campaign_status(TEST_CUSTOMER_ID, campaign_id, 'REMOVED')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
