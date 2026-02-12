# Google Ads 授权流程启动指南

本文档介绍如何启动和验证 Google Ads OAuth2 授权流程。

## 前置条件

### 1. 配置 Google Cloud Console

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建或选择一个项目
3. 启用 Google Ads API:
   - 导航到 "API和服务" > "库"
   - 搜索 "Google Ads API"
   - 点击"启用"

4. 创建 OAuth 2.0 凭据:
   - 导航到 "API和服务" > "凭据"
   - 点击 "创建凭据" > "OAuth客户端ID"
   - 应用类型选择 "Web应用"
   - 添加授权的重定向URI:
     ```
     http://localhost:8000/auth/callback
     ```
   - 保存并记录:
     - 客户端 ID (Client ID)
     - 客户端密钥 (Client Secret)

5. 获取 Developer Token:
   - 访问 [Google Ads API Center](https://ads.google.com/aw/apicenter)
   - 申请并获取 Developer Token

### 2. 配置环境变量

编辑 `conf/.env` 文件:

```bash
# Google OAuth2 配置
GOOGLE_CLIENT_ID=你的客户端ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=你的客户端密钥
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Google Ads API 配置
GOOGLE_ADS_DEVELOPER_TOKEN=你的开发者令牌
GOOGLE_ADS_API_VERSION=v16
GOOGLE_ADS_LOGIN_CUSTOMER_ID=  # MCC账户ID(可选)

# 数据库配置
DB_HOST=db.office.pg.domob-inc.cn
DB_PORT=5433
DB_USER=socialbooster
DB_PASSWORD=B<JRsi3.lI
DB_NAME=socialbooster

# 加密密钥 (随机生成)
ENCRYPTION_KEY=你的32字节加密密钥_base64编码
```

**生成加密密钥:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 初始化数据库

**方式1: 使用 psql 命令行**

```bash
psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster -f conf/schema.sql
```

**方式2: 使用测试脚本**

```bash
python test_postgresql.py
```

按提示选择 'y' 自动创建数据库表。

## 启动授权流程

### 步骤1: 启动服务器

```bash
# 开发模式 (自动重载)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

服务器启动后,你应该看到:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 步骤2: 访问授权页面

打开浏览器访问:

```
http://localhost:8000/auth/authorize?customer_id=123-456-7890
```

**重要**: 必须提供 `customer_id` 参数,格式为 `xxx-xxx-xxxx`。

**如何获取 Customer ID:**

1. 登录 [Google Ads](https://ads.google.com/)
2. 在顶部可以看到你的账户ID (格式: 123-456-7890)
3. 或者从账户URL中获取: `https://ads.google.com/aw/overview?ocid=1234567890`

### 步骤3: 完成 Google 授权

1. 页面会自动跳转到 Google 授权页面
2. 选择你的 Google 账户
3. 审核并同意授权范围:
   - Google Ads 账户访问权限
4. 点击 "允许"
5. 页面会重定向回 `http://localhost:8000/auth/callback`
6. 如果成功,你会看到 "✅ 授权成功!" 页面

### 步骤4: 验证授权结果

**方式1: 查看数据库**

```bash
psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster
```

```sql
-- 查看OAuth tokens
SELECT platform, account_key, is_valid, expires_at, created_at
FROM oauth_tokens
WHERE platform = 'google';

-- 查看Google账户
SELECT customer_id, account_name, account_type, status
FROM google_ad_accounts;

-- 查看授权日志
SELECT platform, account_key, action_type, status, created_at
FROM authorization_logs
WHERE platform = 'google'
ORDER BY created_at DESC
LIMIT 10;
```

**方式2: 使用Python测试脚本**

创建 `test_auth.py`:

```python
#!/usr/bin/env python
"""测试授权状态"""
import sys
sys.path.insert(0, '.')

from src.database import SessionLocal
from src.models import OAuthToken, GoogleAdAccount, AuthorizationLog

db = SessionLocal()

print("=== OAuth Tokens ===")
tokens = db.query(OAuthToken).filter(OAuthToken.platform == 'google').all()
for token in tokens:
    print(f"Customer ID: {token.account_key}, Valid: {token.is_valid}, Expires: {token.expires_at}")

print("\n=== Google Accounts ===")
accounts = db.query(GoogleAdAccount).all()
for account in accounts:
    print(f"Customer ID: {account.customer_id}, Name: {account.account_name}, Type: {account.account_type}")

print("\n=== Recent Authorization Logs ===")
logs = db.query(AuthorizationLog).filter(
    AuthorizationLog.platform == 'google'
).order_by(AuthorizationLog.created_at.desc()).limit(5).all()
for log in logs:
    print(f"{log.created_at}: {log.action_type} - {log.status} (Customer: {log.account_key})")

db.close()
```

运行测试:

```bash
python test_auth.py
```

## 常见问题排查

### 问题1: 授权后提示 "redirect_uri_mismatch"

**原因**: 回调地址不匹配

**解决方案**:
1. 检查 `.env` 中的 `GOOGLE_REDIRECT_URI` 是否正确
2. 确保 Google Cloud Console 中配置了相同的重定向URI
3. 注意 HTTP/HTTPS 和端口号必须完全一致

### 问题2: 授权成功但没有 refresh_token

**原因**: 用户已经授权过,Google 不会再次返回 refresh_token

**解决方案**:
1. 访问 [Google 账户权限页面](https://myaccount.google.com/permissions)
2. 撤销对你的应用的访问权限
3. 重新进行授权流程

### 问题3: Token已过期

**原因**: Access token 默认1小时过期

**解决方案**:
- 系统会自动使用 refresh_token 刷新 access_token
- 或者使用 Token 刷新脚本 (见下一节)

### 问题4: 提示 "invalid_client"

**原因**: 客户端ID或密钥错误

**解决方案**:
1. 检查 `.env` 中的 `GOOGLE_CLIENT_ID` 和 `GOOGLE_CLIENT_SECRET`
2. 确保没有多余的空格或换行符
3. 从 Google Cloud Console 重新复制凭据

### 问题5: 数据库连接失败

**原因**: 数据库配置错误或网络问题

**解决方案**:
1. 运行 `python test_postgresql.py` 测试连接
2. 检查数据库主机、端口、用户名、密码
3. 确保可以访问数据库服务器

## API 端点说明

### 授权端点

**GET `/auth/authorize`**

开始授权流程

参数:
- `customer_id` (必需): Google Ads Customer ID (格式: 123-456-7890)

示例:
```
http://localhost:8000/auth/authorize?customer_id=123-456-7890
```

### 回调端点

**GET `/auth/callback`**

OAuth2 回调端点 (由 Google 自动调用)

参数:
- `code`: 授权码
- `state`: 状态参数
- `error`: 错误信息 (如果授权失败)

### 健康检查

**GET `/health`**

检查服务器状态

响应:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00"
}
```

## 日志查看

服务器日志会显示授权流程的详细信息:

```bash
# 实时查看日志
tail -f logs/xmp_auth_server.log

# 查看最近的错误
grep ERROR logs/xmp_auth_server.log | tail -20
```

日志级别:
- `INFO`: 正常流程信息
- `WARNING`: 警告信息 (非致命错误)
- `ERROR`: 错误信息 (操作失败)

## 下一步

授权成功后,你可以:

1. **同步推广活动数据**:
   ```python
   from src.services.google_ads_service import google_ads_service
   from src.database import SessionLocal

   db = SessionLocal()
   customer_id = "123-456-7890"

   # 同步campaigns
   success = google_ads_service.sync_campaigns(db, customer_id)

   # 同步ad groups
   success = google_ads_service.sync_ad_groups(db, customer_id)

   db.close()
   ```

2. **设置 Token 自动刷新** (见 `refresh_tokens.py`)

3. **创建定时任务** 定期同步数据

## 安全建议

1. **生产环境**:
   - 使用 HTTPS
   - 更新重定向URI为生产域名
   - 设置强密码和密钥

2. **密钥管理**:
   - 不要将 `.env` 文件提交到版本控制
   - 定期轮换 `ENCRYPTION_KEY`
   - 使用密钥管理服务 (如 AWS Secrets Manager)

3. **访问控制**:
   - 限制 API 访问 (添加认证中间件)
   - 记录所有授权操作
   - 定期审查授权日志

## 总结

完整的授权流程:

1. ✅ 配置 Google Cloud Console 和环境变量
2. ✅ 初始化数据库表
3. ✅ 启动 FastAPI 服务器
4. ✅ 访问授权URL (带 customer_id)
5. ✅ 完成 Google 授权
6. ✅ 验证授权结果
7. ✅ 开始同步数据

如果遇到问题,请查看日志文件或运行测试脚本进行排查。
