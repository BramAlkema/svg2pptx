#!/usr/bin/env python3
"""
File processing utilities for handling uploads and temporary files.
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FileProcessor:
    """Handle file processing operations for API."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize file processor.
        
        Args:
            temp_dir: Directory for temporary files
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self._ensure_temp_dir()
    
    def _ensure_temp_dir(self):
        """Ensure temp directory exists."""
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def create_temp_file(self, content: bytes, suffix: str = '') -> str:
        """
        Create temporary file with content.
        
        Args:
            content: File content as bytes
            suffix: File suffix/extension
            
        Returns:
            Path to created temporary file
        """
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        filename = f"temp_{unique_id}{suffix}"
        temp_path = os.path.join(self.temp_dir, filename)
        
        try:
            with open(temp_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"Created temporary file: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to create temp file: {e}")
            raise
    
    def cleanup_file(self, file_path: str) -> bool:
        """
        Clean up temporary file.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if successful
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")
            return False
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file information
        """
        try:
            stat = os.stat(file_path)
            return {
                'path': file_path,
                'name': os.path.basename(file_path),
                'size': stat.st_size,
                'exists': True,
                'extension': Path(file_path).suffix.lower()
            }
        except Exception as e:
            return {
                'path': file_path,
                'exists': False,
                'error': str(e)
            }


class UploadManager:
    """Manage file uploads to Google Drive with cleanup."""
    
    def __init__(self, drive_service, file_processor: Optional[FileProcessor] = None):
        """
        Initialize upload manager.
        
        Args:
            drive_service: GoogleDriveService instance
            file_processor: FileProcessor instance
        """
        self.drive_service = drive_service
        self.file_processor = file_processor or FileProcessor()
        self.temp_files = []  # Track files for cleanup
    
    def upload_content_as_file(self, content: bytes, filename: str, 
                              folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload content as file to Google Drive.
        
        Args:
            content: File content as bytes
            filename: Name for the file
            folder_id: Optional Google Drive folder ID
            
        Returns:
            Upload result dictionary
        """
        temp_path = None
        try:
            # Create temporary file
            suffix = Path(filename).suffix
            temp_path = self.file_processor.create_temp_file(content, suffix)
            self.temp_files.append(temp_path)
            
            # Upload to Google Drive
            result = self.drive_service.upload_file(
                file_path=temp_path,
                file_name=filename,
                folder_id=folder_id
            )
            
            logger.info(f"Successfully uploaded {filename} to Google Drive")
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload {filename}: {e}")
            raise
        finally:
            # Clean up temporary file
            if temp_path:
                self.file_processor.cleanup_file(temp_path)
                if temp_path in self.temp_files:
                    self.temp_files.remove(temp_path)
    
    def update_file_content(self, file_id: str, content: bytes, 
                           filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Update existing Google Drive file with new content.
        
        Args:
            file_id: Google Drive file ID to update
            content: New file content as bytes
            filename: Optional new filename
            
        Returns:
            Update result dictionary
        """
        temp_path = None
        try:
            # Create temporary file
            suffix = Path(filename).suffix if filename else '.pptx'
            temp_path = self.file_processor.create_temp_file(content, suffix)
            self.temp_files.append(temp_path)
            
            # Update file in Google Drive
            result = self.drive_service.update_file(
                file_id=file_id,
                file_path=temp_path,
                file_name=filename
            )
            
            logger.info(f"Successfully updated file {file_id} in Google Drive")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update file {file_id}: {e}")
            raise
        finally:
            # Clean up temporary file
            if temp_path:
                self.file_processor.cleanup_file(temp_path)
                if temp_path in self.temp_files:
                    self.temp_files.remove(temp_path)
    
    def cleanup_all(self):
        """Clean up all tracked temporary files."""
        for temp_file in self.temp_files[:]:  # Copy list to avoid modification during iteration
            self.file_processor.cleanup_file(temp_file)
            self.temp_files.remove(temp_file)
        
        logger.info("Cleaned up all temporary files")


if __name__ == "__main__":
    # Test file processor
    processor = FileProcessor()
    
    # Test creating temp file
    test_content = b"Test file content"
    temp_path = processor.create_temp_file(test_content, '.txt')
    
    # Test file info
    info = processor.get_file_info(temp_path)
    print(f"File info: {info}")
    
    # Test cleanup
    processor.cleanup_file(temp_path)
    print("File processor test complete")