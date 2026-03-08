"""
JWT中间件混合返回类型的处理方案

问题: 当中间件可能返回 dict 或 JSONResponse 时如何区分?
"""

from typing import Union
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.api.base_response import BaseResponse, RespCode


# ============================================================
# 方案1: 不混用返回类型 (推荐 - 当前token_verify.py使用的方案)
# ============================================================
class JWTBearerClean(HTTPBearer):
    """
    始终返回dict,失败时抛出异常

    优点:
    - 返回类型明确,类型安全
    - 路由函数逻辑简单清晰
    - 符合FastAPI最佳实践
    """
    async def __call__(self, request: Request) -> dict:
        credentials = await super().__call__(request)
        if not credentials:
            # 失败: 抛出异常,不返回Response
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="No token")
        # 成功: 返回dict
        return {"user_uid": "123", "is_valid": True}


# 使用方式 (推荐)
app = FastAPI()

@app.get("/api/users")
async def get_users(auth_data: dict = Depends(JWTBearerClean())):
    # auth_data 一定是 dict,类型安全
    user_uid = auth_data["user_uid"]  # 类型提示正常工作
    return {"users": [], "requester": user_uid}


# ============================================================
# 方案2: 使用 Union 类型并在路由中检查类型
# ============================================================
class JWTBearerMixed(HTTPBearer):
    """
    可能返回dict或JSONResponse

    缺点:
    - 返回类型不确定
    - 路由函数需要额外的类型检查
    - 代码可读性差
    """
    async def __call__(self, request: Request) -> Union[dict, JSONResponse]:
        credentials = await super().__call__(request)
        if not credentials:
            # 失败: 返回JSONResponse
            return JSONResponse(
                status_code=403,
                content=BaseResponse.with_code(RespCode.AUTH_FAIL).model_dump()
            )
        # 成功: 返回dict
        return {"user_uid": "123", "is_valid": True}


# 使用方式 (不推荐)
@app.get("/api/products")
async def get_products(auth_result: Union[dict, JSONResponse] = Depends(JWTBearerMixed())):
    # 必须先检查类型
    if isinstance(auth_result, JSONResponse):
        # 如果是JSONResponse,直接返回错误响应
        return auth_result

    # 否则是dict,继续处理
    auth_data: dict = auth_result
    user_uid = auth_data["user_uid"]
    return {"products": [], "requester": user_uid}


# ============================================================
# 方案3: 使用自定义依赖包装器自动处理
# ============================================================
class JWTBearerWithWrapper(HTTPBearer):
    """可能返回dict或JSONResponse"""
    async def __call__(self, request: Request) -> Union[dict, JSONResponse]:
        credentials = await super().__call__(request)
        if not credentials:
            return JSONResponse(
                status_code=403,
                content=BaseResponse.with_code(RespCode.AUTH_FAIL).model_dump()
            )
        return {"user_uid": "123", "is_valid": True}


def require_auth(jwt_bearer: JWTBearerWithWrapper = Depends(JWTBearerWithWrapper())):
    """
    依赖包装器: 自动处理Response,只返回dict

    这样路由函数只需要处理dict类型
    """
    async def wrapper(request: Request) -> dict:
        result = await jwt_bearer(request)

        # 如果是Response,直接抛出包含该Response的异常
        if isinstance(result, Response):
            from fastapi import HTTPException
            # 注意: 这样做会丢失Response对象,需要特殊处理
            raise HTTPException(status_code=result.status_code, detail="Auth failed")

        return result

    return Depends(wrapper)


# 使用方式 (较复杂)
@app.get("/api/orders")
async def get_orders(auth_data: dict = Depends(require_auth())):
    # auth_data 一定是 dict
    user_uid = auth_data["user_uid"]
    return {"orders": [], "requester": user_uid}


# ============================================================
# 方案4: 使用Response子类携带元数据 (高级用法)
# ============================================================
class AuthResponse(JSONResponse):
    """
    自定义Response类,携带认证信息

    即使验证成功也返回Response,但包含auth_data
    """
    def __init__(self, auth_data: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.auth_data = auth_data


class JWTBearerAdvanced(HTTPBearer):
    """始终返回AuthResponse"""
    async def __call__(self, request: Request) -> AuthResponse:
        credentials = await super().__call__(request)
        if not credentials:
            # 失败: 返回错误响应
            return AuthResponse(
                status_code=403,
                content=BaseResponse.with_code(RespCode.AUTH_FAIL).model_dump(),
                auth_data=None
            )
        # 成功: 返回成功响应,但携带auth_data
        auth_data = {"user_uid": "123", "is_valid": True}
        return AuthResponse(
            content={"status": "authenticated"},
            auth_data=auth_data  # 认证数据存储在Response对象中
        )


# 使用方式 (需要自定义中间件配合)
@app.get("/api/dashboard")
async def get_dashboard(auth_response: AuthResponse = Depends(JWTBearerAdvanced())):
    if auth_response.status_code != 200:
        return auth_response  # 返回错误响应

    # 从Response中提取auth_data
    auth_data = auth_response.auth_data
    return {"dashboard": "data", "user": auth_data["user_uid"]}


# ============================================================
# 最佳实践总结
# ============================================================
"""
推荐使用 **方案1** (当前 token_verify.py 的方案):

✅ 优点:
1. 类型安全: 返回类型始终是 dict
2. 代码清晰: 路由函数不需要类型检查
3. FastAPI标准: 使用HTTPException处理错误
4. 易于测试: mock和测试都很简单

❌ 避免方案2和方案4:
1. 增加复杂度
2. 类型检查麻烦
3. 代码可读性差
4. 不符合FastAPI最佳实践

示例对比:

# 方案1 (推荐)
@app.get("/users")
async def get_users(auth: dict = Depends(JWTBearer())):
    return {"user": auth["user_uid"]}  # 简单清晰

# 方案2 (不推荐)
@app.get("/users")
async def get_users(auth: Union[dict, Response] = Depends(JWTBearer())):
    if isinstance(auth, Response):  # 每个路由都要做这个检查
        return auth
    return {"user": auth["user_uid"]}  # 代码复杂
"""


# ============================================================
# FastAPI如何处理依赖返回的Response对象
# ============================================================
"""
FastAPI的行为:

1. 如果依赖返回 Response 对象:
   - FastAPI会直接使用这个Response
   - 跳过路由函数的执行
   - 直接返回给客户端

2. 如果依赖返回 非Response 对象:
   - 传递给路由函数作为参数
   - 路由函数正常执行

示例:

@app.get("/test")
async def test(result = Depends(some_dependency)):
    # 如果 some_dependency 返回了 Response:
    #   这个函数不会执行
    #   Response 直接返回给客户端

    # 如果 some_dependency 返回了 dict:
    #   result 就是那个 dict
    #   这个函数正常执行
    return {"data": result}

结论:
- 返回Response会短路路由处理
- 不需要在路由函数中检查类型
- 但会导致类型注解不准确

因此,推荐使用方案1,保持返回类型一致!
"""
