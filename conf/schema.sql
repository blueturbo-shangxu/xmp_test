-- XMP Auth Server Database Schema (PostgreSQL)
-- Database: socialbooster
-- Description: Multi-platform ad authorization and data management
-- Current Support: Google Ads (Meta and TikTok to be added later)

-- ========================================
-- 通用表: OAuth Tokens (支持所有平台)
-- ========================================
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    account_key VARCHAR(100) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at TIMESTAMP NOT NULL,
    scope TEXT,
    grant_type VARCHAR(50) DEFAULT 'authorization_code',
    is_valid BOOLEAN DEFAULT TRUE,
    last_refreshed_at TIMESTAMP,
    refresh_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, account_key)
);

CREATE INDEX idx_oauth_tokens_platform ON oauth_tokens(platform);
CREATE INDEX idx_oauth_tokens_account_key ON oauth_tokens(account_key);
CREATE INDEX idx_oauth_tokens_expires_at ON oauth_tokens(expires_at);
CREATE INDEX idx_oauth_tokens_is_valid ON oauth_tokens(is_valid);

COMMENT ON TABLE oauth_tokens IS 'OAuth令牌表(多平台通用)';
COMMENT ON COLUMN oauth_tokens.platform IS '平台标识: google, meta, tiktok';
COMMENT ON COLUMN oauth_tokens.account_key IS '账户唯一标识(customer_id/ad_account_id/advertiser_id)';
COMMENT ON COLUMN oauth_tokens.access_token IS '访问令牌(加密存储)';
COMMENT ON COLUMN oauth_tokens.refresh_token IS '刷新令牌(加密存储)';

-- ========================================
-- 通用表: Authorization Logs (支持所有平台)
-- ========================================
CREATE TABLE IF NOT EXISTS authorization_logs (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    account_key VARCHAR(100),
    action_type VARCHAR(20) NOT NULL CHECK (action_type IN ('AUTHORIZE', 'REFRESH', 'REVOKE', 'VALIDATE')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'PENDING')),
    error_code VARCHAR(50),
    error_message TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_data JSONB,
    response_data JSONB,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_authorization_logs_platform ON authorization_logs(platform);
CREATE INDEX idx_authorization_logs_account_key ON authorization_logs(account_key);
CREATE INDEX idx_authorization_logs_action_type ON authorization_logs(action_type);
CREATE INDEX idx_authorization_logs_status ON authorization_logs(status);
CREATE INDEX idx_authorization_logs_created_at ON authorization_logs(created_at);

COMMENT ON TABLE authorization_logs IS '授权操作日志表(多平台通用)';
COMMENT ON COLUMN authorization_logs.platform IS '平台标识';
COMMENT ON COLUMN authorization_logs.account_key IS '账户标识';

-- ========================================
-- Google Ads: 账户表
-- ========================================
CREATE TABLE IF NOT EXISTS google_ad_accounts (
    id BIGSERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL UNIQUE,
    account_name VARCHAR(255) NOT NULL,
    currency_code VARCHAR(10) DEFAULT 'USD',
    timezone VARCHAR(50) DEFAULT 'UTC',
    account_type VARCHAR(20) DEFAULT 'CLIENT' CHECK (account_type IN ('CLIENT', 'MANAGER')),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    manager_customer_id VARCHAR(50),
    descriptive_name VARCHAR(255),
    can_manage_clients BOOLEAN DEFAULT FALSE,
    test_account BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_google_accounts_customer_id ON google_ad_accounts(customer_id);
CREATE INDEX idx_google_accounts_status ON google_ad_accounts(status);
CREATE INDEX idx_google_accounts_manager_id ON google_ad_accounts(manager_customer_id);

COMMENT ON TABLE google_ad_accounts IS 'Google Ads账户表';
COMMENT ON COLUMN google_ad_accounts.customer_id IS 'Google Ads Customer ID (格式: 123-456-7890)';
COMMENT ON COLUMN google_ad_accounts.account_type IS '账户类型: CLIENT(普通账户), MANAGER(MCC账户)';
COMMENT ON COLUMN google_ad_accounts.manager_customer_id IS 'MCC管理账户ID';

-- ========================================
-- Google Ads: 推广活动表
-- ========================================
CREATE TABLE IF NOT EXISTS google_campaigns (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES google_ad_accounts(id) ON DELETE CASCADE,
    customer_id VARCHAR(50) NOT NULL,
    campaign_id VARCHAR(50) NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    campaign_status VARCHAR(20) DEFAULT 'ENABLED' CHECK (campaign_status IN ('ENABLED', 'PAUSED', 'REMOVED')),
    campaign_type VARCHAR(50),
    advertising_channel_type VARCHAR(50),
    budget_amount DECIMAL(15, 2),
    budget_period VARCHAR(20),
    bidding_strategy_type VARCHAR(50),
    start_date DATE,
    end_date DATE,
    serving_status VARCHAR(50),
    target_spend_micros BIGINT,
    target_cpa_micros BIGINT,
    target_roas DECIMAL(10, 4),
    raw_data JSONB,
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, campaign_id)
);

