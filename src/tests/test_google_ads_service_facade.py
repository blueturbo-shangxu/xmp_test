"""
Google Ads Service Facade 单元测试
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List

from src.services.google.service_facade import GoogleAdsServiceFacade, GoogleAdsService


class TestGoogleAdsServiceFacadeInit:
    """测试 Facade 初始化"""

    def test_init_with_token_id(self):
        """测试使用 token_id 初始化"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = 1
        facade._account_service = None
        facade._campaign_service = None
        facade._ad_group_service = None
        facade._ad_service = None

        assert facade.token_id == 1
        assert facade._account_service is None
        assert facade._campaign_service is None
        assert facade._ad_group_service is None
        assert facade._ad_service is None

    def test_google_ads_service_alias(self):
        """测试 GoogleAdsService 是 GoogleAdsServiceFacade 的别名"""
        assert GoogleAdsService is GoogleAdsServiceFacade


class TestGoogleAdsServiceFacadeLazyInit:
    """测试延迟初始化"""

    @pytest.fixture
    def facade(self):
        """创建一个未初始化子服务的 facade"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = 1
        facade._account_service = None
        facade._campaign_service = None
        facade._ad_group_service = None
        facade._ad_service = None
        return facade

    @patch('src.services.google.service_facade.GoogleAdsAccountService')
    def test_account_property_lazy_init(self, mock_account_service, facade):
        """测试 account 属性延迟初始化"""
        mock_instance = Mock()
        mock_account_service.return_value = mock_instance

        # 第一次访问应该创建实例
        result = facade.account
        mock_account_service.assert_called_once_with(1)
        assert result == mock_instance

        # 第二次访问应该返回缓存的实例
        result2 = facade.account
        mock_account_service.assert_called_once()  # 不应该再次调用
        assert result2 == mock_instance

    @patch('src.services.google.service_facade.GoogleAdsCampaignService')
    def test_campaign_property_lazy_init(self, mock_campaign_service, facade):
        """测试 campaign 属性延迟初始化"""
        mock_instance = Mock()
        mock_campaign_service.return_value = mock_instance

        result = facade.campaign
        mock_campaign_service.assert_called_once_with(1)
        assert result == mock_instance

    @patch('src.services.google.service_facade.GoogleAdsAdGroupService')
    def test_ad_group_property_lazy_init(self, mock_ad_group_service, facade):
        """测试 ad_group 属性延迟初始化"""
        mock_instance = Mock()
        mock_ad_group_service.return_value = mock_instance

        result = facade.ad_group
        mock_ad_group_service.assert_called_once_with(1)
        assert result == mock_instance

    @patch('src.services.google.service_facade.GoogleAdsAdService')
    def test_ad_property_lazy_init(self, mock_ad_service, facade):
        """测试 ad 属性延迟初始化"""
        mock_instance = Mock()
        mock_ad_service.return_value = mock_instance

        result = facade.ad
        mock_ad_service.assert_called_once_with(1)
        assert result == mock_instance


class TestGoogleAdsServiceFacadeAccountMethods:
    """测试账户相关方法"""

    @pytest.fixture
    def facade_with_mock_account(self):
        """创建带有 mock account 服务的 facade"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = 1
        facade._account_service = Mock()
        facade._campaign_service = None
        facade._ad_group_service = None
        facade._ad_service = None
        return facade

    def test_get_accessible_customers(self, facade_with_mock_account):
        """测试获取可访问客户列表"""
        expected = ['123-456-7890', '234-567-8901']
        facade_with_mock_account._account_service.get_accessible_customers.return_value = expected

        result = facade_with_mock_account.get_accessible_customers()

        facade_with_mock_account._account_service.get_accessible_customers.assert_called_once()
        assert result == expected

    def test_get_account_info(self, facade_with_mock_account):
        """测试获取账户信息"""
        expected = {
            'customer_id': '123-456-7890',
            'account_name': 'Test Account',
            'currency_code': 'USD',
            'timezone': 'America/Los_Angeles',
            'account_type': 'CLIENT',
            'status': 'ENABLED'
        }
        facade_with_mock_account._account_service.get_account_info.return_value = expected

        result = facade_with_mock_account.get_account_info('123-456-7890')

        facade_with_mock_account._account_service.get_account_info.assert_called_once_with('123-456-7890')
        assert result == expected

    def test_sync_all_accounts(self, facade_with_mock_account):
        """测试同步所有账户"""
        mock_db = Mock()
        expected = {
            'token_id': 1,
            'total': 2,
            'synced': 2,
            'failed': 0,
            'accounts': [],
            'errors': []
        }
        facade_with_mock_account._account_service.sync_all_accounts.return_value = expected

        result = facade_with_mock_account.sync_all_accounts(mock_db)

        facade_with_mock_account._account_service.sync_all_accounts.assert_called_once_with(mock_db)
        assert result == expected


