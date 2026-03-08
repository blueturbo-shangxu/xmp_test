"""
如何将 JWTBearer 注册到 FastAPI App

这个文件展示了多种方式在FastAPI中使用JWT中间件进行认证
"""

from fastapi import FastAPI, Depends, APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from src.middleware.token_verify import JWTBearer
from src.api.base_response import BaseResponse, RespCode


# ============================================================
# 方法1: 作为路由依赖使用 (最常用,推荐)
# ============================================================

# 示例1: 单个路由添加认证
router_v1 = APIRouter(prefix="/api/v1", tags=["api-v1"])

@router_v1.get("/users")
async def get_users(auth_data: dict = Depends(JWTBearer())):
    """
    获取用户列表 - 需要JWT认证

    使用方式:
    curl -H "Authorization: Bearer <your_jwt_token>" http://localhost:8000/api/v1/users
    """
    user_uid = auth_data.get('user_uid')
    return {
        "users": ["user1", "user2"],
        "requester": user_uid
    }


@router_v1.get("/profile")
async def get_profile(auth_data: dict = Depends(JWTBearer())):
    """
    获取用户资料 - 需要JWT认证
    """
    return {
        "user_uid": auth_data.get('user_uid'),
        "is_valid": auth_data.get('is_token_valid'),
        "expires_at": auth_data.get('expires_at')
    }


@router_v1.get("/public")
async def public_endpoint():
    """
    公开接口 - 不需要认证
    """
    return {"message": "This is a public endpoint"}


# ============================================================
# 方法2: 整个路由器添加认证 (推荐用于所有接口都需要认证的模块)
# ============================================================

router_v2 = APIRouter(
    prefix="/api/v2",
    tags=["api-v2"],
    dependencies=[Depends(JWTBearer())]  # 所有路由都需要JWT认证
)

@router_v2.get("/protected-users")
async def protected_users(request: Request):
    """
    这个路由自动需要JWT认证(因为router设置了dependencies)

    注意: auth_data不会自动注入,需要通过request.state获取
    或者在路由参数中显式声明 Depends(JWTBearer())
    """
    return {"message": "All routes in this router are protected"}


@router_v2.get("/protected-data")
async def protected_data(auth_data: dict = Depends(JWTBearer())):
    """
    如果需要使用auth_data,仍然需要在参数中显式声明
    """
    return {
        "data": "sensitive data",
        "user": auth_data.get('user_uid')
    }


# ============================================================
# 方法3: 使用可选认证 (允许匿名访问,但识别已登录用户)
# ============================================================

router_v3 = APIRouter(prefix="/api/v3", tags=["api-v3"])

@router_v3.get("/optional-auth")
async def optional_auth(auth_data: Optional[dict] = Depends(JWTBearer(auto_error=False))):
    """
    可选认证: 有token则验证,没有token也不报错

    使用场景:
    - 公开内容,但登录用户可以看到更多信息
    - 统计登录和未登录用户的行为
    """
    if auth_data and auth_data.get('is_token_valid'):
        return {
            "message": "Welcome back!",
            "user_uid": auth_data.get('user_uid'),
            "premium_content": True
        }
    else:
        return {
            "message": "Welcome guest!",
            "premium_content": False
        }


# ============================================================
# 方法4: 全局中间件 (不推荐,除非所有接口都需要认证)
# ============================================================

async def jwt_middleware(request: Request, call_next):
    """
    全局JWT中间件

    注意: 这种方式会拦截所有请求,包括静态文件、health check等
    通常不推荐使用,建议用方法1或方法2
    """
    # 排除不需要认证的路径
    excluded_paths = ["/", "/health", "/docs", "/openapi.json", "/ads/auth"]

    if any(request.url.path.startswith(path) for path in excluded_paths):
        return await call_next(request)

    # 验证JWT
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return JSONResponse(
            status_code=403,
            content=BaseResponse.with_code(RespCode.AUTH_FAIL).model_dump()
        )

    # 这里可以调用JWTBearer的验证逻辑
    # 但通常不推荐这样做,因为无法使用FastAPI的依赖注入优势

    return await call_next(request)


# ============================================================
# 方法5: 自定义依赖工厂 (高级用法)
# ============================================================

def require_auth(check_admin: bool = False):
    """
    依赖工厂: 根据参数返回不同的认证依赖

    使用场景:
    - 需要不同级别的权限验证
    - 需要额外的业务逻辑判断
    """
    async def auth_dependency(auth_data: dict = Depends(JWTBearer())):
        # 基础JWT验证已通过
        user_uid = auth_data.get('user_uid')

        # 额外的权限检查
        if check_admin:
            # 这里可以查询数据库检查是否是管理员
            # is_admin = check_user_is_admin(user_uid)
            # if not is_admin:
            #     raise HTTPException(status_code=403, detail="Admin access required")
            pass

        return auth_data

    return Depends(auth_dependency)


router_v4 = APIRouter(prefix="/api/v4", tags=["api-v4"])

