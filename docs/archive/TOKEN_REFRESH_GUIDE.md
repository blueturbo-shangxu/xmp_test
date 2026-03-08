# Token 刷新脚本使用指南

## 概述

`refresh_tokens.py` 脚本用于自动刷新即将过期的 OAuth2 访问令牌 (Access Token)。

Google OAuth2 访问令牌默认有效期为 1 小时。本脚本使用 Refresh Token 自动获取新的 Access Token,无需用户重新授权。

## 功能特性

1. **自动刷新**: 检测即将过期的 token 并自动刷新
2. **提前刷新**: 可配置提前时间 (默认提前2小时)
3. **试运行模式**: 查看哪些 token 需要刷新,不实际执行
4. **无效 token 检查**: 识别需要重新授权的账户
5. **详细日志**: 记录所有刷新操作和结果
6. **多平台支持**: 支持 Google、Meta、TikTok 等多个平台

## 基本用法

### 手动刷新

```bash
# 刷新所有即将在2小时内过期的token (默认)
python refresh_tokens.py

# 刷新所有即将在6小时内过期的token
python refresh_tokens.py --hours 6

# 试运行模式 (只查看,不实际刷新)
python refresh_tokens.py --dry-run

# 检查所有无效的token
python refresh_tokens.py --check-invalid
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--hours N` | 提前N小时刷新token | 2 |
| `--dry-run` | 试运行模式,不实际刷新 | False |
| `--check-invalid` | 检查无效的token | False |

## 自动化执行

### 方式1: Cron (Linux/Mac)

编辑 crontab:

```bash
crontab -e
```

添加定时任务:

```bash
# 每小时执行一次token刷新
0 * * * * cd /path/to/xmp_server && /usr/bin/python3 refresh_tokens.py >> logs/cron_refresh.log 2>&1

# 每天检查一次无效token
0 9 * * * cd /path/to/xmp_server && /usr/bin/python3 refresh_tokens.py --check-invalid >> logs/cron_invalid.log 2>&1
```

### 方式2: Windows 任务计划程序

1. 打开"任务计划程序" (Task Scheduler)
2. 创建基本任务
3. 触发器: 每小时执行一次
4. 操作: 启动程序
   - 程序: `python.exe`
   - 参数: `refresh_tokens.py`
   - 起始于: `G:\work\xmp_server`

### 方式3: Systemd Timer (Linux)

创建服务文件 `/etc/systemd/system/token-refresh.service`:

```ini
[Unit]
Description=XMP Token Refresh Service

[Service]
Type=oneshot
WorkingDirectory=/path/to/xmp_server
ExecStart=/usr/bin/python3 refresh_tokens.py
User=your-user
```

创建定时器文件 `/etc/systemd/system/token-refresh.timer`:

```ini
[Unit]
Description=Run token refresh every hour

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h

[Install]
WantedBy=timers.target
```

启用定时器:

```bash
sudo systemctl daemon-reload
sudo systemctl enable token-refresh.timer
sudo systemctl start token-refresh.timer
sudo systemctl status token-refresh.timer
```

### 方式4: Docker + Cron

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  token-refresh:
    build: .
    command: cron -f
    volumes:
      - ./logs:/app/logs
      - ./conf:/app/conf
    environment:
      - TZ=Asia/Shanghai
```

创建 `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 添加cron任务
RUN echo "0 * * * * cd /app && python refresh_tokens.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/token-refresh
RUN chmod 0644 /etc/cron.d/token-refresh
RUN crontab /etc/cron.d/token-refresh

CMD ["cron", "-f"]
```

## 输出示例

### 正常刷新

```
============================================================
Token Refresh Task Started
Mode: PRODUCTION
Threshold: 2 hours before expiration
============================================================
Found 3 token(s) that need refreshing:
  - Platform: google, Account: 123-456-7890, Expires in: 1.5 hours, Refresh count: 5
  - Platform: google, Account: 987-654-3210, Expires in: 0.8 hours, Refresh count: 12
  - Platform: meta, Account: act_123456, Expires in: 1.2 hours, Refresh count: 3

Starting token refresh...
Refreshing token for platform=google, account_key=123-456-7890
Token refreshed successfully for google:123-456-7890 (refresh_count=6)
Refreshing token for platform=google, account_key=987-654-3210
Token refreshed successfully for google:987-654-3210 (refresh_count=13)
Refreshing token for platform=meta, account_key=act_123456
Token refreshed successfully for meta:act_123456 (refresh_count=4)
============================================================
Token Refresh Task Completed
Total: 3
Success: 3
Failed: 0
============================================================
```

### 试运行模式

```bash
python refresh_tokens.py --dry-run
```

```
============================================================
Token Refresh Task Started
Mode: DRY RUN
Threshold: 2 hours before expiration
============================================================
Found 2 token(s) that need refreshing:
  - Platform: google, Account: 123-456-7890, Expires in: 1.3 hours, Refresh count: 8
  - Platform: google, Account: 555-666-7777, Expires in: 0.5 hours, Refresh count: 2

DRY RUN MODE - No tokens will be refreshed
```

### 检查无效token

```bash
python refresh_tokens.py --check-invalid
```

```
Found 2 invalid token(s):
  - Platform: google, Account: 111-222-3333, Error: Refresh token无效或已被撤销,需要重新授权
  - Platform: meta, Account: act_999999, Error: invalid_grant

These accounts need re-authorization:
  - Re-authorize: http://localhost:8000/auth/authorize?customer_id=111-222-3333
```

## 日志文件

### 主日志文件

**位置**: `logs/token_refresh.log`

包含所有刷新操作的详细日志:
- 刷新开始/结束时间
- 成功/失败的token
- 错误信息
- 刷新统计

### 数据库授权日志

刷新操作也会记录到数据库的 `authorization_logs` 表:

```sql
SELECT
    platform,
    account_key,
    action_type,
    status,
    error_message,
    created_at
