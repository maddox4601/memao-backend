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

    # --- 1. 确认 wallet_users.user_id_uuid 存在 ---
    inspector = sa.inspect(connection)
    columns = [c['name'] for c in inspector.get_columns('wallet_users')]
    if 'user_id_uuid' not in columns:
        raise RuntimeError("wallet_users.user_id_uuid column not found")

    # --- 2. 确认旧外键存在再删除 ---
    fk_constraints = [fk['name'] for fk in inspector.get_foreign_keys('wallet_users')]
    if 'wallet_users_ibfk_1' in fk_constraints:
        with op.batch_alter_table("wallet_users") as batch_op:
            batch_op.drop_constraint("wallet_users_ibfk_1", type_="foreignkey")

    # --- 3. 删除旧列 user_id ---
    if 'user_id' in columns:
        with op.batch_alter_table("wallet_users") as batch_op:
            batch_op.drop_column("user_id")

    # --- 4. 将 user_id_uuid 改名为 user_id 并设置 NOT NULL ---
    with op.batch_alter_table("wallet_users") as batch_op:
        batch_op.alter_column(
            'user_id_uuid',
            new_column_name='user_id',
            existing_type=sa.String(36),
            nullable=False
        )
        # --- 5. 创建新外键 ---
        batch_op.create_foreign_key(
            "wallet_users_ibfk_1",
            "users",
            ["user_id"],
            ["id"]
        )

def downgrade():
    raise NotImplementedError("Downgrade is not supported.")
