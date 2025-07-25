"""update memaoadmin status

Revision ID: e39fdc6e62c0
Revises: 402be89df705
Create Date: 2025-07-26 16:31:16.804975

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e39fdc6e62c0'
down_revision = '402be89df705'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_column('status')

    # ### end Alembic commands ###
