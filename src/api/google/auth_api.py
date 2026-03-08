"""
Google OAuth API接口
核心授权逻辑
"""
import logging
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from src.sql import get_db
from src.sql import AuthorizationLog
from src.services import oauth_service
from src.middleware import get_request_uuid
from src.api.base_response import BaseResp, RespCode, RespStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google/auth", tags=["google-auth-api"])


class AuthorizeRequest(BaseModel):
    """授权请求参数"""
    redirect_uri: str
    extra_params: Optional[dict] = None


class CallbackRequest(BaseModel):
    """回调请求参数"""
    code: str
    state: Optional[str] = None


@router.post("/authorize")
async def create_authorize_url(
    request: Request,
    body: AuthorizeRequest,
    db: Session = Depends(get_db)
):
    """
    创建OAuth2授权URL

    Args:
        body: 包含redirect_uri和可选的extra_params

    Returns:
        授权URL和state
    """
    req_uuid = get_request_uuid(request)

    try:
        # 记录授权日志
        auth_log = AuthorizationLog(
            platform='google',
            account_key=None,
            action_type='AUTHORIZE',
            status='PENDING',
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        db.add(auth_log)
        db.commit()

        # 创建授权URL，传入redirect_uri和其他参数
        extra_params = body.extra_params or {}
        authorization_url, state = oauth_service.create_authorization_url(
            redirect_uri=body.redirect_uri,
            **extra_params
        )

        logger.info(f"[{req_uuid}] Authorization URL created for redirect_uri: {body.redirect_uri}")

        return BaseResp(
            code=RespCode.SUCCESS,
            status=RespStatus.SUCCESS,
            message="授权URL创建成功",
            data={
                "authorization_url": authorization_url,
                "state": state
            }
        )

    except Exception as e:
        error_message = str(e)
        logger.error(f"[{req_uuid}] Failed to create authorization URL: {error_message}")

        # 记录失败日志
        error_log = AuthorizationLog(
            platform='google',
            account_key=None,
            action_type='AUTHORIZE',
            status='FAILED',
            error_message=error_message,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        db.add(error_log)
        db.commit()

        return BaseResp(
            code=RespCode.FAIL,
            status=RespStatus.FAIL,
            message=f"创建授权URL失败: {error_message}"
        )


@router.post("/callback")
async def handle_callback(
    request: Request,
    body: CallbackRequest,
    db: Session = Depends(get_db)
):
    """
    处理OAuth2回调，交换token

    Args:
        body: 包含code和state

    Returns:
        Token信息和用户信息
    """
    req_uuid = get_request_uuid(request)

    try:
        # 交换授权码获取token
        logger.info(f"[{req_uuid}] Exchanging authorization code for tokens...")
        token_data = oauth_service.exchange_code_for_tokens(body.code, body.state)

        # 从token_data中提取信息
        user_info = token_data.get('user_info', {})
        state_data = token_data.get('state_data', {})
        user_id = user_info.get('user_id')
        user_email = user_info.get('email')

        if not user_id:
            logger.error(f"[{req_uuid}] No user_id found in token_data")
            return BaseResp(
                code=RespCode.PARAM_ERROR,
                status=RespStatus.FAIL,
                message="无法从id_token中获取用户唯一标识"
            )

        logger.info(f"[{req_uuid}] User authenticated: user_id={user_id}, email={user_email}")

        # 保存token到数据库
        oauth_service.save_tokens_to_db(
            db,
            user_id,
            token_data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )

        logger.info(f"[{req_uuid}] Authorization completed successfully for user: {user_email or user_id}")

        return BaseResp(
            code=RespCode.SUCCESS,
            status=RespStatus.SUCCESS,
            message="授权成功",
            data={
                "user_id": user_id,
                "email": user_email,
                "user_info": user_info,
                "state_data": state_data,
                "access_token": token_data.get('access_token'),
                "refresh_token": token_data.get('refresh_token'),
                "expires_in": token_data.get('expires_in')
            }
        )

    except ValueError as e:
        error_message = str(e)
        logger.error(f"[{req_uuid}] Token exchange failed: {error_message}")
        return BaseResp(
            code=RespCode.PARAM_ERROR,
            status=RespStatus.FAIL,
            message=error_message
        )

    except Exception as e:
        db.rollback()
        error_message = str(e)
        logger.error(f"[{req_uuid}] Authorization callback failed: {error_message}")
        return BaseResp(
            code=RespCode.FAIL,
            status=RespStatus.FAIL,
            message=f"授权回调失败: {error_message}"
        )


@router.get("/callback")
async def handle_callback_get(
    request: Request,
    code: Optional[str] = Query(None, description="授权码"),
    state: Optional[str] = Query(None, description="状态参数"),
    error: Optional[str] = Query(None, description="错误信息"),
    db: Session = Depends(get_db)
):
    """
    处理OAuth2 GET回调（用于直接从Google重定向）

    Args:
        code: 授权码
        state: 状态参数
        error: 错误信息

    Returns:
        Token信息和用户信息
    """
    req_uuid = get_request_uuid(request)

    # 处理用户拒绝授权
    if error:
        logger.warning(f"[{req_uuid}] User denied authorization: {error}")
        return BaseResp(
            code=RespCode.PARAM_ERROR,
            status=RespStatus.FAIL,
            message=f"用户拒绝授权: {error}"
        )

    # 检查必需参数
    if not code:
        logger.error(f"[{req_uuid}] Authorization callback missing code parameter")
        return BaseResp(
            code=RespCode.PARAM_ERROR,
            status=RespStatus.FAIL,
            message="缺少授权码参数"
        )

    # 复用POST处理逻辑
    body = CallbackRequest(code=code, state=state)
    return await handle_callback(request, body, db)
