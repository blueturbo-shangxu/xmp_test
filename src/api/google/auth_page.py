"""
Google OAuth 测试页面
简单的HTML页面用于测试授权流程
"""
import logging
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional

from src.sql import get_db
from src.services import oauth_service
from src.core import settings
from src.middleware import get_request_uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google/auth", tags=["google-auth-page"])


@router.get("/test", response_class=HTMLResponse)
async def test_authorize_page(request: Request):
    """
    测试授权页面 - 用于发起OAuth授权
    """
    # 使用默认的redirect_uri
    default_redirect_uri = settings.GOOGLE_REDIRECT_URI

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google OAuth 测试</title>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .container {{
                text-align: center;
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                max-width: 600px;
                width: 90%;
            }}
            h2 {{ color: #333; }}
            .form-group {{
                margin: 20px 0;
                text-align: left;
            }}
            label {{
                display: block;
                margin-bottom: 5px;
                color: #666;
                font-weight: bold;
            }}
            input[type="text"] {{
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
                box-sizing: border-box;
            }}
            .btn {{
                margin-top: 20px;
                padding: 12px 30px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }}
            .btn:hover {{
                background: #5a6fd6;
            }}
            .info {{
                background: #e3f2fd;
                padding: 15px;
                border-radius: 5px;
                margin-top: 20px;
                text-align: left;
                font-size: 14px;
                color: #1565c0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Google OAuth 授权测试</h2>
            <form id="authForm">
                <div class="form-group">
                    <label for="redirect_uri">Redirect URI:</label>
                    <input type="text" id="redirect_uri" name="redirect_uri"
                           value="{default_redirect_uri}" required>
                </div>
                <div class="form-group">
                    <label for="extra_param">额外参数 (可选，如 user_tag):</label>
                    <input type="text" id="extra_param" name="extra_param"
                           placeholder="例如: test_user_123">
                </div>
                <button type="submit" class="btn">开始授权</button>
            </form>
            <div class="info">
                <strong>说明:</strong><br>
                1. Redirect URI 需要在 Google Cloud Console 中配置<br>
                2. 额外参数会被编码到 state 中，回调时返回
            </div>
        </div>
        <script>
            document.getElementById('authForm').addEventListener('submit', async function(e) {{
                e.preventDefault();

                const redirectUri = document.getElementById('redirect_uri').value;
                const extraParam = document.getElementById('extra_param').value;

                const body = {{
                    redirect_uri: redirectUri
                }};

                if (extraParam) {{
                    body.extra_params = {{ user_tag: extraParam }};
                }}

                try {{
                    const response = await fetch('/api/google/auth/authorize', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(body)
                    }});

                    const data = await response.json();

                    if (data.code === 0 && data.data.authorization_url) {{
                        window.location.href = data.data.authorization_url;
                    }} else {{
                        alert('获取授权URL失败: ' + (data.message || '未知错误'));
                    }}
                }} catch (err) {{
                    alert('请求失败: ' + err.message);
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/callback", response_class=HTMLResponse)
async def callback_page(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    OAuth回调页面 - 显示授权结果
    """
    req_uuid = get_request_uuid(request)

    # 处理错误
    if error:
        logger.warning(f"[{req_uuid}] User denied authorization: {error}")
        return _error_page("授权被拒绝", f"用户取消了授权: {error}")

    if not code:
        return _error_page("参数错误", "缺少授权码参数")

    try:
        # 交换token
        token_data = oauth_service.exchange_code_for_tokens(code, state)

        user_info = token_data.get('user_info', {})
        state_data = token_data.get('state_data', {})
        user_id = user_info.get('user_id')
        user_email = user_info.get('email')

        if not user_id:
            return _error_page("授权失败", "无法获取用户信息")

        # 保存token
        oauth_service.save_tokens_to_db(
            db,
            user_id,
            token_data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )

        logger.info(f"[{req_uuid}] Authorization completed: {user_email or user_id}")

        return _success_page(user_info, state_data, token_data)

    except ValueError as e:
        logger.error(f"[{req_uuid}] Token exchange failed: {str(e)}")
        return _error_page("授权失败", str(e))

    except Exception as e:
        db.rollback()
        logger.error(f"[{req_uuid}] Authorization failed: {str(e)}")
        return _error_page("系统错误", str(e))


def _success_page(user_info: dict, state_data: dict, token_data: dict) -> HTMLResponse:
    """生成成功页面"""
    import json

    user_email = user_info.get('email', '未知')
    user_id = user_info.get('user_id', '未知')
    state_json = json.dumps(state_data, indent=2, ensure_ascii=False)

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
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            }}
            .container {{
                text-align: center;
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                max-width: 600px;
            }}
            h2 {{ color: #4CAF50; }}
            .success-icon {{ font-size: 64px; margin-bottom: 20px; }}
            .info-box {{
                background: #e8f5e9;
                padding: 15px;
                border-left: 4px solid #4CAF50;
                text-align: left;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .state-box {{
                background: #e3f2fd;
                padding: 15px;
                border-left: 4px solid #2196f3;
                text-align: left;
                margin: 20px 0;
                border-radius: 4px;
            }}
            pre {{
                background: #f5f5f5;
                padding: 10px;
                border-radius: 4px;
                overflow-x: auto;
                font-size: 12px;
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
                <strong>用户信息:</strong><br>
                Email: {user_email}<br>
                User ID: {user_id}
            </div>
            <div class="state-box">
                <strong>State 数据:</strong>
                <pre>{state_json}</pre>
            </div>
            <a href="/google/auth/test" class="back-link">返回测试页</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


def _error_page(title: str, message: str) -> HTMLResponse:
    """生成错误页面"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
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
                word-break: break-all;
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
            <h2>❌ {title}</h2>
            <div class="error-details">
                <strong>错误信息:</strong><br>
                {message}
            </div>
            <a href="/google/auth/test" class="back-link">返回测试页</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=400)
