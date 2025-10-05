#!/usr/bin/env python3
"""
Database models for Google Drive integration in batch processing.

Provides SQLite-based persistence for batch job tracking, Google Drive metadata,
and individual file processing status with comprehensive error handling.
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database connections and operations."""
    
    def __init__(self, db_path: str):
        """Initialize database manager with path to SQLite database."""
        self.db_path = db_path
        self.connection = None
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections with automatic cleanup."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like row access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()


class BatchJob:
    """Model for batch conversion jobs with Google Drive integration."""
    
    def __init__(self, job_id: str, status: str, total_files: int,
                 drive_integration_enabled: bool = False,
                 drive_upload_status: str = "not_requested",
                 drive_folder_pattern: str | None = None,
                 created_at: datetime | None = None,
                 updated_at: datetime | None = None):
        """Initialize BatchJob model."""
        self.job_id = job_id
        self.status = status
        self.total_files = total_files
        self.drive_integration_enabled = drive_integration_enabled
        self.drive_upload_status = drive_upload_status
        self.drive_folder_pattern = drive_folder_pattern
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def save(self, db_path: str):
        """Save or update batch job in database."""
        self.updated_at = datetime.utcnow()
        
        with DatabaseManager(db_path).get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if job exists
            cursor.execute("SELECT job_id FROM batch_jobs WHERE job_id = ?", (self.job_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                cursor.execute("""
                    UPDATE batch_jobs SET 
                        status = ?,
                        total_files = ?,
                        drive_integration_enabled = ?,
                        drive_upload_status = ?,
                        drive_folder_pattern = ?,
                        updated_at = ?
                    WHERE job_id = ?
                """, (
                    self.status,
                    self.total_files,
                    self.drive_integration_enabled,
                    self.drive_upload_status,
                    self.drive_folder_pattern,
                    self.updated_at.isoformat(),
                    self.job_id,
                ))
            else:
                cursor.execute("""
                    INSERT INTO batch_jobs (
                        job_id, status, total_files, drive_integration_enabled,
                        drive_upload_status, drive_folder_pattern, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.job_id,
                    self.status,
                    self.total_files,
                    self.drive_integration_enabled,
                    self.drive_upload_status,
                    self.drive_folder_pattern,
                    self.created_at.isoformat(),
                    self.updated_at.isoformat(),
                ))
            
            conn.commit()
            logger.debug(f"Saved batch job {self.job_id} with status {self.status}")
    
    @classmethod
    def get_by_id(cls, db_path: str, job_id: str) -> Optional['BatchJob']:
        """Retrieve batch job by ID."""
        with DatabaseManager(db_path).get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM batch_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return cls(
                job_id=row['job_id'],
                status=row['status'],
                total_files=row['total_files'],
                drive_integration_enabled=bool(row['drive_integration_enabled']),
                drive_upload_status=row['drive_upload_status'],
                drive_folder_pattern=row['drive_folder_pattern'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
            )


class BatchDriveMetadata:
    """Model for Google Drive folder metadata per batch job."""
    
    def __init__(self, batch_job_id: str, drive_folder_id: str | None = None,
                 drive_folder_url: str | None = None,
                 created_at: datetime | None = None,
                 updated_at: datetime | None = None):
        """Initialize BatchDriveMetadata model."""
        self.batch_job_id = batch_job_id
        self.drive_folder_id = drive_folder_id
        self.drive_folder_url = drive_folder_url
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def save(self, db_path: str):
        """Save or update Drive metadata in database."""
        # Verify parent batch job exists
        batch_job = BatchJob.get_by_id(db_path, self.batch_job_id)
        if not batch_job:
            raise ValueError(f"Batch job {self.batch_job_id} does not exist")
        
        self.updated_at = datetime.utcnow()
        
        with DatabaseManager(db_path).get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if metadata exists
            cursor.execute("SELECT id FROM batch_drive_metadata WHERE batch_job_id = ?", (self.batch_job_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                cursor.execute("""
                    UPDATE batch_drive_metadata SET
                        drive_folder_id = ?,
                        drive_folder_url = ?,
                        updated_at = ?
                    WHERE batch_job_id = ?
                """, (
                    self.drive_folder_id,
                    self.drive_folder_url,
                    self.updated_at.isoformat(),
                    self.batch_job_id,
                ))
            else:
                cursor.execute("""
                    INSERT INTO batch_drive_metadata (
                        batch_job_id, drive_folder_id, drive_folder_url, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    self.batch_job_id,
                    self.drive_folder_id,
                    self.drive_folder_url,
                    self.created_at.isoformat(),
                    self.updated_at.isoformat(),
                ))
            
            conn.commit()
            logger.debug(f"Saved Drive metadata for batch {self.batch_job_id}")
    
    @classmethod
    def get_by_job_id(cls, db_path: str, batch_job_id: str) -> Optional['BatchDriveMetadata']:
        """Retrieve Drive metadata by batch job ID."""
        with DatabaseManager(db_path).get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM batch_drive_metadata WHERE batch_job_id = ?", (batch_job_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return cls(
                batch_job_id=row['batch_job_id'],
                drive_folder_id=row['drive_folder_id'],
                drive_folder_url=row['drive_folder_url'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
            )


class BatchFileDriveMetadata:
    """Model for individual file Google Drive metadata within batch jobs."""
    
    def __init__(self, batch_job_id: str, original_filename: str,
                 drive_file_id: str | None = None,
                 drive_file_url: str | None = None,
                 preview_url: str | None = None,
                 upload_status: str = "pending",
                 upload_error: str | None = None,
                 created_at: datetime | None = None,
                 updated_at: datetime | None = None):
        """Initialize BatchFileDriveMetadata model."""
        self.batch_job_id = batch_job_id
        self.original_filename = original_filename
        self.drive_file_id = drive_file_id
        self.drive_file_url = drive_file_url
        self.preview_url = preview_url
        self.upload_status = upload_status
        self.upload_error = upload_error
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def save(self, db_path: str):
        """Save or update file Drive metadata in database."""
        # Verify parent batch job exists
        batch_job = BatchJob.get_by_id(db_path, self.batch_job_id)
        if not batch_job:
            raise ValueError(f"Batch job {self.batch_job_id} does not exist")
        
        self.updated_at = datetime.utcnow()
        
        with DatabaseManager(db_path).get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if file metadata exists
            cursor.execute("""
                SELECT id FROM batch_file_drive_metadata 
                WHERE batch_job_id = ? AND original_filename = ?
            """, (self.batch_job_id, self.original_filename))
            exists = cursor.fetchone() is not None
            
            if exists:
                cursor.execute("""
                    UPDATE batch_file_drive_metadata SET
                        drive_file_id = ?,
                        drive_file_url = ?,
                        preview_url = ?,
                        upload_status = ?,
                        upload_error = ?,
                        updated_at = ?
                    WHERE batch_job_id = ? AND original_filename = ?
                """, (
                    self.drive_file_id,
                    self.drive_file_url,
                    self.preview_url,
                    self.upload_status,
                    self.upload_error,
                    self.updated_at.isoformat(),
                    self.batch_job_id,
                    self.original_filename,
                ))
            else:
                cursor.execute("""
                    INSERT INTO batch_file_drive_metadata (
                        batch_job_id, original_filename, drive_file_id, drive_file_url,
                        preview_url, upload_status, upload_error, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.batch_job_id,
                    self.original_filename,
                    self.drive_file_id,
                    self.drive_file_url,
                    self.preview_url,
                    self.upload_status,
                    self.upload_error,
                    self.created_at.isoformat(),
                    self.updated_at.isoformat(),
                ))
            
            conn.commit()
            logger.debug(f"Saved file metadata for {self.original_filename} in batch {self.batch_job_id}")
    
    @classmethod
    def get_by_job_id(cls, db_path: str, batch_job_id: str) -> list['BatchFileDriveMetadata']:
        """Retrieve all file metadata for a batch job."""
        with DatabaseManager(db_path).get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM batch_file_drive_metadata 
                WHERE batch_job_id = ? 
                ORDER BY created_at ASC
            """, (batch_job_id,))
            rows = cursor.fetchall()
            
            return [
                cls(
                    batch_job_id=row['batch_job_id'],
                    original_filename=row['original_filename'],
                    drive_file_id=row['drive_file_id'],
                    drive_file_url=row['drive_file_url'],
                    preview_url=row['preview_url'],
                    upload_status=row['upload_status'],
                    upload_error=row['upload_error'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
                )
                for row in rows
            ]


def create_tables(db_path: str):
    """Create all necessary database tables with proper indexes."""
    with DatabaseManager(db_path).get_connection() as conn:
        cursor = conn.cursor()
        
        # Create batch_jobs table with Drive integration columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(255) NOT NULL UNIQUE,
                status VARCHAR(50) NOT NULL,
                total_files INTEGER NOT NULL,
                drive_integration_enabled BOOLEAN DEFAULT FALSE,
                drive_upload_status VARCHAR(50) DEFAULT 'not_requested',
                drive_folder_pattern VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create batch_drive_metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_drive_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_job_id VARCHAR(255) NOT NULL,
                drive_folder_id VARCHAR(255),
                drive_folder_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(job_id)
            )
        """)
        
        # Create batch_file_drive_metadata table
        cursor.execute("""
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
            )
        """)
        
        # Create performance indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_drive_metadata_job_id 
            ON batch_drive_metadata(batch_job_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_file_drive_metadata_job_id 
            ON batch_file_drive_metadata(batch_job_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_file_drive_metadata_status
            ON batch_file_drive_metadata(upload_status)
        """)

        # Create batch_file_storage table for file manager integration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_file_storage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_job_id VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                stored_path VARCHAR(500) NOT NULL,
                file_size INTEGER NOT NULL,
                storage_metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(job_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_file_storage_job_id
            ON batch_file_storage(batch_job_id)
        """)

        conn.commit()
        logger.info("Database tables and indexes created successfully")


def init_database(db_path: str) -> str:
    """Initialize database with all tables and indexes."""
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Create tables
    create_tables(db_path)
    
    logger.info(f"Database initialized at {db_path}")
    return db_path


def get_default_db_path() -> str:
    """Get default database path for batch processing."""
    return str(Path(__file__).parent.parent.parent / "data" / "batch_jobs.db")


# Default database instance
DEFAULT_DB_PATH = get_default_db_path()