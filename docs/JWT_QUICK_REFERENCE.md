# JWT Handler 快速参考

## 导入
```python
from src.core.jwt_handler import generate_jwt_token, decrypt_jwt_token, JwtError
```

## 生成 Token
```python
# 最简用法（使用默认过期时间：6个月）
token = generate_jwt_token(secret="your_secret", user_id="user_123")

# 自定义过期时间（1小时后）
import time
token = generate_jwt_token(
    secret="your_secret",
    user_id="user_123",
    expires_at=int(time.time()) + 3600
)

# 完整参数（包含 User-Agent）
token = generate_jwt_token(
    secret="your_secret",
    user_id="user_123",
    expires_at=int(time.time()) + 3600,
    ua="Mozilla/5.0 ..."
)
```

## 验证 Token
```python
# 基本用法
try:
    data = decrypt_jwt_token(token, secret="your_secret")
    user_id = data['user_id']
    expires_at = data['expires_at']
    ua = data['ua']
    print(f"验证成功: {user_id}")
except JwtError as e:
    print(f"验证失败: {e}")
    print(f"错误代码: {e.error_code}")
```

## 在 FastAPI 中使用
```python
from fastapi import HTTPException, Depends
from src.core.jwt_handler import decrypt_jwt_token, JwtError

def get_current_user(token: str) -> str:
    """从 token 中获取当前用户"""
    try:
        data = decrypt_jwt_token(token, "your_secret")
        return data['user_id']
    except JwtError as e:
        raise HTTPException(
            status_code=401,
            detail=f"{e.error_code}: {e.message}"
        )

# 在路由中使用
@app.get("/protected")
async def protected_route(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id, "message": "Access granted"}
```

## 错误代码
- `MISSING_USER_ID` - 缺少用户ID
- `MISSING_EXPIRES_AT` - 缺少过期时间
- `MISSING_SIGNATURE` - 缺少签名
- `SIGNATURE_MISMATCH` - 签名不匹配
- `TOKEN_EXPIRED` - Token已过期
- `JWT_EXPIRED` - JWT级别过期
- `INVALID_TOKEN` - Token格式无效
- `DECRYPTION_ERROR` - 解密错误

## Token 内容结构
```python
{
    "user_id": "用户ID",
    "expires_at": 1234567890,  # Unix时间戳
    "ua": "User-Agent字符串",
    "signature": "MD5签名"
}
```

## 安全提示
- 使用强随机字符串作为 secret
- 不要在代码中硬编码 secret
- 始终在 HTTPS 下传输 token
- 根据业务需求设置合理的过期时间
- 敏感操作使用较短的过期时间
