"""
Feishu OAuth Authentication Router
飞书OAuth认证路由
"""
import logging
import time
import json
import base64
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from src.services import feishu_oauth_service, IdpEnum
from src.core.jwt_handler import generate_jwt_token
from src.core import settings
from src.middleware import get_request_uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feishu", tags=["Feishu OAuth"])


def encode_state(data: Dict) -> str:
    """
    将状态数据编码为base64字符串

    Args:
        data: 要编码的状态数据字典

    Returns:
        base64编码的字符串
    """
    json_str = json.dumps(data, ensure_ascii=False)
    return base64.urlsafe_b64encode(json_str.encode('utf-8')).decode('utf-8')


def decode_state(state: str) -> Dict:
    """
    将base64字符串解码为状态数据

    Args:
        state: base64编码的状态字符串

    Returns:
        解码后的状态数据字典
    """
    try:
        json_str = base64.urlsafe_b64decode(state.encode('utf-8')).decode('utf-8')
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Failed to decode state. Error: {str(e)}")
        return {}


@router.get("/login")
async def feishu_login(
    request: Request,
    idp: str = Query(default="BlueFocus", description="身份提供商: BlueFocus 或 Tomato"),
    redirect_after_login: Optional[str] = Query(default=None, description="登录成功后的跳转URL")
):
    """
    步骤 1: 生成飞书授权URL并重定向到飞书授权页面

    Args:
        request: FastAPI Request对象，用于获取当前请求的域名
        idp: 身份提供商，可选值: BlueFocus, Tomato
        redirect_after_login: 登录成功后跳转的URL（可选）

    Returns:
        重定向到飞书授权页面
    """
    req_uuid = get_request_uuid(request)

    try:
        # 验证IDP参数
        if idp not in [IdpEnum.BlueFocus.value, IdpEnum.Tomato.value]:
            idp = IdpEnum.BlueFocus.value

        # 根据IDP选择对应的app_id
        app_id = settings.FEISHU_APP_ID if idp == IdpEnum.BlueFocus.value else settings.FEISHU_TOMATO_APP_ID

        # 获取当前请求的host（包含域名和端口）
        host = request.headers.get("host", f"localhost:{settings.PORT}")
        scheme = request.url.scheme  # http 或 https

        # 构建回调地址（使用请求来源的域名）
        redirect_uri = f"{scheme}://{host}/feishu/callback"

        # 构建state数据（包含域名、IDP、登录后跳转URL等信息）
        state_data = {
            "idp": idp,
            "redirect_uri": redirect_uri,
            "scheme": scheme,
            "host": host
        }

        # 如果指定了登录后跳转URL，添加到state中
        if redirect_after_login:
            state_data["redirect_after_login"] = redirect_after_login

        state = encode_state(state_data)

        # 构建飞书授权URL
        auth_url = (
            f"https://passport.feishu.cn/suite/passport/oauth/authorize"
            f"?client_id={app_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&state={state}"
        )

        logger.info(
            f"[{req_uuid}] Redirecting to Feishu authorization. "
            f"IDP: {idp}, scheme: {scheme}, host: {host}, redirect_uri: {redirect_uri}, "
            f"redirect_after_login: {redirect_after_login or 'None'}"
        )

        # 直接302重定向到飞书授权页面
        return RedirectResponse(url=auth_url, status_code=302)

    except Exception as e:
        logger.error(f"[{req_uuid}] Failed to redirect to Feishu login. Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"跳转登录页面失败: {str(e)}"
        )


