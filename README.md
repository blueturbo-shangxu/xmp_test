# XMP Auth Server

Google Ads OAuth2授权与数据同步系统 - 专为广告XMP系统设计

## 🚀 项目简介

XMP Auth Server 是一个基于 Python + FastAPI 的 Google Ads 授权和数据同步服务。提供完整的 OAuth2 授权流程、Token 自动刷新、数据同步等功能。

## ✨ 核心功能

- **🔐 OAuth2 授权**: 完整的 Google Ads OAuth2 授权流程
- **🔄 自动刷新**: Token 过期自动刷新机制
- **📊 数据同步**: 支持推广活动、广告组等数据同步
- **🔒 安全存储**: Token 加密存储,保障数据安全
- **📝 操作日志**: 完整的授权和操作记录
- **🎯 异常处理**: 多种异常情况的清晰提示
- **🌐 Web 界面**: 提供便捷的授权测试前端页面

## 📋 技术栈

- **Web 框架**: FastAPI 0.109.0
- **数据库**: MySQL + SQLAlchemy 2.0
- **Google Ads**: google-ads 23.1.0
- **认证**: google-auth-oauthlib 1.2.0
- **加密**: cryptography 42.0.0
- **服务器**: Uvicorn

## 📁 项目结构

```
xmp_auth_server/
├── conf/                       # 配置文件目录
│   ├── .env.example           # 环境变量示例
│   └── schema.sql             # 数据库表结构
├── src/                       # 源代码目录
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   ├── database.py            # 数据库连接
│   ├── models.py              # 数据库模型
│   ├── main.py                # 应用入口
│   ├── routes/                # 路由目录
│   │   ├── __init__.py
│   │   ├── auth.py            # 授权路由
│   │   └── api.py             # API路由
│   ├── services/              # 服务层
│   │   ├── __init__.py
│   │   ├── oauth_service.py   # OAuth服务
│   │   └── google_ads_service.py  # Google Ads API服务
│   └── utils/                 # 工具函数
│       ├── __init__.py
│       └── encryption.py      # 加密工具
├── logs/                      # 日志目录(自动创建)
├── requirements.txt           # Python依赖
└── README.md                  # 项目文档
```

## 🛠️ 安装部署

### 1. 环境要求

- Python 3.9+
- MySQL 5.7+ / 8.0+
- Google Cloud Platform 账号
- Google Ads 账号和 Developer Token

### 2. 克隆项目

```bash
git clone <repository-url>
cd xmp_auth_server
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制配置文件并修改:

```bash
cp conf/.env.example conf/.env
```

编辑 `conf/.env` 文件,配置以下关键信息:

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=xmp_auth_server

# Google OAuth2 配置
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Google Ads API 配置
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token

# Token加密密钥(必须是32字符)
TOKEN_ENCRYPTION_KEY=your_32_character_encryption_key
```

### 5. 创建数据库

```bash
# 登录MySQL
mysql -u root -p

# 执行SQL文件
source conf/schema.sql
```

或者直接执行:

```bash
mysql -u root -p < conf/schema.sql
```

### 6. Google Cloud Platform 配置

#### 6.1 创建 OAuth 2.0 客户端

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 "Google Ads API"
4. 创建 OAuth 2.0 客户端 ID:
   - 应用类型: Web 应用
   - 授权重定向 URI: `http://localhost:8000/auth/callback`
5. 获取客户端 ID 和密钥

#### 6.2 申请 Google Ads Developer Token

