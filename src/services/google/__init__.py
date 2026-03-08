"""
Google Services module - Google Ads OAuth and API services
"""
# OAuth 服务
from src.services.google.oauth_service import oauth_service, GoogleAdsOAuthService

# 基础服务
from src.services.google.base_service import GoogleAdsBaseService

# 分层服务
from src.services.google.account_service import GoogleAdsAccountService
from src.services.google.campaign_service import GoogleAdsCampaignService
from src.services.google.ad_group_service import GoogleAdsAdGroupService
from src.services.google.ad_service import GoogleAdsAdService

# 外观服务（推荐使用）
from src.services.google.service_facade import GoogleAdsServiceFacade, GoogleAdsService

__all__ = [
    # OAuth
    'oauth_service',
    'GoogleAdsOAuthService',

    # 基础服务
    'GoogleAdsBaseService',

    # 分层服务
    'GoogleAdsAccountService',
    'GoogleAdsCampaignService',
    'GoogleAdsAdGroupService',
    'GoogleAdsAdService',

    # 外观服务（推荐）
    'GoogleAdsServiceFacade',
    'GoogleAdsService',
]