class TestGoogleAdsServiceFacadeCampaignMethods:
    """测试 Campaign 相关方法"""

    @pytest.fixture
    def facade_with_mock_campaign(self):
        """创建带有 mock campaign 服务的 facade"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = 1
        facade._account_service = None
        facade._campaign_service = Mock()
        facade._ad_group_service = None
        facade._ad_service = None
        return facade

    def test_get_campaigns(self, facade_with_mock_campaign):
        """测试获取 Campaign 列表"""
        expected = [
            {'campaign_id': '111', 'campaign_name': 'Campaign 1', 'status': 'ENABLED'},
            {'campaign_id': '222', 'campaign_name': 'Campaign 2', 'status': 'PAUSED'}
        ]
        facade_with_mock_campaign._campaign_service.get_campaigns.return_value = expected

        result = facade_with_mock_campaign.get_campaigns('123-456-7890')

        facade_with_mock_campaign._campaign_service.get_campaigns.assert_called_once_with('123-456-7890', None)
        assert result == expected

    def test_get_campaigns_with_filter(self, facade_with_mock_campaign):
        """测试带过滤条件获取 Campaign 列表"""
        expected = [{'campaign_id': '111', 'campaign_name': 'Campaign 1', 'status': 'ENABLED'}]
        facade_with_mock_campaign._campaign_service.get_campaigns.return_value = expected

        result = facade_with_mock_campaign.get_campaigns('123-456-7890', status_filter=['ENABLED'])

        facade_with_mock_campaign._campaign_service.get_campaigns.assert_called_once_with(
            '123-456-7890', ['ENABLED']
        )
        assert result == expected

    def test_sync_campaigns(self, facade_with_mock_campaign):
        """测试同步 Campaign"""
        mock_db = Mock()
        facade_with_mock_campaign._campaign_service.sync_campaigns.return_value = True

        result = facade_with_mock_campaign.sync_campaigns(mock_db, '123-456-7890')

        facade_with_mock_campaign._campaign_service.sync_campaigns.assert_called_once_with(
            mock_db, '123-456-7890', None
        )
        assert result is True

    def test_sync_campaigns_with_task_id(self, facade_with_mock_campaign):
        """测试带任务ID同步 Campaign"""
        mock_db = Mock()
        facade_with_mock_campaign._campaign_service.sync_campaigns.return_value = True

        result = facade_with_mock_campaign.sync_campaigns(mock_db, '123-456-7890', task_id=100)

        facade_with_mock_campaign._campaign_service.sync_campaigns.assert_called_once_with(
            mock_db, '123-456-7890', 100
        )
        assert result is True

    def test_create_campaign(self, facade_with_mock_campaign):
        """测试创建 Campaign"""
        facade_with_mock_campaign._campaign_service.create_campaign.return_value = '12345'

        result = facade_with_mock_campaign.create_campaign(
            '123-456-7890',
            'New Campaign',
            10000000,
            channel_type='SEARCH'
        )

        facade_with_mock_campaign._campaign_service.create_campaign.assert_called_once_with(
            '123-456-7890', 'New Campaign', 10000000, channel_type='SEARCH'
        )
        assert result == '12345'


class TestGoogleAdsServiceFacadeAdGroupMethods:
    """测试 AdGroup 相关方法"""

    @pytest.fixture
    def facade_with_mock_ad_group(self):
        """创建带有 mock ad_group 服务的 facade"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = 1
        facade._account_service = None
        facade._campaign_service = None
        facade._ad_group_service = Mock()
        facade._ad_service = None
        return facade

    def test_get_ad_groups(self, facade_with_mock_ad_group):
        """测试获取 AdGroup 列表"""
        expected = [
            {'ad_group_id': '111', 'ad_group_name': 'AdGroup 1', 'status': 'ENABLED'},
            {'ad_group_id': '222', 'ad_group_name': 'AdGroup 2', 'status': 'PAUSED'}
        ]
        facade_with_mock_ad_group._ad_group_service.get_ad_groups.return_value = expected

        result = facade_with_mock_ad_group.get_ad_groups('123-456-7890')

        facade_with_mock_ad_group._ad_group_service.get_ad_groups.assert_called_once_with(
            '123-456-7890', None, None
        )
        assert result == expected

    def test_get_ad_groups_with_campaign_filter(self, facade_with_mock_ad_group):
        """测试按 Campaign 过滤获取 AdGroup"""
        expected = [{'ad_group_id': '111', 'ad_group_name': 'AdGroup 1'}]
        facade_with_mock_ad_group._ad_group_service.get_ad_groups.return_value = expected

        result = facade_with_mock_ad_group.get_ad_groups('123-456-7890', campaign_id='999')

        facade_with_mock_ad_group._ad_group_service.get_ad_groups.assert_called_once_with(
            '123-456-7890', '999', None
        )
        assert result == expected

    def test_sync_ad_groups(self, facade_with_mock_ad_group):
        """测试同步 AdGroup"""
        mock_db = Mock()
        facade_with_mock_ad_group._ad_group_service.sync_ad_groups.return_value = True

        result = facade_with_mock_ad_group.sync_ad_groups(mock_db, '123-456-7890')

        facade_with_mock_ad_group._ad_group_service.sync_ad_groups.assert_called_once_with(
            mock_db, '123-456-7890', None, None
        )
        assert result is True

    def test_create_ad_group(self, facade_with_mock_ad_group):
        """测试创建 AdGroup"""
        facade_with_mock_ad_group._ad_group_service.create_ad_group.return_value = '67890'

        result = facade_with_mock_ad_group.create_ad_group(
            '123-456-7890',
            '12345',
            'New AdGroup',
            cpc_bid_micros=1000000
        )

        facade_with_mock_ad_group._ad_group_service.create_ad_group.assert_called_once_with(
            '123-456-7890', '12345', 'New AdGroup', cpc_bid_micros=1000000
        )
        assert result == '67890'