1. 访问 [Google Ads API Center](https://ads.google.com/aw/apicenter)
2. 申请 Developer Token
3. 等待审批(测试环境可以立即使用)

### 7. 启动服务

```bash
cd src
python main.py
```

或使用 uvicorn:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问: http://localhost:8000

## 📖 使用指南

### 1. 授权流程

#### Web 界面授权

1. 访问首页: http://localhost:8000
2. 输入 Google Ads Customer ID (可选)
3. 点击"开始授权 Google Ads"
4. 在 Google 授权页面登录并授权
5. 授权成功后会自动跳转回系统

#### API 授权

```bash
# 开始授权
curl "http://localhost:8000/auth/authorize?customer_id=123-456-7890"
```

### 2. API 接口

#### 获取账户列表

```bash
curl http://localhost:8000/api/accounts
```

#### 同步推广活动

```bash
curl -X POST http://localhost:8000/api/sync/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "task_type": "CAMPAIGNS",
    "customer_id": "123-456-7890"
  }'
```

#### 同步广告组

```bash
curl -X POST http://localhost:8000/api/sync/ad-groups \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "task_type": "AD_GROUPS",
    "customer_id": "123-456-7890"
  }'
```

#### 查询推广活动

```bash
curl "http://localhost:8000/api/campaigns?account_id=1"
```

#### 查询广告组

```bash
curl "http://localhost:8000/api/ad-groups?account_id=1&campaign_id=1"
```

### 3. 查看 API 文档

访问自动生成的 API 文档:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔒 安全特性

### Token 加密

所有 OAuth Token 在存储前都会使用 AES-256 加密,确保数据安全。

### 异常处理

系统提供详细的异常处理和提示:

1. **用户拒绝授权**: 显示友好的拒绝页面,提供重新授权选项
2. **授权码无效**: 提示授权码过期或无效,引导重新授权
3. **回调地址不匹配**: 提示检查 Google Cloud Console 配置
4. **客户端认证失败**: 提示检查客户端 ID 和密钥
5. **Refresh Token 无效**: 提示需要重新授权
6. **API 调用失败**: 记录详细错误日志,便于排查

### 操作日志

所有授权操作都会记录到 `authorization_logs` 表:
- 操作类型 (AUTHORIZE, REFRESH, REVOKE, VALIDATE)
- 操作状态 (SUCCESS, FAILED, PENDING)
- 错误信息
- IP 地址和 User Agent
- 操作耗时

## 📊 数据库表说明

### accounts (账户表)
存储 Google Ads 账户信息

### oauth_tokens (令牌表)
存储加密的 OAuth 令牌

### authorization_logs (授权日志表)
记录所有授权操作

### campaigns (推广活动表)
存储同步的推广活动数据

### ad_groups (广告组表)
存储同步的广告组数据

### sync_tasks (同步任务表)
跟踪数据同步任务状态

### api_rate_limits (API速率限制表)
跟踪 API 速率限制使用情况

完整的表结构请查看 [conf/schema.sql](conf/schema.sql)

## 🐛 常见问题

### Q1: 授权时提示 redirect_uri_mismatch

**A**: 检查 Google Cloud Console 中配置的重定向 URI 是否与 `.env` 中的 `GOOGLE_REDIRECT_URI` 完全一致。

### Q2: Token 刷新失败

**A**: Refresh Token 可能已被撤销,需要用户重新授权。

### Q3: 数据同步失败

**A**: 检查:
1. Developer Token 是否有效
2. 账户是否有访问权限
3. Customer ID 格式是否正确 (123-456-7890)

### Q4: 数据库连接失败

**A**: 检查:
1. MySQL 服务是否启动
2. 数据库配置是否正确
3. 用户是否有访问权限

## 🔄 Token 自动刷新机制

系统会在以下情况自动刷新 Token:

1. 调用 API 时检测到 Token 已过期
2. Token 即将过期时主动刷新
3. 刷新成功后更新数据库记录
4. 刷新失败标记 Token 为无效,需重新授权

## 📝 开发说明

### 添加新的数据同步功能

1. 在 `models.py` 中定义数据模型
2. 在 `google_ads_service.py` 中实现同步逻辑
3. 在 `api.py` 中添加 API 端点
4. 更新数据库表结构

### 扩展异常处理

在 `oauth_service.py` 和路由文件中添加更多异常类型的处理。

## 📄 许可证

[MIT License](LICENSE)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

## 📧 联系方式

如有问题或建议,请提交 Issue。

---

**注意**: 本项目仅用于学习和开发目的。生产环境使用前请确保:
1. 使用 HTTPS
2. 配置强密码和密钥
3. 启用防火墙和安全组
4. 定期备份数据库
5. 监控日志和异常
