# JWT 配置说明

## 配置项

### 1. JWT_SECRET（必需）

JWT token 的加密密钥，用于生成和验证 JWT token。

**配置位置：** `conf/.env`

**配置示例：**
```env
JWT_SECRET=JLp?9O&02jFfsoE$23_xmp_auth_server_v1_2026
```

**安全建议：**
- ✅ 使用至少 32 个字符的强随机字符串
- ✅ 包含大小写字母、数字和特殊字符
- ✅ 每个环境（开发、测试、生产）使用不同的密钥
- ❌ 不要在代码中硬编码
- ❌ 不要提交到版本控制系统（生产环境的密钥）
- ❌ 不要与其他人分享

**生成强密钥的方法：**

Python:
```python
import secrets
import string

# 生成 64 字符的随机密钥
characters = string.ascii_letters + string.digits + string.punctuation
jwt_secret = ''.join(secrets.choice(characters) for _ in range(64))
print(f"JWT_SECRET={jwt_secret}")
```

Linux/Mac:
```bash
# 使用 openssl
openssl rand -base64 48

# 或使用 /dev/urandom
tr -dc 'A-Za-z0-9!@#$%^&*()_+=-' < /dev/urandom | head -c 64
```

### 2. JWT_TOKEN_EXPIRE_DAYS（可选）

JWT token 的默认过期天数。

**配置位置：** `conf/.env`

**默认值：** 180（6个月）

**配置示例：**
```env
JWT_TOKEN_EXPIRE_DAYS=180
```

**根据业务场景设置：**
- **短期 token（1-7天）**: 适用于敏感操作、高安全性要求的场景
- **中期 token（30-90天）**: 适用于一般应用、平衡安全性和用户体验
- **长期 token（180-365天）**: 适用于低频使用的应用、用户体验优先

## 在代码中使用

### 读取配置

```python
from src.core.config import settings

# 获取 JWT 密钥
jwt_secret = settings.JWT_SECRET

# 获取过期天数
expire_days = settings.JWT_TOKEN_EXPIRE_DAYS
```

### 在中间件中使用

[src/middleware/token_verify.py](../src/middleware/token_verify.py) 已经自动使用配置：

```python
from src.core import settings

jwt_secret = settings.JWT_SECRET

class JWTBearer(HTTPBearer):
    def verify_jwt(self, jwtoken: str) -> dict:
        # 使用配置中的 JWT_SECRET
        data = decrypt_jwt_token(jwtoken, jwt_secret)
        # ...
```

### 生成 Token 时使用

```python
from src.core.config import settings
from src.core.jwt_handler import generate_jwt_token
import time

# 使用配置中的过期时间
expires_at = int(time.time()) + (settings.JWT_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)

token = generate_jwt_token(
    secret=settings.JWT_SECRET,
    user_id="user_123",
    expires_at=expires_at
)
```

## 配置文件结构

### conf/.env（实际配置）

```env
# JWT配置
JWT_SECRET=JLp?9O&02jFfsoE$23_xmp_auth_server_v1_2026
JWT_TOKEN_EXPIRE_DAYS=180
```

### conf/.env.example（示例模板）

```env
# JWT配置
JWT_SECRET=your_jwt_secret_key_at_least_32_characters_long
JWT_TOKEN_EXPIRE_DAYS=180
```

### src/core/config.py（配置类）

```python
class Settings(BaseSettings):
    # JWT配置
    JWT_SECRET: str = os.getenv('JWT_SECRET', 'default_jwt_secret_please_change_in_production')
    JWT_TOKEN_EXPIRE_DAYS: int = int(os.getenv('JWT_TOKEN_EXPIRE_DAYS', 180))
```

## 环境变量优先级

1. 环境变量（最高优先级）
   ```bash
   export JWT_SECRET="my_secret_key"
   python run.py
   ```

2. `.env` 文件
   ```env
   JWT_SECRET=my_secret_key
   ```

