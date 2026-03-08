"""
Request context utilities
提供从请求中提取上下文信息的工具函数
"""
from typing import Optional
from fastapi import Request


def get_request_uuid(request: Request) -> str:
    """
    从请求头中获取req-uuid

    Args:
        request: FastAPI Request对象

    Returns:
        请求的UUID,如果不存在则返回"unknown"
    """
    # 尝试从headers中获取req-uuid
    req_uuid = request.headers.get("req-uuid", "unknown")
    return req_uuid


async def get_request_uuid_dependency(request: Request) -> str:
    """
    FastAPI依赖函数,用于从请求头中获取req-uuid

    Usage:
        @router.get("/example")
        async def example(req_uuid: str = Depends(get_request_uuid_dependency)):
            logger.info(f"[{req_uuid}] Processing request")

    Args:
        request: FastAPI Request对象

    Returns:
        请求的UUID,如果不存在则返回"unknown"
    """
    return get_request_uuid(request)
