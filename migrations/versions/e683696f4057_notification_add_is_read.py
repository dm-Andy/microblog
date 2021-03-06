"""notification add is_read

Revision ID: e683696f4057
Revises: ede6381e341b
Create Date: 2019-01-15 23:09:11.644621

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e683696f4057'
down_revision = 'ede6381e341b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('notification', sa.Column('is_read', sa.Boolean(), nullable=True))
    op.create_index(op.f('ix_notification_is_read'), 'notification', ['is_read'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_notification_is_read'), table_name='notification')
    op.drop_column('notification', 'is_read')
    # ### end Alembic commands ###
