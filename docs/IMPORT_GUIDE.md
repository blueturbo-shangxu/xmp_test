# 导入指南

本项目已优化导入路径，通过模块的 `__init__.py` 文件重新导出常用类和函数，简化导入语句。

## 优化后的导入方式

### 1. 核心配置 (src.core)

**旧方式：**
```python
from src.core.config import settings, setup_logging
```

**新方式：**
```python
from src.core import settings, setup_logging
```

### 2. 数据库和模型 (src.sql)

**旧方式：**
```python
from src.sql.database import get_db, init_db, SessionLocal
from src.sql.models import OAuthToken, GoogleAdAccount
```

**新方式：**
```python
from src.sql import get_db, init_db, SessionLocal
from src.sql import OAuthToken, GoogleAdAccount
```

或者一次性导入：
```python
from src.sql import (
    get_db, init_db, SessionLocal,
    OAuthToken, GoogleAdAccount, GoogleCampaign
)
```

### 3. 服务层 (src.services)

**旧方式：**
```python
from src.services.google.oauth_service import oauth_service
from src.services.google.account_service import GoogleAdsAccountService
```

**新方式：**
```python
from src.services import oauth_service, GoogleAdsService
```

### 4. API 路由 (src.api)

**旧方式：**
```python
from src.api.auth import router as auth_router
from src.api.api import router as api_router
```

**新方式：**
```python
from src.api import auth_router, api_router
```

## 可用的导出

### src.core
- `settings` - 配置实例
- `setup_logging` - 日志配置函数
- `Settings` - 配置类
- `BASE_DIR` - 项目根目录

### src.sql
**数据库相关：**
- `Base` - SQLAlchemy 基类
- `SessionLocal` - 会话工厂
- `engine` - 数据库引擎
- `get_db` - 依赖注入函数
- `check_db_connection` - 检查数据库连接
- `init_db` - 初始化数据库

**模型类：**
- `OAuthToken` - OAuth 令牌模型
- `AuthorizationLog` - 授权日志模型
- `GoogleAdAccount` - Google Ads 账户模型
- `GoogleCampaign` - 推广活动模型
- `GoogleAdGroup` - 广告组模型
- `SyncTask` - 同步任务模型

### src.services
- `oauth_service` - OAuth 服务实例
- `GoogleAdsOAuthService` - OAuth 服务类
- `GoogleAdsService` - Google Ads API 服务外观类（推荐）
- `GoogleAdsServiceFacade` - Google Ads API 服务外观类
- `GoogleAdsAccountService` - 账户服务类
- `GoogleAdsCampaignService` - Campaign 服务类
- `GoogleAdsAdGroupService` - AdGroup 服务类
- `GoogleAdsAdService` - Ad 服务类

### src.api
- `auth_router` - 授权相关路由
- `api_router` - 业务 API 路由

## 示例

### 完整的应用入口文件

```python
from fastapi import FastAPI
from src.core import settings, setup_logging
from src.sql import check_db_connection, init_db
from src.api import auth_router, api_router

logger = setup_logging()

app = FastAPI(title="XMP Auth Server")
app.include_router(auth_router)
app.include_router(api_router)
```

### API 路由文件

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.sql import get_db, GoogleAdAccount, OAuthToken
from src.services import oauth_service

router = APIRouter()

@router.get("/accounts")
async def get_accounts(db: Session = Depends(get_db)):
    accounts = db.query(GoogleAdAccount).all()
    return accounts
```

### 服务文件

```python
from src.core import settings
from src.sql import OAuthToken, AuthorizationLog

class MyService:
    def __init__(self):
        self.api_key = settings.GOOGLE_ADS_DEVELOPER_TOKEN
```

## 优势

1. **更简洁** - 减少导入层级，代码更清晰
2. **更易维护** - 模块重构时只需修改 `__init__.py`
3. **更规范** - 统一的导入风格
4. **IDE 友好** - 更好的自动补全支持
5. **符合 Python 最佳实践** - 使用包级别的导出

## 注意事项

1. 避免循环导入 - `__init__.py` 中的导入应该是单向的
2. 保持 `__all__` 列表更新 - 明确模块的公共 API
3. 文档化导出 - 在 `__init__.py` 中添加清晰的注释
