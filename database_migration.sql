-- Time Management Feature Database Migration
-- Run this on your Railway PostgreSQL database

-- Add time management columns to existing todos table
ALTER TABLE todos ADD COLUMN IF NOT EXISTS start_time TIMESTAMP;
ALTER TABLE todos ADD COLUMN IF NOT EXISTS end_time TIMESTAMP;
ALTER TABLE todos ADD COLUMN IF NOT EXISTS due_date DATE;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_todos_due_date ON todos(due_date);
CREATE INDEX IF NOT EXISTS idx_todos_start_time ON todos(start_time);
CREATE INDEX IF NOT EXISTS idx_todos_overdue ON todos(due_date, done) WHERE due_date < CURRENT_DATE AND done = false;

-- Verify the migration
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'todos' 
ORDER BY ordinal_position; 