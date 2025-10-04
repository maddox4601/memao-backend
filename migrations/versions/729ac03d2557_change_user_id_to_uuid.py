"""Finalize UUID migration for wallet_users

Revision ID: fix_wallet_user_uuid
Revises: 729ac03d2557
Create Date: 2025-10-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'fix_wallet_user_uuid'
down_revision = '729ac03d2557'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    # 使用原生 SQL 执行，避免 alembic 批处理的开销
    inspector = sa.inspect(connection)
    columns = [c['name'] for c in inspector.get_columns('wallet_users')]

    # 1. 删除外键（如果存在）
    try:
        connection.execute(sa.text("ALTER TABLE wallet_users DROP FOREIGN KEY wallet_users_ibfk_1"))
        print("Dropped foreign key")
    except Exception as e:
        print(f"Foreign key may not exist: {e}")

    # 2. 删除旧列（如果存在）
    if 'user_id' in columns:
        try:
            connection.execute(sa.text("ALTER TABLE wallet_users DROP COLUMN user_id"))
            print("Dropped old user_id column")
        except Exception as e:
            print(f"Error dropping column: {e}")
            raise

    # 3. 重命名列
    if 'user_id_uuid' in columns:
        try:
            connection.execute(sa.text("ALTER TABLE wallet_users CHANGE user_id_uuid user_id VARCHAR(36) NOT NULL"))
            print("Renamed user_id_uuid to user_id")
        except Exception as e:
            print(f"Error renaming column: {e}")
            raise

    # 4. 创建新外键
    try:
        connection.execute(sa.text("""
            ALTER TABLE wallet_users 
            ADD CONSTRAINT wallet_users_ibfk_1 
            FOREIGN KEY (user_id) REFERENCES users(id)
        """))
        print("Created new foreign key")
    except Exception as e:
        print(f"Error creating foreign key: {e}")
        raise
