"""
Services module - Business logic services
"""
# Google 服务
from src.services.google import (
    oauth_service,
    GoogleAdsOAuthService,
    GoogleAdsBaseService,
    GoogleAdsAccountService,
    GoogleAdsCampaignService,
    GoogleAdsAdGroupService,
    GoogleAdsAdService,
    GoogleAdsServiceFacade,
    GoogleAdsService,
)

# 飞书服务
from src.services.feishu_service import feishu_oauth_service, FeishuOAuthService, IdpEnum

__all__ = [
    # Google OAuth
    'oauth_service',
    'GoogleAdsOAuthService',

    # Google Ads 服务（推荐使用 Facade）
    'GoogleAdsServiceFacade',
    'GoogleAdsService',

    # Google Ads 分层服务
    'GoogleAdsBaseService',
    'GoogleAdsAccountService',
    'GoogleAdsCampaignService',
    'GoogleAdsAdGroupService',
    'GoogleAdsAdService',

    # 飞书服务
    'feishu_oauth_service',
    'FeishuOAuthService',
    'IdpEnum',
]
