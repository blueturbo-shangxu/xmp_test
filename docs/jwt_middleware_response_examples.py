"""
JWT中间件直接返回特定Response的几种方法示例

这个文件展示了在FastAPI的JWT中间件中如何直接返回特定的response
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from src.api.base_response import BaseResponse, RespCode


# ============================================================
# 方法1: 使用 HTTPException + detail (当前token_verify.py使用的方法)
# ============================================================
class JWTBearerMethod1(HTTPBearer):
    """
    优点: FastAPI标准做法,异常会自动被异常处理器捕获
    缺点: 只能返回HTTP 4xx/5xx错误状态码
    """
    async def __call__(self, request: Request):
        credentials = await super().__call__(request)
        if not credentials:
            # 抛出HTTPException,FastAPI会自动转换为JSON响应
            raise HTTPException(
                status_code=403,
                detail=BaseResponse.with_code(RespCode.AUTH_FAIL).model_dump()
            )
        return {"user": "validated"}


# ============================================================
# 方法2: 直接返回 JSONResponse (推荐用于需要自定义响应的场景)
# ============================================================
class JWTBearerMethod2(HTTPBearer):
    """
    优点: 完全控制响应(状态码、headers等)
    缺点: 需要注意返回类型,可能与依赖注入的期望类型不匹配
    注意: 返回JSONResponse后,后续的依赖注入和路由函数不会执行
    """
    async def __call__(self, request: Request):
        try:
            credentials = await super().__call__(request)
            if not credentials:
                # 直接返回JSONResponse
                return JSONResponse(
                    status_code=403,
                    content=BaseResponse.with_code(RespCode.AUTH_FAIL).model_dump(),
                    headers={"X-Auth-Error": "No credentials"}  # 可以添加自定义headers
                )
            return {"user": "validated"}
        except Exception as e:
            # 捕获所有异常并返回统一格式
            return JSONResponse(
                status_code=403,
                content=BaseResponse.fail(str(e)).model_dump()
            )


# ============================================================
# 方法3: 使用自定义异常 + 全局异常处理器 (最佳实践)
# ============================================================
class TokenAuthError(Exception):
    """自定义Token认证异常"""
    def __init__(self, response: BaseResponse, status_code: int = 403):
        self.response = response
        self.status_code = status_code
        super().__init__(response.message)


class JWTBearerMethod3(HTTPBearer):
    """
    优点:
    - 解耦了业务逻辑和响应格式
    - 可以在全局异常处理器中统一处理
    - 支持自定义状态码和响应内容

    使用方法:
    1. 在main.py中注册全局异常处理器
    2. 在中间件中抛出自定义异常
    """
    async def __call__(self, request: Request):
        credentials = await super().__call__(request)
        if not credentials:
            # 抛出自定义异常
            raise TokenAuthError(
                response=BaseResponse.with_code(RespCode.AUTH_FAIL),
                status_code=403
            )
        return {"user": "validated"}


# ============================================================
# 方法4: 使用 Request.state 传递错误信息 + 中间件处理
# ============================================================
class JWTBearerMethod4(HTTPBearer):
    """
    优点: 不中断请求处理流程,可以在后续中间件或路由中处理
    缺点: 需要额外的中间件来处理错误状态
    适用场景: 需要收集多个验证错误后统一返回
    """
    async def __call__(self, request: Request):
        credentials = await super().__call__(request)
        if not credentials:
            # 将错误信息存储在request.state中
            request.state.auth_error = BaseResponse.with_code(RespCode.AUTH_FAIL)
            request.state.auth_status_code = 403
            return None  # 返回None表示验证失败
        return {"user": "validated"}


# ============================================================
# 在main.py中注册全局异常处理器 (配合方法3使用)
# ============================================================
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(TokenAuthError)
async def token_auth_error_handler(request: Request, exc: TokenAuthError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.response.model_dump(),
        headers={"X-Error-Type": "TokenAuthError"}
    )
"""


# ============================================================
# 在main.py中添加中间件 (配合方法4使用)
# ============================================================
"""
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

class AuthErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 检查是否有认证错误
        if hasattr(request.state, 'auth_error'):
            return JSONResponse(
                status_code=request.state.auth_status_code,
                content=request.state.auth_error.model_dump()
            )

        return response

app.add_middleware(AuthErrorMiddleware)
"""


# ============================================================
# 实际使用示例
# ============================================================
"""
from fastapi import FastAPI, Depends

app = FastAPI()

# 使用方法1 (当前token_verify.py的方法)
@app.get("/api/v1/user")
async def get_user(auth_data: dict = Depends(JWTBearerMethod1())):
    return {"user": auth_data}

# 使用方法2
@app.get("/api/v1/profile")
async def get_profile(auth_data = Depends(JWTBearerMethod2())):
    # 注意: 如果返回JSONResponse,auth_data将是Response对象,不是dict
    if isinstance(auth_data, JSONResponse):
        return auth_data  # 直接返回错误响应
    return {"profile": auth_data}

# 使用方法3 (推荐)
@app.get("/api/v1/dashboard")
async def get_dashboard(auth_data: dict = Depends(JWTBearerMethod3())):
    return {"dashboard": auth_data}
"""


# ============================================================
# 总结与建议
# ============================================================
"""
选择建议:

1. **简单项目**: 使用方法1 (HTTPException)
   - 最简单直接
   - FastAPI官方推荐
   - 适合大多数场景

2. **需要完全控制响应**: 使用方法2 (JSONResponse)
   - 可以自定义headers
   - 可以自定义任何响应内容
   - 但要注意类型注解

3. **大型项目**: 使用方法3 (自定义异常 + 全局处理器)
   - 最佳实践
   - 解耦业务逻辑
   - 统一异常处理
   - 易于维护和扩展

4. **特殊需求**: 使用方法4 (Request.state)
   - 需要收集多个错误
   - 需要在后续流程中处理

当前 token_verify.py 使用的是 **方法1**,这是合适的选择。
如果未来需要更灵活的控制,建议迁移到 **方法3**。
"""
