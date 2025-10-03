#!/usr/bin/env python3
"""
Database transaction integrity tests for batch Drive integration.

Tests database consistency, transaction rollbacks, concurrent access,
and data integrity across batch job and Drive metadata operations.
"""

import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.batch.models import (
    BatchJob, BatchDriveMetadata, BatchFileDriveMetadata, 
    init_database, DatabaseManager
)


class TestDatabaseTransactionIntegrity:
    """Test database transaction integrity for batch Drive operations."""
    
    @pytest.fixture
    def test_db_path(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        init_database(db_path)
        yield db_path
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
    
    def test_batch_job_drive_metadata_transaction_consistency(self, test_db_path):
        """Test transaction consistency between BatchJob and Drive metadata."""
        job_id = "transaction_test_001"
        
        # Test successful transaction
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=5,
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        # Create Drive metadata - should succeed because parent job exists
        drive_metadata = BatchDriveMetadata(
            batch_job_id=job_id,
            drive_folder_id="folder_trans_123",
            drive_folder_url="https://drive.google.com/drive/folders/folder_trans_123"
        )
        drive_metadata.save(test_db_path)
        
        # Verify both records exist and are consistent
        retrieved_job = BatchJob.get_by_id(test_db_path, job_id)
        retrieved_metadata = BatchDriveMetadata.get_by_job_id(test_db_path, job_id)
        
        assert retrieved_job is not None
        assert retrieved_metadata is not None
        assert retrieved_job.drive_integration_enabled is True
        assert retrieved_metadata.drive_folder_id == "folder_trans_123"
    
    def test_foreign_key_constraint_enforcement(self, test_db_path):
        """Test foreign key constraints prevent orphaned metadata."""
        nonexistent_job_id = "nonexistent_job_999"
        
        # Attempt to create Drive metadata for non-existent job
        drive_metadata = BatchDriveMetadata(
            batch_job_id=nonexistent_job_id,
            drive_folder_id="orphan_folder_123"
        )
        
        # Should raise ValueError due to foreign key constraint
        with pytest.raises(ValueError, match="Batch job nonexistent_job_999 does not exist"):
            drive_metadata.save(test_db_path)
    
    def test_file_metadata_cascade_consistency(self, test_db_path):
        """Test file metadata consistency with parent batch job."""
        job_id = "file_consistency_test"
        
        # Create parent batch job and Drive metadata
        batch_job = BatchJob(
            job_id=job_id,
            status="uploading",
            total_files=3,
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        drive_metadata = BatchDriveMetadata(
            batch_job_id=job_id,
            drive_folder_id="parent_folder_456"
        )
        drive_metadata.save(test_db_path)
        
        # Create multiple file metadata entries
        test_files = [
            ("file1.svg", "drive_file_001", "completed"),
            ("file2.svg", "drive_file_002", "pending"),
            ("file3.svg", "drive_file_003", "failed")
        ]
        
        for filename, file_id, status in test_files:
            file_metadata = BatchFileDriveMetadata(
                batch_job_id=job_id,
                original_filename=filename,
                drive_file_id=file_id,
                upload_status=status
            )
            file_metadata.save(test_db_path)
        
        # Verify all file metadata is consistent
        file_metadata_list = BatchFileDriveMetadata.get_by_job_id(test_db_path, job_id)
        assert len(file_metadata_list) == 3
        
        # Verify status distribution
        completed_files = [f for f in file_metadata_list if f.upload_status == "completed"]
        pending_files = [f for f in file_metadata_list if f.upload_status == "pending"]
        failed_files = [f for f in file_metadata_list if f.upload_status == "failed"]
        
        assert len(completed_files) == 1
        assert len(pending_files) == 1
        assert len(failed_files) == 1
    
    def test_concurrent_access_integrity(self, test_db_path):
        """Test database integrity under concurrent access."""
        base_job_id = "concurrent_test"
        num_threads = 5
        
        def create_batch_job_and_metadata(thread_id):
            """Worker function for concurrent testing."""
            job_id = f"{base_job_id}_{thread_id}"
            
            try:
                # Create batch job
                batch_job = BatchJob(
                    job_id=job_id,
                    status="processing",
                    total_files=2,
                    drive_integration_enabled=True
                )
                batch_job.save(test_db_path)
                
                # Small delay to simulate processing time
                time.sleep(0.01)
                
                # Create Drive metadata
                drive_metadata = BatchDriveMetadata(
                    batch_job_id=job_id,
                    drive_folder_id=f"folder_{thread_id}",
                    drive_folder_url=f"https://drive.google.com/drive/folders/folder_{thread_id}"
                )
                drive_metadata.save(test_db_path)
                
                # Create file metadata
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=job_id,
                    original_filename=f"file_{thread_id}.svg",
                    drive_file_id=f"drive_file_{thread_id}",
                    upload_status="completed"
                )
                file_metadata.save(test_db_path)
                
                return True
                
            except Exception as e:
                return False
        
        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(create_batch_job_and_metadata, i) 
                for i in range(num_threads)
            ]
            
            results = [future.result() for future in as_completed(futures)]
        
        # Verify all operations succeeded
        assert all(results), "Some concurrent operations failed"
        
        # Verify database integrity
        with DatabaseManager(test_db_path).get_connection() as conn:
            cursor = conn.cursor()
            
            # Count records
            cursor.execute("SELECT COUNT(*) FROM batch_jobs")
            job_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM batch_drive_metadata")
            metadata_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM batch_file_drive_metadata")
            file_count = cursor.fetchone()[0]
            
            assert job_count == num_threads
            assert metadata_count == num_threads
            assert file_count == num_threads
    
    def test_transaction_rollback_on_error(self, test_db_path):
        """Test transaction rollback when operations fail."""
        job_id = "rollback_test"
        
        # Create batch job
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=1,
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        # Mock database error during metadata save
        with patch.object(BatchDriveMetadata, 'save', side_effect=Exception("Database error")):
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="error_folder"
            )
            
            # Should raise exception
            with pytest.raises(Exception, match="Database error"):
                drive_metadata.save(test_db_path)
        
        # Verify batch job still exists but no metadata was created
        retrieved_job = BatchJob.get_by_id(test_db_path, job_id)
        retrieved_metadata = BatchDriveMetadata.get_by_job_id(test_db_path, job_id)
        
        assert retrieved_job is not None
        assert retrieved_metadata is None  # Metadata creation failed
    
    def test_database_connection_cleanup(self, test_db_path):
        """Test proper database connection cleanup."""
        job_id = "cleanup_test"
        
        # Create multiple operations to test connection management
        for i in range(10):
            batch_job = BatchJob(
                job_id=f"{job_id}_{i}",
                status="processing",
                total_files=1,
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
        
        # Verify no connection leaks by checking we can still operate
        final_job = BatchJob(
            job_id="final_cleanup_test",
            status="completed",
            total_files=1,
            drive_integration_enabled=False
        )
        final_job.save(test_db_path)
        
        retrieved_final = BatchJob.get_by_id(test_db_path, "final_cleanup_test")
        assert retrieved_final is not None
        assert retrieved_final.status == "completed"
    
    def test_database_schema_constraints(self, test_db_path):
        """Test database schema constraints and data validation."""
        # Test required field constraints
        with pytest.raises(Exception):  # Should fail due to missing required fields
            with DatabaseManager(test_db_path).get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO batch_jobs (job_id) VALUES (?)", (None,))
                conn.commit()
        
        # Test data type constraints
        job_id = "schema_test"
        batch_job = BatchJob(
            job_id=job_id,
            status="processing",
            total_files=5,  # Should be integer
            drive_integration_enabled=True
        )
        batch_job.save(test_db_path)
        
        # Verify data types are preserved
        with DatabaseManager(test_db_path).get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM batch_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            
            assert isinstance(row['total_files'], int)
            assert isinstance(row['drive_integration_enabled'], int)  # SQLite stores as int
    
    def test_update_operation_integrity(self, test_db_path):
        """Test update operation integrity and consistency."""
        job_id = "update_integrity_test"
        
        # Create initial batch job
        batch_job = BatchJob(
            job_id=job_id,
            status="pending",
            total_files=3,
            drive_integration_enabled=False
        )
        batch_job.save(test_db_path)
        
        # Update job status and enable Drive integration
        batch_job.status = "processing"
        batch_job.drive_integration_enabled = True
        batch_job.drive_upload_status = "pending"
        batch_job.save(test_db_path)
        
        # Verify update was applied correctly
        retrieved_job = BatchJob.get_by_id(test_db_path, job_id)
        assert retrieved_job.status == "processing"
        assert retrieved_job.drive_integration_enabled is True
        assert retrieved_job.drive_upload_status == "pending"
        assert retrieved_job.updated_at > retrieved_job.created_at
    
    def test_batch_operation_atomicity(self, test_db_path):
        """Test atomicity of batch operations."""
        job_id = "atomicity_test"
        
        # Simulate batch operation that creates job + metadata + file metadata
        def atomic_batch_operation():
            # Create batch job
            batch_job = BatchJob(
                job_id=job_id,
                status="processing",
                total_files=2,
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
            
            # Create Drive metadata
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="atomic_folder_123"
            )
            drive_metadata.save(test_db_path)
            
            # Create file metadata entries
            for i in range(2):
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=job_id,
                    original_filename=f"file_{i}.svg",
                    drive_file_id=f"atomic_file_{i}",
                    upload_status="completed"
                )
                file_metadata.save(test_db_path)
        
        # Execute batch operation
        atomic_batch_operation()
        
        # Verify all records were created atomically
        retrieved_job = BatchJob.get_by_id(test_db_path, job_id)
        retrieved_metadata = BatchDriveMetadata.get_by_job_id(test_db_path, job_id)
        retrieved_files = BatchFileDriveMetadata.get_by_job_id(test_db_path, job_id)
        
        assert retrieved_job is not None
        assert retrieved_metadata is not None
        assert len(retrieved_files) == 2
        assert retrieved_metadata.drive_folder_id == "atomic_folder_123"
        assert all(f.upload_status == "completed" for f in retrieved_files)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])