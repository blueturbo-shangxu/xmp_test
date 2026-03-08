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
    from src.core import settings
    from src.sql import init_db
    import uvicorn
    import logging

    logger = logging.getLogger(__name__)


    # 启动服务器
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        # reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
