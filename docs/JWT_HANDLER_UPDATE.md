# JWT Handler 更新说明

## 修改内容

已按照要求修改 `src/core/jwt_handler.py`，主要变更如下：

### 1. 新增自定义异常类 `JwtError`

```python
class JwtError(Exception):
    """JWT 相关错误的自定义异常类"""
    def __init__(self, message: str, error_code: str = "JWT_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
```

异常包含两个属性：
- `message`: 错误消息
- `error_code`: 错误代码（便于程序化处理）

### 2. 修改 `decrypt_jwt_token` 函数

**修改前（返回三元组）：**
```python
def decrypt_jwt_token(token: str, secret: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    # 返回 (success, data, error)
    return True, payload, None  # 成功
    return False, None, "error message"  # 失败
```

**修改后（直接返回或抛异常）：**
```python
def decrypt_jwt_token(token: str, secret: str) -> Dict[str, Any]:
    # 成功：直接返回数据
    return payload

    # 失败：抛出 JwtError 异常
    raise JwtError("error message", "ERROR_CODE")
```

### 3. 错误代码列表

| 错误代码 | 说明 |
|---------|------|
| `MISSING_USER_ID` | Token 中缺少 user_id 字段 |
| `MISSING_EXPIRES_AT` | Token 中缺少 expires_at 字段 |
| `MISSING_SIGNATURE` | Token 中缺少 signature 字段 |
| `SIGNATURE_MISMATCH` | 签名验证失败 |
| `TOKEN_EXPIRED` | Token 已过期 |
| `JWT_EXPIRED` | JWT 级别的过期错误 |
| `INVALID_TOKEN` | JWT 格式无效 |
| `DECRYPTION_ERROR` | 解密过程中发生错误 |

## 使用方法

### 新的调用方式

```python
from src.core.jwt_handler import generate_jwt_token, decrypt_jwt_token, JwtError

# 生成 token
token = generate_jwt_token("secret", "user_123")

# 解密 token（新方式）
try:
    data = decrypt_jwt_token(token, "secret")
    print(f"用户ID: {data['user_id']}")
except JwtError as e:
    print(f"错误: {e}")
    print(f"错误代码: {e.error_code}")
```

### 旧的调用方式对比

```python
# ❌ 旧方式（已废弃）
success, data, error = decrypt_jwt_token(token, secret)
if success:
    print(data['user_id'])
else:
    print(error)

# ✅ 新方式
try:
    data = decrypt_jwt_token(token, secret)
    print(data['user_id'])
except JwtError as e:
    print(e.message)
```

## 迁移指南

如果现有代码使用了旧的 API，需要进行以下修改：

**修改前：**
```python
success, data, error = decrypt_jwt_token(token, secret)
if success:
    # 处理成功情况
    user_id = data['user_id']
else:
    # 处理失败情况
    raise ValueError(error)
```

**修改后：**
```python
try:
    data = decrypt_jwt_token(token, secret)
    # 处理成功情况
    user_id = data['user_id']
except JwtError as e:
    # 处理失败情况
    raise ValueError(f"{e.error_code}: {e.message}")
```

## 优势

1. **更符合 Python 惯例**：使用异常处理而不是返回错误码
2. **代码更简洁**：不需要检查 success 标志
3. **类型安全**：返回值始终是 Dict，不会是 None
4. **错误代码**：便于程序化处理不同类型的错误
5. **错误信息更详细**：包含 error_code 和 message 两个维度

## 文件清单

- `src/core/jwt_handler.py` - 核心模块（已修改）
- `docs/JWT_HANDLER_USAGE.md` - 使用文档（已更新）
- `test_jwt_simple.py` - 测试文件（已更新）
- `example_jwt_usage.py` - 使用示例（新增）
