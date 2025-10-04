"""Change user id to UUID

Revision ID: 729ac03d2557
Revises: f9b8d5f71a00
Create Date: 2025-10-03 20:41:56.294093
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '729ac03d2557'
down_revision = 'f9b8d5f71a00'
branch_labels = None
depends_on = None


def upgrade():
    # 1. 删除 wallet_users 外键约束
    op.drop_constraint("wallet_users_ibfk_1", "wallet_users", type_="foreignkey")

    # 2. 修改 user_accounts.user_id
    with op.batch_alter_table('user_accounts', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=mysql.INTEGER(),
            type_=sa.String(length=36),
            existing_nullable=False
        )

    # 3. 修改 users.id
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'id',
            existing_type=mysql.INTEGER(),
            type_=sa.String(length=36),
            existing_nullable=False
        )

    # 4. 修改 wallet_users.user_id
    with op.batch_alter_table('wallet_users', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=mysql.INTEGER(),
            type_=sa.String(length=36),
            existing_nullable=True
        )

    # 5. 重新添加外键约束
    op.create_foreign_key(
        "wallet_users_ibfk_1",
        "wallet_users",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade():
    # 回滚：先删掉外键
    op.drop_constraint("wallet_users_ibfk_1", "wallet_users", type_="foreignkey")

    # 回滚 wallet_users.user_id
    with op.batch_alter_table('wallet_users', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=sa.String(length=36),
            type_=mysql.INTEGER(),
            existing_nullable=True
        )

    # 回滚 users.id
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'id',
            existing_type=sa.String(length=36),
            type_=mysql.INTEGER(),
            existing_nullable=False
        )

    # 回滚 user_accounts.user_id
    with op.batch_alter_table('user_accounts', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=sa.String(length=36),
            type_=mysql.INTEGER(),
            existing_nullable=False
        )

    # 恢复外键
    op.create_foreign_key(
        "wallet_users_ibfk_1",
        "wallet_users",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )
