"""Add unique constraint

Revision ID: 8c8cccda3c31
Revises: 
Create Date: 2025-06-14 16:24:46.358635

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8c8cccda3c31'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('checkin_history', schema=None) as batch_op:
        batch_op.create_unique_constraint('uix_wallet_checkin_date', ['wallet_user_id', 'checkin_date'])

    with op.batch_alter_table('user_points_accounts', schema=None) as batch_op:
        batch_op.alter_column('total_points',
               existing_type=mysql.INTEGER(),
               nullable=False)
        batch_op.alter_column('consecutive_days',
               existing_type=mysql.INTEGER(),
               nullable=False)
        batch_op.alter_column('milestone_reached',
               existing_type=mysql.INTEGER(),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_points_accounts', schema=None) as batch_op:
        batch_op.alter_column('milestone_reached',
               existing_type=mysql.INTEGER(),
               nullable=True)
        batch_op.alter_column('consecutive_days',
               existing_type=mysql.INTEGER(),
               nullable=True)
        batch_op.alter_column('total_points',
               existing_type=mysql.INTEGER(),
               nullable=True)

    with op.batch_alter_table('checkin_history', schema=None) as batch_op:
        batch_op.drop_constraint('uix_wallet_checkin_date', type_='unique')

    # ### end Alembic commands ###
