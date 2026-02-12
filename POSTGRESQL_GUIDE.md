# PostgreSQL 数据库配置说明

## 数据库信息

项目已配置为使用 PostgreSQL 数据库:

```
主机: db.office.pg.domob-inc.cn
端口: 5433
用户: socialbooster
密码: B<JRsi3.lI
数据库: socialbooster
```

## 初始化数据库

### 方法1: 使用 psql 命令行

```bash
# 连接到数据库
psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster

# 执行 schema 文件
\i conf/schema.sql
```

### 方法2: 使用文件重定向

```bash
psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster -f conf/schema.sql
```

### 方法3: 在 Python 中自动初始化

项目启动时会自动创建表(如果不存在):

```python
python run.py
```

或者手动初始化:

```python
from src.database import init_db
init_db()
```

## 与 MySQL 的主要差异

### 1. 数据类型变化

| MySQL | PostgreSQL |
|-------|-----------|
| BIGINT AUTO_INCREMENT | BIGSERIAL |
| ENUM | VARCHAR + CHECK 约束 |
| JSON | JSONB (更高性能) |
| DATETIME | TIMESTAMP |

### 2. 自增主键

**MySQL:**
```sql
id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY
```

**PostgreSQL:**
```sql
id BIGSERIAL PRIMARY KEY
```

### 3. 枚举类型

**MySQL:**
```sql
status ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE'
```

**PostgreSQL:**
```sql
status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE'))
```

### 4. JSON 字段

**MySQL:**
```sql
data JSON
```

**PostgreSQL:**
```sql
data JSONB  -- 二进制格式,支持索引,性能更好
```

### 5. 更新时间戳触发器

PostgreSQL 使用触发器函数自动更新 `updated_at`:

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_accounts_updated_at
BEFORE UPDATE ON accounts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## 连接字符串格式

**MySQL:**
```
mysql+pymysql://user:password@host:port/database?charset=utf8mb4
```

**PostgreSQL:**
```
postgresql+psycopg2://user:password@host:port/database
```

## Python 依赖变化

**MySQL:**
```
pymysql==1.1.0
```

**PostgreSQL:**
```
psycopg2-binary==2.9.9
```

## 验证数据库连接

```python
from src.database import check_db_connection

if check_db_connection():
    print("✅ PostgreSQL 连接成功")
else:
    print("❌ PostgreSQL 连接失败")
```

或使用命令行:

```bash
psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster -c "SELECT version();"
```

## 常见问题

### Q1: 连接被拒绝

**A:** 检查:
1. 服务器地址和端口是否正确
2. 防火墙是否允许连接
3. PostgreSQL 是否允许远程连接
4. `pg_hba.conf` 配置是否正确

### Q2: 密码认证失败

**A:** 确认密码正确,注意特殊字符需要转义

### Q3: 数据库不存在

**A:** 确认数据库 `socialbooster` 已创建:
```sql
CREATE DATABASE socialbooster;
```

### Q4: 权限不足

**A:** 确保用户有足够权限:
```sql
GRANT ALL PRIVILEGES ON DATABASE socialbooster TO socialbooster;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO socialbooster;
```

## PostgreSQL 特性优势

1. **JSONB 类型**: 二进制存储,支持索引,查询更快
2. **更好的并发控制**: MVCC 机制
3. **丰富的数据类型**: 支持数组、hstore、ltree 等
4. **强大的全文搜索**: 内置全文搜索功能
5. **扩展性**: 支持自定义函数和触发器
6. **标准兼容**: 更符合 SQL 标准

## 性能优化建议

### 1. 索引优化

```sql
-- JSONB 字段索引
CREATE INDEX idx_campaigns_raw_data_gin ON campaigns USING GIN (raw_data);

-- 部分索引
CREATE INDEX idx_active_accounts ON accounts(id) WHERE status = 'ACTIVE';
```

### 2. 查询优化

```sql
-- 使用 EXPLAIN ANALYZE 分析查询
EXPLAIN ANALYZE SELECT * FROM accounts WHERE status = 'ACTIVE';
```

### 3. 连接池配置

在 `conf/.env` 中调整:
```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

## 监控和维护

### 查看活动连接

```sql
SELECT * FROM pg_stat_activity WHERE datname = 'socialbooster';
```

### 查看表大小

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 清理和优化

```sql
-- 清理和分析表
VACUUM ANALYZE accounts;

-- 或清理所有表
VACUUM ANALYZE;
```

## 备份和恢复

### 备份

```bash
pg_dump -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster > backup.sql
```

### 恢复

```bash
psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster < backup.sql
```

## 相关文档

- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [psycopg2 文档](https://www.psycopg.org/docs/)
- [SQLAlchemy PostgreSQL 方言](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
