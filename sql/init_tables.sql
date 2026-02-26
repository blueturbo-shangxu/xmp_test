-- ========================================
-- XMP Auth Server Database Schema
-- Multi-Platform Architecture
-- ========================================

-- 注意: 需要先安装 PostgreSQL 的 uuid-ossp 扩展 (如果需要UUID)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================
-- 通用表: OAuth Tokens (支持所有平台)
-- ========================================

CREATE TABLE IF NOT EXISTS oauth_tokens (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,                          -- 平台标识: google, meta, tiktok
    account_key VARCHAR(100) NOT NULL,                      -- 账户唯一标识
    access_token TEXT NOT NULL,                             -- 访问令牌(加密存储)
    refresh_token TEXT,                                     -- 刷新令牌(加密存储)
    token_type VARCHAR(50) DEFAULT 'Bearer',                -- Token类型
    expires_at TIMESTAMP NOT NULL,                          -- 访问令牌过期时间
    scope TEXT,                                             -- 授权范围
    grant_type VARCHAR(50) DEFAULT 'authorization_code',    -- 授权类型
    is_valid BOOLEAN DEFAULT TRUE,                          -- Token是否有效
    last_refreshed_at TIMESTAMP,                            -- 最后刷新时间
    refresh_count INTEGER DEFAULT 0,                        -- 刷新次数
    error_message TEXT,                                     -- 最后一次错误信息
    ext_info JSONB DEFAULT '{}',                            -- 扩展信息(预留字段)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_platform ON oauth_tokens(platform);
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_account_key ON oauth_tokens(account_key);
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_expires_at ON oauth_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_is_valid ON oauth_tokens(is_valid);
CREATE UNIQUE INDEX IF NOT EXISTS uk_platform_account ON oauth_tokens(platform, account_key);

-- 注释
COMMENT ON TABLE oauth_tokens IS 'OAuth令牌表(多平台通用)';
COMMENT ON COLUMN oauth_tokens.platform IS '平台标识: google, meta, tiktok';
COMMENT ON COLUMN oauth_tokens.account_key IS '账户唯一标识';
COMMENT ON COLUMN oauth_tokens.ext_info IS '扩展信息(预留字段)';


-- ========================================
-- 通用表: Authorization Logs (支持所有平台)
-- ========================================

CREATE TABLE IF NOT EXISTS authorization_logs (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,                          -- 平台标识
    account_key VARCHAR(100),                               -- 账户标识
    action_type VARCHAR(20) NOT NULL,                       -- 操作类型
    status VARCHAR(20) NOT NULL,                            -- 操作状态
    error_code VARCHAR(50),                                 -- 错误码
    error_message TEXT,                                     -- 错误详情
    ip_address VARCHAR(45),                                 -- 请求IP地址
    user_agent TEXT,                                        -- 用户代理
    request_data JSONB,                                     -- 请求数据(脱敏)
    response_data JSONB,                                    -- 响应数据(脱敏)
    duration_ms INTEGER,                                    -- 操作耗时(毫秒)
    ext_info JSONB DEFAULT '{}',                            -- 扩展信息(预留字段)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 约束
ALTER TABLE authorization_logs ADD CONSTRAINT ck_action_type
    CHECK (action_type IN ('AUTHORIZE', 'REFRESH', 'REVOKE', 'VALIDATE'));
ALTER TABLE authorization_logs ADD CONSTRAINT ck_status
    CHECK (status IN ('SUCCESS', 'FAILED', 'PENDING'));

-- 索引
CREATE INDEX IF NOT EXISTS idx_auth_logs_platform ON authorization_logs(platform);
CREATE INDEX IF NOT EXISTS idx_auth_logs_account_key ON authorization_logs(account_key);
CREATE INDEX IF NOT EXISTS idx_auth_logs_action_type ON authorization_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_auth_logs_status ON authorization_logs(status);
CREATE INDEX IF NOT EXISTS idx_auth_logs_created_at ON authorization_logs(created_at);

-- 注释
COMMENT ON TABLE authorization_logs IS '授权操作日志表(多平台通用)';
COMMENT ON COLUMN authorization_logs.action_type IS '操作类型: AUTHORIZE, REFRESH, REVOKE, VALIDATE';
COMMENT ON COLUMN authorization_logs.status IS '操作状态: SUCCESS, FAILED, PENDING';
COMMENT ON COLUMN authorization_logs.ext_info IS '扩展信息(预留字段)';


-- ========================================
-- 通用表: 同步任务表 (支持所有平台)
-- ========================================

CREATE TABLE IF NOT EXISTS sync_tasks (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,                          -- 平台标识: google, meta, tiktok
    account_key VARCHAR(100) NOT NULL,                      -- 账户标识
    task_type VARCHAR(30) NOT NULL,                         -- 任务类型: CAMPAIGNS, AD_GROUPS等
    status VARCHAR(20) DEFAULT 'PENDING',                   -- 任务状态
    priority INTEGER DEFAULT 5,                             -- 优先级(1-10, 10最高)
    start_date DATE,                                        -- 数据开始日期
    end_date DATE,                                          -- 数据结束日期
    total_records INTEGER DEFAULT 0,                        -- 总记录数
    processed_records INTEGER DEFAULT 0,                    -- 已处理记录数
    failed_records INTEGER DEFAULT 0,                       -- 失败记录数
    error_message TEXT,                                     -- 错误信息
    started_at TIMESTAMP,                                   -- 开始时间
    completed_at TIMESTAMP,                                 -- 完成时间
    duration_seconds INTEGER,                               -- 耗时(秒)
    retry_count INTEGER DEFAULT 0,                          -- 重试次数
    next_retry_at TIMESTAMP,                                -- 下次重试时间
    raw_data JSONB,                                         -- 原始任务数据(保留完整信息)
    ext_info JSONB DEFAULT '{}',                            -- 扩展信息(预留字段)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 约束
ALTER TABLE sync_tasks ADD CONSTRAINT ck_task_status
    CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'));

-- 索引
CREATE INDEX IF NOT EXISTS idx_sync_tasks_platform ON sync_tasks(platform);
CREATE INDEX IF NOT EXISTS idx_sync_tasks_account_key ON sync_tasks(account_key);
CREATE INDEX IF NOT EXISTS idx_sync_tasks_task_type ON sync_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_sync_tasks_status ON sync_tasks(status);
CREATE INDEX IF NOT EXISTS idx_sync_tasks_priority ON sync_tasks(priority);
CREATE INDEX IF NOT EXISTS idx_sync_tasks_next_retry_at ON sync_tasks(next_retry_at);
CREATE INDEX IF NOT EXISTS idx_sync_tasks_created_at ON sync_tasks(created_at);

-- 注释
COMMENT ON TABLE sync_tasks IS '同步任务表(多平台通用)';
COMMENT ON COLUMN sync_tasks.task_type IS '任务类型: CAMPAIGNS, AD_GROUPS, ADS等';
COMMENT ON COLUMN sync_tasks.status IS '任务状态: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED';
COMMENT ON COLUMN sync_tasks.raw_data IS '原始任务数据(保留完整信息)';
COMMENT ON COLUMN sync_tasks.ext_info IS '扩展信息(预留字段)';


-- ========================================
-- 通用表: API速率限制表 (支持所有平台)
-- ========================================

CREATE TABLE IF NOT EXISTS api_rate_limits (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,                          -- 平台标识
    account_key VARCHAR(100) NOT NULL,                      -- 账户标识
    endpoint VARCHAR(255) NOT NULL,                         -- API端点
    request_count INTEGER DEFAULT 0,                        -- 请求次数
    quota_limit INTEGER,                                    -- 配额限制
    quota_remaining INTEGER,                                -- 剩余配额
    window_start TIMESTAMP NOT NULL,                        -- 时间窗口开始
    window_end TIMESTAMP NOT NULL,                          -- 时间窗口结束
    is_throttled BOOLEAN DEFAULT FALSE,                     -- 是否被限流
    ext_info JSONB DEFAULT '{}',                            -- 扩展信息(预留字段)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_rate_limits_platform ON api_rate_limits(platform);
CREATE INDEX IF NOT EXISTS idx_rate_limits_account_key ON api_rate_limits(account_key);
CREATE INDEX IF NOT EXISTS idx_rate_limits_window_end ON api_rate_limits(window_end);
CREATE INDEX IF NOT EXISTS idx_rate_limits_is_throttled ON api_rate_limits(is_throttled);

-- 注释
COMMENT ON TABLE api_rate_limits IS 'API速率限制表(多平台通用)';
COMMENT ON COLUMN api_rate_limits.ext_info IS '扩展信息(预留字段)';


-- ========================================
-- Google Ads: 账户表
-- ========================================

CREATE TABLE IF NOT EXISTS google_ad_accounts (
    id BIGSERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL UNIQUE,                -- Google Ads Customer ID (格式: 123-456-7890)
    account_name VARCHAR(255) NOT NULL,                     -- 账户名称
    currency_code VARCHAR(10) DEFAULT 'USD',                -- 币种
    timezone VARCHAR(50) DEFAULT 'UTC',                     -- 时区
    account_type VARCHAR(20) DEFAULT 'CLIENT',              -- 账户类型: CLIENT, MANAGER
    status VARCHAR(20) DEFAULT 'ACTIVE',                    -- 账户状态
    manager_customer_id VARCHAR(50),                        -- MCC管理账户ID
    descriptive_name VARCHAR(255),                          -- 描述性名称
    can_manage_clients BOOLEAN DEFAULT FALSE,               -- 是否可管理客户
    test_account BOOLEAN DEFAULT FALSE,                     -- 是否测试账户
    sync_enabled BOOLEAN DEFAULT TRUE,                      -- 是否启用同步功能
    raw_data JSONB,                                         -- 原始账户数据(保留完整信息)
    ext_info JSONB DEFAULT '{}',                            -- 扩展信息(预留字段)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 约束
ALTER TABLE google_ad_accounts ADD CONSTRAINT ck_google_account_type
    CHECK (account_type IN ('CLIENT', 'MANAGER'));

-- 索引
CREATE INDEX IF NOT EXISTS idx_google_accounts_customer_id ON google_ad_accounts(customer_id);
CREATE INDEX IF NOT EXISTS idx_google_accounts_status ON google_ad_accounts(status);
CREATE INDEX IF NOT EXISTS idx_google_accounts_manager_id ON google_ad_accounts(manager_customer_id);
CREATE INDEX IF NOT EXISTS idx_google_accounts_sync_enabled ON google_ad_accounts(sync_enabled);

-- 注释
COMMENT ON TABLE google_ad_accounts IS 'Google Ads账户表';
COMMENT ON COLUMN google_ad_accounts.customer_id IS 'Google Ads Customer ID (格式: 123-456-7890)';
COMMENT ON COLUMN google_ad_accounts.account_type IS '账户类型: CLIENT(客户账户), MANAGER(MCC管理账户)';
COMMENT ON COLUMN google_ad_accounts.sync_enabled IS '是否启用同步功能';
COMMENT ON COLUMN google_ad_accounts.raw_data IS '原始账户数据(保留完整信息)';
COMMENT ON COLUMN google_ad_accounts.ext_info IS '扩展信息(预留字段)';


-- ========================================
-- Google Ads: 推广活动表
-- ========================================

CREATE TABLE IF NOT EXISTS google_campaigns (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES google_ad_accounts(id) ON DELETE CASCADE,
    customer_id VARCHAR(50) NOT NULL,                       -- 关联的Google Ads Customer ID
    campaign_id VARCHAR(50) NOT NULL,                       -- Google Ads Campaign ID
    campaign_name VARCHAR(255) NOT NULL,                    -- 推广活动名称
    campaign_status VARCHAR(20) DEFAULT 'ENABLED',          -- 状态
    campaign_type VARCHAR(50),                              -- 推广活动类型
    advertising_channel_type VARCHAR(50),                   -- 广告网络类型
    budget_amount DECIMAL(15, 2),                           -- 预算金额
    budget_period VARCHAR(20),                              -- 预算周期
    bidding_strategy_type VARCHAR(50),                      -- 出价策略类型
    start_date DATE,                                        -- 开始日期
    end_date DATE,                                          -- 结束日期
    serving_status VARCHAR(50),                             -- 投放状态
    target_spend_micros BIGINT,                             -- 目标支出(微单位)
    target_cpa_micros BIGINT,                               -- 目标CPA(微单位)
    target_roas DECIMAL(10, 4),                             -- 目标ROAS
    raw_data JSONB,                                         -- 原始数据(JSON)
    ext_info JSONB DEFAULT '{}',                            -- 扩展信息(预留字段)
    last_synced_at TIMESTAMP,                               -- 最后同步时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 约束
ALTER TABLE google_campaigns ADD CONSTRAINT ck_google_campaign_status
    CHECK (campaign_status IN ('ENABLED', 'PAUSED', 'REMOVED'));

-- 索引
CREATE INDEX IF NOT EXISTS idx_google_campaigns_account_id ON google_campaigns(account_id);
CREATE INDEX IF NOT EXISTS idx_google_campaigns_customer_id ON google_campaigns(customer_id);
CREATE INDEX IF NOT EXISTS idx_google_campaigns_status ON google_campaigns(campaign_status);
CREATE INDEX IF NOT EXISTS idx_google_campaigns_last_synced ON google_campaigns(last_synced_at);
CREATE UNIQUE INDEX IF NOT EXISTS uk_google_customer_campaign ON google_campaigns(customer_id, campaign_id);

-- 注释
COMMENT ON TABLE google_campaigns IS 'Google Ads推广活动表';
COMMENT ON COLUMN google_campaigns.raw_data IS '原始数据(JSON格式,保留API返回的完整信息)';
COMMENT ON COLUMN google_campaigns.ext_info IS '扩展信息(预留字段)';


-- ========================================
-- Google Ads: 广告组表
-- ========================================

CREATE TABLE IF NOT EXISTS google_ad_groups (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES google_ad_accounts(id) ON DELETE CASCADE,
    campaign_id BIGINT NOT NULL REFERENCES google_campaigns(id) ON DELETE CASCADE,
    customer_id VARCHAR(50) NOT NULL,                       -- 关联的Google Ads Customer ID
    ad_group_id VARCHAR(50) NOT NULL,                       -- Google Ads Ad Group ID
    ad_group_name VARCHAR(255) NOT NULL,                    -- 广告组名称
    ad_group_status VARCHAR(20) DEFAULT 'ENABLED',          -- 状态
    ad_group_type VARCHAR(50),                              -- 广告组类型
    cpc_bid_micros BIGINT,                                  -- CPC出价(微单位)
    cpm_bid_micros BIGINT,                                  -- CPM出价(微单位)
    target_cpa_micros BIGINT,                               -- 目标CPA(微单位)
    percent_cpc_bid_micros BIGINT,                          -- 百分比CPC出价(微单位)
    raw_data JSONB,                                         -- 原始数据(JSON)
    ext_info JSONB DEFAULT '{}',                            -- 扩展信息(预留字段)
    last_synced_at TIMESTAMP,                               -- 最后同步时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 约束
ALTER TABLE google_ad_groups ADD CONSTRAINT ck_google_ad_group_status
    CHECK (ad_group_status IN ('ENABLED', 'PAUSED', 'REMOVED'));

-- 索引
CREATE INDEX IF NOT EXISTS idx_google_ad_groups_account_id ON google_ad_groups(account_id);
CREATE INDEX IF NOT EXISTS idx_google_ad_groups_campaign_id ON google_ad_groups(campaign_id);
CREATE INDEX IF NOT EXISTS idx_google_ad_groups_customer_id ON google_ad_groups(customer_id);
CREATE INDEX IF NOT EXISTS idx_google_ad_groups_status ON google_ad_groups(ad_group_status);
CREATE INDEX IF NOT EXISTS idx_google_ad_groups_last_synced ON google_ad_groups(last_synced_at);
CREATE UNIQUE INDEX IF NOT EXISTS uk_google_customer_ad_group ON google_ad_groups(customer_id, ad_group_id);

-- 注释
COMMENT ON TABLE google_ad_groups IS 'Google Ads广告组表';
COMMENT ON COLUMN google_ad_groups.raw_data IS '原始数据(JSON格式,保留API返回的完整信息)';
COMMENT ON COLUMN google_ad_groups.ext_info IS '扩展信息(预留字段)';


-- ========================================
-- 创建更新时间触发器函数
-- ========================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有带有 updated_at 字段的表创建触发器
CREATE TRIGGER update_oauth_tokens_updated_at
    BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sync_tasks_updated_at
    BEFORE UPDATE ON sync_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_rate_limits_updated_at
    BEFORE UPDATE ON api_rate_limits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_google_ad_accounts_updated_at
    BEFORE UPDATE ON google_ad_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_google_campaigns_updated_at
    BEFORE UPDATE ON google_campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_google_ad_groups_updated_at
    BEFORE UPDATE ON google_ad_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ========================================
-- 表结构总览
-- ========================================
-- 通用表 (4张):
--   1. oauth_tokens         - OAuth令牌(所有平台)
--   2. authorization_logs   - 授权日志(所有平台)
--   3. sync_tasks           - 同步任务(所有平台)
--   4. api_rate_limits      - API限流(所有平台)
--
-- Google Ads 专用表 (3张):
--   5. google_ad_accounts   - Google Ads账户
--   6. google_campaigns     - Google推广活动
--   7. google_ad_groups     - Google广告组
--
-- 总计: 7张表
-- ========================================
