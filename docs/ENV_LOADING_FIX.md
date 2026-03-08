# .env 文件加载问题诊断和修复

## 🔍 问题诊断

### 发现的问题

**问题：** `.env` 文件未正确加载

**原因：** `BASE_DIR` 路径计算错误

## ❌ 错误的代码

**文件：** `src/core/config.py`

```python
# 错误的 BASE_DIR 计算
BASE_DIR = Path(__file__).resolve().parent.parent
```

**路径计算：**
```
__file__           = /path/to/project/src/core/config.py
.parent            = /path/to/project/src/core/
.parent.parent     = /path/to/project/src/        ← 错误！这不是项目根目录
```

**结果：**
```python
env_file = BASE_DIR / 'conf' / '.env'
# = /path/to/project/src/conf/.env  ← 错误路径！实际文件在 /path/to/project/conf/.env
```

## ✅ 修复后的代码

```python
# 正确的 BASE_DIR 计算
# __file__ = src/core/config.py
# .parent = src/core/
# .parent.parent = src/
# .parent.parent.parent = 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent
```

**路径计算：**
```
__file__                = /path/to/project/src/core/config.py
.parent                 = /path/to/project/src/core/
.parent.parent          = /path/to/project/src/
.parent.parent.parent   = /path/to/project/        ← 正确！项目根目录
```

**结果：**
```python
env_file = BASE_DIR / 'conf' / '.env'
# = /path/to/project/conf/.env  ← 正确路径！
```

## 📂 项目结构

```
xmp_server/                    ← BASE_DIR 应该指向这里
├── conf/
│   ├── .env                         ← .env 文件在这里
│   └── .env.example
├── src/
│   ├── core/
│   │   └── config.py                ← config.py 在这里
│   ├── api/
│   ├── middleware/
│   └── main.py
├── run.py
└── ...
```

## 🔧 修复步骤

### 1. 修改 config.py

**文件：** `src/core/config.py:13-17`

```python
# 修复前
BASE_DIR = Path(__file__).resolve().parent.parent

# 修复后
BASE_DIR = Path(__file__).resolve().parent.parent.parent
```

### 2. 验证修复

运行测试脚本：
```bash
python test_config_loading.py
```

**预期输出：**
```
============================================================
配置加载测试
============================================================

1. BASE_DIR 检查
------------------------------------------------------------
BASE_DIR: g:\work\xmp_server
BASE_DIR 类型: <class 'pathlib.WindowsPath'>
BASE_DIR 存在: True

2. .env 文件检查
------------------------------------------------------------
.env 文件路径: g:\work\xmp_server\conf\.env
.env 文件存在: True
.env 文件大小: 1541 字节

3. 配置值检查
------------------------------------------------------------
ENV: development
HOST: 0.0.0.0
PORT: 8007                           ← 应该是 8007，不是默认的 8000
DEBUG: True

DB_HOST: db.office.pg.domob-inc.cn
DB_PORT: 5433
DB_NAME: socialbooster

JWT_SECRET: ******************** (长度: 45)
JWT_TOKEN_EXPIRE_DAYS: 180

GOOGLE_CLIENT_ID: 623677055674-t3rnsb07qj4ofnip2hqbcvltstucbqhq...
GOOGLE_ADS_DEVELOPER_TOKEN: FtO2vhMLB4ynfuw_4qk37g
GOOGLE_ADS_API_VERSION: v22         ← 应该是 v22，不是默认的 v16

4. 关键配置验证
------------------------------------------------------------
✓ JWT_SECRET 配置正确 (长度: 45)
✓ PORT 配置正确: 8007
✓ GOOGLE_ADS_API_VERSION 配置正确: v22

============================================================
测试总结
============================================================
✓ 所有配置检查通过
✓ .env 文件已正确加载
```

## 🎯 验证要点

### 检查以下配置是否从 .env 加载

| 配置项 | 默认值 | .env 中的值 | 验证方法 |
|--------|--------|------------|---------|
| `PORT` | `8000` | `8007` | 如果显示 8007，说明加载成功 |
| `GOOGLE_ADS_API_VERSION` | `v16` | `v22` | 如果显示 v22，说明加载成功 |
| `JWT_SECRET` | `default_jwt_secret...` | `JLp?9O&02j...` | 长度应该是 45 |

### 如果仍然显示默认值

说明 `.env` 文件仍未正确加载，可能的原因：

1. **BASE_DIR 路径仍然错误**
   ```python
   # 检查 BASE_DIR
   from src.core.config import BASE_DIR
   print(BASE_DIR)
   # 应该输出: /path/to/xmp_server
   # 而不是: /path/to/xmp_server/src
   ```

2. **python-dotenv 未安装**
   ```bash
   pip install python-dotenv
   ```

3. **.env 文件格式错误**
   - 确保每行格式为 `KEY=VALUE`
   - 确保没有多余的空格或引号

4. **缓存问题**
   - 删除 `__pycache__` 目录
   - 重启 Python 解释器

## 🧪 手动测试

如果自动测试脚本有问题，可以手动测试：

```python
# test_manual.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path

# 1. 检查 BASE_DIR
config_file = Path('src/core/config.py').resolve()
print(f"config_file: {config_file}")

# 修复前的计算
BASE_DIR_OLD = config_file.parent.parent
print(f"BASE_DIR (old): {BASE_DIR_OLD}")
print(f".env file (old): {BASE_DIR_OLD / 'conf' / '.env'}")
print(f".env exists (old): {(BASE_DIR_OLD / 'conf' / '.env').exists()}")

# 修复后的计算
BASE_DIR_NEW = config_file.parent.parent.parent
print(f"\nBASE_DIR (new): {BASE_DIR_NEW}")
print(f".env file (new): {BASE_DIR_NEW / 'conf' / '.env'}")
print(f".env exists (new): {(BASE_DIR_NEW / 'conf' / '.env').exists()}")

# 2. 测试 dotenv 加载
from dotenv import load_dotenv
import os as os_module

env_file = BASE_DIR_NEW / 'conf' / '.env'
load_dotenv(env_file)

print(f"\nPORT from env: {os_module.getenv('PORT')}")
print(f"GOOGLE_ADS_API_VERSION from env: {os_module.getenv('GOOGLE_ADS_API_VERSION')}")
print(f"JWT_SECRET length: {len(os_module.getenv('JWT_SECRET', ''))}")
```

运行：
```bash
python test_manual.py
```

## 📝 相关文件

- ✅ [src/core/config.py:13](../src/core/config.py#L13) - BASE_DIR 计算已修复
- 📋 [conf/.env](../conf/.env) - 环境变量配置文件
- 🧪 [test_config_loading.py](../test_config_loading.py) - 配置加载测试脚本

## 🎉 总结

**问题：** `.env` 文件未正确加载
**原因：** `BASE_DIR` 计算少了一个 `.parent`
**修复：** 添加第三个 `.parent` 使 BASE_DIR 指向项目根目录
**验证：** 运行 `python test_config_loading.py` 检查配置是否正确加载

修复后，所有从 `.env` 读取的配置都应该生效！
