"""
Database models for XMP Auth Server (Multi-Platform Architecture)
"""
from sqlalchemy import (
    Column, BigInteger, String, Integer, Boolean, Text,
    TIMESTAMP, Date, DECIMAL, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional

from src.database import Base


# ========================================
# 通用表: OAuth Tokens (支持所有平台)
# ========================================

class OAuthToken(Base):
    """OAuth令牌表(多平台通用)"""
    __tablename__ = 'oauth_tokens'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False, index=True, comment='平台标识: google, meta, tiktok')
    account_key = Column(String(100), nullable=False, index=True, comment='账户唯一标识')
    access_token = Column(Text, nullable=False, comment='访问令牌(加密存储)')
    refresh_token = Column(Text, comment='刷新令牌(加密存储)')
    token_type = Column(String(50), default='Bearer', comment='Token类型')
    expires_at = Column(TIMESTAMP, nullable=False, index=True, comment='访问令牌过期时间')
    scope = Column(Text, comment='授权范围')
    grant_type = Column(String(50), default='authorization_code', comment='授权类型')
    is_valid = Column(Boolean, default=True, index=True, comment='Token是否有效')
    last_refreshed_at = Column(TIMESTAMP, comment='最后刷新时间')
    refresh_count = Column(Integer, default=0, comment='刷新次数')
    error_message = Column(Text, comment='最后一次错误信息')
    ext_info = Column(JSONB, default={}, comment='扩展信息(预留字段)')
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('uk_platform_account', 'platform', 'account_key', unique=True),
    )

    def __repr__(self):
        return f"<OAuthToken(platform='{self.platform}', account_key='{self.account_key}', is_valid={self.is_valid})>"

    @property
    def is_expired(self) -> bool:
        """检查token是否已过期"""
        if not self.expires_at:
            return True
        return datetime.now() > self.expires_at


# ========================================
# 通用表: Authorization Logs (支持所有平台)
# ========================================

class AuthorizationLog(Base):
    """授权操作日志表(多平台通用)"""
    __tablename__ = 'authorization_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False, index=True, comment='平台标识')
    account_key = Column(String(100), index=True, comment='账户标识')
    action_type = Column(String(20), nullable=False, index=True, comment='操作类型')
    status = Column(String(20), nullable=False, index=True, comment='操作状态')
    error_code = Column(String(50), comment='错误码')
    error_message = Column(Text, comment='错误详情')
    ip_address = Column(String(45), comment='请求IP地址')
    user_agent = Column(Text, comment='用户代理')
    request_data = Column(JSONB, comment='请求数据(脱敏)')
    response_data = Column(JSONB, comment='响应数据(脱敏)')
    duration_ms = Column(Integer, comment='操作耗时(毫秒)')
    ext_info = Column(JSONB, default={}, comment='扩展信息(预留字段)')
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    __table_args__ = (
        CheckConstraint("action_type IN ('AUTHORIZE', 'REFRESH', 'REVOKE', 'VALIDATE')", name='ck_action_type'),
        CheckConstraint("status IN ('SUCCESS', 'FAILED', 'PENDING')", name='ck_status'),
    )

    def __repr__(self):
        return f"<AuthorizationLog(platform='{self.platform}', action='{self.action_type}', status='{self.status}')>"


# ========================================
# 通用表: 同步任务表 (支持所有平台)
# ========================================

