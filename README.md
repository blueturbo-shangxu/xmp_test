# XMP Auth Server

Google Ads OAuth2 授权与数据同步系统

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-316192.svg)](https://www.postgresql.org/)

## 📖 项目简介

XMP Auth Server 是一个基于 Python + FastAPI 的 Google Ads OAuth2 授权和数据同步服务，为广告 XMP 系统提供完整的授权管理和数据同步能力。

### 核心特性

- 🔐 **OAuth2 授权** - 完整的 Google Ads OAuth2 授权流程
- 🔄 **自动刷新** - Token 过期自动刷新机制
- 📊 **数据同步** - 支持推广活动、广告组等数据同步
- 📝 **操作日志** - 完整的授权和操作记录
- 🎯 **异常处理** - 友好的错误提示和处理
- 🌐 **Web 界面** - 便捷的授权测试前端页面
- 🚀 **高性能** - 基于 FastAPI 的异步框架

## 🏗️ 项目结构

```
xmp_auth_server/
├── conf/                           # 配置文件目录
│   ├── .env.example               # 环境变量示例
│   └── .env                       # 环境变量配置(需创建)
├── src/                           # 源代码目录
│   ├── api/                       # API 接口定义
│   │   ├── auth.py               # 授权相关 API
│   │   └── api.py                # 业务 API
│   ├── core/                      # 核心配置
│   │   └── config.py             # 配置管理
│   ├── sql/                       # 数据库相关
│   │   ├── database.py           # 数据库连接
│   │   └── models.py             # 数据模型
│   ├── services/                  # 服务层
│   │   ├── oauth_service.py      # OAuth 服务
│   │   └── google/               # Google Ads 服务模块
│   │       ├── oauth_service.py      # OAuth 服务
│   │       ├── base_service.py       # 基础服务类
│   │       ├── account_service.py    # 账户服务
│   │       ├── campaign_service.py   # Campaign 服务
│   │       ├── ad_group_service.py   # AdGroup 服务
│   │       ├── ad_service.py         # Ad 服务
│   │       └── service_facade.py     # 服务外观（统一入口）
│   ├── middleware/                # 中间件
│   ├── utils/                     # 工具函数
│   ├── scripts/                   # 脚本工具
│   │   ├── refresh_tokens.py     # Token 刷新脚本
│   │   ├── test_api.py           # API 测试脚本
│   │   └── test_postgresql.py    # 数据库测试脚本
│   └── main.py                    # 应用入口
├── logs/                          # 日志目录(自动创建)
├── requirements.txt               # Python 依赖
├── run.py                         # 启动脚本
└── README.md                      # 项目文档
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.9+
- PostgreSQL 13+
- Google Cloud Platform 账号
- Google Ads 账号和 Developer Token

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd xmp_auth_server

# 创建虚拟环境(推荐)
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置数据库

```bash
# 创建数据库
createdb xmp_auth_server

# 或使用 psql
psql -U postgres
CREATE DATABASE xmp_auth_server;
\q
```

### 4. 配置环境变量

```bash
# 复制配置文件
cp conf/.env.example conf/.env

# 编辑配置文件
# 修改数据库连接、Google OAuth 配置等
```

关键配置项：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=xmp_auth_server

# Google OAuth2 配置
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Google Ads API 配置
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
```

### 5. 配置 Google Cloud Platform

#### 5.1 创建 OAuth 2.0 客户端

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 "Google Ads API"
4. 创建 OAuth 2.0 客户端 ID：
   - 应用类型：Web 应用
   - 授权重定向 URI：`http://localhost:8000/auth/callback`
5. 获取客户端 ID 和密钥

#### 5.2 申请 Google Ads Developer Token

1. 访问 [Google Ads API Center](https://ads.google.com/aw/apicenter)
2. 申请 Developer Token
3. 测试环境可立即使用，生产环境需等待审批

### 6. 启动服务

```bash
# 使用启动脚本
python run.py

# 或直接运行
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问：http://localhost:8000

### 7. 测试授权

1. 访问首页：http://localhost:8000
2. 输入 Google Ads Customer ID（格式：123-456-7890）
3. 点击"开始授权 Google Ads"
4. 在 Google 授权页面登录并授权
5. 授权成功后自动返回系统

## 📚 API 文档

### 自动生成的文档

- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

### 主要接口

#### 授权接口

```bash
# 开始授权
GET /ads/auth/authorize?customer_id=123-456-7890

# 授权回调
GET /ads/auth/callback?code=xxx&state=xxx
```

#### 账户管理

```bash
# 获取账户列表
GET /api/accounts?skip=0&limit=100

# 获取账户详情
GET /api/accounts/{account_id}
```

#### 数据同步

```bash
# 同步推广活动
POST /api/sync/campaigns
Content-Type: application/json
{
  "account_id": 1,
  "task_type": "CAMPAIGNS",
  "customer_id": "123-456-7890"
}

# 同步广告组
POST /api/sync/ad-groups
Content-Type: application/json
{
  "account_id": 1,
  "task_type": "AD_GROUPS",
  "customer_id": "123-456-7890"
}
```

#### 数据查询

```bash
# 查询推广活动
GET /api/campaigns?account_id=1&skip=0&limit=100

# 查询广告组
GET /api/ad-groups?account_id=1&campaign_id=1&skip=0&limit=100
```

## 🛠️ 技术栈

| 类别 | 技术 | 版本 | 说明 |
|-----|------|------|------|
| Web 框架 | FastAPI | 0.109.0 | 现代、快速的 Web 框架 |
| 数据库 | PostgreSQL | 13+ | 关系型数据库 |
| ORM | SQLAlchemy | 2.0+ | Python SQL 工具包 |
| Google Ads | google-ads | 23.1.0 | Google Ads API 客户端 |
| OAuth | google-auth-oauthlib | 1.2.0 | Google OAuth2 认证 |
| ASGI 服务器 | Uvicorn | - | 高性能 ASGI 服务器 |

## 📊 数据库设计

### 核心表结构

#### oauth_tokens - OAuth 令牌表（多平台通用）
存储加密的 OAuth 令牌，支持 Google、Meta、TikTok 等多平台。

#### google_ad_accounts - Google Ads 账户表
存储 Google Ads 账户信息。

#### google_campaigns - 推广活动表
存储同步的 Google Ads 推广活动数据。

#### google_ad_groups - 广告组表
存储同步的广告组数据。

#### authorization_logs - 授权日志表
记录所有授权操作，包括授权、刷新、撤销等。

#### sync_tasks - 同步任务表
跟踪数据同步任务的状态和进度。

## 🔐 安全特性

### Token 存储
- OAuth Token 以明文形式存储在 PostgreSQL 数据库中
- 数据库连接使用加密传输
- 建议在生产环境启用数据库加密

### 操作日志
所有授权操作都会记录：
- 操作类型（AUTHORIZE、REFRESH、REVOKE、VALIDATE）
- 操作状态（SUCCESS、FAILED、PENDING）
- 错误信息
- IP 地址和 User Agent
- 操作耗时

### 异常处理
提供友好的错误提示：
- 用户拒绝授权
- 授权码无效
- 回调地址不匹配
- 客户端认证失败
- Refresh Token 无效
- API 调用失败

## 🔄 Token 自动刷新

系统提供自动 Token 刷新机制：

### 自动刷新
调用 API 时检测到 Token 过期会自动刷新。

### 手动刷新脚本
```bash
# 刷新即将过期的 Token（2小时内）
python src/scripts/refresh_tokens.py

# 试运行模式
python src/scripts/refresh_tokens.py --dry-run

# 自定义提前刷新时间
python src/scripts/refresh_tokens.py --hours 4

# 查看统计信息
python src/scripts/refresh_tokens.py --stats

# 检查无效 Token
python src/scripts/refresh_tokens.py --check-invalid
```

### 定时任务
建议配置 cron 定时任务自动刷新：

```bash
# 每小时执行一次
0 * * * * cd /path/to/xmp_auth_server && python src/scripts/refresh_tokens.py
```

## 🧪 测试

### 数据库测试
```bash
python src/scripts/test_postgresql.py
```

### API 测试
```bash
python src/scripts/test_api.py
```

### Python 客户端示例
```python
from src.scripts.test_api import XMPAuthClient

# 创建客户端
client = XMPAuthClient("http://localhost:8000")

# 健康检查
health = client.health_check()

# 获取账户
accounts = client.list_accounts()

# 同步推广活动
task = client.sync_campaigns(account_id=1, customer_id="123-456-7890")

# 查询推广活动
campaigns = client.list_campaigns(account_id=1)
```

## 🐛 常见问题

### Q1: 授权时提示 redirect_uri_mismatch
**A**: 检查 Google Cloud Console 中配置的重定向 URI 是否与 `.env` 中的 `GOOGLE_REDIRECT_URI` 完全一致。

### Q2: Token 刷新失败
**A**: Refresh Token 可能已被撤销，需要用户重新授权。

### Q3: 数据同步失败
**A**: 检查：
1. Developer Token 是否有效
2. 账户是否有访问权限
3. Customer ID 格式是否正确（123-456-7890）

### Q4: 数据库连接失败
**A**: 检查：
1. PostgreSQL 服务是否启动
2. 数据库配置是否正确
3. 用户是否有访问权限

### Q5: 找不到 Customer ID
**A**: 登录 Google Ads 账户，在右上角可以看到 Customer ID。

## 🔧 开发指南

### 添加新的数据同步功能

1. 在 `src/sql/models.py` 中定义数据模型
2. 在 `src/services/google/` 中实现同步逻辑（继承 base_service.py）
3. 在 `src/api/api.py` 中添加 API 端点
4. 更新数据库表结构

### 扩展到其他广告平台

项目已设计为多平台架构，可轻松扩展到 Meta、TikTok 等平台：

1. 在 `src/services/` 中创建平台服务类
2. 在 `src/api/` 中添加平台路由
3. 使用统一的 `oauth_tokens` 表存储不同平台的 Token

## 📝 日志

日志文件位置：
- 应用日志：`logs/app.log`
- Token 刷新日志：`logs/token_refresh.log`

日志级别可在 `.env` 中配置：
```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 🚀 生产部署

### 环境检查清单
- [ ] 使用 HTTPS
- [ ] 配置强密码和密钥
- [ ] 启用防火墙和安全组
- [ ] 定期备份数据库
- [ ] 监控日志和异常
- [ ] 配置定时任务刷新 Token
- [ ] 设置日志轮转

### 使用 Systemd 管理服务

创建服务文件 `/etc/systemd/system/xmp-auth-server.service`：

```ini
[Unit]
Description=XMP Auth Server
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/xmp_auth_server
Environment="PATH=/path/to/xmp_auth_server/venv/bin"
ExecStart=/path/to/xmp_auth_server/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable xmp-auth-server
sudo systemctl start xmp-auth-server
sudo systemctl status xmp-auth-server
```

### 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请提交 Issue。

---

**注意**: 本项目仅用于学习和开发目的。生产环境使用前请确保已配置所有安全措施。
