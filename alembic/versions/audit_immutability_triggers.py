"""audit immutability triggers

Revision ID: audit_immutability
Revises: 
Create Date: 2026-04-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'audit_immutability'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create trigger function to prevent UPDATE on audit_logs
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_update()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit logs are immutable. UPDATE operation is not allowed.';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger to prevent UPDATE on audit_logs
    op.execute("""
        CREATE TRIGGER trigger_prevent_audit_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_update();
    """)
    
    # Create trigger function to prevent DELETE on audit_logs
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit logs are immutable. DELETE operation is not allowed.';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger to prevent DELETE on audit_logs
    op.execute("""
        CREATE TRIGGER trigger_prevent_audit_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_delete();
    """)
    
    # Add comment to audit_logs table
    op.execute("""
        COMMENT ON TABLE audit_logs IS 'Immutable audit trail. UPDATE and DELETE operations are blocked by triggers.';
    """)


def downgrade():
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_prevent_audit_delete ON audit_logs;")
    op.execute("DROP TRIGGER IF EXISTS trigger_prevent_audit_update ON audit_logs;")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_delete();")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_update();")
    
    # Remove comment
    op.execute("COMMENT ON TABLE audit_logs IS NULL;")
