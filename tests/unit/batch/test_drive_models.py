#!/usr/bin/env python3
"""
Unit tests for Google Drive integration database models.

Tests the BatchDriveMetadata and BatchFileDriveMetadata models including
creation, relationships, and database operations.
"""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
import tempfile
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.batch.models import (
    DatabaseManager, BatchDriveMetadata, BatchFileDriveMetadata, BatchJob,
    init_database, create_tables
)


@pytest.mark.integration
class TestDatabaseManager:
    """Test the database manager and connection handling."""
    
    def test_database_manager_initialization(self):
        """Test DatabaseManager initialization with temporary database."""
        with tempfile.NamedTemporaryFile(suffix='.db') as tmp_db:
            db_manager = DatabaseManager(tmp_db.name)
            assert db_manager.db_path == tmp_db.name
            assert db_manager.connection is None
    
    def test_database_connection_context(self):
        """Test database connection context manager."""
        with tempfile.NamedTemporaryFile(suffix='.db') as tmp_db:
            db_manager = DatabaseManager(tmp_db.name)
            
            with db_manager.get_connection() as conn:
                assert isinstance(conn, sqlite3.Connection)
                # Test basic query
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1
    
    def test_database_initialization(self):
        """Test complete database initialization."""
        with tempfile.NamedTemporaryFile(suffix='.db') as tmp_db:
            init_database(tmp_db.name)
            
            # Verify tables were created
            conn = sqlite3.connect(tmp_db.name)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('batch_jobs', 'batch_drive_metadata', 'batch_file_drive_metadata')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'batch_jobs' in tables
            assert 'batch_drive_metadata' in tables  
            assert 'batch_file_drive_metadata' in tables
            
            conn.close()


@pytest.mark.integration
class TestBatchJob:
    """Test the BatchJob model."""
    
    def setup_method(self):
        """Set up test database for each test."""
        self.tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp_db.name
        self.tmp_db.close()
        init_database(self.db_path)
    
    def teardown_method(self):
        """Clean up test database."""
        Path(self.db_path).unlink(missing_ok=True)
    
    def test_batch_job_creation(self):
        """Test BatchJob model creation and storage."""
        batch_job = BatchJob(
            job_id="batch_test123",
            status="processing",
            total_files=5,
            drive_integration_enabled=True,
            drive_upload_status="pending",
            drive_folder_pattern="SVG2PPTX-Batches/{date}/batch-{job_id}/"
        )
        
        batch_job.save(self.db_path)
        
        # Verify job was saved
        loaded_job = BatchJob.get_by_id(self.db_path, "batch_test123")
        assert loaded_job is not None
        assert loaded_job.job_id == "batch_test123"
        assert loaded_job.status == "processing"
        assert loaded_job.total_files == 5
        assert loaded_job.drive_integration_enabled is True
        assert loaded_job.drive_upload_status == "pending"
    
    def test_batch_job_update(self):
        """Test BatchJob status updates."""
        batch_job = BatchJob(
            job_id="batch_update123",
            status="processing",
            total_files=3,
            drive_integration_enabled=True
        )
        batch_job.save(self.db_path)
        
        # Update status
        batch_job.status = "completed"
        batch_job.drive_upload_status = "completed"
        batch_job.save(self.db_path)
        
        # Verify update
        loaded_job = BatchJob.get_by_id(self.db_path, "batch_update123")
        assert loaded_job.status == "completed"
        assert loaded_job.drive_upload_status == "completed"


