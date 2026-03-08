# JWT Handler 使用文档

## 概述

`src/core/jwt_handler.py` 提供了 JWT token 的加密和解密功能，用于用户身份验证。

## 功能特性

- ✓ JWT token 生成（加密）
- ✓ JWT token 解密和验证
- ✓ 自定义签名机制（MD5 + 盐）
- ✓ 过期时间验证
- ✓ User-Agent 绑定支持

## Token 结构

每个 JWT token 包含以下字段：

```json
{
  "user_id": "用户ID（必填）",
  "expires_at": "过期时间戳（秒）",
  "ua": "User-Agent 字符串",
  "signature": "签名（MD5）"
}
```

### 签名算法

签名使用以下算法生成：
```
签名盐 = user_id + (expires_at × 3) + ua + SIGNATURE_SALT
签名 = MD5(签名盐)
```

其中 `SIGNATURE_SALT = "xmp_server_v1_2026"` 是常量。

## API 参考

### 1. generate_jwt_token()

生成 JWT token。

**函数签名：**
```python
def generate_jwt_token(
    secret: str,
    user_id: str,
    expires_at: Optional[int] = None,
    ua: str = ""
) -> str
```

**参数：**
- `secret` (str, 必填): JWT 加密密钥
- `user_id` (str, 必填): 用户ID
- `expires_at` (int, 可选): 过期时间戳（秒），默认为当前时间 + 6个月
- `ua` (str, 可选): User-Agent 字符串，默认为空字符串

**返回值：**
- `str`: 加密后的 JWT token 字符串

**异常：**
- `ValueError`: 当 user_id 为空时抛出

**示例：**
```python
from src.core.jwt_handler import generate_jwt_token
import time

# 1. 最简单的用法（使用默认过期时间和空UA）
token = generate_jwt_token("my_secret_key", "user_123")

# 2. 指定过期时间（1小时后）
expires_at = int(time.time()) + 3600
token = generate_jwt_token("my_secret_key", "user_456", expires_at)

# 3. 完整参数
expires_at = int(time.time()) + 7200  # 2小时后
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
token = generate_jwt_token("my_secret_key", "user_789", expires_at, ua)
```

---

### 2. decrypt_jwt_token()

解密并验证 JWT token。

**函数签名：**
```python
def decrypt_jwt_token(
    token: str,
    secret: str
) -> Dict[str, Any]
```

**参数：**
- `token` (str, 必填): JWT token 字符串
- `secret` (str, 必填): JWT 解密密钥（必须与加密时使用的密钥相同）

**返回值：**
- `Dict[str, Any]`: 解密后的数据字典，包含：
  - `user_id`: 用户ID
  - `expires_at`: 过期时间戳
  - `ua`: User-Agent
  - `signature`: 签名

**异常：**
- `JwtError`: 当 token 无效、签名验证失败或已过期时抛出

**验证检查：**
1. JWT 格式是否正确
2. 签名是否匹配
3. Token 是否过期

**示例：**
```python
from src.core.jwt_handler import decrypt_jwt_token, JwtError

# 解密 token
try:
    data = decrypt_jwt_token(token, "my_secret_key")
    print(f"用户ID: {data['user_id']}")
    print(f"过期时间: {data['expires_at']}")
    print(f"UA: {data['ua']}")
except JwtError as e:
    print(f"验证失败: {e}")
    print(f"错误代码: {e.error_code}")
```

**JwtError 错误代码：**
- `MISSING_USER_ID`: Token 中缺少 user_id 字段
- `MISSING_EXPIRES_AT`: Token 中缺少 expires_at 字段
- `MISSING_SIGNATURE`: Token 中缺少 signature 字段
- `SIGNATURE_MISMATCH`: 签名验证失败
- `TOKEN_EXPIRED`: Token 已过期
- `JWT_EXPIRED`: JWT 级别的过期错误
- `INVALID_TOKEN`: JWT 格式无效
- `DECRYPTION_ERROR`: 解密过程中发生错误

---

### 3. verify_jwt_signature()

独立验证签名是否正确（辅助函数）。

**函数签名：**
```python
def verify_jwt_signature(
    user_id: str,
    expires_at: int,
    ua: str,
    signature: str
) -> bool
```

**参数：**
- `user_id` (str): 用户ID
- `expires_at` (int): 过期时间戳
- `ua` (str): User-Agent
- `signature` (str): 待验证的签名

**返回值：**
- `bool`: 签名是否正确

**示例：**
```python
from src.core.jwt_handler import verify_jwt_signature

is_valid = verify_jwt_signature(
    user_id="user_123",
    expires_at=1735689600,
    ua="Mozilla/5.0",
    signature="abc123..."
)
```

## 完整使用示例

### 场景 1: 用户登录，生成 token

