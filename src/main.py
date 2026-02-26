"""
Main application entry point
FastAPI应用主入口
"""
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import settings, setup_logging
from src.database import check_db_connection, init_db
from src.routes.auth import router as auth_router
from src.routes.api import router as api_router

# 配置日志
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Starting XMP Auth Server...")

    # 检查数据库连接
    if check_db_connection():
        logger.info("Database connection OK")
    else:
        logger.error("Database connection failed!")

    yield

    # 关闭时执行
    logger.info("Shutting down XMP Auth Server...")


# 创建FastAPI应用
app = FastAPI(
    title="XMP Auth Server",
    description="Google Ads授权和数据同步服务",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def home():
    """
    首页 - 提供授权测试界面
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>XMP Auth Server - Google Ads授权系统</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 800px;
                width: 100%;
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }
            .header h1 {
                font-size: 32px;
                margin-bottom: 10px;
            }
            .header p {
                font-size: 16px;
                opacity: 0.9;
            }
            .content {
                padding: 40px;
            }
            .section {
                margin-bottom: 30px;
            }
            .section h2 {
                color: #333;
                margin-bottom: 15px;
                font-size: 24px;
            }
            .section p {
                color: #666;
                line-height: 1.6;
                margin-bottom: 15px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                color: #333;
                font-weight: 600;
                margin-bottom: 8px;
            }
            .form-group input {
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
            }
            .form-group small {
                display: block;
                color: #999;
                margin-top: 5px;
            }
            .btn {
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                border: none;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
                width: 100%;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            .btn:active {
                transform: translateY(0);
            }
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .feature {
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                text-align: center;
            }
            .feature-icon {
                font-size: 32px;
                margin-bottom: 10px;
            }
            .feature h3 {
                color: #333;
                font-size: 16px;
                margin-bottom: 8px;
            }
            .feature p {
                color: #666;
                font-size: 14px;
            }
            .api-section {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-top: 20px;
            }
            .api-section h3 {
                color: #333;
                margin-bottom: 15px;
            }
            .api-endpoint {
                background: white;
                padding: 12px;
                border-left: 4px solid #667eea;
                margin-bottom: 10px;
                border-radius: 4px;
            }
            .api-endpoint code {
                color: #667eea;
                font-family: 'Courier New', monospace;
                font-size: 14px;
            }
            .api-endpoint p {
                margin: 5px 0 0 0;
                font-size: 13px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 XMP Auth Server</h1>
                <p>Google Ads OAuth2授权与数据同步系统</p>
            </div>

            <div class="content">
                <div class="section">
                    <h2>快速开始授权</h2>
                    <p>输入您的Google Ads Customer ID开始授权流程。Customer ID格式为: 123-456-7890</p>

                    <div class="form-group">
                        <label for="customerId">Google Ads Customer ID (可选)</label>
                        <input
                            type="text"
                            id="customerId"
                            placeholder="例如: 123-456-7890"
                            pattern="[0-9]{3}-[0-9]{3}-[0-9]{4}"
                        >
                        <small>可以留空,稍后在系统中配置</small>
                    </div>

                    <button class="btn" onclick="startAuthorization()">
                        开始授权 Google Ads
                    </button>
                </div>

                <div class="section">
                    <h2>系统功能</h2>
                    <div class="features">
                        <div class="feature">
                            <div class="feature-icon">🔐</div>
                            <h3>安全授权</h3>
                            <p>OAuth2标准授权流程</p>
                        </div>
                        <div class="feature">
                            <div class="feature-icon">🔄</div>
                            <h3>自动刷新</h3>
                            <p>Token自动刷新机制</p>
                        </div>
                        <div class="feature">
                            <div class="feature-icon">📊</div>
                            <h3>数据同步</h3>
                            <p>推广活动和广告组同步</p>
                        </div>
                        <div class="feature">
                            <div class="feature-icon">📝</div>
                            <h3>操作日志</h3>
                            <p>完整的授权和操作记录</p>
                        </div>
                    </div>
                </div>

                <div class="api-section">
                    <h3>API接口文档</h3>
                    <div class="api-endpoint">
                        <code>GET /ads/auth/authorize</code>
                        <p>启动OAuth2授权流程</p>
                    </div>
                    <div class="api-endpoint">
                        <code>GET /api/accounts</code>
                        <p>获取已授权的账户列表</p>
                    </div>
                    <div class="api-endpoint">
                        <code>POST /api/sync/campaigns</code>
                        <p>同步推广活动数据</p>
                    </div>
                    <div class="api-endpoint">
                        <code>POST /api/sync/ad-groups</code>
                        <p>同步广告组数据</p>
                    </div>
                    <p style="margin-top: 15px;">
                        <a href="/docs" style="color: #667eea; text-decoration: none; font-weight: 600;">
                            查看完整API文档 →
                        </a>
                    </p>
                </div>
            </div>
        </div>

        <script>
            function startAuthorization() {
                const customerIdInput = document.getElementById('customerId');
                const customerId = customerIdInput.value.trim();

                // 验证Customer ID格式(如果填写了)
                if (customerId && !/^[0-9]{3}-[0-9]{3}-[0-9]{4}$/.test(customerId)) {
                    alert('Customer ID格式不正确!正确格式: 123-456-7890');
                    return;
                }

                // 构建授权URL
                let authUrl = '/ads/auth/authorize';
                if (customerId) {
                    authUrl += '?customer_id=' + encodeURIComponent(customerId);
                }

                // 跳转到授权页面
                window.location.href = authUrl;
            }

            // 支持回车键提交
            document.getElementById('customerId').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    startAuthorization();
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """
    健康检查端点
    """
    db_status = check_db_connection()

    return JSONResponse(
        status_code=200 if db_status else 503,
        content={
            "status": "healthy" if db_status else "unhealthy",
            "database": "connected" if db_status else "disconnected",
            "version": "1.0.0"
        }
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404错误处理"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"路径 {request.url.path} 不存在",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """500错误处理"""
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "服务器内部错误,请稍后重试"
        }
    )


if __name__ == "__main__":
    import uvicorn

    # 创建数据库表(如果不存在)
    try:
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")

    # 启动服务器
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