@router_v4.get("/user-endpoint")
async def user_endpoint(auth_data: dict = require_auth(check_admin=False)):
    """普通用户端点"""
    return {"message": "User access granted"}


@router_v4.get("/admin-endpoint")
async def admin_endpoint(auth_data: dict = require_auth(check_admin=True)):
    """管理员端点 - 需要额外的权限验证"""
    return {"message": "Admin access granted"}


# ============================================================
# 方法6: 全局异常处理器 (配合JWT使用)
# ============================================================

def register_exception_handlers(app: FastAPI):
    """
    注册全局异常处理器
    统一处理JWT认证失败的情况
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        统一处理HTTPException
        包括JWT认证失败的403错误
        """
        # 如果是JWT认证失败(status_code=403且detail是dict)
        if exc.status_code == 403 and isinstance(exc.detail, dict):
            return JSONResponse(
                status_code=403,
                content=exc.detail,
                headers={"X-Auth-Error": "JWT-Verification-Failed"}
            )

        # 其他HTTP异常
        return JSONResponse(
            status_code=exc.status_code,
            content=BaseResponse.fail(
                message=str(exc.detail),
                code=exc.status_code
            ).model_dump()
        )


# ============================================================
# 完整的应用配置示例
# ============================================================

def create_app() -> FastAPI:
    """
    创建并配置FastAPI应用
    展示如何注册JWT中间件
    """
    app = FastAPI(
        title="XMP Server",
        description="API with JWT Authentication",
        version="1.0.0"
    )

    # 注册全局异常处理器
    register_exception_handlers(app)

    # 注册路由器
    app.include_router(router_v1)  # 方法1: 单个路由添加认证
    app.include_router(router_v2)  # 方法2: 整个路由器添加认证
    app.include_router(router_v3)  # 方法3: 可选认证
    app.include_router(router_v4)  # 方法5: 自定义依赖工厂

    # 方法4: 添加全局中间件 (不推荐,此处注释掉)
    # app.middleware("http")(jwt_middleware)

    return app


# ============================================================
# 实际使用示例 (在 src/main.py 中)
# ============================================================
"""
# src/main.py

from fastapi import FastAPI, Depends
from src.middleware.token_verify import JWTBearer
from src.api import api_router, auth_router

app = FastAPI(title="XMP Server")

# 方式1: 在路由文件中使用 (推荐)
# 在 src/api/api.py 中:
@router.get("/accounts")
async def list_accounts(
    db: Session = Depends(get_db),
    auth_data: dict = Depends(JWTBearer())
):
    user_uid = auth_data['user_uid']
    # ... 业务逻辑
    return accounts

# 方式2: 对整个路由器应用认证
protected_router = APIRouter(
    prefix="/api",
    dependencies=[Depends(JWTBearer())]  # 所有/api/*路由都需要认证
)
protected_router.include_router(api_router)
app.include_router(protected_router)

# 公开路由不需要认证
app.include_router(auth_router)  # /ads/auth/* 路由不需要认证
"""


# ============================================================
# 测试JWT认证的curl命令示例
# ============================================================
"""
# 1. 先获取JWT token (假设有登录接口)
curl -X POST http://localhost:8000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username":"user","password":"pass"}' \\
  | jq -r '.data.token'

# 2. 使用token访问受保护的API
curl http://localhost:8000/api/v1/users \\
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 3. 不带token访问(会返回403错误)
curl http://localhost:8000/api/v1/users

# 4. 访问可选认证的接口
curl http://localhost:8000/api/v3/optional-auth
# 不带token: 返回guest信息
# 带token: 返回用户信息

# 5. 访问公开接口
curl http://localhost:8000/api/v1/public
# 不需要token
"""


# ============================================================
# 最佳实践总结
# ============================================================
"""
推荐做法:

1. **大多数API路由**: 使用方法1 (单个路由添加 Depends(JWTBearer()))
   - 清晰明确
   - 易于理解和维护
   - 可以选择性地保护路由

2. **整个模块都需要认证**: 使用方法2 (路由器级别dependencies)
   - 适合admin模块、user模块等
   - 避免重复代码

3. **需要区分登录/未登录用户**: 使用方法3 (auto_error=False)
   - 适合公开内容
   - 可以为登录用户提供额外功能

4. **需要复杂权限逻辑**: 使用方法5 (依赖工厂)
   - 可以添加额外的权限检查
   - 可以根据参数定制认证逻辑

5. **统一错误处理**: 使用方法6 (全局异常处理器)
   - 提供一致的错误响应格式
   - 可以添加日志、监控等

避免做法:

❌ 不推荐方法4 (全局中间件)
  - 难以排除特定路径
  - 无法使用依赖注入
  - 性能开销大
  - 难以测试

当前项目建议:
- 对 /api/* 路由使用方法1或方法2
- 对 /ads/auth/* 路由不使用认证(OAuth回调)
- 对 /health、/docs 等管理接口不使用认证
"""