3. 代码默认值（最低优先级）
   ```python
   JWT_SECRET: str = os.getenv('JWT_SECRET', 'default_jwt_secret_please_change_in_production')
   ```

## 安全检查清单

部署前请检查：

- [ ] ✅ JWT_SECRET 已设置为强随机字符串（至少 32 字符）
- [ ] ✅ JWT_SECRET 与默认值不同
- [ ] ✅ JWT_SECRET 未提交到版本控制系统
- [ ] ✅ 生产环境和开发环境使用不同的 JWT_SECRET
- [ ] ✅ JWT_TOKEN_EXPIRE_DAYS 根据业务需求设置
- [ ] ✅ 所有使用 JWT 的代码都通过 `settings.JWT_SECRET` 获取密钥
- [ ] ✅ 日志中不会输出 JWT_SECRET

## 更换 JWT_SECRET

如果需要更换 JWT_SECRET（例如密钥泄露），请遵循以下步骤：

1. **生成新密钥**
   ```bash
   openssl rand -base64 48
   ```

2. **更新配置文件**
   ```env
   # 旧密钥
   # JWT_SECRET=old_secret_key

   # 新密钥
   JWT_SECRET=new_secret_key
   ```

3. **重启应用**
   ```bash
   # 重启服务
   systemctl restart xmp_auth_server
   ```

4. **用户影响**
   - ⚠️ 所有现有的 JWT token 将立即失效
   - ⚠️ 所有用户需要重新登录
   - ✅ 使用旧密钥生成的 token 无法通过验证

5. **平滑过渡方案（可选）**

   如果需要平滑过渡，可以临时支持双密钥：

   ```python
   # config.py
   JWT_SECRET: str = os.getenv('JWT_SECRET', 'new_secret')
   JWT_SECRET_OLD: str = os.getenv('JWT_SECRET_OLD', '')  # 旧密钥（可选）

   # token_verify.py
   def verify_jwt(self, jwtoken: str) -> dict:
       try:
           # 先尝试新密钥
           data = decrypt_jwt_token(jwtoken, settings.JWT_SECRET)
           return self._build_response(data, jwtoken)
       except JwtError:
           # 如果新密钥失败，尝试旧密钥
           if settings.JWT_SECRET_OLD:
               try:
                   data = decrypt_jwt_token(jwtoken, settings.JWT_SECRET_OLD)
                   # 返回数据，但建议客户端刷新 token
                   return self._build_response(data, jwtoken, should_refresh=True)
               except JwtError:
                   pass
           raise ValueError("Token validation failed")
   ```

## 常见问题

**Q: JWT_SECRET 泄露了怎么办？**
A: 立即更换新密钥，所有用户需要重新登录。参考"更换 JWT_SECRET"章节。

**Q: 可以在多个服务器上使用不同的 JWT_SECRET 吗？**
A: 不可以。同一个应用集群的所有服务器必须使用相同的 JWT_SECRET，否则 token 无法跨服务器验证。

**Q: JWT_TOKEN_EXPIRE_DAYS 设置为多少合适？**
A: 取决于业务场景：
- 高安全性应用：7-30天
- 一般应用：30-90天
- 低频使用应用：180-365天

**Q: 如何查看当前使用的 JWT_SECRET？**
A:
```python
from src.core.config import settings
print(f"JWT_SECRET length: {len(settings.JWT_SECRET)}")
# 注意：不要在日志中打印完整的密钥！
```

**Q: 修改配置后需要重启服务吗？**
A: 是的，配置在应用启动时加载，修改后需要重启服务才能生效。

## 相关文档

- [JWT Handler 使用文档](JWT_HANDLER_USAGE.md)
- [Token Verify 中间件迁移说明](TOKEN_VERIFY_MIGRATION.md)
- [JWT 快速参考](JWT_QUICK_REFERENCE.md)
