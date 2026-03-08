"""
Feishu (Lark) OAuth Service
处理飞书的OAuth2授权流程
"""
import logging
from typing import Dict, Optional
from enum import Enum
import httpx

from src.core import settings

logger = logging.getLogger(__name__)


class IdpEnum(str, Enum):
    """身份提供商枚举"""
    BlueFocus = "BlueFocus"
    Tomato = "Tomato"


class FeishuOAuthService:
    """飞书OAuth2服务类"""

    def __init__(self):
        """初始化飞书OAuth服务"""
        self.token_url = settings.FEISHU_TOKEN_URL
        self.user_url = settings.FEISHU_USER_URL

        # BlueFocus 应用配置
        self.app_id = settings.FEISHU_APP_ID
        self.app_secret = settings.FEISHU_APP_SECRET

        # Tomato 应用配置
        self.tomato_app_id = settings.FEISHU_TOMATO_APP_ID
        self.tomato_app_secret = settings.FEISHU_TOMATO_APP_SECRET

    def get_token_info(
        self,
        code: str,
        redirect_uri: str,
        idp: str = IdpEnum.BlueFocus.value
    ) -> Dict:
        """
        使用code换取token

        Args:
            code: 授权码
            redirect_uri: 回调地址
            idp: 身份提供商类型 (BlueFocus 或 Tomato)

        Returns:
            Dict: Token信息，包含:
                - access_token: 访问令牌
                - token_type: 令牌类型
                - expires_in: 过期时间（秒）
                - refresh_token: 刷新令牌（如果有）

        Raises:
            ValueError: code为空时抛出
            httpx.HTTPError: HTTP请求失败时抛出
            Exception: 其他错误
        """
        if not code:
            raise ValueError("code is empty")

        # 根据 idp 选择对应的应用配置
        if idp == IdpEnum.Tomato.value:
            app_id = self.tomato_app_id
            app_secret = self.tomato_app_secret
        else:
            app_id = self.app_id
            app_secret = self.app_secret

        headers = {
            "Content-Type": "application/json;charset=UTF-8"
        }

        params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code
        }

        logger.info(
            f"Requesting token from Feishu. "
            f"URL: {self.token_url}, "
            f"IDP: {idp}, "
            f"redirect_uri: {redirect_uri}"
        )

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    url=self.token_url,
                    json=params,
                    headers=headers
                )

                logger.info(
                    f"Token response received. "
                    f"status_code: {response.status_code}, "
                    f"text: {response.text}"
                )

                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to get token from Feishu. "
                f"Error: {str(e)}, "
                f"IDP: {idp}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error when getting token. "
                f"Error: {str(e)}, "
                f"IDP: {idp}"
            )
            raise

    def get_user_info(
        self,
        token_type: str,
        access_token: str
    ) -> Dict:
        """
        使用token获取用户信息

        Args:
            token_type: 令牌类型（通常是 "Bearer"）
            access_token: 访问令牌

        Returns:
            Dict: 用户信息，包含:
                - open_id: 用户在应用中的唯一标识
                - union_id: 用户在企业中的唯一标识
                - name: 用户名
                - email: 邮箱
                - mobile: 手机号
                - avatar_url: 头像URL
                等其他飞书返回的用户信息

        Raises:
            httpx.HTTPError: HTTP请求失败时抛出
            Exception: 其他错误
        """
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": f"{token_type} {access_token}",
        }

        logger.info(
            f"Requesting user info from Feishu. "
            f"URL: {self.user_url}"
        )

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    url=self.user_url,
                    headers=headers
                )

                logger.info(
                    f"User info response received. "
                    f"status_code: {response.status_code}"
                )

                response.raise_for_status()
                user_info = response.json()

                # 记录用户信息（不包含敏感数据）
                logger.info(
                    f"User info retrieved successfully. "
                    f"open_id: {user_info.get('open_id', 'N/A')}"
                )

                return user_info

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to get user info from Feishu. "
                f"Error: {str(e)}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error when getting user info. "
                f"Error: {str(e)}"
            )
            raise

    async def get_token_info_async(
        self,
        code: str,
        redirect_uri: str,
        idp: str = IdpEnum.BlueFocus.value
    ) -> Dict:
        """
        异步方式使用code换取token

        Args:
            code: 授权码
            redirect_uri: 回调地址
            idp: 身份提供商类型

        Returns:
            Dict: Token信息

        Raises:
            ValueError: code为空时抛出
            httpx.HTTPError: HTTP请求失败时抛出
        """
        if not code:
            raise ValueError("code is empty")

        # 根据 idp 选择对应的应用配置
        if idp == IdpEnum.Tomato.value:
            app_id = self.tomato_app_id
            app_secret = self.tomato_app_secret
        else:
            app_id = self.app_id
            app_secret = self.app_secret

        headers = {
            "Content-Type": "application/json;charset=UTF-8"
        }

        params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code
        }

        logger.info(
            f"Requesting token from Feishu (async). "
            f"URL: {self.token_url}, "
            f"IDP: {idp}"
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url=self.token_url,
                    json=params,
                    headers=headers
                )

                logger.info(
                    f"Token response received (async). "
                    f"status_code: {response.status_code}"
                )

                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to get token from Feishu (async). "
                f"Error: {str(e)}"
            )
            raise

    async def get_user_info_async(
        self,
        token_type: str,
        access_token: str
    ) -> Dict:
        """
        异步方式使用token获取用户信息

        Args:
            token_type: 令牌类型
            access_token: 访问令牌

        Returns:
            Dict: 用户信息

        Raises:
            httpx.HTTPError: HTTP请求失败时抛出
        """
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": f"{token_type} {access_token}",
        }

        logger.info(
            f"Requesting user info from Feishu (async). "
            f"URL: {self.user_url}"
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url=self.user_url,
                    headers=headers
                )

                logger.info(
                    f"User info response received (async). "
                    f"status_code: {response.status_code}"
                )

                response.raise_for_status()
                user_info = response.json()

                logger.info(
                    f"User info retrieved successfully (async). "
                    f"open_id: {user_info.get('open_id', 'N/A')}"
                )

                return user_info

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to get user info from Feishu (async). "
                f"Error: {str(e)}"
            )
            raise


# 创建全局服务实例
feishu_oauth_service = FeishuOAuthService()
