# 快速启动指南

## 第一步: 安装依赖

```bash
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

## 第二步: 配置数据库

### 2.1 安装并启动 MySQL

确保 MySQL 服务已启动。

### 2.2 创建数据库

```bash
# 登录 MySQL
mysql -u root -p

# 执行数据库初始化脚本
source conf/schema.sql

# 或者
mysql -u root -p < conf/schema.sql
```

## 第三步: 配置环境变量

### 3.1 复制配置文件

```bash
cp conf/.env.example conf/.env
```

### 3.2 编辑配置文件

打开 `conf/.env` 文件,修改以下关键配置:

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的数据库密码
DB_NAME=xmp_auth_server

# Google OAuth2 配置 (从 Google Cloud Console 获取)
GOOGLE_CLIENT_ID=你的客户端ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=你的客户端密钥
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Google Ads API 配置
GOOGLE_ADS_DEVELOPER_TOKEN=你的开发者令牌

# Token加密密钥 (必须是32字符)
TOKEN_ENCRYPTION_KEY=abcdefghijklmnopqrstuvwxyz123456
```

## 第四步: 配置 Google Cloud Platform

### 4.1 创建项目

1. 访问 https://console.cloud.google.com/
2. 创建新项目或选择现有项目

### 4.2 启用 Google Ads API

1. 在项目中启用 "Google Ads API"
2. 等待几分钟让 API 生效

### 4.3 创建 OAuth 2.0 客户端

1. 进入 "API和服务" > "凭据"
2. 点击 "创建凭据" > "OAuth 2.0 客户端 ID"
3. 选择应用类型: "Web 应用"
4. 添加授权重定向 URI: `http://localhost:8000/auth/callback`
5. 创建后复制客户端 ID 和密钥到 `.env` 文件

### 4.4 申请 Developer Token

1. 访问 https://ads.google.com/aw/apicenter
2. 申请 Developer Token
3. 复制到 `.env` 文件
4. 测试环境可以立即使用,生产环境需要等待审批

## 第五步: 启动服务

```bash
# 方式1: 使用启动脚本
python run.py

# 方式2: 直接运行主程序
cd src
python main.py

# 方式3: 使用 uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

启动成功后会看到:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Starting XMP Auth Server...
INFO:     Database connection OK
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 第六步: 测试授权

### 6.1 访问首页

打开浏览器访问: http://localhost:8000

### 6.2 开始授权

1. 在首页输入 Google Ads Customer ID (格式: 123-456-7890)
2. 点击 "开始授权 Google Ads"
3. 在 Google 授权页面登录并授权
4. 授权成功后会自动返回系统

### 6.3 查看 API 文档

访问自动生成的 API 文档:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 第七步: 测试数据同步

### 7.1 获取账户列表

```bash
curl http://localhost:8000/api/accounts
```

### 7.2 同步推广活动

```bash
curl -X POST http://localhost:8000/api/sync/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "task_type": "CAMPAIGNS",
    "customer_id": "123-456-7890"
  }'
```

### 7.3 查询同步数据

```bash
# 查询推广活动
curl "http://localhost:8000/api/campaigns?account_id=1"

# 查询广告组
curl "http://localhost:8000/api/ad-groups?account_id=1"
```

## 常见问题

### Q: 数据库连接失败?

A: 检查:
- MySQL 服务是否启动
- 数据库配置是否正确
- 用户密码是否正确
- 数据库是否已创建

### Q: 授权时提示 redirect_uri_mismatch?

A: 确保 Google Cloud Console 中配置的重定向 URI 与 `.env` 中的完全一致。

### Q: 找不到 Customer ID?

A: 登录 Google Ads 账户,在右上角可以看到 Customer ID。

### Q: Developer Token 申请失败?

A: 测试环境可以使用待审批的 Token。生产环境需要完整的审批流程。

## 下一步

- 查看完整的 [README.md](README.md) 了解更多功能
- 阅读 API 文档了解所有可用接口
- 根据业务需求扩展数据同步功能

## 需要帮助?

如有问题,请提交 Issue 或查看项目文档。
