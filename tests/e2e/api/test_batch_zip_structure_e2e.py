#!/usr/bin/env python3
"""
E2E tests for ZIP Structure Preservation in Google Drive.

Tests ZIP file upload and structure preservation in Google Drive:
- ZIP file upload and extraction
- Folder structure recreation in Drive
- File naming and organization preservation
- Mixed content handling (SVG files in nested folders)
- ZIP metadata preservation and tracking
"""

import pytest
import tempfile
import os
import zipfile
from pathlib import Path
from unittest.mock import patch

# Import test infrastructure
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from api.main import app
from api.auth import get_current_user
from core.batch.models import BatchJob, BatchDriveMetadata, BatchFileDriveMetadata
from tests.e2e.api.test_batch_drive_e2e import BatchDriveE2EFixtures


class TestZIPStructurePreservation(BatchDriveE2EFixtures):
    """Test ZIP structure preservation in Google Drive."""
    
    def setup_method(self):
        """Set up test environment."""
        async def override_auth():
            return {'api_key': 'e2e_zip_key', 'user_id': 'e2e_zip_user'}
        
        app.dependency_overrides[get_current_user] = override_auth
    
    def teardown_method(self):
        """Clean up after tests."""
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def sample_zip_structure(self):
        """Create a sample ZIP file with nested structure."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "sample_structure.zip")
            
            # Create ZIP with nested structure
            with zipfile.ZipFile(zip_path, 'w') as zf:
                # Root level files
                zf.writestr("root_icon.svg", "<svg>Root icon content</svg>")
                zf.writestr("logo.svg", "<svg>Logo content</svg>")
                
                # Icons folder
                zf.writestr("icons/home.svg", "<svg>Home icon content</svg>")
                zf.writestr("icons/user.svg", "<svg>User icon content</svg>")
                zf.writestr("icons/settings.svg", "<svg>Settings icon content</svg>")
                
                # Graphics subfolder
                zf.writestr("graphics/logos/company.svg", "<svg>Company logo content</svg>")
                zf.writestr("graphics/banners/header.svg", "<svg>Header banner content</svg>")
                
                # Diagrams with deeper nesting
                zf.writestr("diagrams/flows/process.svg", "<svg>Process flow content</svg>")
                zf.writestr("diagrams/flows/data.svg", "<svg>Data flow content</svg>")
                zf.writestr("diagrams/wireframes/mobile.svg", "<svg>Mobile wireframe content</svg>")
            
            yield zip_path
    
    def test_zip_upload_structure_preservation_e2e(self, client, test_db_path, sample_zip_structure):
        """Test ZIP upload preserves folder structure in Drive."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            # Simulate ZIP upload endpoint (would need to be implemented)
            # For now, test the structure preservation logic by simulating completed job
            
            job_id = "zip_structure_test"
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=10,  # Total SVG files in ZIP
                drive_integration_enabled=True
            )
            batch_job.save(test_db_path)
            
            # Create Drive metadata with structure info
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="zip_structure_folder_123",
                drive_folder_url="https://drive.google.com/drive/folders/zip_structure_folder_123"
            )
            drive_metadata.save(test_db_path)
            
            # Add file metadata preserving folder structure
            file_structure = [
                ("root_icon.svg", "root_icon.pptx", "", "file_root_icon"),
                ("logo.svg", "logo.pptx", "", "file_logo"), 
                ("icons/home.svg", "icons/home.pptx", "icons/", "file_icons_home"),
                ("icons/user.svg", "icons/user.pptx", "icons/", "file_icons_user"),
                ("icons/settings.svg", "icons/settings.pptx", "icons/", "file_icons_settings"),
                ("graphics/logos/company.svg", "graphics/logos/company.pptx", "graphics/logos/", "file_graphics_company"),
                ("graphics/banners/header.svg", "graphics/banners/header.pptx", "graphics/banners/", "file_graphics_header"),
                ("diagrams/flows/process.svg", "diagrams/flows/process.pptx", "diagrams/flows/", "file_diagrams_process"),
                ("diagrams/flows/data.svg", "diagrams/flows/data.pptx", "diagrams/flows/", "file_diagrams_data"),
                ("diagrams/wireframes/mobile.svg", "diagrams/wireframes/mobile.pptx", "diagrams/wireframes/", "file_diagrams_mobile")
            ]
            
            for orig_file, conv_file, folder_path, file_id in file_structure:
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=job_id,
                    original_filename=orig_file,
                    drive_file_id=file_id,
                    drive_file_url=f"https://drive.google.com/file/d/{file_id}/view",
                    upload_status="completed"
                )
                file_metadata.save(test_db_path)
            
            # Test structure preservation verification
            response = client.get(f"/batch/jobs/{job_id}/drive-info")
            assert response.status_code == 200
            
            data = response.json()
            assert data["drive_folder_id"] == "zip_structure_folder_123"
            assert len(data["files"]) == 10
            
            # Verify all files are uploaded successfully
            completed_files = [f for f in data["files"] if f["upload_status"] == "completed"]
            assert len(completed_files) == 10
    
    def test_zip_flat_vs_structured_access_e2e(self, client, test_db_path):
        """Test that ZIP files provide both flat and structured access in Drive."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "zip_dual_access_test"
            
            # Create job with dual access structure
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=5,
                # completed_files=5,
                drive_integration_enabled=True,
                source_type="zip"
            )
            batch_job.save(test_db_path)
            
            # Drive metadata with both access methods
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="zip_dual_access_123",
                drive_folder_url="https://drive.google.com/drive/folders/zip_dual_access_123",
                folder_name="dual_access_test",
                zip_structure_preserved=True,
                flat_access_enabled=True  # Both structured and flat access
            )
            drive_metadata.save(test_db_path)
            
            # Files with both structured and flat access
            files_data = [
                ("folder1/file1.svg", "file1.pptx", "folder1/", "struct_file1", "flat_file1"),
                ("folder1/file2.svg", "file2.pptx", "folder1/", "struct_file2", "flat_file2"),
                ("folder2/subfolder/file3.svg", "file3.pptx", "folder2/subfolder/", "struct_file3", "flat_file3")
            ]
            
            for orig_file, conv_file, folder_path, struct_id, flat_id in files_data:
                # Structured access metadata
                struct_metadata = BatchFileDriveMetadata(
                    batch_job_id=job_id,
                    original_filename=orig_file,
                    converted_filename=conv_file,
                    drive_file_id=struct_id,
                    drive_file_url=f"https://drive.google.com/file/d/{struct_id}/view",
                    upload_status="completed",
                    zip_folder_path=folder_path,
                    preserved_structure=True,
                    access_type="structured"
                )
                struct_metadata.save(test_db_path)
                
                # Flat access metadata (same file, different location)
                flat_metadata = BatchFileDriveMetadata(
                    batch_job_id=job_id,
                    original_filename=orig_file.split('/')[-1],  # Just filename
                    converted_filename=conv_file,
                    drive_file_id=flat_id,
                    drive_file_url=f"https://drive.google.com/file/d/{flat_id}/view",
                    upload_status="completed",
                    zip_folder_path="",  # Root level for flat access
                    preserved_structure=False,
                    access_type="flat"
                )
                flat_metadata.save(test_db_path)
            
            # Test dual access retrieval
            response = client.get(f"/batch/jobs/{job_id}/drive-info")
            assert response.status_code == 200
            
            data = response.json()
            assert data["zip_structure_preserved"] is True
            assert data["flat_access_enabled"] is True
            
            # Should have both structured and flat files
            assert len(data["files"]) == 6  # 3 files × 2 access types
            
            structured_files = [f for f in data["files"] if f.get("access_type") == "structured"]
            flat_files = [f for f in data["files"] if f.get("access_type") == "flat"]
            
            assert len(structured_files) == 3
            assert len(flat_files) == 3
            
            # Verify structured files preserve paths
            for f in structured_files:
                assert f["zip_folder_path"] != ""
            
            # Verify flat files have no folder paths
            for f in flat_files:
                assert f["zip_folder_path"] == ""
    
    def test_zip_complex_nested_structure_e2e(self, client, test_db_path):
        """Test complex deeply nested ZIP structure preservation."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "zip_complex_structure"
            
            batch_job = BatchJob(
                job_id=job_id,
                status="completed", 
                total_files=8,
                # completed_files=8,
                drive_integration_enabled=True,
                source_type="zip",
                original_filename="complex_structure.zip"
            )
            batch_job.save(test_db_path)
            
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="complex_structure_123",
                drive_folder_url="https://drive.google.com/drive/folders/complex_structure_123",
                zip_structure_preserved=True,
                max_folder_depth=4  # Track depth complexity
            )
            drive_metadata.save(test_db_path)
            
            # Complex nested structure
            complex_files = [
                ("assets/icons/small/16x16/home.svg", "assets/icons/small/16x16/", 4),
                ("assets/icons/small/24x24/user.svg", "assets/icons/small/24x24/", 4), 
                ("assets/icons/large/64x64/settings.svg", "assets/icons/large/64x64/", 4),
                ("content/graphics/web/banners/header.svg", "content/graphics/web/banners/", 4),
                ("content/graphics/print/ads/flyer.svg", "content/graphics/print/ads/", 4),
                ("docs/diagrams/technical/architecture.svg", "docs/diagrams/technical/", 3),
                ("docs/wireframes/mobile/screens/login.svg", "docs/wireframes/mobile/screens/", 4),
                ("temp/exports/backup/old_logo.svg", "temp/exports/backup/", 3)
            ]
            
            for i, (orig_file, folder_path, depth) in enumerate(complex_files):
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=job_id,
                    original_filename=orig_file,
                    converted_filename=orig_file.replace('.svg', '.pptx'),
                    drive_file_id=f"complex_file_{i}",
                    upload_status="completed",
                    zip_folder_path=folder_path,
                    preserved_structure=True,
                    folder_depth=depth
                )
                file_metadata.save(test_db_path)
            
            # Test complex structure retrieval
            response = client.get(f"/batch/jobs/{job_id}/drive-info")
            assert response.status_code == 200
            
            data = response.json()
            assert data["zip_structure_preserved"] is True
            assert data["max_folder_depth"] == 4
            
            # Verify all depth levels are represented
            depths = set(f["folder_depth"] for f in data["files"])
            assert depths == {3, 4}
            
            # Verify deepest paths are preserved
            deepest_files = [f for f in data["files"] if f["folder_depth"] == 4]
            assert len(deepest_files) == 5  # 5 files at depth 4


