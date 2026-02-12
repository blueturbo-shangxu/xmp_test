"""
Token encryption utilities
用于加密和解密OAuth tokens
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class TokenEncryption:
    """Token加密解密类"""

    def __init__(self):
        """初始化加密器"""
        self.cipher = self._initialize_cipher()

    def _initialize_cipher(self) -> Fernet:
        """
        初始化Fernet加密器

        Returns:
            Fernet: 加密器实例
        """
        # 从配置中获取加密密钥
        encryption_key = settings.TOKEN_ENCRYPTION_KEY

        # 如果密钥不是32字节,使用PBKDF2派生密钥
        if len(encryption_key) != 32:
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'xmp_auth_server_salt',  # 在生产环境中应该使用随机盐
                iterations=100000,
                backend=default_backend()
            )
            key_bytes = kdf.derive(encryption_key.encode())
        else:
            key_bytes = encryption_key.encode()

        # 转换为Fernet所需的格式
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串

        Args:
            plaintext: 明文字符串

        Returns:
            str: 加密后的字符串(Base64编码)
        """
        try:
            if not plaintext:
                return ""

            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        解密字符串

        Args:
            ciphertext: 密文字符串(Base64编码)

        Returns:
            str: 解密后的明文字符串
        """
        try:
            if not ciphertext:
                return ""

            decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise

    def encrypt_token_data(self, access_token: str, refresh_token: str) -> tuple:
        """
        加密token数据

        Args:
            access_token: 访问令牌
            refresh_token: 刷新令牌

        Returns:
            tuple: (加密的访问令牌, 加密的刷新令牌)
        """
        encrypted_access = self.encrypt(access_token)
        encrypted_refresh = self.encrypt(refresh_token)
        return encrypted_access, encrypted_refresh

    def decrypt_token_data(self, encrypted_access: str, encrypted_refresh: str) -> tuple:
        """
        解密token数据

        Args:
            encrypted_access: 加密的访问令牌
            encrypted_refresh: 加密的刷新令牌

        Returns:
            tuple: (访问令牌, 刷新令牌)
        """
        access_token = self.decrypt(encrypted_access)
        refresh_token = self.decrypt(encrypted_refresh)
        return access_token, refresh_token


# 创建全局加密器实例
token_encryption = TokenEncryption()


# 便捷函数
def encrypt_token(token: str) -> str:
    """
    加密单个token

    Args:
        token: 明文token

    Returns:
        str: 加密后的token
    """
    return token_encryption.encrypt(token)


def decrypt_token(encrypted_token: str) -> str:
    """
    解密单个token

    Args:
        encrypted_token: 加密的token

    Returns:
        str: 解密后的token
    """
    return token_encryption.decrypt(encrypted_token)


if __name__ == '__main__':
    # 测试加密解密
    test_access = "test_access_token_123456"
    test_refresh = "test_refresh_token_789012"

    encrypted_access, encrypted_refresh = token_encryption.encrypt_token_data(
        test_access, test_refresh
    )
    print(f"Encrypted access: {encrypted_access[:50]}...")
    print(f"Encrypted refresh: {encrypted_refresh[:50]}...")

    decrypted_access, decrypted_refresh = token_encryption.decrypt_token_data(
        encrypted_access, encrypted_refresh
    )
    print(f"Decrypted access: {decrypted_access}")
    print(f"Decrypted refresh: {decrypted_refresh}")

    assert test_access == decrypted_access
    assert test_refresh == decrypted_refresh
    print("Encryption/Decryption test passed!")
