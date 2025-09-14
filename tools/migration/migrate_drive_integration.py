#!/usr/bin/env python3
"""
Database migration script for Google Drive integration in batch processing.

This script safely migrates existing batch processing databases to support
Google Drive integration by adding new tables and columns.
"""

import sqlite3
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from batch.models import DEFAULT_DB_PATH, create_tables

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Custom exception for migration errors."""
    pass


def check_table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    """Check if a table exists in the database."""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None


def check_column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns
    except sqlite3.Error:
        return False


def backup_database(db_path: str) -> str:
    """Create a backup of the database before migration."""
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Copy database file
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        raise MigrationError(f"Failed to create backup: {e}")


def migrate_database(db_path: str, create_backup: bool = True) -> bool:
    """
    Migrate database to support Google Drive integration.
    
    Args:
        db_path: Path to SQLite database file
        create_backup: Whether to create backup before migration
    
    Returns:
        bool: True if migration was successful
    """
    logger.info(f"Starting migration for database: {db_path}")
    
    # Ensure database file exists
    db_file = Path(db_path)
    if not db_file.exists():
        logger.info("Database doesn't exist, creating new database with Drive integration")
        create_tables(db_path)
        return True
    
    # Create backup if requested
    backup_path = None
    if create_backup:
        backup_path = backup_database(db_path)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            migration_steps = []
            
            # Step 1: Check and create batch_jobs table if it doesn't exist
            if not check_table_exists(cursor, 'batch_jobs'):
                migration_steps.append("Creating batch_jobs table")
                cursor.execute("""
                    CREATE TABLE batch_jobs (
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
            else:
                # Add new columns to existing batch_jobs table
                if not check_column_exists(cursor, 'batch_jobs', 'drive_integration_enabled'):
                    migration_steps.append("Adding drive_integration_enabled column")
                    cursor.execute("ALTER TABLE batch_jobs ADD COLUMN drive_integration_enabled BOOLEAN DEFAULT FALSE")
                
                if not check_column_exists(cursor, 'batch_jobs', 'drive_upload_status'):
                    migration_steps.append("Adding drive_upload_status column") 
                    cursor.execute("ALTER TABLE batch_jobs ADD COLUMN drive_upload_status VARCHAR(50) DEFAULT 'not_requested'")
                
                if not check_column_exists(cursor, 'batch_jobs', 'drive_folder_pattern'):
                    migration_steps.append("Adding drive_folder_pattern column")
                    cursor.execute("ALTER TABLE batch_jobs ADD COLUMN drive_folder_pattern VARCHAR(255)")
            
            # Step 2: Create batch_drive_metadata table
            if not check_table_exists(cursor, 'batch_drive_metadata'):
                migration_steps.append("Creating batch_drive_metadata table")
                cursor.execute("""
                    CREATE TABLE batch_drive_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        batch_job_id VARCHAR(255) NOT NULL,
                        drive_folder_id VARCHAR(255),
                        drive_folder_url VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(job_id)
                    )
                """)
            
            # Step 3: Create batch_file_drive_metadata table
            if not check_table_exists(cursor, 'batch_file_drive_metadata'):
                migration_steps.append("Creating batch_file_drive_metadata table")
                cursor.execute("""
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
                    )
                """)
            
            # Step 4: Create indexes
            indexes_to_create = [
                ("idx_batch_drive_metadata_job_id", "batch_drive_metadata", "batch_job_id"),
                ("idx_batch_file_drive_metadata_job_id", "batch_file_drive_metadata", "batch_job_id"),
                ("idx_batch_file_drive_metadata_status", "batch_file_drive_metadata", "upload_status"),
                ("idx_batch_jobs_drive_enabled", "batch_jobs", "drive_integration_enabled"),
                ("idx_batch_jobs_drive_status", "batch_jobs", "drive_upload_status")
            ]
            
            for index_name, table_name, column_name in indexes_to_create:
                # Check if index exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name=?
                """, (index_name,))
                
                if not cursor.fetchone():
                    migration_steps.append(f"Creating index {index_name}")
                    cursor.execute(f"CREATE INDEX {index_name} ON {table_name}({column_name})")
            
            # Commit all changes
            conn.commit()
            
            # Log migration summary
            if migration_steps:
                logger.info("Migration completed successfully with the following changes:")
                for step in migration_steps:
                    logger.info(f"  - {step}")
            else:
                logger.info("Database is already up to date, no migration needed")
            
            return True
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        
        # Restore backup if migration failed and backup exists
        if backup_path and Path(backup_path).exists():
            try:
                import shutil
                shutil.copy2(backup_path, db_path)
                logger.info(f"Database restored from backup: {backup_path}")
            except Exception as restore_error:
                logger.error(f"Failed to restore backup: {restore_error}")
        
        raise MigrationError(f"Database migration failed: {e}")


def verify_migration(db_path: str) -> bool:
    """
    Verify that migration was successful by checking all expected tables and columns exist.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        bool: True if all expected structures exist
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check required tables exist
            required_tables = ['batch_jobs', 'batch_drive_metadata', 'batch_file_drive_metadata']
            for table in required_tables:
                if not check_table_exists(cursor, table):
                    logger.error(f"Missing table: {table}")
                    return False
            
            # Check batch_jobs has Drive integration columns
            required_columns = ['drive_integration_enabled', 'drive_upload_status', 'drive_folder_pattern']
            for column in required_columns:
                if not check_column_exists(cursor, 'batch_jobs', column):
                    logger.error(f"Missing column in batch_jobs: {column}")
                    return False
            
            # Check indexes exist
            required_indexes = [
                'idx_batch_drive_metadata_job_id',
                'idx_batch_file_drive_metadata_job_id',
                'idx_batch_file_drive_metadata_status'
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            existing_indexes = [row[0] for row in cursor.fetchall()]
            
            for index in required_indexes:
                if index not in existing_indexes:
                    logger.warning(f"Missing index: {index} (performance may be affected)")
            
            logger.info("Migration verification passed")
            return True
            
    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        return False


def main():
    """Main migration script entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate batch processing database for Google Drive integration")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to database file")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backup")
    parser.add_argument("--verify-only", action="store_true", help="Only verify migration, don't perform it")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        if args.verify_only:
            logger.info(f"Verifying migration for database: {args.db_path}")
            if verify_migration(args.db_path):
                print("✅ Migration verification passed")
                sys.exit(0)
            else:
                print("❌ Migration verification failed")
                sys.exit(1)
        else:
            logger.info(f"Running migration for database: {args.db_path}")
            success = migrate_database(args.db_path, create_backup=not args.no_backup)
            
            if success:
                if verify_migration(args.db_path):
                    print("✅ Migration completed and verified successfully")
                    sys.exit(0)
                else:
                    print("⚠️  Migration completed but verification failed")
                    sys.exit(1)
            else:
                print("❌ Migration failed")
                sys.exit(1)
                
    except MigrationError as e:
        print(f"❌ Migration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()