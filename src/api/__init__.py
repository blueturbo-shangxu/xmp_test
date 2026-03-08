"""
API module - Routes and endpoints
"""
from src.api.auth import router as auth_router
from src.api.api import router as api_router
from src.api.google import auth_api_router, auth_page_router

__all__ = ['auth_router', 'api_router', 'auth_api_router', 'auth_page_router']
