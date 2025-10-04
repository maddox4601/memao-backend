"""Change user id to UUID

Revision ID: 729ac03d2557
Revises: f9b8d5f71a00
Create Date: 2025-10-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision = '729ac03d2557'
down_revision = 'f9b8d5f71a00'
branch_labels = None
depends_on = None


def drop_fk_if_exists(table_name, fk_name):
    """如果外键存在，则删除"""
    bind = op.get_bind()
    insp = reflection.Inspector.from_engine(bind)
    fks = [fk['name'] for fk in insp.get_foreign_keys(table_name)]
    if fk_name in fks:
        op.drop_constraint(fk_name, table_name, type_="foreignkey")


def upgrade():
    # 动态删除外键，避免线上不存在时报错
    drop_fk_if_exists("user_accounts", "user_accounts_ibfk_1")
    drop_fk_if_exists("wallet_users", "wallet_users_ibfk_1")

    # 修改 users 表主键 id 为 UUID
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.Integer(),
            type_=sa.String(36),
            existing_nullable=False
        )

    # 修改 user_accounts 表外键 user_id 类型为 UUID
    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            type_=sa.String(36),
            existing_nullable=False
        )

    # 修改 wallet_users 表外键 user_id 类型为 UUID
    with op.batch_alter_table("wallet_users") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            type_=sa.String(36),
            existing_nullable=False
        )

    # 重新添加外键
    op.create_foreign_key(
        "user_accounts_ibfk_1",
        "user_accounts",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "wallet_users_ibfk_1",
        "wallet_users",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade():
    # 删除外键
    drop_fk_if_exists("user_accounts", "user_accounts_ibfk_1")
    drop_fk_if_exists("wallet_users", "wallet_users_ibfk_1")

    # 恢复列类型为整数
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.String(36),
            type_=sa.Integer(),
            existing_nullable=False
        )

    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.String(36),
            type_=sa.Integer(),
            existing_nullable=False
        )

    with op.batch_alter_table("wallet_users") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.String(36),
            type_=sa.Integer(),
            existing_nullable=False
        )

    # 恢复外键
    op.create_foreign_key(
        "user_accounts_ibfk_1",
        "user_accounts",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "wallet_users_ibfk_1",
        "wallet_users",
        "users",
        ["user_id"],
        ["id"],
    )
