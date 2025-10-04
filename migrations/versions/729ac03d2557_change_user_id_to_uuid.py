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
    # 已经手动完成迁移，无需执行任何操作
    pass


def downgrade():
    # 不支持回滚
    raise NotImplementedError("Downgrade is not supported.")
