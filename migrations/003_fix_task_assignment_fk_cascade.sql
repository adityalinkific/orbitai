-- Migration: Fix TaskAssignment foreign key cascade behaviors
-- Date: 2026-04-24
-- Description: Update foreign key constraints to use CASCADE for proper cleanup

-- Drop existing foreign key constraints
ALTER TABLE task_assignments DROP CONSTRAINT IF EXISTS task_assignments_task_id_fkey;
ALTER TABLE task_assignments DROP CONSTRAINT IF EXISTS task_assignments_user_id_fkey;

-- Re-add with CASCADE behavior
ALTER TABLE task_assignments ADD CONSTRAINT task_assignments_task_id_fkey 
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;
ALTER TABLE task_assignments ADD CONSTRAINT task_assignments_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
