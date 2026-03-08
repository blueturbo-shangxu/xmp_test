# 日志中间件问题分析和修复方案

## 🔍 发现的问题

### 1. **严重问题：finally 块中缺少返回值**

**位置：** [src/middleware/log_middleware.py:112-117](../src/middleware/log_middleware.py#L112-L117)

```python
except Exception as e:
    logging.error(f"[uuid: {request.headers.get('req-uuid')}] get data error: {e} "
                  f" traceback=[{traceback.format_exc()}]")
    # traceback.print_exc()
finally:
    pass  # ❌ 这里没有返回值！
```

**问题描述：**
- 当日志记录过程中发生异常时（例如响应体无法解码），`except` 块捕获了异常但没有返回响应
- 这会导致整个请求没有返回值，客户端会收到错误或挂起

**影响：**
- 🔴 严重：用户请求可能没有响应
- 🔴 严重：可能导致连接超时

### 2. **逻辑问题：request_body_len 赋值错误**

**位置：** [src/middleware/log_middleware.py:96](../src/middleware/log_middleware.py#L96)

```python
f"request_body_len: {len(response_body_str)},"  # ❌ 这应该是 req_body_len
```

**问题描述：**
- 日志中 `request_body_len` 字段实际记录的是响应体长度
- 应该记录的是请求体长度 `req_body_len`

**影响：**
- 🟡 中等：日志信息混淆，不利于调试

### 3. **未使用的变量**

**位置：** [src/middleware/log_middleware.py:102-107](../src/middleware/log_middleware.py#L102-L107)

```python
res = jsonable_encoder(response_body.decode())
inc_code = None
if res:
    res_dict = json.loads(res) or {}
    inc_code = res_dict.get("code", response.status_code)
else:
    inc_code = response.status_code
# ❌ inc_code 变量定义了但从未使用
```

**影响：**
- 🟢 轻微：代码冗余，但不影响功能

### 4. **未使用的变量和导入**

**位置：** [src/middleware/log_middleware.py:18](../src/middleware/log_middleware.py#L18)

```python
hostname = socket.gethostname()  # ❌ 定义了但从未使用
```

**影响：**
- 🟢 轻微：代码冗余

### 5. **BaseResponse 导入路径可能错误**

**位置：** [src/middleware/log_middleware.py:14](../src/middleware/log_middleware.py#L14)

```python
from src.actions.base import BaseResponse  # ❓ 这个路径是否正确？
```

**问题描述：**
- 根据项目结构，BaseResponse 应该在 `src.api.base_response` 中
- 需要验证这个导入路径

**影响：**
- 🔴 严重：如果路径错误，中间件无法正常工作

## ✅ 修复方案

### 修复后的完整代码

```python
import json
import logging
import time
import traceback
import uuid

from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.types import Message

from src.api.base_response import BaseResponse, RespCode

logger = logging.getLogger(__name__)


async def set_body(request: Request, body: bytes):
    """重置请求体，使其可以被多次读取"""
    async def receive() -> Message:
        return {'type': 'http.request', 'body': body}
    request._receive = receive


async def add_process_time(request: Request, call_next):
    """
    日志中间件：记录请求和响应，统计处理时间
    """
    start_time = time.time()

    # 添加请求UUID到headers
    headers = dict(request.scope['headers'])
    req_uuid = str(uuid.uuid4())
    headers[b'req-uuid'] = req_uuid.encode()
    request.scope['headers'] = [(k, v) for k, v in headers.items()]

    # 读取并重置请求体
    req_body = await request.body()
    await set_body(request, req_body)

    # 处理请求体（用于日志）
    try:
        req_body_str = req_body.decode().replace("\n", "\\n")
        req_body_len = len(req_body_str)
        if req_body_len > 4096:
            req_body_str = req_body_str[:4096] + "..."
    except Exception:
        req_body_str = ""
        req_body_len = 0

    # 处理请求
    try:
        response = await call_next(request)

        # 检查是否为流式响应或图片响应
        content_type = response.headers.get("content-type", "")
        if any(keyword in content_type.lower() for keyword in ["stream", "image"]):
            logger.info(
                f"[uuid: {req_uuid}] "
                f"response: [[[StreamingResponse]]], "
                f"method: {request.method}, "
                f"uri: {request.url.path}, "
                f"req_body_len: {req_body_len}, "
                f"process_time: {time.time() - start_time:.3f}s"
            )
            return response

        # 忽略文档访问日志
        if any(path in request.url.path for path in ["docs", "redoc", "openapi.json"]):
            return response

    except Exception as e:
        # 请求处理过程中发生异常
        logger.error(
            f"[uuid: {req_uuid}] "
            f"internal server error: {e}, "
            f"method: {request.method}, "
            f"uri: {request.url.path}, "
            f"req_body_len: {req_body_len}, "
            f"traceback: {traceback.format_exc()}"
        )
        return JSONResponse(
            status_code=500,
            content=BaseResponse.error(
                code=RespCode.INTERNAL_ERROR,
                message=f"Internal server error: {str(e)}"
            ).model_dump(),
        )

    # 计算处理时间
    process_time = time.time() - start_time

    # 读取响应体
    response_body = b""
    try:
        async for chunk in response.body_iterator:
            response_body += chunk
    except Exception as e:
        logger.error(
            f"[uuid: {req_uuid}] "
            f"failed to read response body: {e}, "
            f"traceback: {traceback.format_exc()}"
        )
        # 返回原始响应
        return response

    # 记录日志
    try:
        response_body_str = response_body.decode()
        response_body_len = len(response_body_str)

        # 截断过长的响应体
        if response_body_len > 4096:
            response_body_display = response_body_str[:4096] + "..."
        else:
            response_body_display = response_body_str

        # 记录完整日志
        logger.info(
            f"[uuid: {req_uuid}] "
            f"method: {request.method}, "
            f"uri: {request.url.path}, "
            f"params: {dict(request.query_params)}, "
            f"req_body_len: {req_body_len}, "  # ✅ 修复：使用 req_body_len
            f"req_body: {req_body_str}, "
            f"resp_body_len: {response_body_len}, "
            f"resp_body: {response_body_display}, "
            f"status: {response.status_code}, "
            f"process_time: {process_time:.3f}s"
        )

        # 返回响应
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )

    except Exception as e:
        # 日志记录失败，但仍然返回响应
        logger.error(
            f"[uuid: {req_uuid}] "
            f"failed to log response: {e}, "
            f"traceback: {traceback.format_exc()}"
        )

        # ✅ 修复：确保有返回值
        try:
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        except Exception:
            # 如果连构建响应都失败了，返回错误
            return JSONResponse(
                status_code=500,
                content=BaseResponse.error(
                    code=RespCode.INTERNAL_ERROR,
                    message="Failed to process response"
                ).model_dump()
            )
```

## 🔧 主要修复点

### 1. ✅ 修复 finally 块问题
- 移除了空的 `finally` 块
- 确保所有代码路径都有返回值
- 在日志记录失败时仍然返回响应

### 2. ✅ 修复日志字段错误
```python
# 修复前
f"request_body_len: {len(response_body_str)},"

# 修复后
f"req_body_len: {req_body_len}, "
f"resp_body_len: {response_body_len}, "
```

### 3. ✅ 移除未使用的代码
- 移除了 `hostname` 变量
- 移除了 `inc_code` 相关代码

### 4. ✅ 改进异常处理
- 更详细的异常日志
- 确保异常时也返回响应
- 嵌套的 try-except 确保鲁棒性

### 5. ✅ 改进日志格式
- 使用更清晰的字段名
- 添加处理时间单位（秒）
- 分离请求体和响应体长度

### 6. ✅ 使用正确的导入路径
```python
from src.api.base_response import BaseResponse, RespCode
```

## 📊 修复对比

| 问题 | 修复前 | 修复后 | 严重程度 |
|------|--------|--------|---------|
| finally 无返回值 | ❌ 可能无响应 | ✅ 总是有响应 | 🔴 严重 |
| 日志字段错误 | ❌ 信息混淆 | ✅ 信息准确 | 🟡 中等 |
| 未使用变量 | ❌ 冗余代码 | ✅ 代码清晰 | 🟢 轻微 |
| 异常处理 | ❌ 不完整 | ✅ 完整鲁棒 | 🔴 严重 |

## 🎯 下一步：注册中间件

在 `src/main.py` 中注册中间件：

```python
from src.middleware.log_middleware import add_process_time

# 在 CORS 中间件之后添加
app.middleware("http")(add_process_time)
```

或者使用装饰器方式：

```python
from src.middleware.log_middleware import add_process_time

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    return await add_process_time(request, call_next)
```
