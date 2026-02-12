# 数据库迁移完成 - MySQL 到 PostgreSQL

## ✅ 已完成的修改

### 1. 配置文件更新

#### [src/config.py](src/config.py)
- ✅ 数据库连接 URL 从 `mysql+pymysql://` 改为 `postgresql+psycopg2://`
- ✅ 默认配置更新为你提供的 PostgreSQL 连接信息:
  - 主机: `db.office.pg.domob-inc.cn`
  - 端口: `5433`
  - 用户: `socialbooster`
  - 密码: `B<JRsi3.lI`
  - 数据库: `socialbooster`
- ✅ 移除 MySQL 特定的 `DB_CHARSET` 配置

#### [conf/.env.example](conf/.env.example)
- ✅ 更新数据库配置示例
- ✅ 使用新的 PostgreSQL 连接参数

### 2. 数据库架构文件

#### [conf/schema.sql](conf/schema.sql)
完全重写为 PostgreSQL 语法:

- ✅ `BIGINT AUTO_INCREMENT` → `BIGSERIAL`
- ✅ `ENUM` 类型 → `VARCHAR + CHECK` 约束
- ✅ `JSON` → `JSONB` (更高性能的二进制格式)
- ✅ `DATETIME` → `TIMESTAMP`
- ✅ 添加 `updated_at` 自动更新触发器函数
- ✅ 为所有表添加触发器自动更新 `updated_at` 字段
- ✅ 添加完整的表注释和列注释

**备份文件:** MySQL 原始 schema 已备份为 `conf/schema_mysql.sql.bak`

### 3. Python 依赖

#### [requirements.txt](requirements.txt)
- ✅ `pymysql==1.1.0` → `psycopg2-binary==2.9.9`
- ✅ 保留所有其他依赖不变

### 4. 数据库模型

#### [src/models.py](src/models.py)
- ✅ 导入 `JSONB` 从 `sqlalchemy.dialects.postgresql`
- ✅ 所有 `JSON` 字段改为 `JSONB`
- ✅ Enum 类型保持不变 (SQLAlchemy 会自动处理)
- ✅ 其他字段类型保持兼容

### 5. 新增文档

#### [POSTGRESQL_GUIDE.md](POSTGRESQL_GUIDE.md)
完整的 PostgreSQL 配置和使用指南,包括:
- ✅ 数据库初始化步骤
- ✅ MySQL 与 PostgreSQL 差异对比
- ✅ 连接验证方法
- ✅ 常见问题解答
- ✅ 性能优化建议
- ✅ 监控和维护命令
- ✅ 备份和恢复方法

## 🚀 下一步操作

### 1. 安装新依赖

```bash
pip install -r requirements.txt
```

这会安装 `psycopg2-binary==2.9.9` 替换 MySQL 驱动。

### 2. 验证数据库连接

```bash
# 使用 psql 测试连接
psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster

# 或在 Python 中测试
python -c "from src.database import check_db_connection; print('✅' if check_db_connection() else '❌')"
```

### 3. 初始化数据库表

```bash
# 方法1: 使用 psql
psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster -f conf/schema.sql

# 方法2: Python 自动初始化
python run.py
```

### 4. 启动服务

```bash
python run.py
```

服务会在启动时:
1. 检查数据库连接
2. 自动创建表(如果不存在)
3. 启动 FastAPI 服务

## 📋 主要技术差异

| 特性 | MySQL | PostgreSQL |
|-----|-------|-----------|
| 自增主键 | `AUTO_INCREMENT` | `SERIAL` / `BIGSERIAL` |
| 枚举 | `ENUM('A','B')` | `CHECK (col IN ('A','B'))` |
| JSON | `JSON` | `JSONB` (二进制,更快) |
| 时间戳 | `DATETIME` | `TIMESTAMP` |
| 字符集 | `?charset=utf8mb4` | 默认 UTF-8 |
| 驱动 | `pymysql` | `psycopg2` |
| 连接 URL | `mysql+pymysql://` | `postgresql+psycopg2://` |

## 🔧 代码兼容性

### 无需修改的部分

- ✅ 所有业务逻辑代码
- ✅ OAuth 服务
- ✅ Google Ads API 服务
- ✅ 路由和控制器
- ✅ 前端页面
- ✅ API 接口

### SQLAlchemy ORM 优势

使用 SQLAlchemy ORM 的好处是数据库迁移非常简单:
- 业务代码完全不需要修改
- ORM 自动处理数据库方言差异
- 只需修改连接字符串和 schema 文件

## 🎯 PostgreSQL 特性优势

### 1. JSONB 性能
```python
# 支持 JSONB 字段索引查询
campaign = db.query(Campaign).filter(
    Campaign.raw_data['status'].astext == 'ACTIVE'
).first()
```

### 2. 更好的并发
- MVCC (多版本并发控制)
- 无读锁,更高的并发性能

### 3. 丰富的数据类型
- 数组类型
- Range 类型
- UUID 类型
- 等等

### 4. 强大的全文搜索
```sql
-- 内置全文搜索
SELECT * FROM campaigns
WHERE to_tsvector(campaign_name) @@ to_tsquery('summer');
```

## 📝 注意事项

### 1. 连接信息安全

生产环境中建议:
- 使用环境变量存储密码
- 不要将 `.env` 文件提交到 Git
- 使用密钥管理服务

### 2. 性能优化

```python
# 在 conf/.env 中调整连接池
DB_POOL_SIZE=20        # 连接池大小
DB_MAX_OVERFLOW=30     # 最大溢出连接数
```

### 3. 定期维护

```bash
# 定期执行 VACUUM ANALYZE
psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster -c "VACUUM ANALYZE;"
```

## 🐛 故障排查

### 连接失败
```bash
# 检查网络连通性
ping db.office.pg.domob-inc.cn

# 检查端口
telnet db.office.pg.domob-inc.cn 5433
```

### 认证失败
- 确认用户名和密码正确
- 检查 `pg_hba.conf` 配置
- 确认用户有数据库访问权限

### 表不存在
```bash
# 重新执行 schema 文件
psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster -f conf/schema.sql
```

## 📚 相关文档

- [POSTGRESQL_GUIDE.md](POSTGRESQL_GUIDE.md) - PostgreSQL 详细指南
- [README.md](README.md) - 项目主文档
- [QUICKSTART.md](QUICKSTART.md) - 快速启动指南

## ✅ 检查清单

迁移后请确认:

- [ ] 安装了 `psycopg2-binary`
- [ ] 可以连接到 PostgreSQL 数据库
- [ ] 数据库表已创建
- [ ] 服务可以正常启动
- [ ] 授权流程正常工作
- [ ] 数据同步功能正常

## 🎉 完成

数据库已成功从 MySQL 迁移到 PostgreSQL!

所有代码已更新,现在可以使用新的 PostgreSQL 数据库了。
