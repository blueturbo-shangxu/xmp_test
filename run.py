#!/usr/bin/env python
"""
启动脚本
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from src.main import app
    from src.config import settings
    from src.database import init_db
    import uvicorn
    import logging

    logger = logging.getLogger(__name__)

    # 初始化数据库
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        logger.warning("Continuing without database initialization...")

    # 启动服务器
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        # reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
