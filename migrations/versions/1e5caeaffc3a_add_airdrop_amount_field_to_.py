"""Add airdrop_amount field to AirdropConfig

Revision ID: 1e5caeaffc3a
Revises: aa3ce7791cdf
Create Date: 2025-06-22 16:19:49.442637

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1e5caeaffc3a'
down_revision = 'aa3ce7791cdf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('airdrop_config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('airdrop_amount', sa.BigInteger(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('airdrop_config', schema=None) as batch_op:
        batch_op.drop_column('airdrop_amount')

    # ### end Alembic commands ###