@pytest.mark.integration
class TestBatchDriveMetadata:
    """Test the BatchDriveMetadata model."""
    
    def setup_method(self):
        """Set up test database for each test."""
        self.tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp_db.name
        self.tmp_db.close()
        init_database(self.db_path)
        
        # Create parent batch job
        self.batch_job = BatchJob(
            job_id="batch_drive_test",
            status="processing",
            total_files=2,
            drive_integration_enabled=True
        )
        self.batch_job.save(self.db_path)
    
    def teardown_method(self):
        """Clean up test database."""
        Path(self.db_path).unlink(missing_ok=True)
    
    def test_drive_metadata_creation(self):
        """Test BatchDriveMetadata creation and storage."""
        drive_metadata = BatchDriveMetadata(
            batch_job_id="batch_drive_test",
            drive_folder_id="1A2B3C4D5E6F",
            drive_folder_url="https://drive.google.com/drive/folders/1A2B3C4D5E6F"
        )
        
        drive_metadata.save(self.db_path)
        
        # Verify metadata was saved
        loaded_metadata = BatchDriveMetadata.get_by_job_id(self.db_path, "batch_drive_test")
        assert loaded_metadata is not None
        assert loaded_metadata.batch_job_id == "batch_drive_test"
        assert loaded_metadata.drive_folder_id == "1A2B3C4D5E6F"
        assert loaded_metadata.drive_folder_url.startswith("https://drive.google.com")
        assert loaded_metadata.created_at is not None
    
    def test_drive_metadata_foreign_key_relationship(self):
        """Test foreign key relationship with BatchJob."""
        # Try to create metadata for non-existent job
        invalid_metadata = BatchDriveMetadata(
            batch_job_id="nonexistent_job",
            drive_folder_id="1INVALID",
            drive_folder_url="https://drive.google.com/drive/folders/1INVALID"
        )
        
        # This should not raise an error in SQLite without FK constraints
        # but we'll test the relationship logic in the model
        with pytest.raises(ValueError, match="Batch job .* does not exist"):
            invalid_metadata.save(self.db_path)


@pytest.mark.integration
class TestBatchFileDriveMetadata:
    """Test the BatchFileDriveMetadata model."""
    
    def setup_method(self):
        """Set up test database for each test."""
        self.tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp_db.name
        self.tmp_db.close()
        init_database(self.db_path)
        
        # Create parent batch job
        self.batch_job = BatchJob(
            job_id="batch_file_test",
            status="processing", 
            total_files=2,
            drive_integration_enabled=True
        )
        self.batch_job.save(self.db_path)
    
    def teardown_method(self):
        """Clean up test database."""
        Path(self.db_path).unlink(missing_ok=True)
    
    def test_file_drive_metadata_creation(self):
        """Test BatchFileDriveMetadata creation and storage."""
        file_metadata = BatchFileDriveMetadata(
            batch_job_id="batch_file_test",
            original_filename="design1.svg",
            drive_file_id="1G2H3I4J5K6L",
            drive_file_url="https://docs.google.com/presentation/d/1G2H3I4J5K6L",
            preview_url="https://drive.google.com/thumbnail?id=1G2H3I4J5K6L",
            upload_status="completed"
        )
        
        file_metadata.save(self.db_path)
        
        # Verify metadata was saved
        loaded_files = BatchFileDriveMetadata.get_by_job_id(self.db_path, "batch_file_test")
        assert len(loaded_files) == 1
        
        loaded_file = loaded_files[0]
        assert loaded_file.batch_job_id == "batch_file_test"
        assert loaded_file.original_filename == "design1.svg"
        assert loaded_file.drive_file_id == "1G2H3I4J5K6L"
        assert loaded_file.upload_status == "completed"
        assert loaded_file.preview_url is not None
    
    def test_multiple_files_per_batch(self):
        """Test multiple file metadata entries for single batch job."""
        files_data = [
            {
                "filename": "design1.svg",
                "drive_file_id": "1FILE1",
                "status": "completed"
            },
            {
                "filename": "design2.svg", 
                "drive_file_id": "1FILE2",
                "status": "pending"
            },
            {
                "filename": "design3.svg",
                "drive_file_id": None,
                "status": "failed",
                "error": "Upload quota exceeded"
            }
        ]
        
        for file_data in files_data:
            file_metadata = BatchFileDriveMetadata(
                batch_job_id="batch_file_test",
                original_filename=file_data["filename"],
                drive_file_id=file_data["drive_file_id"],
                upload_status=file_data["status"],
                upload_error=file_data.get("error")
            )
            file_metadata.save(self.db_path)
        
        # Verify all files were saved
        loaded_files = BatchFileDriveMetadata.get_by_job_id(self.db_path, "batch_file_test")
        assert len(loaded_files) == 3
        
        # Check individual files
        filenames = [f.original_filename for f in loaded_files]
        assert "design1.svg" in filenames
        assert "design2.svg" in filenames
        assert "design3.svg" in filenames
        
        # Check failed file has error message
        failed_file = next(f for f in loaded_files if f.upload_status == "failed")
        assert failed_file.upload_error == "Upload quota exceeded"
    
    def test_file_upload_status_updates(self):
        """Test updating file upload status."""
        file_metadata = BatchFileDriveMetadata(
            batch_job_id="batch_file_test",
            original_filename="updating_file.svg", 
            upload_status="pending"
        )
        file_metadata.save(self.db_path)
        
        # Update to in_progress
        file_metadata.upload_status = "uploading"
        file_metadata.save(self.db_path)
        
        # Update to completed with Drive URLs
        file_metadata.upload_status = "completed"
        file_metadata.drive_file_id = "1UPDATED_FILE"
        file_metadata.drive_file_url = "https://docs.google.com/presentation/d/1UPDATED_FILE"
        file_metadata.preview_url = "https://drive.google.com/thumbnail?id=1UPDATED_FILE"
        file_metadata.save(self.db_path)
        
        # Verify final state
        loaded_files = BatchFileDriveMetadata.get_by_job_id(self.db_path, "batch_file_test")
        updated_file = next(f for f in loaded_files if f.original_filename == "updating_file.svg")
        
        assert updated_file.upload_status == "completed"
        assert updated_file.drive_file_id == "1UPDATED_FILE"
        assert updated_file.drive_file_url is not None
        assert updated_file.preview_url is not None


