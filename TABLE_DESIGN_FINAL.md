# 最终表结构设计方案

## 设计原则

1. **✅ 删除平台配置表** - 配置信息写在代码/配置文件中
2. **✅ OAuth Token 通用表** - 所有平台的Token字段完全相同,使用同一张表
3. **✅ 账户表分平台** - 不同平台账户字段差异大,每个平台独立账户表
4. **✅ 数据表分平台** - 推广活动/广告组等数据表按平台分开
5. **✅ 只创建Google表** - Meta和TikTok后续接入时再创建

## 表结构总览

### 通用表 (4张)

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `oauth_tokens` | OAuth令牌(所有平台) | platform, account_key |
| `authorization_logs` | 授权日志(所有平台) | platform, account_key |
| `sync_tasks` | 同步任务(所有平台) | platform, account_key |
| `api_rate_limits` | API限流(所有平台) | platform, account_key |

### Google Ads 专用表 (3张)

| 表名 | 说明 |
|------|------|
| `google_ad_accounts` | Google Ads账户 |
| `google_campaigns` | Google推广活动 |
| `google_ad_groups` | Google广告组 |

**总计: 7张表**

## 核心设计逻辑

### 1. OAuth Tokens - 通用表设计

```sql
oauth_tokens (
    platform VARCHAR(20),      -- 'google', 'meta', 'tiktok'
    account_key VARCHAR(100),  -- customer_id / ad_account_id / advertiser_id
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    ...
    UNIQUE(platform, account_key)
)
```

**为什么能通用?**
- ✅ 所有平台OAuth流程完全一致
- ✅ Token字段(access_token, refresh_token, expires_at)都相同
- ✅ 使用 `platform + account_key` 唯一标识不同平台的账户

**示例数据:**
```
platform='google', account_key='123-456-7890'  → Google账户的token
platform='meta',   account_key='act_123456'    → Meta账户的token
platform='tiktok', account_key='987654321'     → TikTok账户的token
```

### 2. Authorization Logs - 通用日志表

```sql
authorization_logs (
    platform VARCHAR(20),
    account_key VARCHAR(100),
    action_type VARCHAR(20),  -- AUTHORIZE, REFRESH, REVOKE
    status VARCHAR(20),       -- SUCCESS, FAILED
    ...
)
```

**为什么能通用?**
- ✅ 授权动作(authorize, refresh, revoke)所有平台一致
- ✅ 日志格式统一
- ✅ 便于跨平台的授权行为分析

### 3. 账户表 - 按平台分开

**Google Ads账户:**
```sql
google_ad_accounts (
    customer_id VARCHAR(50) UNIQUE,  -- 格式: 123-456-7890
    account_type VARCHAR(20),        -- CLIENT / MANAGER (Google特有)
    manager_customer_id VARCHAR(50), -- MCC管理账户 (Google特有)
    can_manage_clients BOOLEAN,      -- 是否可管理客户 (Google特有)
    ...
)
```

**未来Meta账户(示例):**
```sql
meta_ad_accounts (
    ad_account_id VARCHAR(50) UNIQUE,  -- 格式: act_xxxxx
    business_id VARCHAR(50),           -- Meta特有
    account_status INTEGER,            -- Meta状态是数字
    ...
)
```

**未来TikTok账户(示例):**
```sql
tiktok_ad_accounts (
    advertiser_id VARCHAR(50) UNIQUE,  -- TikTok账户ID
    business_center_id VARCHAR(50),    -- TikTok特有
    ...
)
```

**为什么分开?**
- ❌ 账户ID格式完全不同 (customer_id vs ad_account_id vs advertiser_id)
- ❌ 账户类型不同 (Google的CLIENT/MANAGER vs Meta的业务账户)
- ❌ 平台特有字段多 (MCC, Business Manager等)
- ✅ 分开后每个表结构清晰,不会有大量NULL字段

### 4. 同步任务 - 通用表

```sql
sync_tasks (
    platform VARCHAR(20),        -- 平台标识
    account_key VARCHAR(100),    -- 账户标识
    task_type VARCHAR(30),       -- CAMPAIGNS, AD_GROUPS等
    status VARCHAR(20),          -- PENDING, RUNNING, COMPLETED等
    ...
)
```

**为什么能通用?**
- ✅ 任务流程所有平台一致(创建→运行→完成)
- ✅ 状态字段通用
- ✅ 统计字段通用(total_records, processed_records等)