class SyncTask(Base):
    """同步任务表(多平台通用)"""
    __tablename__ = 'sync_tasks'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False, index=True, comment='平台标识: google, meta, tiktok')
    account_key = Column(String(100), nullable=False, index=True, comment='账户标识')
    task_type = Column(String(30), nullable=False, index=True, comment='任务类型: CAMPAIGNS, AD_GROUPS等')
    status = Column(String(20), default='PENDING', index=True, comment='任务状态')
    priority = Column(Integer, default=5, index=True, comment='优先级(1-10, 10最高)')
    start_date = Column(Date, comment='数据开始日期')
    end_date = Column(Date, comment='数据结束日期')
    total_records = Column(Integer, default=0, comment='总记录数')
    processed_records = Column(Integer, default=0, comment='已处理记录数')
    failed_records = Column(Integer, default=0, comment='失败记录数')
    error_message = Column(Text, comment='错误信息')
    started_at = Column(TIMESTAMP, comment='开始时间')
    completed_at = Column(TIMESTAMP, comment='完成时间')
    duration_seconds = Column(Integer, comment='耗时(秒)')
    retry_count = Column(Integer, default=0, comment='重试次数')
    next_retry_at = Column(TIMESTAMP, index=True, comment='下次重试时间')
    raw_data = Column(JSONB, comment='原始任务数据(保留完整信息)')
    ext_info = Column(JSONB, default={}, comment='扩展信息(预留字段)')
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')", name='ck_task_status'),
    )

    def __repr__(self):
        return f"<SyncTask(platform='{self.platform}', type='{self.task_type}', status='{self.status}')>"


# ========================================
# 通用表: API速率限制表 (支持所有平台)
# ========================================

class APIRateLimit(Base):
    """API速率限制表(多平台通用)"""
    __tablename__ = 'api_rate_limits'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    platform = Column(String(20), nullable=False, index=True, comment='平台标识')
    account_key = Column(String(100), nullable=False, index=True, comment='账户标识')
    endpoint = Column(String(255), nullable=False, comment='API端点')
    request_count = Column(Integer, default=0, comment='请求次数')
    quota_limit = Column(Integer, comment='配额限制')
    quota_remaining = Column(Integer, comment='剩余配额')
    window_start = Column(TIMESTAMP, nullable=False, comment='时间窗口开始')
    window_end = Column(TIMESTAMP, nullable=False, index=True, comment='时间窗口结束')
    is_throttled = Column(Boolean, default=False, index=True, comment='是否被限流')
    ext_info = Column(JSONB, default={}, comment='扩展信息(预留字段)')
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<APIRateLimit(platform='{self.platform}', endpoint='{self.endpoint}', throttled={self.is_throttled})>"


# ========================================
# Google Ads: 账户表
# ========================================

class GoogleAdAccount(Base):
    """Google Ads账户表"""
    __tablename__ = 'google_ad_accounts'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    customer_id = Column(String(50), unique=True, nullable=False, index=True, comment='Google Ads Customer ID (格式: 123-456-7890)')
    account_name = Column(String(255), nullable=False, comment='账户名称')
    currency_code = Column(String(10), default='USD', comment='币种')
    timezone = Column(String(50), default='UTC', comment='时区')
    account_type = Column(String(20), default='CLIENT', comment='账户类型: CLIENT, MANAGER')
    status = Column(String(20), default='ACTIVE', index=True, comment='账户状态')
    manager_customer_id = Column(String(50), index=True, comment='MCC管理账户ID')
    descriptive_name = Column(String(255), comment='描述性名称')
    can_manage_clients = Column(Boolean, default=False, comment='是否可管理客户')
    test_account = Column(Boolean, default=False, comment='是否测试账户')
    sync_enabled = Column(Boolean, default=True, index=True, comment='是否启用同步功能')
    raw_data = Column(JSONB, comment='原始账户数据(保留完整信息)')
    ext_info = Column(JSONB, default={}, comment='扩展信息(预留字段)')
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 关系
    campaigns = relationship("GoogleCampaign", back_populates="account", cascade="all, delete-orphan")
    ad_groups = relationship("GoogleAdGroup", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("account_type IN ('CLIENT', 'MANAGER')", name='ck_google_account_type'),
    )

    def __repr__(self):
        return f"<GoogleAdAccount(customer_id='{self.customer_id}', name='{self.account_name}')>"


# ========================================
# Google Ads: 推广活动表
# ========================================

