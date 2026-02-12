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

from src.database import get_db
from src.models import GoogleAdAccount, AuthorizationLog
from src.services.oauth_service import oauth_service
from src.services.google_ads_service import google_ads_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/authorize", response_class=HTMLResponse)
async def authorize(
    request: Request,
    customer_id: Optional[str] = Query(None, description="Google Ads Customer ID"),
    db: Session = Depends(get_db)
):
    """
    开始OAuth2授权流程

    Args:
        customer_id: 可选的Google Ads Customer ID
        db: 数据库会话

    Returns:
        重定向到Google授权页面

    异常情况:
    1. 配置错误 - 客户端ID或密钥未设置
    2. 网络错误 - 无法连接到Google授权服务器
    """
    try:
        # 生成随机state用于防止CSRF攻击
        state = secrets.token_urlsafe(32)

        # 如果提供了customer_id,将其编码到state中
        if customer_id:
            state = f"{state}|{customer_id}"

        # 记录授权日志 (使用新的platform字段)
        auth_log = AuthorizationLog(
            platform='google',
            account_key=customer_id,
            action_type='AUTHORIZE',
            status='PENDING',
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        db.add(auth_log)
        db.commit()

        # 创建授权URL
        authorization_url, _ = oauth_service.create_authorization_url(state)

        logger.info(f"Authorization started for customer_id: {customer_id}")

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
        logger.error(f"Authorization failed: {error_message}")

        # 记录失败日志 (使用新的platform字段)
        error_log = AuthorizationLog(
            platform='google',
            account_key=customer_id,
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
    # 处理用户拒绝授权的情况
    if error:
        logger.warning(f"User denied authorization: {error}")

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
                <a href="/auth/authorize" class="back-link">重新授权</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    # 检查必需的参数
    if not code:
        logger.error("Authorization callback missing code parameter")

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
                <a href="/auth/authorize" class="back-link">重新授权</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=400)

    try:
        # 解析state以获取customer_id
        customer_id = None
        if state and '|' in state:
            parts = state.split('|')
            if len(parts) == 2:
                customer_id = parts[1]

        # 如果没有customer_id,无法继续
        if not customer_id:
            logger.error("Missing customer_id in authorization callback")
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
                    <p>缺少Customer ID参数。请在授权URL中提供customer_id参数。</p>
                    <p>示例: /auth/authorize?customer_id=123-456-7890</p>
                    <a href="/auth/authorize" class="back-link">重新授权</a>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=400)

        # 交换授权码获取token
        logger.info(f"Exchanging authorization code for tokens (customer_id: {customer_id})...")
        token_data = oauth_service.exchange_code_for_tokens(code, state)

        # 保存token到数据库 (使用新的接口,传入customer_id)
        oauth_service.save_tokens_to_db(
            db,
            customer_id,
            token_data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )

        # 尝试获取账户信息并创建/更新账户记录
        try:
            account_info = google_ads_service.get_account_info(db, customer_id)
            if account_info:
                # 查找现有账户
                existing_account = db.query(GoogleAdAccount).filter(
                    GoogleAdAccount.customer_id == customer_id
                ).first()

                if existing_account:
                    # 更新现有账户
                    existing_account.account_name = account_info['account_name']
                    existing_account.currency_code = account_info['currency_code']
                    existing_account.timezone = account_info['timezone']
                    existing_account.account_type = account_info['account_type']
                    existing_account.status = account_info['status']
                    logger.info(f"Updated existing account: {customer_id}")
                else:
                    # 创建新账户
                    new_account = GoogleAdAccount(
                        customer_id=customer_id,
                        account_name=account_info['account_name'],
                        currency_code=account_info['currency_code'],
                        timezone=account_info['timezone'],
                        account_type=account_info['account_type'],
                        status=account_info['status']
                    )
                    db.add(new_account)
                    logger.info(f"Created new account: {customer_id}")

                db.commit()
                success_message = f"账户 {account_info['account_name']} ({customer_id}) 授权成功!"
            else:
                # 如果无法获取账户信息,创建基本账户记录
                existing_account = db.query(GoogleAdAccount).filter(
                    GoogleAdAccount.customer_id == customer_id
                ).first()

                if not existing_account:
                    new_account = GoogleAdAccount(
                        customer_id=customer_id,
                        account_name=f"Account {customer_id}",
                        status='ACTIVE'
                    )
                    db.add(new_account)
                    db.commit()

                success_message = f"授权成功! Customer ID: {customer_id} (部分信息获取失败)"
        except Exception as e:
            logger.warning(f"Failed to get/create account info: {str(e)}")
            # 即使账户信息获取失败,token已经保存,所以仍然算授权成功
            success_message = f"授权成功! Customer ID: {customer_id} (账户信息获取失败: {str(e)})"

        logger.info(f"Authorization completed successfully: {success_message}")

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
        logger.error(f"Token exchange failed: {error_message}")

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
                <a href="/auth/authorize" class="back-link">重新授权</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=400)

    except Exception as e:
        db.rollback()
        error_message = str(e)
        logger.error(f"Authorization callback failed: {error_message}")

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
