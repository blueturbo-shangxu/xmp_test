# JWT 配置集成完成

## ✅ 已完成的工作

### 1. 环境变量配置文件

#### conf/.env（实际配置）
```env
# JWT配置
JWT_SECRET=JLp?9O&02jFfsoE$23_xmp_auth_server_v1_2026
JWT_TOKEN_EXPIRE_DAYS=180
```

#### conf/.env.example（示例模板）
```env
# JWT配置
JWT_SECRET=your_jwt_secret_key_at_least_32_characters_long
JWT_TOKEN_EXPIRE_DAYS=180
```

### 2. Settings 配置类

**文件：** [src/core/config.py](../src/core/config.py:70-72)

```python
class Settings(BaseSettings):
    # JWT配置
    JWT_SECRET: str = os.getenv('JWT_SECRET', 'default_jwt_secret_please_change_in_production')
    JWT_TOKEN_EXPIRE_DAYS: int = int(os.getenv('JWT_TOKEN_EXPIRE_DAYS', 180))
```

### 3. 中间件集成

**文件：** [src/middleware/token_verify.py](../src/middleware/token_verify.py:9-11)

```python
from src.core import settings

jwt_secret = settings.JWT_SECRET
```

**使用方式：**
```python
class JWTBearer(HTTPBearer):
    def verify_jwt(self, jwtoken: str) -> dict:
        # 使用配置中的 JWT_SECRET
        data = decrypt_jwt_token(jwtoken, jwt_secret)
        # ...
```

### 4. 文档

创建了完整的配置文档：[docs/JWT_CONFIGURATION.md](JWT_CONFIGURATION.md)

## 🔑 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `JWT_SECRET` | string | `default_jwt_secret...` | JWT 加密密钥（必需修改） |
| `JWT_TOKEN_EXPIRE_DAYS` | int | `180` | Token 过期天数（6个月） |

## 📝 使用示例

### 读取配置

```python
from src.core.config import settings

# 获取 JWT 密钥
jwt_secret = settings.JWT_SECRET

# 获取过期天数
expire_days = settings.JWT_TOKEN_EXPIRE_DAYS

print(f"JWT Secret length: {len(jwt_secret)}")
print(f"Token will expire in {expire_days} days")
```

### 生成 Token

```python
from src.core.config import settings
from src.core.jwt_handler import generate_jwt_token
import time

# 计算过期时间
expires_at = int(time.time()) + (settings.JWT_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)

# 生成 token
token = generate_jwt_token(
    secret=settings.JWT_SECRET,
    user_id="user_123",
    expires_at=expires_at,
    ua="Mozilla/5.0 ..."
)
```

### 验证 Token（自动使用配置）

```python
from src.middleware.token_verify import JWTBearer
from fastapi import Depends

@app.get("/protected")
async def protected_route(user_data: dict = Depends(JWTBearer())):
    # JWTBearer 会自动使用 settings.JWT_SECRET 验证 token
    user_uid = user_data['user_uid']
    return {"message": f"Hello {user_uid}"}
```

## 🔒 安全建议

### ✅ 必须做的

1. **更换默认密钥**
   ```bash
   # 生成强密钥
   openssl rand -base64 48
   ```

2. **环境隔离**
   - 开发环境和生产环境使用不同的 JWT_SECRET
   - 不要在代码中硬编码密钥
   - 不要将生产环境的密钥提交到版本控制

3. **密钥强度**
   - 至少 32 个字符
   - 包含大小写字母、数字和特殊字符
   - 使用加密安全的随机数生成器

### ❌ 不要做的

1. ❌ 不要使用默认密钥 `default_jwt_secret_please_change_in_production`
2. ❌ 不要在日志中打印完整的 JWT_SECRET
3. ❌ 不要与他人分享 JWT_SECRET
4. ❌ 不要使用简单的字符串（如 `123456`, `password`）

## 🚀 部署检查清单

部署前请确认：

- [ ] ✅ `conf/.env` 中已设置 `JWT_SECRET`
- [ ] ✅ JWT_SECRET 不是默认值
- [ ] ✅ JWT_SECRET 长度至少 32 字符
- [ ] ✅ JWT_TOKEN_EXPIRE_DAYS 根据业务需求设置
- [ ] ✅ 生产环境和开发环境使用不同的密钥
- [ ] ✅ JWT_SECRET 未提交到 Git（检查 .gitignore）
- [ ] ✅ 日志配置不会输出 JWT_SECRET
- [ ] ✅ 已测试 token 生成和验证功能

## 📊 配置流程图

```
┌─────────────────────────────────────────────────────────┐
│  1. 读取配置                                             │
│  ┌──────────────┐                                       │
│  │ conf/.env    │ ──> JWT_SECRET=xxx                    │
│  └──────────────┘     JWT_TOKEN_EXPIRE_DAYS=180        │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  2. 加载到 Settings 类                                   │
│  ┌────────────────────────────────────┐                 │
│  │ src/core/config.py                 │                 │
│  │                                    │                 │
│  │ class Settings:                    │                 │
│  │   JWT_SECRET: str                  │                 │
│  │   JWT_TOKEN_EXPIRE_DAYS: int       │                 │
│  └────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  3. 在中间件中使用                                        │
│  ┌────────────────────────────────────┐                 │
│  │ src/middleware/token_verify.py     │                 │
│  │                                    │                 │
│  │ from src.core import settings      │                 │
│  │ jwt_secret = settings.JWT_SECRET   │                 │
│  └────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  4. Token 验证                                           │
│  decrypt_jwt_token(token, jwt_secret)                   │
└─────────────────────────────────────────────────────────┘
```

## 🔧 故障排查

### 问题 1: 提示 JWT_SECRET 未设置

**症状：**
```
ValueError: JWT_SECRET is not configured
```

**解决方案：**
1. 检查 `conf/.env` 文件是否存在
2. 检查 `JWT_SECRET` 是否已设置
3. 重启应用

### 问题 2: Token 验证失败

**症状：**
```
[SIGNATURE_MISMATCH] Signature verification failed
```

**可能原因：**
1. 生成 token 和验证 token 使用了不同的密钥
2. 服务器集群中的不同服务器使用了不同的密钥
3. 密钥被修改但应用未重启

**解决方案：**
1. 确认所有服务器使用相同的 JWT_SECRET
2. 重启所有服务
3. 用户重新登录获取新 token

### 问题 3: 配置修改后不生效

**症状：**
修改了 `conf/.env` 中的配置，但应用仍使用旧配置。

**解决方案：**
配置在应用启动时加载，需要重启服务：
```bash
# 重启服务
systemctl restart xmp_auth_server

# 或者使用进程管理工具
pm2 restart xmp_auth_server
```

## 📚 相关文档

- [JWT 配置详细说明](JWT_CONFIGURATION.md)
- [JWT Handler 使用文档](JWT_HANDLER_USAGE.md)
- [Token Verify 中间件迁移说明](TOKEN_VERIFY_MIGRATION.md)
- [JWT 系统集成总结](JWT_INTEGRATION_SUMMARY.md)

## 🎉 总结

JWT 配置已完全集成到项目中：

✅ **配置文件** - .env 和 .env.example 已添加 JWT 配置项
✅ **Settings 类** - config.py 已添加 JWT_SECRET 和 JWT_TOKEN_EXPIRE_DAYS
✅ **中间件** - token_verify.py 已使用 settings.JWT_SECRET
✅ **文档** - 完整的配置说明文档已创建

现在可以通过修改 `conf/.env` 文件来配置 JWT 密钥和过期时间，无需修改代码！