```python
from src.core.jwt_handler import generate_jwt_token
import time

def login_user(user_id: str, user_agent: str = "") -> str:
    """用户登录，生成并返回 JWT token"""
    # 从配置文件读取密钥
    secret = "your_secret_key_from_config"

    # 设置过期时间为 6 个月后（默认值）
    # 或者自定义过期时间
    expires_at = int(time.time()) + (30 * 24 * 60 * 60)  # 30天

    # 生成 token
    token = generate_jwt_token(
        secret=secret,
        user_id=user_id,
        expires_at=expires_at,
        ua=user_agent
    )

    return token

# 使用
token = login_user("user_12345", "Mozilla/5.0 ...")
print(f"Token: {token}")
```

### 场景 2: 验证用户请求的 token

```python
from src.core.jwt_handler import decrypt_jwt_token, JwtError
from fastapi import HTTPException

def verify_user_token(token: str) -> dict:
    """验证用户的 JWT token"""
    secret = "your_secret_key_from_config"

    # 解密并验证
    try:
        data = decrypt_jwt_token(token, secret)
        return data
    except JwtError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token 验证失败: {e.message}"
        )

# 使用
try:
    user_data = verify_user_token(token)
    user_id = user_data['user_id']
    print(f"验证成功，用户ID: {user_id}")
except HTTPException as e:
    print(f"验证失败: {e.detail}")
```

### 场景 3: 在 FastAPI 中间件中使用

```python
from fastapi import Request, HTTPException
from src.core.jwt_handler import decrypt_jwt_token, JwtError

async def authenticate_request(request: Request):
    """验证请求中的 JWT token"""
    # 从 Authorization header 获取 token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]  # 移除 "Bearer " 前缀
    secret = "your_secret_key_from_config"

    # 验证 token
    try:
        data = decrypt_jwt_token(token, secret)
    except JwtError as e:
        raise HTTPException(
            status_code=401,
            detail=f"{e.error_code}: {e.message}"
        )

    # 验证 User-Agent 是否匹配（可选）
    request_ua = request.headers.get("User-Agent", "")
    if data['ua'] and data['ua'] != request_ua:
        raise HTTPException(status_code=401, detail="User-Agent mismatch")

    return data['user_id']
```

## 安全建议

1. **密钥管理**：
   - 使用强随机字符串作为 `secret`
   - 不要在代码中硬编码密钥，使用环境变量或配置文件
   - 定期轮换密钥

2. **过期时间**：
   - 根据业务需求设置合理的过期时间
   - 敏感操作使用较短的过期时间
   - 普通会话可以使用较长的过期时间

3. **User-Agent 绑定**：
   - 启用 UA 绑定可以防止 token 被盗用
   - 但要注意移动端 UA 可能会变化

4. **HTTPS**：
   - 始终在 HTTPS 下传输 token
   - 防止中间人攻击

## 与现有代码集成

可以在 [src/middleware/token_verify.py](src/middleware/token_verify.py) 中使用新的 JWT handler：

```python
from src.core.jwt_handler import decrypt_jwt_token, JwtError

def verify_jwt(self, jwtoken: str) -> dict:
    """验证JWT Token"""
    secret = cnf.auth['jwt_secret']

    # 使用新的解密函数
    try:
        data = decrypt_jwt_token(jwtoken, secret)
    except JwtError as e:
        raise ValueError(f"{e.error_code}: {e.message}")

    # 构造返回数据（保持与现有格式兼容）
    r_dict = {
        'user_uid': data['user_id'],
        'expires_at': data['expires_at'],
        'is_token_valid': True,
        'token': jwtoken
    }

    return r_dict
```

## 测试

运行测试脚本：
```bash
python test_jwt_simple.py
```

或者在你的代码中进行单元测试：
```python
import time
from src.core.jwt_handler import generate_jwt_token, decrypt_jwt_token, JwtError

# 测试基本功能
secret = "test_secret"
user_id = "test_user"
token = generate_jwt_token(secret, user_id)

try:
    data = decrypt_jwt_token(token, secret)
    assert data['user_id'] == user_id
    print("✓ 测试通过")
except JwtError as e:
    print(f"✗ 测试失败: {e}")
```

## 常见问题

**Q: 为什么签名使用 `expires_at * 3`？**
A: 这是为了增加签名的复杂度和安全性，使签名更难被破解。

**Q: 可以修改 SIGNATURE_SALT 常量吗？**
A: 可以，但修改后之前生成的所有 token 都将失效。建议在项目初始化时设置，之后不要更改。

**Q: 如何刷新 token？**
A: 解密旧 token 获取 user_id，然后生成新的 token 并返回给客户端。

**Q: Token 泄露了怎么办？**
A: 立即更换密钥（secret），所有旧 token 将失效。用户需要重新登录。
