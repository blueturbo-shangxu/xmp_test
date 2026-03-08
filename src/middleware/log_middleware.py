import logging
import time
import traceback
import uuid

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.types import Message

from src.api.base_response import BaseResponse, RespCode

logger = logging.getLogger(__name__)


async def get_body(request: Request):
    receive_ = await request._receive()
    async def receive() -> Message:
        return receive_

    request._receive = receive
    body = await request.body()
    return body


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
    req_body = await get_body(request)

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
        # 忽略文档访问日志
        if any(path in request.url.path for path in ["docs", "redoc", "openapi.json"]):
            return response

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
            status_code=200,
            content=BaseResponse.exception(e).model_dump(),
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
            f"req_body_len: {req_body_len}, "
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

        # 确保有返回值
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
                status_code=200,
                content=BaseResponse.exception(e).model_dump(),
            )