## 数据关系图

```
google_ad_accounts
    ↓ (通过 customer_id 关联)
    ├─→ oauth_tokens (platform='google', account_key=customer_id)
    ├─→ authorization_logs (platform='google', account_key=customer_id)
    ├─→ sync_tasks (platform='google', account_key=customer_id)
    ├─→ api_rate_limits (platform='google', account_key=customer_id)
    ├─→ google_campaigns
    │      ↓
    │   google_ad_groups
```

## 查询示例

### 1. 查询某个Google账户的Token
```sql
SELECT * FROM oauth_tokens
WHERE platform = 'google' AND account_key = '123-456-7890';
```

### 2. 查询所有平台的授权日志
```sql
SELECT platform, account_key, action_type, status, created_at
FROM authorization_logs
ORDER BY created_at DESC
LIMIT 100;
```

### 3. 查询Google账户及其Token状态
```sql
SELECT
    a.customer_id,
    a.account_name,
    a.status as account_status,
    t.is_valid as token_valid,
    t.expires_at as token_expires
FROM google_ad_accounts a
LEFT JOIN oauth_tokens t ON t.platform = 'google' AND t.account_key = a.customer_id;
```

### 4. 统计各平台的同步任务
```sql
SELECT
    platform,
    COUNT(*) as total_tasks,
    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_tasks,
    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_tasks
FROM sync_tasks
GROUP BY platform;
```

## 扩展Meta平台

当需要接入Meta时,只需:

1. **创建Meta账户表:**
```sql
CREATE TABLE meta_ad_accounts (
    id BIGSERIAL PRIMARY KEY,
    ad_account_id VARCHAR(50) NOT NULL UNIQUE,  -- act_xxx格式
    account_name VARCHAR(255),
    business_id VARCHAR(50),
    account_status INTEGER,
    ...
);
```

2. **创建Meta数据表:**
```sql
CREATE TABLE meta_campaigns (...);
CREATE TABLE meta_ad_sets (...);
CREATE TABLE meta_ads (...);
```

3. **通用表自动支持:**
- `oauth_tokens` 直接使用,设置 `platform='meta'`
- `authorization_logs` 直接使用
- `sync_tasks` 直接使用
- `api_rate_limits` 直接使用

## 优势总结

### ✅ 通用表的优势
1. **统一Token管理** - 所有平台Token存储在一起,管理简单
2. **统一授权日志** - 跨平台授权行为分析方便
3. **统一任务调度** - 同步任务统一管理和监控
4. **减少表数量** - 7张表支持多平台,而不是每个平台7张

### ✅ 分平台账户表的优势
1. **字段清晰** - 每个平台的特有字段都能保留
2. **类型安全** - 不同平台的枚举值不冲突
3. **维护简单** - 修改一个平台的表不影响其他平台
4. **性能优化** - 没有冗余的NULL字段

### ✅ 整体优势
1. **易于扩展** - 新增平台只需创建账户表和数据表
2. **代码清晰** - 模型命名明确(`GoogleAdAccount` vs `MetaAdAccount`)
3. **查询高效** - 没有复杂的平台判断逻辑
4. **向后兼容** - Google的代码修改量小

## Python代码修改要点

### 1. 模型名称变化
- `Account` → `GoogleAdAccount`
- `Campaign` → `GoogleCampaign`
- `AdGroup` → `GoogleAdGroup`
- `OAuthToken` 保持不变(增加platform字段)
- `SyncTask` 保持不变(增加platform字段)

### 2. OAuth Service修改
```python
# 保存token时
oauth_token = OAuthToken(
    platform='google',
    account_key=customer_id,  # '123-456-7890'
    access_token=encrypted_access,
    refresh_token=encrypted_refresh,
    ...
)
```

### 3. 查询修改
```python
# 查询Google账户的token
token = db.query(OAuthToken).filter(
    OAuthToken.platform == 'google',
    OAuthToken.account_key == customer_id
).first()
```

## 总结

**最终方案:**
- ✅ 4张通用表 (oauth_tokens, authorization_logs, sync_tasks, api_rate_limits)
- ✅ 3张Google表 (google_ad_accounts, google_campaigns, google_ad_groups)
- ✅ 未来Meta/TikTok各自创建账户表和数据表
- ✅ 删除了ad_platforms配置表
- ✅ 简洁、清晰、易扩展

这个设计在**通用性**和**灵活性**之间取得了最佳平衡!