class TestGoogleAdsServiceFacadeAdMethods:
    """测试 Ad 相关方法"""

    @pytest.fixture
    def facade_with_mock_ad(self):
        """创建带有 mock ad 服务的 facade"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = 1
        facade._account_service = None
        facade._campaign_service = None
        facade._ad_group_service = None
        facade._ad_service = Mock()
        return facade

    def test_get_ads(self, facade_with_mock_ad):
        """测试获取 Ad 列表"""
        expected = [
            {'ad_id': '111', 'ad_name': 'Ad 1', 'status': 'ENABLED'},
            {'ad_id': '222', 'ad_name': 'Ad 2', 'status': 'PAUSED'}
        ]
        facade_with_mock_ad._ad_service.get_ads.return_value = expected

        result = facade_with_mock_ad.get_ads('123-456-7890')

        facade_with_mock_ad._ad_service.get_ads.assert_called_once_with('123-456-7890', None, None)
        assert result == expected

    def test_get_ads_with_ad_group_filter(self, facade_with_mock_ad):
        """测试按 AdGroup 过滤获取 Ad"""
        expected = [{'ad_id': '111', 'ad_name': 'Ad 1'}]
        facade_with_mock_ad._ad_service.get_ads.return_value = expected

        result = facade_with_mock_ad.get_ads('123-456-7890', ad_group_id='999')

        facade_with_mock_ad._ad_service.get_ads.assert_called_once_with('123-456-7890', '999', None)
        assert result == expected

    def test_sync_ads(self, facade_with_mock_ad):
        """测试同步 Ad"""
        mock_db = Mock()
        facade_with_mock_ad._ad_service.sync_ads.return_value = True

        result = facade_with_mock_ad.sync_ads(mock_db, '123-456-7890')

        facade_with_mock_ad._ad_service.sync_ads.assert_called_once_with(
            mock_db, '123-456-7890', None, None
        )
        assert result is True

    def test_create_responsive_search_ad(self, facade_with_mock_ad):
        """测试创建响应式搜索广告"""
        facade_with_mock_ad._ad_service.create_responsive_search_ad.return_value = '11111'

        headlines = ['Headline 1', 'Headline 2', 'Headline 3']
        descriptions = ['Description 1', 'Description 2']
        final_urls = ['https://example.com']

        result = facade_with_mock_ad.create_responsive_search_ad(
            '123-456-7890',
            '67890',
            headlines,
            descriptions,
            final_urls,
            path1='path1'
        )

        facade_with_mock_ad._ad_service.create_responsive_search_ad.assert_called_once_with(
            '123-456-7890', '67890', headlines, descriptions, final_urls, path1='path1'
        )
        assert result == '11111'


class TestGoogleAdsServiceFacadeSyncMethods:
    """测试批量同步方法"""

    @pytest.fixture
    def facade_with_all_mocks(self):
        """创建带有所有 mock 服务的 facade"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = 1
        facade._account_service = Mock()
        facade._campaign_service = Mock()
        facade._ad_group_service = Mock()
        facade._ad_service = Mock()
        return facade

    def test_sync_all_success(self, facade_with_all_mocks):
        """测试完整同步成功"""
        mock_db = Mock()

        # 设置 mock 返回值
        facade_with_all_mocks._account_service._sync_single_account.return_value = {'success': True}
        facade_with_all_mocks._campaign_service.sync_campaigns.return_value = True
        facade_with_all_mocks._ad_group_service.sync_ad_groups.return_value = True
        facade_with_all_mocks._ad_service.sync_ads.return_value = True

        result = facade_with_all_mocks.sync_all(mock_db, '123-456-7890')

        assert result['customer_id'] == '123-456-7890'
        assert result['accounts']['success'] is True
        assert result['campaigns']['success'] is True
        assert result['ad_groups']['success'] is True
        assert result['ads']['success'] is True

    def test_sync_all_account_failed(self, facade_with_all_mocks):
        """测试同步账户失败时停止"""
        mock_db = Mock()

        facade_with_all_mocks._account_service._sync_single_account.return_value = {
            'success': False,
            'error': 'Account sync failed'
        }

        result = facade_with_all_mocks.sync_all(mock_db, '123-456-7890')

        assert result['accounts']['success'] is False
        assert result['accounts']['error'] == 'Account sync failed'
        assert result['campaigns']['success'] is False
        # 验证后续同步没有被调用
        facade_with_all_mocks._campaign_service.sync_campaigns.assert_not_called()

    def test_sync_all_campaign_failed(self, facade_with_all_mocks):
        """测试同步 Campaign 失败时停止"""
        mock_db = Mock()

        facade_with_all_mocks._account_service._sync_single_account.return_value = {'success': True}
        facade_with_all_mocks._campaign_service.sync_campaigns.return_value = False

        result = facade_with_all_mocks.sync_all(mock_db, '123-456-7890')

        assert result['accounts']['success'] is True
        assert result['campaigns']['success'] is False
        assert result['campaigns']['error'] == 'Campaign sync failed'
        # 验证后续同步没有被调用
        facade_with_all_mocks._ad_group_service.sync_ad_groups.assert_not_called()

    def test_sync_campaign_tree_success(self, facade_with_all_mocks):
        """测试 Campaign 树同步成功"""
        mock_db = Mock()

        facade_with_all_mocks._ad_group_service.sync_ad_groups.return_value = True
        facade_with_all_mocks._ad_group_service.get_ad_groups.return_value = [
            {'ad_group_id': '111'},
            {'ad_group_id': '222'}
        ]
        facade_with_all_mocks._ad_service.sync_ads.return_value = True

        result = facade_with_all_mocks.sync_campaign_tree(mock_db, '123-456-7890', '12345')

        assert result['customer_id'] == '123-456-7890'
        assert result['campaign_id'] == '12345'
        assert result['ad_groups']['success'] is True
        assert result['ads']['success'] is True

        # 验证 sync_ads 被为每个 ad_group 调用
        assert facade_with_all_mocks._ad_service.sync_ads.call_count == 2

    def test_sync_campaign_tree_ad_group_failed(self, facade_with_all_mocks):
        """测试 Campaign 树同步时 AdGroup 失败"""
        mock_db = Mock()

        facade_with_all_mocks._ad_group_service.sync_ad_groups.return_value = False

        result = facade_with_all_mocks.sync_campaign_tree(mock_db, '123-456-7890', '12345')

        assert result['ad_groups']['success'] is False
        assert result['ad_groups']['error'] == 'AdGroup sync failed'
        assert result['ads']['success'] is False


