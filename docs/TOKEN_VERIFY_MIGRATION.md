# Token Verify 中间件迁移说明

## 修改概述

已将 [src/middleware/token_verify.py](src/middleware/token_verify.py) 中的 `verify_jwt` 方法迁移到使用新的 `decrypt_jwt_token` 函数。

## 修改对比

### 修改前（旧代码）

```python
import jwt
import time

def verify_jwt(self, jwtoken: str) -> dict:
    """ 验证JWT Token """
    try:
        # 解码JWT token
        payload = jwt.decode(jwtoken, cnf.auth['jwt_secret'], algorithms=["HS256"])

        # 提取token信息
        token_data = payload.get('token', {})
        user_uid = token_data.get('user_uid')
        expires_at = token_data.get('expires_at')

        if not user_uid:
            raise ValueError("Invalid token: missing user_uid")

        if not expires_at:
            raise ValueError("Invalid token: missing expires_at")

        # 和 UTC 时间比较
        if expires_at < time.time():
            raise ValueError("Token expired")

        # 构造返回数据
        r_dict = {
            'user_uid': user_uid,
            'expires_at': expires_at,
            'is_token_valid': True,
            'token': jwtoken
        }

        return r_dict

    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")
```

### 修改后（新代码）

```python
from src.core.jwt_handler import decrypt_jwt_token, JwtError

def verify_jwt(self, jwtoken: str) -> dict:
    """ 验证JWT Token """
    try:
        # 使用新的解密函数
        data = decrypt_jwt_token(jwtoken, cnf.auth['jwt_secret'])

        # 构造返回数据（保持与现有格式兼容）
        r_dict = {
            'user_uid': data['user_id'],
            'expires_at': data['expires_at'],
            'is_token_valid': True,
            'token': jwtoken
        }

        return r_dict

    except JwtError as e:
        # 将 JwtError 转换为 ValueError，保持原有的异常处理逻辑
        raise ValueError(f"[{e.error_code}] {e.message}")
```

## 主要改进

### 1. **代码更简洁**
- 从 ~35 行代码减少到 ~15 行
- 移除了重复的验证逻辑
- 不再需要手动导入和处理 `jwt` 库

### 2. **统一的签名验证**
- 旧代码：只验证 JWT 格式和过期时间，**没有自定义签名验证**
- 新代码：使用 `decrypt_jwt_token`，包含完整的自定义 MD5 签名验证

### 3. **更好的错误信息**
- 旧代码：简单的错误消息（如 "Token expired"）
- 新代码：包含错误代码的结构化错误（如 "[TOKEN_EXPIRED] Token expired at ..."）

### 4. **统一的 Token 格式**
- 旧代码使用：`payload.get('token', {}).get('user_uid')`（嵌套结构）
- 新代码使用：`data['user_id']`（扁平结构）
- 返回数据中保持 `user_uid` 字段名以保证向后兼容

### 5. **移除未使用的导入**
```python
# 移除了：
import jwt
import time

# 只需要：
from src.core.jwt_handler import decrypt_jwt_token, JwtError
```

## 兼容性

### ✅ 保持向后兼容

返回的数据结构保持不变：
```python
{
    'user_uid': 'user_123',      # 字段名保持为 user_uid
    'expires_at': 1234567890,
    'is_token_valid': True,
    'token': 'eyJ0eXAi...'
}
```

### ✅ 异常处理保持一致

- 继续抛出 `ValueError` 异常
- 只是错误消息格式更详细：`[ERROR_CODE] message`

## Token 格式变化

### ⚠️ 重要提示

新旧代码期望不同的 token payload 结构：

**旧格式（嵌套）：**
```json
{
  "token": {
    "user_uid": "user_123",
    "expires_at": 1234567890
  }
}
```

**新格式（扁平）：**
```json
{
  "user_id": "user_123",
  "expires_at": 1234567890,
  "ua": "",
  "signature": "abc123..."
}
```

### 🔧 如何处理

如果你的系统中已经存在旧格式的 token，有两种选择：

**方案 1：强制用户重新登录**（推荐）
- 所有旧 token 将失效
- 用户需要重新登录获取新格式的 token
- 更安全，因为新 token 包含签名验证

**方案 2：支持双格式（临时过渡）**
```python
def verify_jwt(self, jwtoken: str) -> dict:
    """ 验证JWT Token """
    try:
        # 先尝试新格式
        data = decrypt_jwt_token(jwtoken, cnf.auth['jwt_secret'])
        r_dict = {
            'user_uid': data['user_id'],
            'expires_at': data['expires_at'],
            'is_token_valid': True,
            'token': jwtoken
        }
        return r_dict
    except JwtError:
        # 回退到旧格式（临时支持）
        try:
            payload = jwt.decode(jwtoken, cnf.auth['jwt_secret'], algorithms=["HS256"])
            token_data = payload.get('token', {})
            # ... 旧的验证逻辑
        except Exception as e:
            raise ValueError(f"Token validation failed: {str(e)}")
```

## 测试建议

在部署到生产环境前，建议测试以下场景：

1. ✅ **有效的新格式 token** - 应该成功验证
2. ✅ **过期的 token** - 应该返回 `[TOKEN_EXPIRED]` 错误
3. ✅ **错误的 secret** - 应该返回 `[INVALID_TOKEN]` 错误
4. ✅ **签名不匹配** - 应该返回 `[SIGNATURE_MISMATCH]` 错误
5. ⚠️ **旧格式的 token** - 应该返回 `[MISSING_USER_ID]` 错误（如果不支持双格式）

## 迁移步骤

1. ✅ 已完成：修改 `src/middleware/token_verify.py`
2. 📝 建议：在测试环境验证功能
3. 📝 建议：通知用户可能需要重新登录
4. 📝 建议：部署到生产环境
5. 📝 建议：监控错误日志，确认没有异常

## 总结

这次迁移带来了：
- ✅ 更简洁的代码（减少 ~20 行）
- ✅ 统一的 JWT 处理逻辑
- ✅ 增强的安全性（自定义签名验证）
- ✅ 更好的错误处理和调试信息
- ✅ 保持 API 向后兼容（返回数据结构不变）
