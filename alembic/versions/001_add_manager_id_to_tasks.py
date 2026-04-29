"""add manager_id to tasks

Revision ID: 001_add_manager_id
Revises: 
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_manager_id'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tasks', sa.Column('manager_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_tasks_manager_id', 'tasks', 'users', ['manager_id'], ['id'], ondelete='SET NULL')
    op.create_index('idx_tasks_manager_id', 'tasks', ['manager_id'])


def downgrade():
    op.drop_index('idx_tasks_manager_id', table_name='tasks')
    op.drop_constraint('fk_tasks_manager_id', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'manager_id')
