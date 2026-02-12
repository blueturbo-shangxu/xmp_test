"""
Google Ads OAuth2 Service
处理Google Ads的OAuth2授权流程
"""
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import json

from src.config import settings
from src.models import GoogleAdAccount, OAuthToken, AuthorizationLog
from src.utils.encryption import token_encryption
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class GoogleAdsOAuthService:
    """Google Ads OAuth2服务类"""

    def __init__(self):
        """初始化OAuth服务"""
        self.client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        }
        self.scopes = settings.GOOGLE_SCOPES_LIST

    def create_authorization_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """
        创建授权URL

        Args:
            state: 可选的状态参数,用于防止CSRF攻击

        Returns:
            Tuple[str, str]: (授权URL, state)

        Raises:
            Exception: 创建授权URL失败
        """
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=settings.GOOGLE_REDIRECT_URI
            )

            authorization_url, state = flow.authorization_url(
                access_type='offline',  # 获取refresh token
                include_granted_scopes='true',  # 增量授权
                prompt='consent',  # 强制显示同意屏幕以获取refresh token
                state=state
            )

            logger.info(f"Authorization URL created with state: {state}")
            return authorization_url, state

        except Exception as e:
            logger.error(f"Failed to create authorization URL: {str(e)}")
            raise

    def exchange_code_for_tokens(
        self,
        code: str,
        state: Optional[str] = None
    ) -> Dict:
        """
        用授权码交换token

        Args:
            code: 授权码
            state: 状态参数(用于验证)

        Returns:
            Dict: Token信息 {
                'access_token': str,
                'refresh_token': str,
                'token_type': str,
                'expires_in': int,
                'scope': str
            }

        Raises:
            ValueError: 授权码无效或交换失败
        """
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=settings.GOOGLE_REDIRECT_URI,
                state=state
            )

            # 交换授权码获取token
            flow.fetch_token(code=code)
            credentials = flow.credentials

            # 验证必要的token是否存在
            if not credentials.token:
                raise ValueError("Failed to obtain access token")

            if not credentials.refresh_token:
                logger.warning("No refresh token received. User may need to revoke and re-authorize.")

            token_data = {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token or '',
                'token_type': 'Bearer',
                'expires_in': 3600,  # Google默认1小时
                'scope': ' '.join(self.scopes)
            }

            logger.info("Successfully exchanged authorization code for tokens")
            return token_data

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to exchange code for tokens: {error_msg}")

            # 提供更详细的错误信息
            if "invalid_grant" in error_msg:
                raise ValueError("授权码无效或已过期,请重新授权")
            elif "redirect_uri_mismatch" in error_msg:
                raise ValueError("回调地址不匹配,请检查Google Cloud Console配置")
            elif "invalid_client" in error_msg:
                raise ValueError("客户端ID或密钥无效,请检查配置")
            else:
                raise ValueError(f"Token交换失败: {error_msg}")

    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        使用refresh token刷新access token

        Args:
            refresh_token: 刷新令牌

        Returns:
            Dict: 新的token信息

        Raises:
            ValueError: 刷新失败
        """
        try:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri=self.client_config["web"]["token_uri"],
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=self.scopes
            )

            # 刷新token
            credentials.refresh(Request())

            if not credentials.token:
                raise ValueError("Failed to refresh access token")

            token_data = {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token or refresh_token,  # 保留原refresh token
                'token_type': 'Bearer',
                'expires_in': 3600,
                'scope': ' '.join(self.scopes)
            }

            logger.info("Successfully refreshed access token")
            return token_data

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to refresh access token: {error_msg}")

            if "invalid_grant" in error_msg:
                raise ValueError("Refresh token无效或已被撤销,需要重新授权")
            elif "invalid_client" in error_msg:
                raise ValueError("客户端认证失败,请检查配置")
            else:
                raise ValueError(f"Token刷新失败: {error_msg}")

    def save_tokens_to_db(
        self,
        db: Session,
        customer_id: str,
        token_data: Dict,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> OAuthToken:
        """
        保存token到数据库

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID (格式: 123-456-7890)
            token_data: Token数据
            ip_address: 请求IP地址
            user_agent: 用户代理

        Returns:
            OAuthToken: 保存的token记录

        Raises:
            Exception: 保存失败
        """
        start_time = datetime.now()

        try:
            # 加密token
            encrypted_access, encrypted_refresh = token_encryption.encrypt_token_data(
                token_data['access_token'],
                token_data['refresh_token']
            )

            # 计算过期时间
            expires_at = datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))

            # 查找现有token记录 (使用 platform + account_key)
            existing_token = db.query(OAuthToken).filter(
                OAuthToken.platform == 'google',
                OAuthToken.account_key == customer_id
            ).first()

            if existing_token:
                # 更新现有记录
                existing_token.access_token = encrypted_access
                existing_token.refresh_token = encrypted_refresh
                existing_token.token_type = token_data.get('token_type', 'Bearer')
                existing_token.expires_at = expires_at
                existing_token.scope = token_data.get('scope')
                existing_token.is_valid = True
                existing_token.last_refreshed_at = datetime.now()
                existing_token.refresh_count += 1
                existing_token.error_message = None

                oauth_token = existing_token
                logger.info(f"Updated existing token for Google account {customer_id}")
            else:
                # 创建新记录
                oauth_token = OAuthToken(
                    platform='google',
                    account_key=customer_id,
                    access_token=encrypted_access,
                    refresh_token=encrypted_refresh,
                    token_type=token_data.get('token_type', 'Bearer'),
                    expires_at=expires_at,
                    scope=token_data.get('scope'),
                    grant_type='authorization_code',
                    is_valid=True
                )
                db.add(oauth_token)
                logger.info(f"Created new token for Google account {customer_id}")

            # 记录授权日志
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            auth_log = AuthorizationLog(
                platform='google',
                account_key=customer_id,
                action_type='AUTHORIZE',
                status='SUCCESS',
                ip_address=ip_address,
                user_agent=user_agent,
                duration_ms=duration_ms
            )
            db.add(auth_log)

            db.commit()
            db.refresh(oauth_token)

            return oauth_token

        except Exception as e:
            db.rollback()
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 记录失败日志
            error_log = AuthorizationLog(
                platform='google',
                account_key=customer_id,
                action_type='AUTHORIZE',
                status='FAILED',
                error_message=str(e),
                ip_address=ip_address,
                user_agent=user_agent,
                duration_ms=duration_ms
            )
            db.add(error_log)
            db.commit()

            logger.error(f"Failed to save tokens: {str(e)}")
            raise

    def get_valid_credentials(self, db: Session, customer_id: str) -> Optional[Credentials]:
        """
        获取有效的凭据(自动刷新)

        Args:
            db: 数据库会话
            customer_id: Google Ads Customer ID (格式: 123-456-7890)

        Returns:
            Optional[Credentials]: Google凭据对象,如果无法获取则返回None
        """
        try:
            # 查找token记录 (使用 platform + account_key)
            oauth_token = db.query(OAuthToken).filter(
                OAuthToken.platform == 'google',
                OAuthToken.account_key == customer_id,
                OAuthToken.is_valid == True
            ).first()

            if not oauth_token:
                logger.warning(f"No valid token found for Google account {customer_id}")
                return None

            # 解密token
            access_token, refresh_token = token_encryption.decrypt_token_data(
                oauth_token.access_token,
                oauth_token.refresh_token
            )

            # 检查是否需要刷新
            if oauth_token.is_expired:
                logger.info(f"Token expired for Google account {customer_id}, refreshing...")

                try:
                    # 刷新token
                    new_token_data = self.refresh_access_token(refresh_token)

                    # 保存新token
                    self.save_tokens_to_db(db, customer_id, new_token_data)

                    # 使用新token
                    access_token = new_token_data['access_token']
                    refresh_token = new_token_data['refresh_token']

                except Exception as e:
                    logger.error(f"Failed to refresh token: {str(e)}")
                    oauth_token.is_valid = False
                    oauth_token.error_message = str(e)
                    db.commit()
                    return None

            # 创建凭据对象
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri=self.client_config["web"]["token_uri"],
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=self.scopes
            )

            return credentials

        except Exception as e:
            logger.error(f"Failed to get valid credentials: {str(e)}")
            return None


# 创建全局服务实例
oauth_service = GoogleAdsOAuthService()
