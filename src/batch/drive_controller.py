#!/usr/bin/env python3
"""
Google Drive integration controller for batch processing.

Handles folder creation, file uploads, preview generation, and error recovery
for Google Drive integration in the SVG2PPTX batch processing system.
"""

import logging
import concurrent.futures
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import sys

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.services.google_drive import GoogleDriveService, GoogleDriveError
from api.services.google_slides import GoogleSlidesService, GoogleSlidesError
from .models import BatchJob, BatchDriveMetadata, BatchFileDriveMetadata, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


class BatchDriveError(Exception):
    """Custom exception for batch Drive operations."""
    
    def __init__(self, message: str, error_code: Optional[int] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


@dataclass
class DriveOperationResult:
    """Result of a Drive operation."""
    success: bool
    folder_id: Optional[str] = None
    folder_url: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class FileUploadResult:
    """Result of a file upload operation."""
    success: bool
    file_id: Optional[str] = None
    file_url: Optional[str] = None
    preview_url: Optional[str] = None
    original_filename: str = ""
    error_message: Optional[str] = None


@dataclass
class PreviewResult:
    """Result of preview generation."""
    success: bool
    file_id: str
    preview_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class FolderStructure:
    """Represents a hierarchical folder structure."""
    root_folder_id: str
    root_folder_name: str
    date_folder_id: Optional[str] = None
    batch_folder_id: Optional[str] = None
    full_path: str = ""


@dataclass
class BatchWorkflowResult:
    """Result of complete batch workflow execution."""
    success: bool
    folder_id: Optional[str] = None
    folder_url: Optional[str] = None
    uploaded_files: List[FileUploadResult] = None
    generated_previews: List[PreviewResult] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.uploaded_files is None:
            self.uploaded_files = []
        if self.generated_previews is None:
            self.generated_previews = []


class BatchDriveController:
    """Controller for Google Drive integration in batch processing."""
    
    DEFAULT_FOLDER_PATTERN = "SVG2PPTX-Batches/{date}/batch-{job_id}/"
    
    def __init__(self, 
                 drive_service: Optional[GoogleDriveService] = None,
                 slides_service: Optional[GoogleSlidesService] = None,
                 db_path: str = DEFAULT_DB_PATH):
        """
        Initialize BatchDriveController.
        
        Args:
            drive_service: Google Drive service instance
            slides_service: Google Slides service instance  
            db_path: Path to SQLite database
        """
        self.drive_service = drive_service or GoogleDriveService()
        self.slides_service = slides_service or GoogleSlidesService()
        self.db_path = db_path
        
        logger.info("BatchDriveController initialized")
    
    def create_batch_folder(self, 
                          batch_job_id: str, 
                          folder_pattern: Optional[str] = None) -> DriveOperationResult:
        """
        Create hierarchical folder structure for batch job.
        
        Args:
            batch_job_id: ID of the batch job
            folder_pattern: Custom folder naming pattern
            
        Returns:
            DriveOperationResult with folder information
        """
        try:
            # Use default pattern if none provided
            pattern = folder_pattern or self.DEFAULT_FOLDER_PATTERN
            
            # Replace placeholders in pattern
            current_date = datetime.now().strftime('%Y-%m-%d')
            folder_path = pattern.format(date=current_date, job_id=batch_job_id)
            
            logger.info(f"Creating batch folder: {folder_path}")
            
            # Create folder hierarchy
            folder_structure = self._create_folder_hierarchy(folder_path)
            
            # Save folder metadata to database
            drive_metadata = BatchDriveMetadata(
                batch_job_id=batch_job_id,
                drive_folder_id=folder_structure.batch_folder_id,
                drive_folder_url=f"https://drive.google.com/drive/folders/{folder_structure.batch_folder_id}"
            )
            drive_metadata.save(self.db_path)
            
            return DriveOperationResult(
                success=True,
                folder_id=folder_structure.batch_folder_id,
                folder_url=f"https://drive.google.com/drive/folders/{folder_structure.batch_folder_id}"
            )
            
        except Exception as e:
            error_msg = f"Failed to create batch folder: {e}"
            logger.error(error_msg)
            raise BatchDriveError(error_msg)
    
    def _create_folder_hierarchy(self, folder_path: str) -> FolderStructure:
        """
        Create hierarchical folder structure from path.
        
        Args:
            folder_path: Full folder path (e.g., "SVG2PPTX-Batches/2025-09-12/batch-123/")
            
        Returns:
            FolderStructure with created folder IDs
        """
        path_parts = [part for part in folder_path.strip('/').split('/') if part]
        
        if not path_parts:
            raise BatchDriveError("Empty folder path provided")
        
        # Create folders step by step
        current_parent_id = None
        folder_ids = {}
        
        for i, folder_name in enumerate(path_parts):
            try:
                # Create folder
                folder_result = self._create_single_folder(folder_name, current_parent_id)
                folder_ids[i] = folder_result['folderId']
                current_parent_id = folder_result['folderId']
                
                logger.debug(f"Created folder '{folder_name}' with ID: {current_parent_id}")
                
            except Exception as e:
                raise BatchDriveError(f"Failed to create folder '{folder_name}': {e}")
        
        return FolderStructure(
            root_folder_id=folder_ids.get(0),
            root_folder_name=path_parts[0],
            date_folder_id=folder_ids.get(1) if len(path_parts) > 1 else None,
            batch_folder_id=folder_ids.get(len(path_parts) - 1),
            full_path=folder_path
        )
    
    def _create_single_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a single folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Parent folder ID (None for root)
            
        Returns:
            Dictionary with folder information
        """
        try:
            # Check if we have a create_folder method, otherwise use files().create()
            if hasattr(self.drive_service, 'create_folder'):
                return self.drive_service.create_folder(folder_name, parent_id)
            else:
                # Fallback to direct API call
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                
                if parent_id:
                    folder_metadata['parents'] = [parent_id]
                
                folder = self.drive_service.service.files().create(
                    body=folder_metadata,
                    fields='id,name,webViewLink'
                ).execute()
                
                return {
                    'success': True,
                    'folderId': folder['id'],
                    'folderName': folder['name'],
                    'folderUrl': folder.get('webViewLink')
                }
                
        except Exception as e:
            logger.error(f"Failed to create folder '{folder_name}': {e}")
            raise
    
    def upload_batch_files(self, 
                          batch_job_id: str,
                          files: List[Dict[str, str]],
                          folder_id: str) -> List[FileUploadResult]:
        """
        Upload multiple files to Google Drive.
        
        Args:
            batch_job_id: ID of the batch job
            files: List of file dictionaries with 'path', 'original_name', 'converted_name'
            folder_id: Target folder ID in Google Drive
            
        Returns:
            List of FileUploadResult objects
        """
        results = []
        
        for file_info in files:
            try:
                # Upload single file
                upload_result = self.drive_service.upload_file(
                    file_path=file_info['path'],
                    file_name=file_info['converted_name'],
                    folder_id=folder_id
                )
                
                # Create file metadata record
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=batch_job_id,
                    original_filename=file_info['original_name'],
                    drive_file_id=upload_result['fileId'],
                    drive_file_url=upload_result.get('shareableLink'),
                    upload_status="completed"
                )
                file_metadata.save(self.db_path)
                
                results.append(FileUploadResult(
                    success=True,
                    file_id=upload_result['fileId'],
                    file_url=upload_result.get('shareableLink'),
                    original_filename=file_info['original_name']
                ))
                
                logger.info(f"Successfully uploaded {file_info['converted_name']}")
                
            except Exception as e:
                error_msg = f"Failed to upload {file_info['converted_name']}: {e}"
                logger.error(error_msg)
                
                # Record failed upload
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=batch_job_id,
                    original_filename=file_info['original_name'],
                    upload_status="failed",
                    upload_error=str(e)
                )
                file_metadata.save(self.db_path)
                
                results.append(FileUploadResult(
                    success=False,
                    original_filename=file_info['original_name'],
                    error_message=error_msg
                ))
        
        return results
    
    def upload_batch_files_parallel(self, 
                                   batch_job_id: str,
                                   files: List[Dict[str, str]],
                                   folder_id: str,
                                   max_workers: int = 3) -> List[FileUploadResult]:
        """
        Upload multiple files in parallel to Google Drive.
        
        Args:
            batch_job_id: ID of the batch job
            files: List of file dictionaries
            folder_id: Target folder ID in Google Drive  
            max_workers: Maximum number of parallel uploads
            
        Returns:
            List of FileUploadResult objects
        """
        results = []
        
        def upload_single_file(file_info):
            try:
                upload_result = self.drive_service.upload_file(
                    file_path=file_info['path'],
                    file_name=file_info['converted_name'],
                    folder_id=folder_id
                )
                
                # Save to database
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=batch_job_id,
                    original_filename=file_info['original_name'],
                    drive_file_id=upload_result['fileId'],
                    drive_file_url=upload_result.get('shareableLink'),
                    upload_status="completed"
                )
                file_metadata.save(self.db_path)
                
                return FileUploadResult(
                    success=True,
                    file_id=upload_result['fileId'],
                    file_url=upload_result.get('shareableLink'),
                    original_filename=file_info['original_name']
                )
                
            except Exception as e:
                error_msg = str(e)
                
                # Record failure
                file_metadata = BatchFileDriveMetadata(
                    batch_job_id=batch_job_id,
                    original_filename=file_info['original_name'],
                    upload_status="failed",
                    upload_error=error_msg
                )
                file_metadata.save(self.db_path)
                
                return FileUploadResult(
                    success=False,
                    original_filename=file_info['original_name'],
                    error_message=error_msg
                )
        
        # Execute parallel uploads
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(upload_single_file, file_info): file_info 
                             for file_info in files}
            
            for future in concurrent.futures.as_completed(future_to_file):
                result = future.result()
                results.append(result)
        
        return results
    
    def generate_batch_previews(self, 
                              batch_job_id: str,
                              file_ids: List[str]) -> List[PreviewResult]:
        """
        Generate PNG previews for batch of PowerPoint files.
        
        Args:
            batch_job_id: ID of the batch job
            file_ids: List of Google Drive file IDs
            
        Returns:
            List of PreviewResult objects
        """
        results = []
        
        for file_id in file_ids:
            try:
                # Generate preview using Slides service
                preview_result = self.slides_service.generate_preview(file_id)
                
                # Update file metadata with preview URL
                file_metadata_list = BatchFileDriveMetadata.get_by_job_id(self.db_path, batch_job_id)
                for file_metadata in file_metadata_list:
                    if file_metadata.drive_file_id == file_id:
                        file_metadata.preview_url = preview_result.get('previewUrl')
                        file_metadata.save(self.db_path)
                        break
                
                results.append(PreviewResult(
                    success=True,
                    file_id=file_id,
                    preview_url=preview_result.get('previewUrl'),
                    thumbnail_url=preview_result.get('thumbnailUrl')
                ))
                
                logger.info(f"Generated preview for file: {file_id}")
                
            except Exception as e:
                error_msg = f"Failed to generate preview for {file_id}: {e}"
                logger.error(error_msg)
                
                results.append(PreviewResult(
                    success=False,
                    file_id=file_id,
                    error_message=error_msg
                ))
        
        return results
    
    def create_batch_folder_with_retry(self, 
                                     batch_job_id: str,
                                     folder_pattern: Optional[str] = None,
                                     max_retries: int = 3) -> DriveOperationResult:
        """
        Create batch folder with retry logic for resilient operation.
        
        Args:
            batch_job_id: ID of the batch job
            folder_pattern: Custom folder naming pattern
            max_retries: Maximum number of retry attempts
            
        Returns:
            DriveOperationResult with folder information
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return self.create_batch_folder(batch_job_id, folder_pattern)
                
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Folder creation attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    import time
                    time.sleep(wait_time)
                else:
                    logger.error(f"All folder creation attempts failed: {e}")
        
        # All retries exhausted
        error_msg = f"Failed to create batch folder after {max_retries + 1} attempts: {last_error}"
        raise BatchDriveError(error_msg)
    
    def execute_complete_batch_workflow(self, 
                                      batch_job_id: str,
                                      files: List[Dict[str, str]],
                                      folder_pattern: Optional[str] = None,
                                      generate_previews: bool = True) -> BatchWorkflowResult:
        """
        Execute complete batch Drive workflow: folder creation, file uploads, and preview generation.
        
        Args:
            batch_job_id: ID of the batch job
            files: List of files to upload
            folder_pattern: Custom folder naming pattern
            generate_previews: Whether to generate previews
            
        Returns:
            BatchWorkflowResult with complete workflow results
        """
        try:
            logger.info(f"Starting complete batch workflow for job: {batch_job_id}")
            
            # Step 1: Create batch folder
            folder_result = self.create_batch_folder(batch_job_id, folder_pattern)
            if not folder_result.success:
                return BatchWorkflowResult(
                    success=False,
                    error_message=f"Folder creation failed: {folder_result.error_message}"
                )
            
            # Step 2: Upload all files
            upload_results = self.upload_batch_files(
                batch_job_id,
                files,
                folder_result.folder_id
            )
            
            # Step 3: Generate previews if requested
            preview_results = []
            if generate_previews:
                successful_uploads = [r for r in upload_results if r.success]
                file_ids = [r.file_id for r in successful_uploads]
                
                if file_ids:
                    preview_results = self.generate_batch_previews(batch_job_id, file_ids)
            
            # Determine overall success
            successful_uploads = len([r for r in upload_results if r.success])
            total_files = len(files)
            
            success = successful_uploads > 0  # At least some files uploaded successfully
            
            logger.info(f"Batch workflow completed: {successful_uploads}/{total_files} files uploaded successfully")
            
            return BatchWorkflowResult(
                success=success,
                folder_id=folder_result.folder_id,
                folder_url=folder_result.folder_url,
                uploaded_files=upload_results,
                generated_previews=preview_results
            )
            
        except Exception as e:
            error_msg = f"Batch workflow failed: {e}"
            logger.error(error_msg)
            
            return BatchWorkflowResult(
                success=False,
                error_message=error_msg
            )