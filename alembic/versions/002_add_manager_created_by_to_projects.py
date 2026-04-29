"""add manager_id and created_by to projects

Revision ID: 002_add_manager_created_by
Revises: 001_add_manager_id
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_manager_created_by'
down_revision = '001_add_manager_id'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('projects', sa.Column('manager_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_projects_manager_id', 'projects', 'users', ['manager_id'], ['id'], ondelete='SET NULL')
    op.create_index('idx_projects_manager_id', 'projects', ['manager_id'])
    
    op.add_column('projects', sa.Column('created_by', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_projects_created_by', 'projects', 'users', ['created_by'], ['id'], ondelete='SET NULL')
    op.create_index('idx_projects_created_by', 'projects', ['created_by'])


def downgrade():
    op.drop_index('idx_projects_created_by', table_name='projects')
    op.drop_constraint('fk_projects_created_by', 'projects', type_='foreignkey')
    op.drop_column('projects', 'created_by')
    
    op.drop_index('idx_projects_manager_id', table_name='projects')
    op.drop_constraint('fk_projects_manager_id', 'projects', type_='foreignkey')
    op.drop_column('projects', 'manager_id')
