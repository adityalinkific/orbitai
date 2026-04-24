-- Migration: Add manager_id to tasks table
-- Date: 2026-04-24
-- Description: Add manager_id column for task ownership tracking

ALTER TABLE tasks ADD COLUMN manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX idx_tasks_manager_id ON tasks(manager_id);