@pytest.mark.integration
class TestDatabaseIndexes:
    """Test database indexes for performance."""
    
    def test_indexes_created(self):
        """Test that performance indexes are created."""
        with tempfile.NamedTemporaryFile(suffix='.db') as tmp_db:
            init_database(tmp_db.name)
            
            conn = sqlite3.connect(tmp_db.name)
            cursor = conn.cursor()
            
            # Check for indexes
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE '%batch%'
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            
            expected_indexes = [
                'idx_batch_drive_metadata_job_id',
                'idx_batch_file_drive_metadata_job_id', 
                'idx_batch_file_drive_metadata_status'
            ]
            
            for expected_index in expected_indexes:
                assert expected_index in indexes, f"Index {expected_index} not found"
            
            conn.close()


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test integrated database operations."""
    
    def setup_method(self):
        """Set up test database for each test."""
        self.tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp_db.name
        self.tmp_db.close()
        init_database(self.db_path)
    
    def teardown_method(self):
        """Clean up test database.""" 
        Path(self.db_path).unlink(missing_ok=True)
    
    def test_complete_batch_workflow(self):
        """Test complete batch job workflow with Drive integration."""
        # Create batch job
        batch_job = BatchJob(
            job_id="workflow_test",
            status="processing",
            total_files=2,
            drive_integration_enabled=True,
            drive_folder_pattern="Test-Batches/{date}/workflow_test/"
        )
        batch_job.save(self.db_path)
        
        # Create Drive folder metadata
        drive_metadata = BatchDriveMetadata(
            batch_job_id="workflow_test",
            drive_folder_id="1WORKFLOW_FOLDER",
            drive_folder_url="https://drive.google.com/drive/folders/1WORKFLOW_FOLDER"
        )
        drive_metadata.save(self.db_path)
        
        # Create file metadata entries
        file1 = BatchFileDriveMetadata(
            batch_job_id="workflow_test",
            original_filename="file1.svg",
            drive_file_id="1FILE1_ID", 
            upload_status="completed"
        )
        file1.save(self.db_path)
        
        file2 = BatchFileDriveMetadata(
            batch_job_id="workflow_test",
            original_filename="file2.svg",
            upload_status="failed",
            upload_error="Network timeout"
        )
        file2.save(self.db_path)
        
        # Update batch job to completed
        batch_job.status = "completed"
        batch_job.drive_upload_status = "partial_success"
        batch_job.save(self.db_path)
        
        # Verify complete workflow
        final_job = BatchJob.get_by_id(self.db_path, "workflow_test")
        assert final_job.status == "completed"
        assert final_job.drive_upload_status == "partial_success"
        
        folder_data = BatchDriveMetadata.get_by_job_id(self.db_path, "workflow_test")
        assert folder_data.drive_folder_id == "1WORKFLOW_FOLDER"
        
        file_data = BatchFileDriveMetadata.get_by_job_id(self.db_path, "workflow_test")
        assert len(file_data) == 2
        
        completed_files = [f for f in file_data if f.upload_status == "completed"]
        failed_files = [f for f in file_data if f.upload_status == "failed"]
        
        assert len(completed_files) == 1
        assert len(failed_files) == 1
        assert failed_files[0].upload_error == "Network timeout"