"""add social account

Revision ID: d9752bfa5457
Revises: 328123afbe3a
Create Date: 2025-08-23 15:17:57.106950

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'd9752bfa5457'
down_revision = '328123afbe3a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('social_accounts', schema=None) as batch_op:
        # 安全删除外键（如果存在）
        try:
            batch_op.drop_constraint('social_accounts_ibfk_1', type_='foreignkey')
        except Exception:
            pass

        # 安全删除唯一索引（如果存在）
        try:
            batch_op.drop_constraint('uix_wallet_provider', type_='unique')
        except Exception:
            pass

        # 创建新的唯一约束
        batch_op.create_unique_constraint('uix_wallet_provider', ['wallet_address', 'provider'])

        # 删除旧的列
        try:
            batch_op.drop_column('wallet_user_id')
        except Exception:
            pass




def downgrade():
    with op.batch_alter_table('social_accounts', schema=None) as batch_op:
        # 先添加旧列
        batch_op.add_column(sa.Column('wallet_user_id', sa.Integer(), nullable=False))

        # 再创建旧外键
        batch_op.create_foreign_key('social_accounts_ibfk_1', 'wallet_users', ['wallet_user_id'], ['id'])

        # 删除新的唯一约束
        batch_op.drop_constraint('uix_wallet_provider', type_='unique')

        # 恢复旧唯一约束
        batch_op.create_unique_constraint('uix_wallet_provider', ['wallet_user_id', 'provider'])


