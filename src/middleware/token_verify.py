from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.jwt_handler import decrypt_jwt_token, JwtError
from src.core import settings

jwt_secret = settings.JWT_SECRET

# 鉴权中间件 token类型 Bearer
class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True, only_user_id=True):
        self.only_user_id = only_user_id
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> dict:
        try:
            credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
            if credentials:
                if not credentials.scheme == "Bearer":
                    raise JwtError("token类型不是Bearer", "INVALID_TOKEN_SCHEME")
                r_dict = decrypt_jwt_token(credentials.credentials, jwt_secret)
                if self.only_user_id:
                    return r_dict.get("user_id")
                return r_dict
            else:
                raise JwtError("token不存在", "TOKEN_MISSING")
        except JwtError as e:
            if self.auto_error:
                raise             
            return {}
        except Exception as e:
            if self.auto_error:
                raise JwtError(f"Unexpected error: {str(e)}")
            return {}

