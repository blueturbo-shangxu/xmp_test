#!/usr/bin/env python
"""
Google Ads Token自动刷新脚本
使用Google SDK刷新即将过期的access token
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session

from src.sql import SessionLocal
from src.sql import OAuthToken, AuthorizationLog
from src.core import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/token_refresh.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_expiring_google_tokens(db: Session, hours_before: int = 2) -> List[OAuthToken]:
    """
    获取即将过期的Google Ads token列表

    Args:
        db: 数据库会话
        hours_before: 提前多少小时刷新 (默认2小时)

    Returns:
        List[OAuthToken]: 即将过期的token列表
    """
    threshold = datetime.now() + timedelta(hours=hours_before)

    tokens = db.query(OAuthToken).filter(
        OAuthToken.platform == 'google',
        OAuthToken.is_valid == True,
        OAuthToken.expires_at <= threshold,
        OAuthToken.refresh_token.isnot(None)
    ).all()

    return tokens


def refresh_google_token_via_sdk(
    client_id: str,
    client_secret: str,
    refresh_token: str
) -> Dict:
    """
    使用 Google Auth SDK 刷新 access_token

    Args:
        client_id: Google OAuth客户端ID
        client_secret: Google OAuth客户端密钥
        refresh_token: 刷新令牌

    Returns:
        Dict: 包含新的access_token和expiry的字典

    Raises:
        Exception: 刷新失败时抛出异常
    """
    # 构造 Credentials 对象
    # token=None 是因为当前的 access_token 已过期或我们不需要它
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )

    # 刷新凭据 - Request() 会处理底层的 HTTP 请求逻辑
    creds.refresh(Request())

    logger.info("Token refreshed successfully via Google SDK")

    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token or refresh_token,  # 保留原refresh_token
        "expiry": creds.expiry,  # datetime对象
    }


def refresh_token(db: Session, oauth_token: OAuthToken) -> bool:
    """
    刷新单个Google Ads token

    Args:
        db: 数据库会话
        oauth_token: OAuthToken对象

    Returns:
        bool: 刷新是否成功
    """
    start_time = datetime.now()

    try:
        logger.info(
            f"Refreshing token for customer_id={oauth_token.account_key}, "
            f"expires_at={oauth_token.expires_at}"
        )

        # 直接使用refresh token
        refresh_token_value = oauth_token.refresh_token

        # 使用Google SDK刷新token
        result = refresh_google_token_via_sdk(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            refresh_token=refresh_token_value
        )

        # 更新数据库
        oauth_token.access_token = result['access_token']
        oauth_token.refresh_token = result['refresh_token']
        oauth_token.expires_at = result['expiry']
        oauth_token.is_valid = True
        oauth_token.last_refreshed_at = datetime.now()
        oauth_token.refresh_count += 1
        oauth_token.error_message = None

        # 记录刷新日志
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        log = AuthorizationLog(
            platform='google',
            account_key=oauth_token.account_key,
            action_type='REFRESH',
            status='SUCCESS',
            duration_ms=duration_ms
        )
        db.add(log)
        db.commit()

        logger.info(
            f"Token refreshed successfully for customer_id={oauth_token.account_key}, "
            f"new_expiry={oauth_token.expires_at}, "
            f"refresh_count={oauth_token.refresh_count}"
        )
        return True

    except Exception as e:
        db.rollback()
        error_message = str(e)
        logger.error(
            f"Failed to refresh token for customer_id={oauth_token.account_key}: "
            f"{error_message}"
        )

        # 更新token状态
        oauth_token.error_message = error_message

        # 如果是refresh token失效,标记为无效
        if "invalid_grant" in error_message.lower() or "token has been expired or revoked" in error_message.lower():
            oauth_token.is_valid = False
            logger.warning(
                f"Refresh token invalid for customer_id={oauth_token.account_key}. "
                f"Re-authorization required."
            )

        # 记录失败日志
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        log = AuthorizationLog(
            platform='google',
            account_key=oauth_token.account_key,
            action_type='REFRESH',
            status='FAILED',
            error_message=error_message,
            duration_ms=duration_ms
        )
        db.add(log)
        db.commit()

        return False


def refresh_all_expiring_tokens(hours_before: int = 2, dry_run: bool = False) -> Dict:
    """
    刷新所有即将过期的Google Ads token

    Args:
        hours_before: 提前多少小时刷新 (默认2小时)
        dry_run: 是否为试运行模式 (只显示,不实际刷新)

    Returns:
        Dict: 刷新结果统计
    """
    logger.info("=" * 60)
    logger.info("Google Ads Token Refresh Task Started")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    logger.info(f"Threshold: {hours_before} hours before expiration")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        # 获取即将过期的Google token
        expiring_tokens = get_expiring_google_tokens(db, hours_before)

        if not expiring_tokens:
            logger.info("No Google Ads tokens need refreshing.")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'skipped': 0
            }

        logger.info(f"Found {len(expiring_tokens)} Google Ads token(s) that need refreshing:")

        for token in expiring_tokens:
            time_until_expiry = token.expires_at - datetime.now()
            hours_left = time_until_expiry.total_seconds() / 3600

            logger.info(
                f"  - Customer ID: {token.account_key}, "
                f"Expires in: {hours_left:.1f} hours, "
                f"Expires at: {token.expires_at.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"Refresh count: {token.refresh_count}"
            )

        if dry_run:
            logger.info("\nDRY RUN MODE - No tokens will be refreshed")
            return {
                'total': len(expiring_tokens),
                'success': 0,
                'failed': 0,
                'skipped': len(expiring_tokens)
            }

        # 执行刷新
        logger.info("\nStarting token refresh...")
        success_count = 0
        failed_count = 0

        for token in expiring_tokens:
            if refresh_token(db, token):
                success_count += 1
            else:
                failed_count += 1

        # 统计结果
        result = {
            'total': len(expiring_tokens),
            'success': success_count,
            'failed': failed_count,
            'skipped': 0
        }

        logger.info("=" * 60)
        logger.info("Google Ads Token Refresh Task Completed")
        logger.info(f"Total: {result['total']}")
        logger.info(f"Success: {result['success']}")
        logger.info(f"Failed: {result['failed']}")
        logger.info("=" * 60)

        return result

    except Exception as e:
        logger.error(f"Token refresh task failed: {str(e)}")
        raise
    finally:
        db.close()


def check_invalid_tokens() -> List[Dict]:
    """
    检查所有无效的Google Ads token

    Returns:
        List[Dict]: 无效token列表
    """
    db = SessionLocal()
    try:
        invalid_tokens = db.query(OAuthToken).filter(
            OAuthToken.platform == 'google',
            OAuthToken.is_valid == False
        ).all()

        if not invalid_tokens:
            logger.info("No invalid Google Ads tokens found.")
            return []

        logger.info(f"\nFound {len(invalid_tokens)} invalid Google Ads token(s):")

        result = []
        for token in invalid_tokens:
            info = {
                'customer_id': token.account_key,
                'error_message': token.error_message,
                'last_refreshed_at': token.last_refreshed_at,
                'refresh_count': token.refresh_count,
                'expires_at': token.expires_at
            }
            result.append(info)

            logger.warning(
                f"  - Customer ID: {token.account_key}, "
                f"Error: {token.error_message}, "
                f"Expires at: {token.expires_at}"
            )

        logger.info("\nThese accounts need re-authorization:")
        for token in invalid_tokens:
            logger.info(
                f"  - Re-authorize: "
                f"http://localhost:8000/auth/authorize?customer_id={token.account_key}"
            )

        return result

    finally:
        db.close()


def get_token_statistics() -> Dict:
    """
    获取token统计信息

    Returns:
        Dict: 统计信息
    """
    db = SessionLocal()
    try:
        # 总token数
        total_tokens = db.query(OAuthToken).filter(
            OAuthToken.platform == 'google'
        ).count()

        # 有效token数
        valid_tokens = db.query(OAuthToken).filter(
            OAuthToken.platform == 'google',
            OAuthToken.is_valid == True
        ).count()

        # 无效token数
        invalid_tokens = db.query(OAuthToken).filter(
            OAuthToken.platform == 'google',
            OAuthToken.is_valid == False
        ).count()

        # 即将过期的token数 (2小时内)
        expiring_soon = db.query(OAuthToken).filter(
            OAuthToken.platform == 'google',
            OAuthToken.is_valid == True,
            OAuthToken.expires_at <= datetime.now() + timedelta(hours=2)
        ).count()

        stats = {
            'total': total_tokens,
            'valid': valid_tokens,
            'invalid': invalid_tokens,
            'expiring_soon': expiring_soon
        }

        logger.info("=" * 60)
        logger.info("Google Ads Token Statistics")
        logger.info("=" * 60)
        logger.info(f"Total tokens: {stats['total']}")
        logger.info(f"Valid tokens: {stats['valid']}")
        logger.info(f"Invalid tokens: {stats['invalid']}")
        logger.info(f"Expiring soon (2h): {stats['expiring_soon']}")
        logger.info("=" * 60)

        return stats

    finally:
        db.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Google Ads Token自动刷新脚本')
    parser.add_argument(
        '--hours',
        type=int,
        default=2,
        help='提前多少小时刷新token (默认: 2)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='试运行模式,只显示将要刷新的token,不实际刷新'
    )
    parser.add_argument(
        '--check-invalid',
        action='store_true',
        help='检查所有无效的token'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='显示token统计信息'
    )

    args = parser.parse_args()

    try:
        if args.stats:
            # 显示统计信息
            get_token_statistics()
        elif args.check_invalid:
            # 检查无效token
            check_invalid_tokens()
        else:
            # 刷新即将过期的token
            result = refresh_all_expiring_tokens(
                hours_before=args.hours,
                dry_run=args.dry_run
            )

            # 返回退出码
            if result['failed'] > 0:
                sys.exit(1)
            else:
                sys.exit(0)

    except Exception as e:
        logger.error(f"Script failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
