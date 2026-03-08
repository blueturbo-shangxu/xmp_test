# Token Verify 中间件错误处理优化

## 修改概述

将 `src/middleware/token_verify.py` 中的错误处理统一使用 `JwtError` 异常，然后在最外层转换为 `HTTPException`。

## 修改内容

### 修改前

```python
async def __call__(self, request: Request) -> dict:
    try:
        credentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403,
                    detail=get_token_error_response("token类型不是Bearer")
                )
            r_dict = decrypt_jwt_token(credentials.credentials, jwt_secret)
            return r_dict
        else:
            raise HTTPException(
                status_code=403,
                detail=get_token_error_response("token不存在")
            )
    except HTTPException:
        raise
    except Exception as e:
        if self.auto_error:
            raise HTTPException(
                status_code=403,
                detail=get_token_error_response(str(e))
            )
        return {}
```

### 修改后

```python
async def __call__(self, request: Request) -> dict:
    try:
        credentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise JwtError("token类型不是Bearer", "INVALID_TOKEN_SCHEME")
            r_dict = decrypt_jwt_token(credentials.credentials, jwt_secret)
            return r_dict
        else:
            raise JwtError("token不存在", "TOKEN_MISSING")
    except JwtError as e:
        # 将 JwtError 转换为 HTTPException
        if self.auto_error:
            raise HTTPException(
                status_code=403,
                detail=get_token_error_response(f"[{e.error_code}] {e.message}")
            )
        return {}
    except HTTPException:
        # 来自父类的 HTTPException，直接重新抛出
        raise
    except Exception as e:
        if self.auto_error:
            raise HTTPException(
                status_code=403,
                detail=get_token_error_response(f"Unexpected error: {str(e)}")
            )
        return {}
```

## 主要改进

### 1. 统一的错误类型

**修改前：**
- 混合使用 `HTTPException` 和其他异常
- 错误信息缺少错误代码

**修改后：**
- 统一使用 `JwtError` 表示所有 JWT 相关错误
- 所有错误都包含错误代码
- 在最外层统一转换为 `HTTPException`

### 2. 新增的错误代码

| 错误代码 | 说明 | 触发条件 |
|---------|------|---------|
| `INVALID_TOKEN_SCHEME` | Token 类型不是 Bearer | credentials.scheme != "Bearer" |
| `TOKEN_MISSING` | Token 不存在 | credentials 为空 |

### 3. 更好的错误信息

**修改前：**
```json
{
  "code": 403,
  "message": "认证失败: token类型不是Bearer"
}
```

**修改后：**
```json
{
  "code": 403,
  "message": "认证失败: [INVALID_TOKEN_SCHEME] token类型不是Bearer"
}
```

## 异常处理流程

```
┌─────────────────────────────────────────────────────────┐
│  请求到达 JWTBearer.__call__()                          │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  验证流程                                                │
│  1. 获取 credentials                                    │
│  2. 检查 scheme 是否为 "Bearer"                         │
│  3. 调用 decrypt_jwt_token() 验证 token                 │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
              ┌─────────┴─────────┐
              │  验证成功？         │
              └─────────┬─────────┘
                        │
           ┌────────────┴────────────┐
           │ YES                     │ NO
           ▼                         ▼
    ┌─────────────┐         ┌─────────────────┐
    │ 返回用户数据 │         │ 抛出 JwtError    │
    └─────────────┘         └─────────────────┘
                                      │
                                      ▼
                            ┌─────────────────┐
                            │ 捕获 JwtError    │
                            │ 转换为 HTTP 403  │
                            └─────────────────┘
                                      │
                                      ▼
                            ┌─────────────────┐
                            │ 返回错误响应     │
                            │ 包含错误代码     │
                            └─────────────────┘
```

## 完整的错误代码列表

### JWT Handler 错误代码

来自 `decrypt_jwt_token()`:
- `MISSING_USER_ID` - Token 中缺少 user_id
- `MISSING_EXPIRES_AT` - Token 中缺少 expires_at
- `MISSING_SIGNATURE` - Token 中缺少 signature
- `SIGNATURE_MISMATCH` - 签名验证失败
- `TOKEN_EXPIRED` - Token 已过期
- `JWT_EXPIRED` - JWT 级别过期
- `INVALID_TOKEN` - Token 格式无效
- `DECRYPTION_ERROR` - 解密错误

### 中间件错误代码

来自 `JWTBearer.__call__()`:
- `INVALID_TOKEN_SCHEME` - Token 类型不是 Bearer
- `TOKEN_MISSING` - Token 不存在

## 示例

### 示例 1: Token 不存在

**请求：**
```http
GET /api/protected HTTP/1.1
Host: localhost:8000
```

**响应：**
```json
{
  "code": 40301,
  "message": "认证失败: [TOKEN_MISSING] token不存在",
  "message_en": "Authentication failed: [TOKEN_MISSING] token不存在",
  "data": null
}
```

### 示例 2: Token 类型错误

**请求：**
```http
GET /api/protected HTTP/1.1
Host: localhost:8000
Authorization: Basic dXNlcjpwYXNz
```

**响应：**
```json
{
  "code": 40301,
  "message": "认证失败: [INVALID_TOKEN_SCHEME] token类型不是Bearer",
  "message_en": "Authentication failed: [INVALID_TOKEN_SCHEME] token类型不是Bearer",
  "data": null
}
```

### 示例 3: Token 已过期

**请求：**
```http
GET /api/protected HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**响应：**
```json
{
  "code": 40301,
  "message": "认证失败: [TOKEN_EXPIRED] Token expired at 1234567890, current time is 1735689600",
  "message_en": "Authentication failed: [TOKEN_EXPIRED] Token expired at 1234567890, current time is 1735689600",
  "data": null
}
```

### 示例 4: 签名验证失败

**请求：**
```http
GET /api/protected HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**响应：**
```json
{
  "code": 40301,
  "message": "认证失败: [SIGNATURE_MISMATCH] Signature verification failed",
  "message_en": "Authentication failed: [SIGNATURE_MISMATCH] Signature verification failed",
  "data": null
}
```

## 优势

### 1. 统一的错误处理

所有 JWT 相关错误都使用 `JwtError`，便于：
- 统一捕获和处理
- 添加日志记录
- 错误监控和告警

### 2. 详细的错误信息

每个错误都包含：
- 错误代码（便于程序化处理）
- 错误消息（便于调试和用户反馈）

### 3. 更好的可维护性

- 错误类型集中管理
- 便于添加新的错误类型
- 便于修改错误处理逻辑

### 4. 更好的调试体验

错误消息格式：`[ERROR_CODE] error message`
- 一眼就能看出错误类型
- 便于日志搜索和过滤
- 便于错误统计和分析

## 向后兼容性

✅ **完全向后兼容**

- HTTP 响应状态码保持 403
- 响应体结构保持不变
- 只是错误消息中增加了错误代码前缀
- 客户端无需修改代码

## 测试建议

建议测试以下场景：

1. ✅ 缺少 Authorization header
2. ✅ Authorization header 不是 "Bearer" 类型
3. ✅ Token 格式无效
4. ✅ Token 签名不匹配
5. ✅ Token 已过期
6. ✅ Token 缺少必要字段
7. ✅ 有效的 Token

## 相关文档

- [JWT Handler 使用文档](JWT_HANDLER_USAGE.md)
- [Token Verify 中间件迁移说明](TOKEN_VERIFY_MIGRATION.md)
- [JWT 系统集成总结](JWT_INTEGRATION_SUMMARY.md)