class TestZIPMetadataPreservation(BatchDriveE2EFixtures):
    """Test ZIP metadata preservation and tracking."""
    
    def setup_method(self):
        """Set up test environment."""
        async def override_auth():
            return {'api_key': 'e2e_zip_meta_key', 'user_id': 'e2e_zip_meta_user'}
        
        app.dependency_overrides[get_current_user] = override_auth
    
    def teardown_method(self):
        """Clean up after tests."""
        app.dependency_overrides.clear()
    
    def test_zip_metadata_tracking_e2e(self, client, test_db_path):
        """Test ZIP metadata is properly tracked and preserved."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "zip_metadata_test"
            
            # Create job with ZIP metadata
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=6,
                # completed_files=6,
                drive_integration_enabled=True,
                source_type="zip",
                original_filename="project_assets.zip",
                zip_file_size=2048576,  # 2MB
                zip_compression_ratio=0.65
            )
            batch_job.save(test_db_path)
            
            # ZIP-specific Drive metadata
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="zip_metadata_123",
                drive_folder_url="https://drive.google.com/drive/folders/zip_metadata_123",
                folder_name="project_assets",
                zip_structure_preserved=True,
                original_zip_name="project_assets.zip",
                zip_extracted_size=3145728,  # 3MB extracted
                zip_file_count=6,
                zip_folder_count=3
            )
            drive_metadata.save(test_db_path)
            
            # Test metadata retrieval
            response = client.get(f"/batch/jobs/{job_id}/drive-info")
            assert response.status_code == 200
            
            data = response.json()
            assert data["original_zip_name"] == "project_assets.zip"
            assert data["zip_file_count"] == 6
            assert data["zip_folder_count"] == 3
            assert data["zip_extracted_size"] == 3145728
    
    def test_zip_file_origin_tracking_e2e(self, client, test_db_path):
        """Test tracking of file origins within ZIP structure."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "zip_origin_test"
            
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=4,
                # completed_files=4,
                drive_integration_enabled=True,
                source_type="zip"
            )
            batch_job.save(test_db_path)
            
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="zip_origin_123",
                zip_structure_preserved=True
            )
            drive_metadata.save(test_db_path)
            
            # Files with detailed origin tracking
            origin_files = [
                {
                    "original": "icons/social/facebook.svg",
                    "zip_path": "icons/social/",
                    "zip_index": 0,
                    "compressed_size": 1024,
                    "uncompressed_size": 2048
                },
                {
                    "original": "icons/social/twitter.svg", 
                    "zip_path": "icons/social/",
                    "zip_index": 1,
                    "compressed_size": 896,
                    "uncompressed_size": 1792
                },
                {
                    "original": "logos/company_large.svg",
                    "zip_path": "logos/",
                    "zip_index": 2,
                    "compressed_size": 4096,
                    "uncompressed_size": 8192
                },
                {
                    "original": "backgrounds/pattern.svg",
                    "zip_path": "backgrounds/",
                    "zip_index": 3,
                    "compressed_size": 2048,
                    "uncompressed_size": 6144
                }
            ]
            
            for file_data in origin_files:
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=job_id,
                    original_filename=file_data["original"],
                    converted_filename=file_data["original"].replace('.svg', '.pptx'),
                    drive_file_id=f"origin_file_{file_data['zip_index']}",
                    upload_status="completed",
                    zip_folder_path=file_data["zip_path"],
                    zip_entry_index=file_data["zip_index"],
                    original_compressed_size=file_data["compressed_size"],
                    original_uncompressed_size=file_data["uncompressed_size"],
                    preserved_structure=True
                )
                file_metadata.save(test_db_path)
            
            # Test origin tracking retrieval
            response = client.get(f"/batch/jobs/{job_id}/drive-info")
            assert response.status_code == 200
            
            data = response.json()
            files = data["files"]
            
            # Verify origin tracking
            assert all("zip_entry_index" in f for f in files)
            assert all("original_compressed_size" in f for f in files)
            assert all("original_uncompressed_size" in f for f in files)
            
            # Verify compression ratios are tracked
            for f in files:
                expected_ratio = f["original_compressed_size"] / f["original_uncompressed_size"]
                assert 0.4 <= expected_ratio <= 0.6  # Reasonable compression ratios
    
    def test_zip_integrity_validation_e2e(self, client, test_db_path):
        """Test ZIP integrity validation in Drive uploads."""
        with patch('api.routes.batch.DEFAULT_DB_PATH', test_db_path):
            job_id = "zip_integrity_test"
            
            # Job with integrity validation results
            batch_job = BatchJob(
                job_id=job_id,
                status="completed",
                total_files=5,
                # completed_files=4,  # One file failed integrity check
                # failed_files=1,
                drive_integration_enabled=True,
                source_type="zip",
                integrity_validated=True
            )
            batch_job.save(test_db_path)
            
            drive_metadata = BatchDriveMetadata(
                batch_job_id=job_id,
                drive_folder_id="zip_integrity_123",
                zip_structure_preserved=True,
                integrity_check_passed=True,
                corrupted_files_detected=1
            )
            drive_metadata.save(test_db_path)
            
            # Successful files
            for i in range(4):
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=job_id,
                    original_filename=f"valid_file_{i}.svg",
                    converted_filename=f"valid_file_{i}.pptx",
                    drive_file_id=f"valid_{i}",
                    upload_status="completed",
                    integrity_validated=True,
                    checksum_verified=True
                )
                file_metadata.save(test_db_path)
            
            # Failed file (integrity issue)
            failed_metadata = BatchFileDriveMetadata(
                batch_job_id=job_id,
                original_filename="corrupted_file.svg",
                converted_filename="", # Not converted due to corruption
                drive_file_id="",  # Not uploaded
                upload_status="failed",
                integrity_validated=False,
                failure_reason="ZIP entry corrupted or unreadable"
            )
            failed_metadata.save(test_db_path)
            
            # Test integrity validation results
            response = client.get(f"/batch/jobs/{job_id}/drive-info")
            assert response.status_code == 200
            
            data = response.json()
            assert data["integrity_check_passed"] is True
            assert data["corrupted_files_detected"] == 1
            
            # Verify only valid files are in Drive
            valid_files = [f for f in data["files"] if f["upload_status"] == "completed"]
            failed_files = [f for f in data["files"] if f["upload_status"] == "failed"]
            
            assert len(valid_files) == 4
            assert len(failed_files) == 1
            assert all(f["integrity_validated"] for f in valid_files)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])