class TestGoogleAdsServiceFacadeStatusMethods:
    """测试状态更新方法"""

    @pytest.fixture
    def facade_with_all_mocks(self):
        """创建带有所有 mock 服务的 facade"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = 1
        facade._account_service = None
        facade._campaign_service = Mock()
        facade._ad_group_service = Mock()
        facade._ad_service = Mock()
        return facade

    def test_update_campaign_status(self, facade_with_all_mocks):
        """测试更新 Campaign 状态"""
        facade_with_all_mocks._campaign_service.update_campaign_status.return_value = True

        result = facade_with_all_mocks.update_campaign_status('123-456-7890', '12345', 'PAUSED')

        facade_with_all_mocks._campaign_service.update_campaign_status.assert_called_once_with(
            '123-456-7890', '12345', 'PAUSED'
        )
        assert result is True

    def test_update_ad_group_status(self, facade_with_all_mocks):
        """测试更新 AdGroup 状态"""
        facade_with_all_mocks._ad_group_service.update_ad_group_status.return_value = True

        result = facade_with_all_mocks.update_ad_group_status('123-456-7890', '67890', 'ENABLED')

        facade_with_all_mocks._ad_group_service.update_ad_group_status.assert_called_once_with(
            '123-456-7890', '67890', 'ENABLED'
        )
        assert result is True

    def test_update_ad_status(self, facade_with_all_mocks):
        """测试更新 Ad 状态"""
        facade_with_all_mocks._ad_service.update_ad_status.return_value = True

        result = facade_with_all_mocks.update_ad_status('123-456-7890', '67890', '11111', 'REMOVED')

        facade_with_all_mocks._ad_service.update_ad_status.assert_called_once_with(
            '123-456-7890', '67890', '11111', 'REMOVED'
        )
        assert result is True


class TestGoogleAdsServiceFacadeUtilMethods:
    """测试工具方法"""

    def test_refresh_all_clients(self):
        """测试刷新所有客户端"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = 1
        facade._account_service = Mock()
        facade._campaign_service = Mock()
        facade._ad_group_service = Mock()
        facade._ad_service = Mock()

        facade.refresh_all_clients()

        facade._account_service.refresh_client.assert_called_once()
        facade._campaign_service.refresh_client.assert_called_once()
        facade._ad_group_service.refresh_client.assert_called_once()
        facade._ad_service.refresh_client.assert_called_once()

    def test_refresh_all_clients_with_none_services(self):
        """测试未初始化服务时刷新不报错"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = 1
        facade._account_service = None
        facade._campaign_service = None
        facade._ad_group_service = None
        facade._ad_service = None

        # 不应该抛出异常
        facade.refresh_all_clients()


class TestGoogleAdsServiceFacadeIntegration:
    """集成测试场景"""

    @pytest.fixture
    def facade_with_all_mocks(self):
        """创建带有所有 mock 服务的 facade"""
        facade = GoogleAdsServiceFacade.__new__(GoogleAdsServiceFacade)
        facade.token_id = 1
        facade._account_service = Mock()
        facade._campaign_service = Mock()
        facade._ad_group_service = Mock()
        facade._ad_service = Mock()
        return facade

    def test_full_workflow_get_hierarchy(self, facade_with_all_mocks):
        """测试完整工作流：获取账户层级数据"""
        # 设置 mock 数据
        facade_with_all_mocks._account_service.get_accessible_customers.return_value = ['123-456-7890']
        facade_with_all_mocks._account_service.get_account_info.return_value = {
            'customer_id': '123-456-7890',
            'account_name': 'Test Account'
        }
        facade_with_all_mocks._campaign_service.get_campaigns.return_value = [
            {'campaign_id': '111', 'campaign_name': 'Campaign 1'}
        ]
        facade_with_all_mocks._ad_group_service.get_ad_groups.return_value = [
            {'ad_group_id': '222', 'ad_group_name': 'AdGroup 1'}
        ]
        facade_with_all_mocks._ad_service.get_ads.return_value = [
            {'ad_id': '333', 'ad_name': 'Ad 1'}
        ]

        # 执行工作流
        customers = facade_with_all_mocks.get_accessible_customers()
        assert len(customers) == 1

        account_info = facade_with_all_mocks.get_account_info(customers[0])
        assert account_info['account_name'] == 'Test Account'

        campaigns = facade_with_all_mocks.get_campaigns(customers[0])
        assert len(campaigns) == 1

        ad_groups = facade_with_all_mocks.get_ad_groups(customers[0], campaigns[0]['campaign_id'])
        assert len(ad_groups) == 1

        ads = facade_with_all_mocks.get_ads(customers[0], ad_groups[0]['ad_group_id'])
        assert len(ads) == 1

    def test_exception_handling_in_sync_all(self, facade_with_all_mocks):
        """测试 sync_all 中的异常处理"""
        mock_db = Mock()
        facade_with_all_mocks._account_service._sync_single_account.side_effect = Exception('Unexpected error')

        result = facade_with_all_mocks.sync_all(mock_db, '123-456-7890')

        # 应该返回初始结果，不应该崩溃
        assert result['accounts']['success'] is False
        assert result['campaigns']['success'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
