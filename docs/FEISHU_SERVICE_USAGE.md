# 飞书 OAuth Service 使用文档

## 概述

`FeishuOAuthService` 提供了飞书（Lark）OAuth2 授权认证功能，支持两种身份提供商（IDP）：
- **BlueFocus** - 蓝色光标应用
- **Tomato** - Tomato 应用

## 功能特性

✅ 使用授权码换取 token
✅ 使用 token 获取用户信息
✅ 支持同步和异步两种模式
✅ 支持多个飞书应用（BlueFocus 和 Tomato）
✅ 完整的日志记录
✅ 异常处理和错误日志

## 配置

### 环境变量配置

在 `conf/.env` 文件中添加飞书配置：

```env
# 飞书配置
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
FEISHU_TOMATO_APP_ID=your_tomato_app_id
FEISHU_TOMATO_APP_SECRET=your_tomato_app_secret
FEISHU_TOKEN_URL=https://passport.feishu.cn/suite/passport/oauth/token
FEISHU_USER_URL=https://passport.feishu.cn/suite/passport/oauth/userinfo
```

### Settings 配置

配置已自动加载到 `src/core/config.py` 中：

```python
class Settings(BaseSettings):
    # 飞书配置
    FEISHU_APP_ID: str = os.getenv('FEISHU_APP_ID', '')
    FEISHU_APP_SECRET: str = os.getenv('FEISHU_APP_SECRET', '')
    FEISHU_TOMATO_APP_ID: str = os.getenv('FEISHU_TOMATO_APP_ID', '')
    FEISHU_TOMATO_APP_SECRET: str = os.getenv('FEISHU_TOMATO_APP_SECRET', '')
    FEISHU_TOKEN_URL: str = os.getenv('FEISHU_TOKEN_URL', 'https://passport.feishu.cn/suite/passport/oauth/token')
    FEISHU_USER_URL: str = os.getenv('FEISHU_USER_URL', 'https://passport.feishu.cn/suite/passport/oauth/userinfo')
```

## API 参考

### 类：FeishuOAuthService

#### 1. get_token_info (同步)

使用授权码换取 token。

```python
def get_token_info(
    self,
    code: str,
    redirect_uri: str,
    idp: str = IdpEnum.BlueFocus.value
) -> Dict
```

**参数：**
- `code` (str): 授权码
- `redirect_uri` (str): 回调地址
- `idp` (str): 身份提供商，可选值：`IdpEnum.BlueFocus.value` 或 `IdpEnum.Tomato.value`

**返回值：**
```python
{
    "access_token": "xxx",      # 访问令牌
    "token_type": "Bearer",     # 令牌类型
    "expires_in": 7200,         # 过期时间（秒）
    "refresh_token": "xxx"      # 刷新令牌（如果有）
}
```

**异常：**
- `ValueError`: code 为空时抛出
- `httpx.HTTPError`: HTTP 请求失败时抛出

#### 2. get_user_info (同步)

使用 token 获取用户信息。

```python
def get_user_info(
    self,
    token_type: str,
    access_token: str
) -> Dict
```

**参数：**
- `token_type` (str): 令牌类型（通常是 "Bearer"）
- `access_token` (str): 访问令牌

**返回值：**
```python
{
    "open_id": "ou_xxx",        # 用户在应用中的唯一标识
    "union_id": "on_xxx",       # 用户在企业中的唯一标识
    "name": "张三",              # 用户名
    "email": "zhangsan@company.com",  # 邮箱
    "mobile": "13800138000",    # 手机号
    "avatar_url": "https://..."  # 头像URL
}
```

**异常：**
- `httpx.HTTPError`: HTTP 请求失败时抛出

#### 3. get_token_info_async (异步)

异步方式使用授权码换取 token。

```python
async def get_token_info_async(
    self,
    code: str,
    redirect_uri: str,
    idp: str = IdpEnum.BlueFocus.value
) -> Dict
```

参数和返回值与同步版本相同。

#### 4. get_user_info_async (异步)

异步方式使用 token 获取用户信息。

```python
async def get_user_info_async(
    self,
    token_type: str,
    access_token: str
) -> Dict
```

参数和返回值与同步版本相同。

### 枚举：IdpEnum

身份提供商枚举类。

```python
class IdpEnum(str, Enum):
    BlueFocus = "BlueFocus"
    Tomato = "Tomato"
```

## 使用示例

### 示例 1: 基本使用（同步）

```python
from src.services import feishu_oauth_service, IdpEnum

# 1. 使用授权码换取 token
try:
    token_info = feishu_oauth_service.get_token_info(
        code="authorization_code_here",
        redirect_uri="http://localhost:8007/feishu/callback",
        idp=IdpEnum.BlueFocus.value
    )

    access_token = token_info['access_token']
    token_type = token_info['token_type']

    print(f"Access Token: {access_token}")
    print(f"Token Type: {token_type}")

except ValueError as e:
    print(f"参数错误: {e}")
except Exception as e:
    print(f"获取 token 失败: {e}")

# 2. 使用 token 获取用户信息
try:
    user_info = feishu_oauth_service.get_user_info(
        token_type=token_type,
        access_token=access_token
    )

    print(f"User OpenID: {user_info['open_id']}")
    print(f"User Name: {user_info['name']}")
    print(f"User Email: {user_info.get('email', 'N/A')}")

except Exception as e:
    print(f"获取用户信息失败: {e}")
```

### 示例 2: 使用 Tomato 应用

```python
from src.services import feishu_oauth_service, IdpEnum

# 使用 Tomato IDP
token_info = feishu_oauth_service.get_token_info(
    code="authorization_code_here",
    redirect_uri="http://localhost:8007/feishu/callback",
    idp=IdpEnum.Tomato.value  # 使用 Tomato 应用
)
```

