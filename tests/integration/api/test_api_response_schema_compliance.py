#!/usr/bin/env python3
"""
API response format validation and schema compliance tests.

Tests API response formats, schema changes, backward compatibility,
and validates that all Drive integration endpoints return consistent schemas.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from typing import Dict, Any
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.main import app
from api.auth import get_current_user
from core.batch.models import BatchJob, BatchDriveMetadata, BatchFileDriveMetadata, init_database


class TestAPIResponseSchemaCompliance:
    """Test API response format and schema compliance."""
    
    @pytest.fixture
    def test_db_path(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        init_database(db_path)
        yield db_path
        
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Setup authentication override."""
        async def override_auth():
            return {'api_key': 'test_key', 'user_id': 'test_user'}
        
        app.dependency_overrides[get_current_user] = override_auth
        yield
        app.dependency_overrides.clear()
    
    def validate_response_schema(self, response_data: Dict[str, Any], required_fields: list, optional_fields: list = None):
        """Helper to validate response schema."""
        optional_fields = optional_fields or []
        
        # Check required fields exist
        for field in required_fields:
            assert field in response_data, f"Required field '{field}' missing from response"
        
        # Check no unexpected fields (only if we want strict validation)
        expected_fields = set(required_fields + optional_fields)
        actual_fields = set(response_data.keys())
        
        # Allow additional fields for extensibility, but log unexpected ones
        unexpected_fields = actual_fields - expected_fields
        if unexpected_fields:
            print(f"Note: Response contains additional fields: {unexpected_fields}")
    
    def test_batch_job_status_response_schema(self, client, test_db_path):
        """Test batch job status response schema compliance."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "schema_test_001"
            
            # Create test batch job with Drive integration
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=3,
                drive_integration_enabled=True,
                drive_upload_status="completed"
            )
            batch_job.save(test_db_path)
            
            response = client.get(f"/batch/jobs/{job_id}")
            assert response.status_code == 200
            
            data = response.json()
            
            # Validate core batch job schema
            required_fields = [
                "job_id", "status", "total_files", "drive_integration_enabled"
            ]
            optional_fields = [
                "drive_upload_status", "drive_folder_pattern", "created_at", "updated_at",
                "completed_files", "failed_files", "progress"
            ]
            
            self.validate_response_schema(data, required_fields, optional_fields)
            
            # Validate field types
            assert isinstance(data["job_id"], str)
            assert isinstance(data["status"], str)
            assert isinstance(data["total_files"], int)
            assert isinstance(data["drive_integration_enabled"], bool)
    
    def test_drive_info_response_schema(self, client, test_db_path):
        """Test Drive info endpoint response schema."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "drive_schema_test"
            
            # Create batch job with Drive metadata
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=2,
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
            
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="folder_schema_123",
                drive_folder_url="https://drive.google.com/drive/folders/folder_schema_123"
            )
            drive_metadata.save(test_db_path)
            
            # Create file metadata
            test_files = [
                ("file1.svg", "drive_file_001", "completed"),
                ("file2.svg", "drive_file_002", "completed")
            ]
            
            for filename, file_id, status in test_files:
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=job_id,
                    original_filename=filename,
                    drive_file_id=file_id,
                    drive_file_url=f"https://drive.google.com/file/d/{file_id}/view",
                    upload_status=status
                )
                file_metadata.save(test_db_path)
            
            response = client.get(f"/batch/jobs/{job_id}/drive-info")
            assert response.status_code == 200
            
            data = response.json()
            
            # Validate Drive info schema
            required_fields = [
                "drive_folder_id", "drive_folder_url", "uploaded_files"
            ]
            optional_fields = [
                "drive_integration_enabled", "upload_summary", "batch_job_id"
            ]
            
            self.validate_response_schema(data, required_fields, optional_fields)
            
            # Validate uploaded_files array schema
            assert isinstance(data["uploaded_files"], list)
            assert len(data["uploaded_files"]) == 2
            
            for file_info in data["uploaded_files"]:
                file_required_fields = [
                    "original_filename", "drive_file_id", "drive_file_url", "upload_status"
                ]
                file_optional_fields = [
                    "preview_url", "upload_error", "created_at", "updated_at"
                ]
                
                self.validate_response_schema(file_info, file_required_fields, file_optional_fields)
    
    def test_backward_compatibility_with_existing_batch_endpoints(self, client, test_db_path):
        """Test backward compatibility of existing batch endpoints."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "backward_compat_test"
            
            # Create batch job WITHOUT Drive integration
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=1,
                drive_integration_enabled=False  # No Drive integration
            )
            batch_job.save(test_db_path)
            
            response = client.get(f"/batch/jobs/{job_id}")
            assert response.status_code == 200
            
            data = response.json()
            
            # Should still contain core fields for backward compatibility
            assert "job_id" in data
            assert "status" in data
            assert "total_files" in data
            assert "drive_integration_enabled" in data
            assert data["drive_integration_enabled"] is False
            
            # Drive-specific fields should be null/absent when not enabled
            if "drive_upload_status" in data:
                assert data["drive_upload_status"] in ["not_requested", None]
    
    def test_error_response_schema_consistency(self, client, test_db_path):
        """Test error response schema consistency."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            # Test 404 error for non-existent job
            response = client.get("/batch/jobs/nonexistent_job_999")
            assert response.status_code == 404
            
            error_data = response.json()
            
            # Standard FastAPI error schema
            required_error_fields = ["detail"]
            self.validate_response_schema(error_data, required_error_fields)
            assert isinstance(error_data["detail"], str)
            
            # Test Drive info endpoint error
            response = client.get("/batch/jobs/nonexistent_job_999/drive-info")
            assert response.status_code == 404
            
            error_data = response.json()
            self.validate_response_schema(error_data, required_error_fields)
    
    def test_api_response_content_types(self, client, test_db_path):
        """Test API response content types are correct."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "content_type_test"
            
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=1,
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
            
            # Test JSON endpoints return correct content type
            response = client.get(f"/batch/jobs/{job_id}")
            assert response.status_code == 200
            assert "application/json" in response.headers.get("content-type", "")
            
            # Ensure JSON is valid
            try:
                data = response.json()
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pytest.fail("Response is not valid JSON")
    
    def test_drive_integration_feature_flags(self, client, test_db_path):
        """Test Drive integration feature flags in responses."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            # Test with Drive integration enabled
            enabled_job_id = "drive_enabled_test"
            enabled_job = BatchJob(
                job_id=enabled_job_id,
                status="completed",
                total_files=1,
                drive_integration_enabled=True
            )
            enabled_job.save(test_db_path)
            
            response = client.get(f"/batch/jobs/{enabled_job_id}")
            data = response.json()
            assert data["drive_integration_enabled"] is True
            
            # Test with Drive integration disabled
            disabled_job_id = "drive_disabled_test"
            disabled_job = BatchJob(
                job_id=disabled_job_id,
                status="completed",
                total_files=1,
                drive_integration_enabled=False
            )
            disabled_job.save(test_db_path)
            
            response = client.get(f"/batch/jobs/{disabled_job_id}")
            data = response.json()
            assert data["drive_integration_enabled"] is False
    
    def test_upload_status_enumeration_compliance(self, client, test_db_path):
        """Test upload status values comply with expected enumeration."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "status_enum_test"
            
            # Create job with various upload statuses
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=4,
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
            
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="status_folder_123"
            )
            drive_metadata.save(test_db_path)
            
            # Create files with different statuses
            status_files = [
                ("completed.svg", "file_completed", "completed"),
                ("pending.svg", "file_pending", "pending"),
                ("uploading.svg", "file_uploading", "uploading"),
                ("failed.svg", "", "failed")
            ]
            
            for filename, file_id, status in status_files:
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=job_id,
                    original_filename=filename,
                    drive_file_id=file_id if file_id else None,
                    upload_status=status
                )
                file_metadata.save(test_db_path)
            
            response = client.get(f"/batch/jobs/{job_id}/drive-info")
            assert response.status_code == 200
            
            data = response.json()
            
            # Validate status enumeration
            valid_statuses = ["pending", "uploading", "completed", "failed"]
            for file_info in data["uploaded_files"]:
                assert file_info["upload_status"] in valid_statuses
    
    def test_timestamp_format_consistency(self, client, test_db_path):
        """Test timestamp format consistency across endpoints."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "timestamp_test"
            
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=1,
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
            
            response = client.get(f"/batch/jobs/{job_id}")
            data = response.json()
            
            # Check timestamp fields if present
            timestamp_fields = ["created_at", "updated_at"]
            for field in timestamp_fields:
                if field in data:
                    timestamp_value = data[field]
                    assert isinstance(timestamp_value, str)
                    
                    # Basic ISO format validation (should contain T and timezone info)
                    assert "T" in timestamp_value or " " in timestamp_value
    
    def test_api_response_size_limits(self, client, test_db_path):
        """Test API response size is reasonable for large datasets."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "large_response_test"
            
            # Create batch job with many files
            large_file_count = 50
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=large_file_count,
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
            
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="large_folder_123"
            )
            drive_metadata.save(test_db_path)
            
            # Create many file metadata entries
            for i in range(large_file_count):
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=job_id,
                    original_filename=f"file_{i:03d}.svg",
                    drive_file_id=f"large_file_{i:03d}",
                    upload_status="completed"
                )
                file_metadata.save(test_db_path)
            
            response = client.get(f"/batch/jobs/{job_id}/drive-info")
            assert response.status_code == 200
            
            data = response.json()
            assert len(data["uploaded_files"]) == large_file_count
            
            # Verify response is still manageable size (rough check)
            response_text = response.text
            assert len(response_text) < 1024 * 1024  # Less than 1MB response
    
    def test_schema_extensibility(self, client, test_db_path):
        """Test schema allows for future extensibility."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "extensibility_test"
            
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=1,
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
            
            response = client.get(f"/batch/jobs/{job_id}")
            assert response.status_code == 200
            
            # Response should be flexible enough to add new fields
            data = response.json()
            
            # Core schema should be stable
            stable_fields = ["job_id", "status", "total_files", "drive_integration_enabled"]
            for field in stable_fields:
                assert field in data
            
            # Response structure should allow additional fields without breaking clients
            assert isinstance(data, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])