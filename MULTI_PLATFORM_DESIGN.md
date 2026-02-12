# 多平台表结构设计说明

## 设计理念

### 1. 平台无关的通用表(支持所有平台)

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `ad_platforms` | 平台配置表 | platform_code (google, meta, tiktok) |
| `ad_accounts` | 广告账户表 | platform_code, account_id, customer_id |
| `oauth_tokens` | OAuth令牌表 | account_id, platform_code, access_token |
| `authorization_logs` | 授权日志表 | account_id, platform_code, action_type |
| `sync_tasks` | 同步任务表 | account_id, platform_code, task_type |
| `api_rate_limits` | API限流表 | account_id, platform_code, endpoint |

### 2. 平台特定表(Google Ads)

| 表名 | 说明 |
|------|------|
| `google_campaigns` | Google推广活动表 |
| `google_ad_groups` | Google广告组表 |

### 3. 平台特定表(Meta/Facebook - 预留)

| 表名 | 说明 |
|------|------|
| `meta_campaigns` | Meta推广活动表 |
| `meta_ad_sets` | Meta广告集表 |

### 4. 平台特定表(TikTok - 预留)

| 表名 | 说明 |
|------|------|
| `tiktok_campaigns` | TikTok推广活动表 |
| `tiktok_ad_groups` | TikTok广告组表 |

## 关键变化

### 旧表名 → 新表名

```
accounts        → ad_accounts (增加platform_code字段)
campaigns       → google_campaigns (Google专属)
ad_groups       → google_ad_groups (Google专属)
oauth_tokens    → oauth_tokens (增加platform_code字段)
sync_tasks      → sync_tasks (增加platform_code字段)
api_rate_limits → api_rate_limits (增加platform_code字段)
authorization_logs → authorization_logs (增加platform_code字段)
```

### 新增表

```
ad_platforms (新增) - 平台配置表,预置了google, meta, tiktok
meta_campaigns (新增) - Meta推广活动
meta_ad_sets (新增) - Meta广告集
tiktok_campaigns (新增) - TikTok推广活动
tiktok_ad_groups (新增) - TikTok广告组
```

## 多平台支持优势

### 1. 统一账户管理
```sql
-- 查询所有平台的账户
SELECT platform_code, account_name, status
FROM ad_accounts;

-- 查询Google账户
SELECT * FROM ad_accounts WHERE platform_code = 'google';

-- 查询Meta账户
SELECT * FROM ad_accounts WHERE platform_code = 'meta';
```

### 2. 统一Token管理
```sql
-- 所有平台的token都存在一张表
SELECT a.platform_code, a.account_name, t.is_valid, t.expires_at
FROM oauth_tokens t
JOIN ad_accounts a ON t.account_id = a.id;
```

### 3. 跨平台数据分析
```sql
-- 统计各平台的推广活动数量
SELECT
    'google' as platform,
    COUNT(*) as campaign_count
FROM google_campaigns
UNION ALL
SELECT
    'meta' as platform,
    COUNT(*) as campaign_count
FROM meta_campaigns
UNION ALL
SELECT
    'tiktok' as platform,
    COUNT(*) as campaign_count
FROM tiktok_campaigns;
```

### 4. 平台配置管理
```sql
-- 启用/禁用某个平台
UPDATE ad_platforms SET is_enabled = FALSE WHERE platform_code = 'tiktok';

-- 查看已启用的平台
SELECT * FROM ad_platforms WHERE is_enabled = TRUE;
```

## 数据关系图

```
ad_platforms
    ↓ (platform_code)
ad_accounts
    ↓ (account_id)
    ├─→ oauth_tokens
    ├─→ authorization_logs
    ├─→ sync_tasks
    ├─→ api_rate_limits
    ├─→ google_campaigns
    │      ↓
    │   google_ad_groups
    ├─→ meta_campaigns
    │      ↓
    │   meta_ad_sets
    └─→ tiktok_campaigns
           ↓
        tiktok_ad_groups
```

## Python代码需要修改的地方

### 1. models.py
需要修改的模型:
- `Account` → `AdAccount` (增加platform_code字段)
- `Campaign` → `GoogleCampaign`
- `AdGroup` → `GoogleAdGroup`
- 新增: `AdPlatform`, `MetaCampaign`, `MetaAdSet`, `TikTokCampaign`, `TikTokAdGroup`

### 2. oauth_service.py
需要修改:
- 所有使用 `Account` 的地方改为 `AdAccount`
- 保存token时添加 `platform_code='google'`
- 授权日志添加 `platform_code`

### 3. google_ads_service.py
需要修改:
- 使用 `GoogleCampaign` 代替 `Campaign`
- 使用 `GoogleAdGroup` 代替 `AdGroup`
- 使用 `AdAccount` 代替 `Account`

### 4. routes/api.py
需要修改:
- 所有模型引用更新
- API端点可能需要增加 platform 参数

## 扩展性

### 添加新平台(例如Twitter Ads)

1. 在 `ad_platforms` 表插入新记录:
```sql
INSERT INTO ad_platforms (platform_code, platform_name, is_enabled)
VALUES ('twitter', 'Twitter Ads', TRUE);
```

2. 创建平台特定表:
```sql
CREATE TABLE twitter_campaigns (...);
CREATE TABLE twitter_ad_groups (...);
```

3. 添加对应的Python模型和服务类

### 向后兼容

- 所有现有的Google Ads代码只需要很小的修改
- 核心业务逻辑基本不变
- 只是表名和模型名调整

## 需要确认的问题

1. **表名设计是否符合需求?**
   - 通用表: `ad_accounts`, `oauth_tokens`等
   - Google表: `google_campaigns`, `google_ad_groups`
   - Meta表: `meta_campaigns`, `meta_ad_sets`
   - TikTok表: `tiktok_campaigns`, `tiktok_ad_groups`

2. **是否需要保留旧表并迁移数据?**
   - 如果数据库已有数据,需要数据迁移脚本

3. **Meta和TikTok表结构是否需要调整?**
   - 目前只是预留了基本字段
   - 可以根据实际需求调整

4. **是否需要添加更多平台特定的表?**
   - 例如: `google_keywords`, `meta_ads`, `tiktok_creatives`等

请确认这个设计是否符合你的需求,然后我会开始修改Python代码!
