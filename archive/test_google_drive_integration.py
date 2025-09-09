#!/usr/bin/env python3
"""
Test script for Google Drive integration.

This script tests the Google Drive service without requiring actual credentials.
It validates the class structure and error handling.
"""

import tempfile
import os
import json
from unittest.mock import Mock, patch


def test_google_drive_service_structure():
    """Test that GoogleDriveService has the expected interface."""
    print("=== Testing Google Drive Service Structure ===")
    
    try:
        from api.services.google_drive import GoogleDriveService, GoogleDriveError
        
        # Test that class can be imported
        print("✓ GoogleDriveService class imported successfully")
        
        # Test error class
        error = GoogleDriveError("Test error", 400)
        assert error.message == "Test error"
        assert error.error_code == 400
        print("✓ GoogleDriveError class working correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Structure test failed: {e}")
        return False


def test_file_processor():
    """Test the FileProcessor utility class."""
    print("\n=== Testing File Processor ===")
    
    try:
        from api.services.file_processor import FileProcessor, UploadManager
        
        # Test FileProcessor
        processor = FileProcessor()
        
        # Test creating temp file
        test_content = b"Test PPTX content"
        temp_path = processor.create_temp_file(test_content, '.pptx')
        
        assert os.path.exists(temp_path)
        print(f"✓ Created temporary file: {temp_path}")
        
        # Test file info
        info = processor.get_file_info(temp_path)
        assert info['exists'] == True
        assert info['size'] == len(test_content)
        print(f"✓ File info: {info['size']} bytes")
        
        # Test cleanup
        processor.cleanup_file(temp_path)
        assert not os.path.exists(temp_path)
        print("✓ File cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"✗ File processor test failed: {e}")
        return False


def test_conversion_service_structure():
    """Test ConversionService structure without Google Drive."""
    print("\n=== Testing Conversion Service Structure ===")
    
    try:
        from api.services.conversion_service import ConversionService, ConversionError
        
        print("✓ ConversionService class imported successfully")
        
        # Test error class
        error = ConversionError("Test conversion error")
        assert str(error) == "Test conversion error"
        print("✓ ConversionError class working correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Conversion service test failed: {e}")
        return False


def test_mock_drive_operations():
    """Test Google Drive operations with mocked service."""
    print("\n=== Testing Mocked Google Drive Operations ===")
    
    try:
        # Create mock credentials file
        mock_creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest-key\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mock_creds, f)
            creds_path = f.name
        
        try:
            with patch('api.services.google_drive.build') as mock_build, \
                 patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_creds:
                
                # Mock credentials
                mock_credentials = Mock()
                mock_creds.return_value = mock_credentials
                
                # Mock the Google Drive service
                mock_service = Mock()
                mock_files = Mock()
                mock_service.files.return_value = mock_files
                mock_service.about.return_value.get.return_value.execute.return_value = {"user": {"name": "Test"}}
                mock_build.return_value = mock_service
                
                # Test service initialization
                from api.services.google_drive import GoogleDriveService
                drive_service = GoogleDriveService(credentials_path=creds_path)
                
                print("✓ GoogleDriveService initialized with mock credentials")
                
                # Test connection
                result = drive_service.test_connection()
                assert result == True
                print("✓ Connection test successful")
                
                # Test mock upload
                mock_files.create.return_value.execute.return_value = {
                    'id': 'mock-file-id',
                    'name': 'test.pptx',
                    'webViewLink': 'https://drive.google.com/file/d/mock-file-id/view',
                    'size': '1024'
                }
                
                # Create test file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(b"test content")
                    temp_path = temp_file.name
                
                try:
                    # Mock permissions for sharing
                    mock_permissions = Mock()
                    mock_service.permissions.return_value = mock_permissions
                    mock_permissions.create.return_value.execute.return_value = {'id': 'perm-id'}
                    
                    result = drive_service.upload_file(temp_path, "test.pptx")
                    
                    assert result['success'] == True
                    assert result['fileId'] == 'mock-file-id'
                    assert result['fileName'] == 'test.pptx'
                    print("✓ Mock file upload successful")
                    
                finally:
                    os.unlink(temp_path)
                
        finally:
            os.unlink(creds_path)
        
        return True
        
    except Exception as e:
        print(f"✗ Mock Drive operations test failed: {e}")
        return False


def test_integration_readiness():
    """Test if all components are ready for integration."""
    print("\n=== Testing Integration Readiness ===")
    
    try:
        # Check if all required modules can be imported
        from api.config import get_settings
        from api.services.google_drive import GoogleDriveService
        from api.services.file_processor import FileProcessor, UploadManager
        from api.services.conversion_service import ConversionService
        
        print("✓ All service modules imported successfully")
        
        # Check settings
        settings = get_settings()
        print(f"✓ Configuration loaded: {settings.google_drive_credentials_path}")
        
        # Check that credentials path is configured
        expected_path = "credentials/service-account.json"
        if expected_path in settings.google_drive_credentials_path:
            print(f"✓ Credentials path configured: {settings.google_drive_credentials_path}")
        else:
            print(f"⚠️  Unexpected credentials path: {settings.google_drive_credentials_path}")
        
        print("✓ All components ready for integration")
        return True
        
    except Exception as e:
        print(f"✗ Integration readiness test failed: {e}")
        return False


def main():
    """Run all Google Drive integration tests."""
    print("Google Drive Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_google_drive_service_structure,
        test_file_processor,
        test_conversion_service_structure,
        test_mock_drive_operations,
        test_integration_readiness
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All Google Drive integration tests passed!")
        print("\nNext steps:")
        print("1. Set up Google Drive service account credentials")
        print("2. Place service-account.json in credentials/ directory")
        print("3. Run: python api/services/google_drive.py")
        return True
    else:
        print("❌ Some tests failed. Check the output above.")
        return False


if __name__ == "__main__":
    main()