@router.get("/callback")
async def feishu_callback(
    request: Request,
    code: str = Query(..., description="授权码"),
    state: str = Query(..., description="状态数据(base64编码)")
):
    """
    步骤 2: 处理飞书授权回调

    Args:
        code: 飞书返回的授权码
        state: base64编码的状态数据，包含idp、redirect_uri等信息

    Returns:
        JSON响应，包含JWT token和用户信息
    """
    req_uuid = get_request_uuid(request)

    if not code:
        logger.warning(f"[{req_uuid}] Feishu callback received without authorization code")
        raise HTTPException(status_code=400, detail="缺少授权码")

    if not state:
        logger.warning(f"[{req_uuid}] Feishu callback received without state parameter")
        raise HTTPException(status_code=400, detail="缺少state参数")

    try:
        # 解析state数据
        state_data = decode_state(state)
        if not state_data:
            raise ValueError("Invalid state parameter")

        # 从state中获取参数
        idp = state_data.get("idp", IdpEnum.BlueFocus.value)
        redirect_uri = state_data.get("redirect_uri", "")
        scheme = state_data.get("scheme", "http")
        host = state_data.get("host", f"localhost:{settings.PORT}")
        redirect_after_login = state_data.get("redirect_after_login", None)

        # 验证IDP参数
        if idp not in [IdpEnum.BlueFocus.value, IdpEnum.Tomato.value]:
            idp = IdpEnum.BlueFocus.value

        # 如果state中没有redirect_uri，构建默认的
        if not redirect_uri:
            redirect_uri = f"{scheme}://{host}/feishu/callback"

        logger.info(
            f"[{req_uuid}] Processing Feishu callback. "
            f"IDP: {idp}, scheme: {scheme}, host: {host}, redirect_uri: {redirect_uri}"
        )

        # 1. 使用授权码换取token
        token_info = await feishu_oauth_service.get_token_info_async(
            code=code,
            redirect_uri=redirect_uri,
            idp=idp
        )

        logger.info(f"[{req_uuid}] Successfully obtained token from Feishu. token_type: {token_info.get('token_type')}")

        # 2. 使用token获取用户信息
        user_info = await feishu_oauth_service.get_user_info_async(
            token_type=token_info['token_type'],
            access_token=token_info['access_token']
        )

        open_id = user_info.get('open_id', '')
        user_name = user_info.get('name', '')

        logger.info(f"[{req_uuid}] Successfully obtained user info from Feishu. open_id: {open_id}, name: {user_name}")

        # 3. 生成JWT token
        # expires_at: JWT_TOKEN_EXPIRE_DAYS天后过期
        expires_at = int(time.time()) + (settings.JWT_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)

        jwt_token = generate_jwt_token(
            secret=settings.JWT_SECRET,
            user_id=open_id,
            expires_at=expires_at,
            ua=""  # 可以从request.headers.get("user-agent")获取
        )

        logger.info(f"[{req_uuid}] Successfully generated JWT token for user. open_id: {open_id}")

        # 4. 如果有redirect_after_login参数，则重定向到指定页面，并将JWT token写入header
        if redirect_after_login:
            logger.info(f"[{req_uuid}] Redirecting to: {redirect_after_login} with JWT token in header")

            response = RedirectResponse(url=redirect_after_login, status_code=302)

            # 将JWT token写入response header
            response.headers["X-Auth-Token"] = jwt_token
            response.headers["X-Token-Expires-At"] = str(expires_at)
            response.headers["X-User-OpenId"] = open_id
            response.headers["X-User-Name"] = user_name

            return response

        # 5. 没有redirect_after_login参数，返回JSON响应
        return {
            "code": 0,
            "message": "登录成功",
            "data": {
                "jwt_token": jwt_token,
                "expires_at": expires_at,
                "user": {
                    "open_id": open_id,
                    "union_id": user_info.get('union_id', ''),
                    "name": user_name,
                    "email": user_info.get('email', ''),
                    "mobile": user_info.get('mobile', ''),
                    "avatar_url": user_info.get('avatar_url', '')
                },
                "idp": idp,
                "request_info": {
                    "scheme": scheme,
                    "host": host,
                    "redirect_after_login": redirect_after_login,
                    "redirect_uri": redirect_uri
                }
            }
        }

    except ValueError as e:
        logger.error(f"[{req_uuid}] Parameter error in Feishu callback. Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")

    except Exception as e:
        logger.error(f"[{req_uuid}] Failed to process Feishu callback. Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"登录失败: {str(e)}"
        )


@router.get("/login-page", response_class=HTMLResponse)
async def feishu_login_page():
    """
    飞书登录选择页面

    Returns:
        HTML页面，允许用户选择身份提供商
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>飞书登录 - 选择身份提供商</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                background: white;
                border-radius: 10px;
                padding: 40px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
                text-align: center;
                max-width: 500px;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 28px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 14px;
            }
            .logo {
                width: 80px;
                height: 80px;
                margin: 0 auto 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 50%;
                display: flex;
                justify-content: center;
                align-items: center;
                font-size: 40px;
                color: white;
            }
            .buttons {
                display: flex;
                flex-direction: column;
                gap: 15px;
                margin-top: 30px;
            }
            .login-btn {
                padding: 15px 30px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s;
                text-decoration: none;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }
            .btn-bluefocus {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .btn-bluefocus:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            }
            .btn-tomato {
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
            }
            .btn-tomato:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(245, 87, 108, 0.4);
            }
            .icon {
                font-size: 20px;
            }
            .footer {
                margin-top: 30px;
                color: #999;
                font-size: 12px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🚀</div>
            <h1>飞书登录</h1>
            <p class="subtitle">选择身份提供商进行登录</p>

            <div class="buttons">
                <a href="/feishu/login?idp=BlueFocus" class="login-btn btn-bluefocus">
                    <span class="icon">🔵</span>
                    <span>使用 BlueFocus 登录</span>
                </a>

                <a href="/feishu/login?idp=Tomato" class="login-btn btn-tomato">
                    <span class="icon">🍅</span>
                    <span>使用 Tomato 登录</span>
                </a>
            </div>

            <div class="footer">
                XMP Server - Feishu OAuth Authentication
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)
