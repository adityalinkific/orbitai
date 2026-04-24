-- Migration: Add manager_id and created_by to projects table
-- Date: 2026-04-24
-- Description: Add manager_id and created_by columns for project ownership tracking

ALTER TABLE projects ADD COLUMN manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE projects ADD COLUMN created_by INTEGER REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX idx_projects_manager_id ON projects(manager_id);
CREATE INDEX idx_projects_created_by ON projects(created_by);
