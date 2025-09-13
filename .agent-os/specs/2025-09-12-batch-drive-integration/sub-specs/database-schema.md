# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-09-12-batch-drive-integration/spec.md

> Created: 2025-09-12
> Version: 1.0.0

## Schema Changes

### New Table: batch_drive_metadata

```sql
CREATE TABLE batch_drive_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_job_id VARCHAR(255) NOT NULL,
    drive_folder_id VARCHAR(255),
    drive_folder_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(job_id)
);
```

### New Table: batch_file_drive_metadata

```sql
CREATE TABLE batch_file_drive_metadata (
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
```

### Modified Table: batch_jobs (Add Columns)

```sql
ALTER TABLE batch_jobs ADD COLUMN drive_integration_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE batch_jobs ADD COLUMN drive_upload_status VARCHAR(50) DEFAULT 'not_requested';
ALTER TABLE batch_jobs ADD COLUMN drive_folder_pattern VARCHAR(255);
```

## Indexes

```sql
CREATE INDEX idx_batch_drive_metadata_job_id ON batch_drive_metadata(batch_job_id);
CREATE INDEX idx_batch_file_drive_metadata_job_id ON batch_file_drive_metadata(batch_job_id);
CREATE INDEX idx_batch_file_drive_metadata_status ON batch_file_drive_metadata(upload_status);
```

## Migration Script

```sql
-- Migration: Add Google Drive integration to batch processing
-- Version: 2025-09-12-batch-drive-integration

BEGIN TRANSACTION;

-- Create batch-level Drive metadata table
CREATE TABLE batch_drive_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_job_id VARCHAR(255) NOT NULL,
    drive_folder_id VARCHAR(255),
    drive_folder_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create file-level Drive metadata table  
CREATE TABLE batch_file_drive_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_job_id VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    drive_file_id VARCHAR(255),
    drive_file_url VARCHAR(500),
    preview_url VARCHAR(500),
    upload_status VARCHAR(50) DEFAULT 'pending',
    upload_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add Drive integration columns to existing batch_jobs table
ALTER TABLE batch_jobs ADD COLUMN drive_integration_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE batch_jobs ADD COLUMN drive_upload_status VARCHAR(50) DEFAULT 'not_requested';
ALTER TABLE batch_jobs ADD COLUMN drive_folder_pattern VARCHAR(255);

-- Create performance indexes
CREATE INDEX idx_batch_drive_metadata_job_id ON batch_drive_metadata(batch_job_id);
CREATE INDEX idx_batch_file_drive_metadata_job_id ON batch_file_drive_metadata(batch_job_id);
CREATE INDEX idx_batch_file_drive_metadata_status ON batch_file_drive_metadata(upload_status);

COMMIT;
```

## Rationale

- **batch_drive_metadata** - Stores folder-level Google Drive information for each batch job, enabling efficient folder management and URL retrieval
- **batch_file_drive_metadata** - Tracks individual file uploads with status monitoring, error handling, and preview URL storage for comprehensive batch tracking
- **batch_jobs extensions** - Minimal additions to existing table to flag Drive integration and track overall upload status without disrupting current schema
- **Indexes** - Performance optimization for common queries (job lookups, status filtering) to maintain batch processing speed
- **Migration approach** - Additive schema changes preserve existing functionality while enabling new Drive integration features