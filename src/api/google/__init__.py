"""
Google OAuth API模块
"""
from .auth_api import router as auth_api_router
from .auth_page import router as auth_page_router

__all__ = ['auth_api_router', 'auth_page_router']