FROM authorization_logs
WHERE action_type = 'REFRESH'
ORDER BY created_at DESC
LIMIT 20;
```

## 监控和告警

### 检查刷新失败

```bash
# 查看最近的失败日志
grep "FAILED" logs/token_refresh.log | tail -20

# 统计最近24小时的失败次数
grep "FAILED" logs/token_refresh.log | grep "$(date +%Y-%m-%d)" | wc -l
```

### 邮件告警脚本

创建 `token_refresh_alert.sh`:

```bash
#!/bin/bash

LOG_FILE="logs/token_refresh.log"
LAST_RUN=$(tail -100 $LOG_FILE | grep "Token Refresh Task Completed" | tail -1)

if echo "$LAST_RUN" | grep -q "Failed: 0"; then
    echo "Token refresh completed successfully"
    exit 0
else
    FAILED_COUNT=$(echo "$LAST_RUN" | grep -oP 'Failed: \K\d+')
    echo "Token refresh failed for $FAILED_COUNT token(s)"

    # 发送告警邮件
    echo "Token refresh failed. Check logs at $LOG_FILE" | \
        mail -s "[ALERT] Token Refresh Failed" admin@example.com

    exit 1
fi
```

添加到 cron:

```bash
5 * * * * /path/to/token_refresh_alert.sh
```

### Prometheus 监控

创建 `token_metrics.py` 导出指标:

```python
from prometheus_client import Gauge, start_http_server
from src.database import SessionLocal
from src.models import OAuthToken
from datetime import datetime

# 定义指标
token_expiring_count = Gauge('oauth_tokens_expiring_2h', 'Tokens expiring in 2 hours')
token_invalid_count = Gauge('oauth_tokens_invalid', 'Invalid tokens')
token_valid_count = Gauge('oauth_tokens_valid', 'Valid tokens')

def collect_metrics():
    db = SessionLocal()
    try:
        # 即将过期的token数量
        expiring = db.query(OAuthToken).filter(
            OAuthToken.is_valid == True,
            OAuthToken.expires_at <= datetime.now() + timedelta(hours=2)
        ).count()
        token_expiring_count.set(expiring)

        # 无效token数量
        invalid = db.query(OAuthToken).filter(OAuthToken.is_valid == False).count()
        token_invalid_count.set(invalid)

        # 有效token数量
        valid = db.query(OAuthToken).filter(OAuthToken.is_valid == True).count()
        token_valid_count.set(valid)

    finally:
        db.close()

if __name__ == '__main__':
    start_http_server(8001)
    while True:
        collect_metrics()
        time.sleep(60)
```

## 故障排查

### 问题1: Refresh token 无效

**错误信息**: `Refresh token无效或已被撤销,需要重新授权`

**原因**:
- 用户手动撤销了授权
- Token超过6个月未使用
- 安全原因被Google撤销

**解决方案**:
1. 重新执行授权流程:
   ```
   http://localhost:8000/auth/authorize?customer_id=123-456-7890
   ```
2. 确保用户选择"允许"而不是"拒绝"

### 问题2: 刷新频率过高

**症状**: 频繁刷新,日志中大量刷新记录

**原因**:
- Token过期时间设置不正确
- 系统时间不同步

**解决方案**:
1. 检查服务器时间是否正确:
   ```bash
   date
   ntpdate -q pool.ntp.org
   ```
2. 调整刷新阈值:
   ```bash
   python refresh_tokens.py --hours 1  # 改为提前1小时刷新
   ```

### 问题3: 数据库连接失败

**错误信息**: `Database connection failed`

**解决方案**:
1. 检查数据库配置
2. 测试数据库连接:
   ```bash
   python test_postgresql.py
   ```
3. 检查网络连接

### 问题4: 加密密钥错误

**错误信息**: `Fernet key must be 32 url-safe base64-encoded bytes`

**解决方案**:
1. 重新生成加密密钥:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. 更新 `.env` 文件中的 `ENCRYPTION_KEY`
3. **注意**: 更改密钥后,所有现有token需要重新授权

## 最佳实践

1. **定期执行**: 建议每小时执行一次刷新任务
2. **监控告警**: 设置邮件或 Slack 告警,及时处理失败
3. **日志轮转**: 使用 logrotate 避免日志文件过大
4. **备份策略**: 定期备份数据库,尤其是 `oauth_tokens` 表
5. **安全审计**: 定期审查 `authorization_logs` 表,发现异常授权行为
6. **测试环境**: 先在测试环境验证脚本,再部署到生产环境

## 日志轮转配置

创建 `/etc/logrotate.d/xmp-token-refresh`:

```
/path/to/xmp_server/logs/token_refresh.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 user group
    postrotate
        /bin/kill -HUP `cat /var/run/syslogd.pid 2> /dev/null` 2> /dev/null || true
    endscript
}
```

## 性能优化

对于大量账户:

1. **批量处理**: 修改脚本支持并发刷新
2. **分批执行**: 将账户分组,分时段执行
3. **限流控制**: 避免触发 API 限流
4. **缓存策略**: 缓存有效的 token,减少数据库查询

## 总结

Token刷新脚本提供了完整的自动化token管理方案:

- ✅ 自动刷新即将过期的token
- ✅ 支持多平台 (Google, Meta, TikTok)
- ✅ 试运行模式
- ✅ 详细日志记录
- ✅ 错误处理和重试
- ✅ 无效token检测
- ✅ 定时任务支持

通过合理配置和监控,可以实现无人值守的 OAuth2 token 管理。
