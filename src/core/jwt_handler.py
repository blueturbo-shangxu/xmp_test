"""
JWT 加密解密模块
包含用户身份验证的 JWT token 生成和验证功能
"""
import json
import hashlib
import time
from typing import Optional, Dict, Any
import jwt


# 签名盐常量
SIGNATURE_SALT = "JLp?9O&02jFfsoE$23"


class JwtError(Exception):
    """JWT 相关错误的自定义异常类"""
    def __init__(self, message: str, error_code: str = "JWT_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self):
        return f"[{self.error_code}] {self.message}"


def signature_gen(user_id:str, expires_at:int, ua:str):
    # 签名盐: user_id + (expires_at * 3) + ua + SIGNATURE_SALT
    signature_raw = f"{user_id}{SIGNATURE_SALT}{expires_at * 3}{ua}{SIGNATURE_SALT}"
    signature = hashlib.md5(signature_raw.encode('utf-8')).hexdigest()
    return signature

def generate_jwt_token(
    secret: str,
    user_id: str,
    expires_at: Optional[int] = None,
    ua: str = ""
) -> str:
    """
    生成 JWT token

    参数:
        secret: JWT 加密密钥
        user_id: 用户ID (必填)
        expires_at: 过期时间戳 (秒), 默认为当前时间 + 6个月
        ua: User-Agent 字符串, 默认为空字符串

    返回:
        str: 加密后的 JWT token

    示例:
        >>> token = generate_jwt_token("my_secret", "user_123")
        >>> token = generate_jwt_token("my_secret", "user_123", expires_at=1735689600, ua="Mozilla/5.0")
    """
    if not user_id:
        raise ValueError("user_id is required")

    # 如果没有提供过期时间，默认为 6 个月后 (180天)
    if expires_at is None:
        expires_at = int(time.time()) + (180 * 24 * 60 * 60)

    # 生成签名
    signature = signature_gen( user_id, expires_at, ua)

    # 构建 payload
    payload = {
        "user_id": user_id,
        "expires_at": expires_at,
        "ua": ua,
        "signature": signature
    }

    # 使用 JWT 加密
    token = jwt.encode(payload, secret, algorithm="HS256")

    return token


def decrypt_jwt_token(
    token: str,
    secret: str
) -> Dict[str, Any]:
    """
    解密并验证 JWT token

    参数:
        token: JWT token 字符串
        secret: JWT 解密密钥

    返回:
        Dict[str, Any]: 解密后的数据字典，包含:
            - user_id: 用户ID
            - expires_at: 过期时间戳
            - ua: User-Agent
            - signature: 签名

    异常:
        JwtError: 当 token 无效、签名验证失败或已过期时抛出

    示例:
        >>> try:
        ...     data = decrypt_jwt_token(token, "my_secret")
        ...     print(f"User ID: {data['user_id']}")
        ... except JwtError as e:
        ...     print(f"Error: {e}")
    """
    try:
        # 解码 JWT
        payload = jwt.decode(token, secret, algorithms=["HS256"])

        # 提取字段
        user_id = payload.get("user_id")
        expires_at = payload.get("expires_at")
        ua = payload.get("ua", "")
        signature = payload.get("signature")

        # 验证必填字段
        if not user_id:
            raise JwtError("Missing user_id in token", "MISSING_USER_ID")

        if expires_at is None:
            raise JwtError("Missing expires_at in token", "MISSING_EXPIRES_AT")

        if not signature:
            raise JwtError("Missing signature in token", "MISSING_SIGNATURE")

        # 重新计算签名进行验证
        expected_signature = signature_gen( user_id, expires_at, ua)

        # 验证签名
        if signature != expected_signature:
            raise JwtError("Signature verification failed", "SIGNATURE_MISMATCH")

        # 检查是否过期
        current_time = int(time.time())
        if expires_at < current_time:
            raise JwtError(
                f"Token expired at {expires_at}, current time is {current_time}",
                "TOKEN_EXPIRED"
            )

        # 返回解密后的数据
        payload.pop("signature")
        return payload

    except jwt.ExpiredSignatureError:
        raise JwtError("Token has expired (JWT level)", "JWT_EXPIRED")
    except jwt.InvalidTokenError as e:
        raise JwtError(f"Invalid token: {str(e)}", "INVALID_TOKEN")
    except JwtError:
        # 重新抛出 JwtError
        raise
    except Exception as e:
        raise JwtError(f"Decryption error: {str(e)}", "DECRYPTION_ERROR")


def verify_jwt_signature( user_id: str, expires_at: int, ua: str, signature: str) -> bool:
    expected_signature = signature_gen(user_id, expires_at, ua)
    return signature == expected_signature
