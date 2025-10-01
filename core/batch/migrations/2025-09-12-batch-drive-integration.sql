-- Migration: Add Google Drive integration to batch processing
-- Version: 2025-09-12-batch-drive-integration
-- Description: Create tables and indexes for Google Drive integration in batch processing

BEGIN TRANSACTION;

-- Create batch-level Drive metadata table
CREATE TABLE IF NOT EXISTS batch_drive_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_job_id VARCHAR(255) NOT NULL,
    drive_folder_id VARCHAR(255),
    drive_folder_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(job_id)
);

-- Create file-level Drive metadata table  
CREATE TABLE IF NOT EXISTS batch_file_drive_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_job_id VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    drive_file_id VARCHAR(255),
    drive_file_url VARCHAR(500),
    preview_url VARCHAR(500),
    upload_status VARCHAR(50) DEFAULT 'pending',
    upload_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(job_id)
);

-- Create batch_jobs table if it doesn't exist (for fresh installs)
CREATE TABLE IF NOT EXISTS batch_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL,
    total_files INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add Drive integration columns to existing batch_jobs table
-- Use ALTER TABLE ADD COLUMN which is safe for existing data
ALTER TABLE batch_jobs ADD COLUMN drive_integration_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE batch_jobs ADD COLUMN drive_upload_status VARCHAR(50) DEFAULT 'not_requested';
ALTER TABLE batch_jobs ADD COLUMN drive_folder_pattern VARCHAR(255);

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_batch_drive_metadata_job_id ON batch_drive_metadata(batch_job_id);
CREATE INDEX IF NOT EXISTS idx_batch_file_drive_metadata_job_id ON batch_file_drive_metadata(batch_job_id);
CREATE INDEX IF NOT EXISTS idx_batch_file_drive_metadata_status ON batch_file_drive_metadata(upload_status);

-- Create index on batch_jobs for Drive-enabled queries
CREATE INDEX IF NOT EXISTS idx_batch_jobs_drive_enabled ON batch_jobs(drive_integration_enabled);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_drive_status ON batch_jobs(drive_upload_status);

COMMIT;