CREATE INDEX idx_google_campaigns_account_id ON google_campaigns(account_id);
CREATE INDEX idx_google_campaigns_customer_id ON google_campaigns(customer_id);
CREATE INDEX idx_google_campaigns_status ON google_campaigns(campaign_status);
CREATE INDEX idx_google_campaigns_synced_at ON google_campaigns(last_synced_at);

COMMENT ON TABLE google_campaigns IS 'Google Ads推广活动表';
COMMENT ON COLUMN google_campaigns.customer_id IS '关联的Google Ads Customer ID';
COMMENT ON COLUMN google_campaigns.campaign_id IS 'Google Ads Campaign ID';

-- ========================================
-- Google Ads: 广告组表
-- ========================================
CREATE TABLE IF NOT EXISTS google_ad_groups (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES google_ad_accounts(id) ON DELETE CASCADE,
    campaign_id BIGINT NOT NULL REFERENCES google_campaigns(id) ON DELETE CASCADE,
    customer_id VARCHAR(50) NOT NULL,
    ad_group_id VARCHAR(50) NOT NULL,
    ad_group_name VARCHAR(255) NOT NULL,
    ad_group_status VARCHAR(20) DEFAULT 'ENABLED' CHECK (ad_group_status IN ('ENABLED', 'PAUSED', 'REMOVED')),
    ad_group_type VARCHAR(50),
    cpc_bid_micros BIGINT,
    cpm_bid_micros BIGINT,
    target_cpa_micros BIGINT,
    percent_cpc_bid_micros BIGINT,
    raw_data JSONB,
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, ad_group_id)
);

CREATE INDEX idx_google_ad_groups_account_id ON google_ad_groups(account_id);
CREATE INDEX idx_google_ad_groups_campaign_id ON google_ad_groups(campaign_id);
CREATE INDEX idx_google_ad_groups_customer_id ON google_ad_groups(customer_id);
CREATE INDEX idx_google_ad_groups_status ON google_ad_groups(ad_group_status);
CREATE INDEX idx_google_ad_groups_synced_at ON google_ad_groups(last_synced_at);

COMMENT ON TABLE google_ad_groups IS 'Google Ads广告组表';
COMMENT ON COLUMN google_ad_groups.customer_id IS '关联的Google Ads Customer ID';
COMMENT ON COLUMN google_ad_groups.ad_group_id IS 'Google Ads Ad Group ID';

-- ========================================
-- 通用表: 同步任务表
-- ========================================
CREATE TABLE IF NOT EXISTS sync_tasks (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    account_key VARCHAR(100) NOT NULL,
    task_type VARCHAR(30) NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    priority INTEGER DEFAULT 5,
    start_date DATE,
    end_date DATE,
    total_records INTEGER DEFAULT 0,
    processed_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sync_tasks_platform ON sync_tasks(platform);
CREATE INDEX idx_sync_tasks_account_key ON sync_tasks(account_key);
CREATE INDEX idx_sync_tasks_task_type ON sync_tasks(task_type);
CREATE INDEX idx_sync_tasks_status ON sync_tasks(status);
CREATE INDEX idx_sync_tasks_priority ON sync_tasks(priority);
CREATE INDEX idx_sync_tasks_next_retry_at ON sync_tasks(next_retry_at);
CREATE INDEX idx_sync_tasks_created_at ON sync_tasks(created_at);

COMMENT ON TABLE sync_tasks IS '同步任务表(多平台通用)';
COMMENT ON COLUMN sync_tasks.platform IS '平台标识: google, meta, tiktok';
COMMENT ON COLUMN sync_tasks.account_key IS '账户标识';
COMMENT ON COLUMN sync_tasks.task_type IS '任务类型: CAMPAIGNS, AD_GROUPS, ADS, KEYWORDS等';

-- ========================================
-- 通用表: API速率限制表
-- ========================================
CREATE TABLE IF NOT EXISTS api_rate_limits (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    account_key VARCHAR(100) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    request_count INTEGER DEFAULT 0,
    quota_limit INTEGER,
    quota_remaining INTEGER,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    is_throttled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_rate_limits_platform ON api_rate_limits(platform);
CREATE INDEX idx_api_rate_limits_account_key ON api_rate_limits(account_key);
CREATE INDEX idx_api_rate_limits_window_end ON api_rate_limits(window_end);
CREATE INDEX idx_api_rate_limits_is_throttled ON api_rate_limits(is_throttled);

COMMENT ON TABLE api_rate_limits IS 'API速率限制表(多平台通用)';

-- ========================================
-- 创建更新时间触发器函数
-- ========================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有表添加触发器
CREATE TRIGGER update_oauth_tokens_updated_at BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_google_ad_accounts_updated_at BEFORE UPDATE ON google_ad_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_google_campaigns_updated_at BEFORE UPDATE ON google_campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_google_ad_groups_updated_at BEFORE UPDATE ON google_ad_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sync_tasks_updated_at BEFORE UPDATE ON sync_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_rate_limits_updated_at BEFORE UPDATE ON api_rate_limits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