class GoogleCampaign(Base):
    """Google Ads推广活动表"""
    __tablename__ = 'google_campaigns'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    account_id = Column(BigInteger, ForeignKey('google_ad_accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = Column(String(50), nullable=False, index=True, comment='关联的Google Ads Customer ID')
    campaign_id = Column(String(50), nullable=False, comment='Google Ads Campaign ID')
    campaign_name = Column(String(255), nullable=False, comment='推广活动名称')
    campaign_status = Column(String(20), default='ENABLED', index=True, comment='状态')
    campaign_type = Column(String(50), comment='推广活动类型')
    advertising_channel_type = Column(String(50), comment='广告网络类型')
    budget_amount = Column(DECIMAL(15, 2), comment='预算金额')
    budget_period = Column(String(20), comment='预算周期')
    bidding_strategy_type = Column(String(50), comment='出价策略类型')
    start_date = Column(Date, comment='开始日期')
    end_date = Column(Date, comment='结束日期')
    serving_status = Column(String(50), comment='投放状态')
    target_spend_micros = Column(BigInteger, comment='目标支出(微单位)')
    target_cpa_micros = Column(BigInteger, comment='目标CPA(微单位)')
    target_roas = Column(DECIMAL(10, 4), comment='目标ROAS')
    raw_data = Column(JSONB, comment='原始数据(JSON)')
    ext_info = Column(JSONB, default={}, comment='扩展信息(预留字段)')
    last_synced_at = Column(TIMESTAMP, index=True, comment='最后同步时间')
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 关系
    account = relationship("GoogleAdAccount", back_populates="campaigns")
    ad_groups = relationship("GoogleAdGroup", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        Index('uk_google_customer_campaign', 'customer_id', 'campaign_id', unique=True),
        CheckConstraint("campaign_status IN ('ENABLED', 'PAUSED', 'REMOVED')", name='ck_google_campaign_status'),
    )

    def __repr__(self):
        return f"<GoogleCampaign(campaign_id='{self.campaign_id}', name='{self.campaign_name}')>"


# ========================================
# Google Ads: 广告组表
# ========================================

class GoogleAdGroup(Base):
    """Google Ads广告组表"""
    __tablename__ = 'google_ad_groups'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    account_id = Column(BigInteger, ForeignKey('google_ad_accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    campaign_id = Column(BigInteger, ForeignKey('google_campaigns.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = Column(String(50), nullable=False, index=True, comment='关联的Google Ads Customer ID')
    ad_group_id = Column(String(50), nullable=False, comment='Google Ads Ad Group ID')
    ad_group_name = Column(String(255), nullable=False, comment='广告组名称')
    ad_group_status = Column(String(20), default='ENABLED', index=True, comment='状态')
    ad_group_type = Column(String(50), comment='广告组类型')
    cpc_bid_micros = Column(BigInteger, comment='CPC出价(微单位)')
    cpm_bid_micros = Column(BigInteger, comment='CPM出价(微单位)')
    target_cpa_micros = Column(BigInteger, comment='目标CPA(微单位)')
    percent_cpc_bid_micros = Column(BigInteger, comment='百分比CPC出价(微单位)')
    raw_data = Column(JSONB, comment='原始数据(JSON)')
    ext_info = Column(JSONB, default={}, comment='扩展信息(预留字段)')
    last_synced_at = Column(TIMESTAMP, index=True, comment='最后同步时间')
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # 关系
    account = relationship("GoogleAdAccount", back_populates="ad_groups")
    campaign = relationship("GoogleCampaign", back_populates="ad_groups")

    __table_args__ = (
        Index('uk_google_customer_ad_group', 'customer_id', 'ad_group_id', unique=True),
        CheckConstraint("ad_group_status IN ('ENABLED', 'PAUSED', 'REMOVED')", name='ck_google_ad_group_status'),
    )

    def __repr__(self):
        return f"<GoogleAdGroup(ad_group_id='{self.ad_group_id}', name='{self.ad_group_name}')>"
