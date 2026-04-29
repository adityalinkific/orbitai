"""fix task assignment fk cascade

Revision ID: 003_fix_task_assignment_fk_cascade
Revises: 002_add_manager_created_by
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_fix_task_assignment_fk_cascade'
down_revision = '002_add_manager_created_by'
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing foreign key constraints
    op.drop_constraint('task_assignments_task_id_fkey', 'task_assignments', type_='foreignkey')
    op.drop_constraint('task_assignments_user_id_fkey', 'task_assignments', type_='foreignkey')
    
    # Re-add with CASCADE behavior
    op.create_foreign_key(
        'task_assignments_task_id_fkey', 
        'task_assignments', 
        'tasks', 
        ['task_id'], 
        ['id'], 
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'task_assignments_user_id_fkey', 
        'task_assignments', 
        'users', 
        ['user_id'], 
        ['id'], 
        ondelete='CASCADE'
    )


def downgrade():
    # Drop CASCADE constraints
    op.drop_constraint('task_assignments_task_id_fkey', 'task_assignments', type_='foreignkey')
    op.drop_constraint('task_assignments_user_id_fkey', 'task_assignments', type_='foreignkey')
    
    # Re-add with SET NULL (original behavior)
    op.create_foreign_key(
        'task_assignments_task_id_fkey', 
        'task_assignments', 
        'tasks', 
        ['task_id'], 
        ['id'], 
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'task_assignments_user_id_fkey', 
        'task_assignments', 
        'users', 
        ['user_id'], 
        ['id'], 
        ondelete='SET NULL'
    )
