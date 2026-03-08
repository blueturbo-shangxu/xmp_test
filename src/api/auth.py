"""
OAuth authentication routes
处理Google Ads OAuth2授权相关的API端点
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import secrets

from src.sql import get_db
from src.sql import AuthorizationLog
from src.services import oauth_service
from src.middleware import get_request_uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ads/auth", tags=["authentication"])


@router.get("/authorize", response_class=HTMLResponse)
async def authorize(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    开始OAuth2授权流程

    Args:
        db: 数据库会话

    Returns:
        重定向到Google授权页面

    异常情况:
    1. 配置错误 - 客户端ID或密钥未设置
    2. 网络错误 - 无法连接到Google授权服务器
    """
    req_uuid = get_request_uuid(request)

    try:
        # 生成随机state用于防止CSRF攻击
        state = secrets.token_urlsafe(32)

        # 记录授权日志 (使用新的platform字段)
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

        # 创建授权URL
        authorization_url, _ = oauth_service.create_authorization_url(state)

        logger.info(f"[{req_uuid}] Authorization started")

        # 返回带有跳转信息的HTML页面
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>正在跳转到Google授权页面...</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    text-align: center;
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }}
                .spinner {{
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #667eea;
                    border-radius: 50%;
                    width: 50px;
                    height: 50px;
                    animation: spin 1s linear infinite;
                    margin: 20px auto;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                h2 {{ color: #333; }}
                p {{ color: #666; }}
                .manual-link {{
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                }}
            </style>
            <script>
                // 3秒后自动跳转
                setTimeout(function() {{
                    window.location.href = "{authorization_url}";
                }}, 3000);
            </script>
        </head>
        <body>
            <div class="container">
                <h2>正在跳转到Google授权页面...</h2>
                <div class="spinner"></div>
                <p>页面将在3秒后自动跳转</p>
                <p>如果没有自动跳转,请点击下面的按钮:</p>
                <a href="{authorization_url}" class="manual-link">手动跳转</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except Exception as e:
        error_message = str(e)
        logger.error(f"[{req_uuid}] Authorization failed: {error_message}")

        # 记录失败日志 (使用新的platform字段)
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

        # 返回错误页面
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>授权失败</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                }}
                .container {{
                    text-align: center;
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    max-width: 500px;
                }}
                h2 {{ color: #f5576c; }}
                .error-details {{
                    background: #ffebee;
                    padding: 15px;
                    border-left: 4px solid #f5576c;
                    text-align: left;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .back-link {{
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>❌ 授权失败</h2>
                <div class="error-details">
                    <strong>错误信息:</strong><br>
                    {error_message}
                </div>
                <p><strong>可能的原因:</strong></p>
                <ul style="text-align: left; color: #666;">
                    <li>Google客户端ID或密钥配置错误</li>
                    <li>网络连接问题</li>
                    <li>服务器配置问题</li>
                </ul>
                <a href="/" class="back-link">返回首页</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=500)


@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = Query(None, description="授权码"),
    state: Optional[str] = Query(None, description="状态参数"),
    error: Optional[str] = Query(None, description="错误信息"),
    db: Session = Depends(get_db)
):
    """
    OAuth2授权回调端点

    Args:
        code: 授权码
        state: 状态参数
        error: 错误信息
        db: 数据库会话

    Returns:
        授权结果页面

    异常情况:
    1. 用户拒绝授权 - error参数存在
    2. 授权码无效 - code参数缺失或无效
    3. State验证失败 - 可能是CSRF攻击
    4. Token交换失败 - 网络错误或配置错误
    5. 账户信息获取失败 - API调用失败
    """
    req_uuid = get_request_uuid(request)

    # 处理用户拒绝授权的情况
    if error:
        logger.warning(f"[{req_uuid}] User denied authorization: {error}")

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>授权被拒绝</title>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
                }
                .container {
                    text-align: center;
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }
                h2 { color: #ff9800; }
                .back-link {
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>⚠️ 授权被拒绝</h2>
                <p>您已取消授权。要使用XMP系统,您需要授予访问权限。</p>
                <a href="/ads/auth/authorize" class="back-link">重新授权</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    # 检查必需的参数
    if not code:
        logger.error(f"[{req_uuid}] Authorization callback missing code parameter")

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>授权失败</title>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                }
                .container {
                    text-align: center;
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }
                h2 { color: #f5576c; }
                .back-link {
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>❌ 授权失败</h2>
                <p>缺少授权码参数。请重新开始授权流程。</p>
                <a href="/ads/auth/authorize" class="back-link">重新授权</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=400)

    try:
        # 交换授权码获取token
        logger.info(f"[{req_uuid}] Exchanging authorization code for tokens...")
        token_data = oauth_service.exchange_code_for_tokens(code, state)

        # 从token_data中提取用户信息
        user_info = token_data.get('user_info', {})
        user_id = user_info.get('user_id')
        user_email = user_info.get('email')

        if not user_id:
            logger.error(f"[{req_uuid}] No user_id found in token_data")
            raise ValueError("无法从id_token中获取用户唯一标识")

        logger.info(f"[{req_uuid}] User authenticated: user_id={user_id}, email={user_email}")

        # 保存token到数据库(使用user_id作为account_key)
        oauth_service.save_tokens_to_db(
            db,
            user_id,
            token_data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )

        # 构建成功消息
        success_message = f"授权成功!<br>用户: {user_email or user_id}"
        logger.info(f"[{req_uuid}] Authorization completed successfully for user: {user_email or user_id}")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>授权成功</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
                }}
                .container {{
                    text-align: center;
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }}
                h2 {{ color: #4CAF50; }}
                .success-icon {{
                    font-size: 64px;
                    margin-bottom: 20px;
                }}
                .info-box {{
                    background: #e8f5e9;
                    padding: 15px;
                    border-left: 4px solid #4CAF50;
                    text-align: left;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .back-link {{
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✅</div>
                <h2>授权成功!</h2>
                <div class="info-box">
                    <strong>授权信息:</strong><br>
                    {success_message}
                </div>
                <p>现在您可以开始同步Google Ads数据了。</p>
                <a href="/" class="back-link">返回首页</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except ValueError as e:
        error_message = str(e)
        logger.error(f"[{req_uuid}] Token exchange failed: {error_message}")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>授权失败</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                }}
                .container {{
                    text-align: center;
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    max-width: 500px;
                }}
                h2 {{ color: #f5576c; }}
                .error-details {{
                    background: #ffebee;
                    padding: 15px;
                    border-left: 4px solid #f5576c;
                    text-align: left;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .back-link {{
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>❌ 授权失败</h2>
                <div class="error-details">
                    <strong>错误信息:</strong><br>
                    {error_message}
                </div>
                <a href="/ads/auth/authorize" class="back-link">重新授权</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=400)

    except Exception as e:
        db.rollback()
        error_message = str(e)
        logger.error(f"[{req_uuid}] Authorization callback failed: {error_message}")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>系统错误</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                }}
                .container {{
                    text-align: center;
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    max-width: 500px;
                }}
                h2 {{ color: #f5576c; }}
                .error-details {{
                    background: #ffebee;
                    padding: 15px;
                    border-left: 4px solid #f5576c;
                    text-align: left;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .back-link {{
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>❌ 系统错误</h2>
                <div class="error-details">
                    <strong>错误信息:</strong><br>
                    {error_message}
                </div>
                <p>请联系系统管理员或稍后重试。</p>
                <a href="/" class="back-link">返回首页</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=500)