### 示例 3: FastAPI 路由中使用（异步）

```python
from fastapi import APIRouter, HTTPException
from src.services import feishu_oauth_service, IdpEnum

router = APIRouter()

@router.get("/feishu/callback")
async def feishu_callback(code: str, state: str = None):
    """
    飞书 OAuth 回调处理
    """
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        # 1. 获取 token
        token_info = await feishu_oauth_service.get_token_info_async(
            code=code,
            redirect_uri="http://localhost:8007/feishu/callback",
            idp=IdpEnum.BlueFocus.value
        )

        # 2. 获取用户信息
        user_info = await feishu_oauth_service.get_user_info_async(
            token_type=token_info['token_type'],
            access_token=token_info['access_token']
        )

        # 3. 处理用户信息（例如创建 session、JWT token 等）
        return {
            "message": "Authorization successful",
            "user": {
                "open_id": user_info['open_id'],
                "name": user_info['name'],
                "email": user_info.get('email')
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authorization failed: {str(e)}")
```

### 示例 4: 完整的授权流程

```python
from fastapi import APIRouter, HTTPException
from src.services import feishu_oauth_service, IdpEnum
from src.core.jwt_handler import generate_jwt_token
from src.core import settings
import time

router = APIRouter(prefix="/feishu", tags=["Feishu"])

@router.get("/login")
async def feishu_login(idp: str = "BlueFocus"):
    """
    步骤 1: 生成飞书授权 URL
    """
    # 构建飞书授权 URL
    app_id = settings.FEISHU_APP_ID if idp == "BlueFocus" else settings.FEISHU_TOMATO_APP_ID
    redirect_uri = "http://localhost:8007/feishu/callback"

    # 飞书授权 URL 格式
    auth_url = (
        f"https://passport.feishu.cn/suite/passport/oauth/authorize"
        f"?client_id={app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&state={idp}"
    )

    return {
        "authorization_url": auth_url,
        "redirect_uri": redirect_uri
    }

@router.get("/callback")
async def feishu_callback(code: str, state: str = "BlueFocus"):
    """
    步骤 2: 处理飞书授权回调
    """
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        # 1. 使用 code 换取 token
        token_info = await feishu_oauth_service.get_token_info_async(
            code=code,
            redirect_uri="http://localhost:8007/feishu/callback",
            idp=state
        )

        # 2. 使用 token 获取用户信息
        user_info = await feishu_oauth_service.get_user_info_async(
            token_type=token_info['token_type'],
            access_token=token_info['access_token']
        )

        # 3. 生成 JWT token
        jwt_token = generate_jwt_token(
            secret=settings.JWT_SECRET,
            user_id=user_info['open_id'],
            expires_at=int(time.time()) + (7 * 24 * 60 * 60),  # 7天
            ua=""
        )

        # 4. 返回结果
        return {
            "message": "Login successful",
            "jwt_token": jwt_token,
            "user": {
                "open_id": user_info['open_id'],
                "union_id": user_info.get('union_id'),
                "name": user_info['name'],
                "email": user_info.get('email'),
                "avatar_url": user_info.get('avatar_url')
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )
```

## 错误处理

### 常见错误

1. **ValueError: code is empty**
   - 原因：授权码为空
   - 解决：确保从飞书回调 URL 中获取到了 code 参数

2. **httpx.HTTPError**
   - 原因：HTTP 请求失败（网络问题、API 错误等）
   - 解决：检查网络连接、API URL 配置、app_id 和 app_secret

3. **401 Unauthorized**
   - 原因：app_id 或 app_secret 错误
   - 解决：检查环境变量配置是否正确

4. **400 Bad Request**
   - 原因：参数错误（code 无效、redirect_uri 不匹配等）
   - 解决：检查 code 是否过期、redirect_uri 是否与注册时一致

### 错误处理示例

```python
import httpx
from src.services import feishu_oauth_service

try:
    token_info = feishu_oauth_service.get_token_info(
        code=code,
        redirect_uri=redirect_uri
    )
except ValueError as e:
    # 参数错误
    print(f"Parameter error: {e}")
except httpx.HTTPStatusError as e:
    # HTTP 状态错误
    print(f"HTTP {e.response.status_code}: {e.response.text}")
except httpx.ConnectError:
    # 网络连接错误
    print("Network connection failed")
except httpx.TimeoutException:
    # 请求超时
    print("Request timeout")
except Exception as e:
    # 其他错误
    print(f"Unexpected error: {e}")
```

## 日志

服务会自动记录详细的日志信息：

```log
# 请求 token
[INFO] Requesting token from Feishu. URL: https://passport.feishu.cn/suite/passport/oauth/token, IDP: BlueFocus, redirect_uri: http://localhost:8007/feishu/callback

# token 响应
[INFO] Token response received. status_code: 200, text: {"access_token":"xxx","token_type":"Bearer",...}

# 请求用户信息
[INFO] Requesting user info from Feishu. URL: https://passport.feishu.cn/suite/passport/oauth/userinfo

# 用户信息响应
[INFO] User info response received. status_code: 200
[INFO] User info retrieved successfully. open_id: ou_xxx

# 错误日志
[ERROR] Failed to get token from Feishu. Error: HTTP 401 Unauthorized, IDP: BlueFocus
```

## 相关文档

- 飞书开放平台文档：https://open.feishu.cn/document/
- OAuth 2.0 规范：https://oauth.net/2/

## 总结

飞书 OAuth Service 已完成：
- ✅ 完整的 OAuth2 授权流程
- ✅ 支持两种身份提供商（BlueFocus 和 Tomato）
- ✅ 同步和异步两种模式
- ✅ 完整的错误处理和日志记录
- ✅ 详细的使用文档和示例
