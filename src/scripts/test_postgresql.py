#!/usr/bin/env python
"""
PostgreSQL 连接测试脚本
"""
import sys
import os
from urllib import parse


# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_postgresql_connection():
    """测试 PostgreSQL 连接"""
    print("=" * 60)
    print("PostgreSQL 连接测试")
    print("=" * 60)

    try:
        from src.core import settings

        print("\n1. 加载配置...")
        print(f"   数据库主机: {settings.DB_HOST}")
        print(f"   数据库端口: {settings.DB_PORT}")
        print(f"   数据库用户: {settings.DB_USER}")
        print(f"   数据库名称: {settings.DB_NAME}")
        print(f"   连接URL: {settings.DATABASE_URL}")

        print("\n2. 测试数据库连接...")
        from src.sql import check_db_connection

        if check_db_connection():
            print("   ✅ PostgreSQL 连接成功!")
        else:
            print("   ❌ PostgreSQL 连接失败!")
            return False

        print("\n3. 测试创建引擎...")
        from src.sql import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"   ✅ PostgreSQL 版本: {version[:50]}...")

        print("\n4. 测试查询表...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]

            if tables:
                print(f"   ✅ 找到 {len(tables)} 张表:")
                for table in tables:
                    print(f"      - {table}")
            else:
                print("   ⚠️  数据库中还没有表,请运行 schema.sql")
                print("\n   运行命令:")
                print("   psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster -f conf/schema.sql")

        print("\n5. 测试 SQLAlchemy ORM...")
        from src.sql import SessionLocal
        from src.sql import GoogleAdAccount

        db = SessionLocal()
        try:
            count = db.query(GoogleAdAccount).count()
            print(f"   ✅ ORM 查询成功,账户数量: {count}")
        except Exception as e:
            print(f"   ⚠️  ORM 查询失败: {str(e)}")
            print("   可能需要先创建表")
        finally:
            db.close()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
        return True

    except ImportError as e:
        print(f"\n❌ 导入错误: {str(e)}")
        print("\n请先安装依赖:")
        print("pip install -r requirements.txt")
        return False

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        print("\n可能的原因:")
        print("1. 数据库连接配置不正确")
        print("2. 网络无法连接到数据库服务器")
        print("3. 数据库用户权限不足")
        print("4. PostgreSQL 服务未启动")
        return False


def init_database_tables():
    """初始化数据库表"""
    print("\n是否要自动创建数据库表? (y/n): ", end="")
    choice = input().strip().lower()

    if choice == 'y':
        print("\n创建数据库表...")
        try:
            from src.sql import init_db
            init_db()
            print("✅ 数据库表创建成功!")
            return True
        except Exception as e:
            print(f"❌ 创建表失败: {str(e)}")
            print("\n请手动执行 SQL 文件:")
            print("psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster -f conf/schema.sql")
            return False
    else:
        print("\n跳过表创建。如需手动创建,请运行:")
        print("psql -h db.office.pg.domob-inc.cn -p 5433 -U socialbooster -d socialbooster -f conf/schema.sql")
        return False


if __name__ == "__main__":
    success = test_postgresql_connection()

    if success:
        print("\n提示: 如果表不存在,可以运行此脚本自动创建")
        init_database_tables()

    sys.exit(0 if success else 1)
