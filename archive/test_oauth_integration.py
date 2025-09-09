#!/usr/bin/env python3
"""
Test OAuth integration for Google Drive authentication.
"""

import os
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path


def test_oauth_service_structure():
    """Test OAuth service can be imported and has correct structure."""
    print("=== Testing OAuth Service Structure ===")
    
    try:
        from api.services.google_oauth import GoogleOAuthService, GoogleOAuthError
        from api.services.google_oauth import setup_oauth_credentials, test_oauth_setup
        
        print("✓ GoogleOAuthService imported successfully")
        print("✓ GoogleOAuthError imported successfully") 
        print("✓ Setup functions imported successfully")
        
        # Test error class
        error = GoogleOAuthError("Test error", "test_code")
        assert error.message == "Test error"
        assert error.error_code == "test_code"
        print("✓ GoogleOAuthError working correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ OAuth service structure test failed: {e}")
        return False


def test_oauth_configuration():
    """Test OAuth configuration loading."""
    print("\n=== Testing OAuth Configuration ===")
    
    try:
        from api.config import get_settings
        
        settings = get_settings()
        
        # Test OAuth-specific settings
        assert hasattr(settings, 'google_drive_auth_method')
        assert hasattr(settings, 'google_drive_client_id') 
        assert hasattr(settings, 'google_drive_client_secret')
        assert hasattr(settings, 'google_drive_token_file')
        
        print("✓ OAuth configuration fields present")
        print(f"✓ Auth method: {settings.google_drive_auth_method}")
        print(f"✓ Token file: {settings.google_drive_token_file}")
        
        return True
        
    except Exception as e:
        print(f"✗ OAuth configuration test failed: {e}")
        return False


def test_oauth_flow_mocked():
    """Test OAuth flow with mocked Google services."""
    print("\n=== Testing OAuth Flow (Mocked) ===")
    
    try:
        # Create temporary config with mock credentials
        test_env = {
            'GOOGLE_DRIVE_CLIENT_ID': 'test-client-id.apps.googleusercontent.com',
            'GOOGLE_DRIVE_CLIENT_SECRET': 'test-client-secret',
            'GOOGLE_DRIVE_AUTH_METHOD': 'oauth'
        }
        
        with patch.dict(os.environ, test_env):
            with patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_config') as mock_flow_class:
                with patch('googleapiclient.discovery.build') as mock_build:
                    
                    # Mock OAuth flow
                    mock_flow = Mock()
                    mock_credentials = Mock()
                    mock_credentials.to_json.return_value = '{"token": "test-token"}'
                    mock_flow.run_local_server.return_value = mock_credentials
                    mock_flow_class.return_value = mock_flow
                    
                    # Mock Google Drive API
                    mock_service = Mock()
                    mock_service.about.return_value.get.return_value.execute.return_value = {
                        "user": {"displayName": "Test User", "emailAddress": "test@example.com"}
                    }
                    mock_build.return_value = mock_service
                    
                    # Test OAuth service
                    from api.services.google_oauth import GoogleOAuthService
                    
                    with tempfile.TemporaryDirectory() as temp_dir:
                        token_file = os.path.join(temp_dir, 'oauth-token.json')
                        
                        with patch.object(GoogleOAuthService, '__init__') as mock_init:
                            def init_mock(self):
                                from api.config import get_settings
                                self.settings = get_settings()
                                self.token_file = token_file
                                self.credentials = None
                                self._ensure_credentials_dir()
                            
                            mock_init.side_effect = init_mock
                            
                            oauth_service = GoogleOAuthService()
                            
                            # Test getting credentials (should trigger OAuth flow)
                            credentials = oauth_service.get_credentials()
                            
                            print("✓ OAuth flow completed successfully")
                            print("✓ Credentials obtained")
                            
                            # Test connection
                            result = oauth_service.test_credentials()
                            assert result == True
                            print("✓ OAuth credentials test successful")
                            
                            # Test user info
                            user_info = oauth_service.get_user_info()
                            assert user_info['authenticated'] == True
                            print(f"✓ User info: {user_info['displayName']}")
        
        return True
        
    except Exception as e:
        print(f"✗ OAuth flow test failed: {e}")
        return False


def test_google_drive_oauth_integration():
    """Test Google Drive service with OAuth authentication."""
    print("\n=== Testing Google Drive OAuth Integration ===")
    
    try:
        with patch('api.services.google_drive.GoogleOAuthService') as mock_oauth_service:
            with patch('googleapiclient.discovery.build') as mock_build:
                
                # Mock OAuth service
                mock_oauth = Mock()
                mock_credentials = Mock()
                mock_oauth.get_credentials.return_value = mock_credentials
                mock_oauth_service.return_value = mock_oauth
                
                # Mock Google Drive service
                mock_service = Mock()
                mock_service.about.return_value.get.return_value.execute.return_value = {"user": {}}
                mock_build.return_value = mock_service
                
                # Test Google Drive service with OAuth
                from api.services.google_drive import GoogleDriveService
                
                # Force OAuth mode
                test_env = {'GOOGLE_DRIVE_AUTH_METHOD': 'oauth'}
                with patch.dict(os.environ, test_env):
                    drive_service = GoogleDriveService()
                    
                    print("✓ GoogleDriveService initialized with OAuth")
                    
                    # Test connection
                    result = drive_service.test_connection()
                    assert result == True
                    print("✓ Google Drive OAuth connection successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Google Drive OAuth integration test failed: {e}")
        return False


def test_setup_script_components():
    """Test setup script components."""
    print("\n=== Testing Setup Script Components ===")
    
    try:
        # Test that setup script can be imported
        import setup_oauth
        print("✓ Setup script imported successfully")
        
        # Test environment file handling
        env_file = ".env"
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                content = f.read()
                assert 'GOOGLE_DRIVE_AUTH_METHOD' in content
                print("✓ Environment file has OAuth settings")
        
        # Test setup functions
        from api.services.google_oauth import setup_oauth_credentials
        print("✓ Setup function available")
        
        return True
        
    except Exception as e:
        print(f"✗ Setup script test failed: {e}")
        return False


def test_auth_method_switching():
    """Test switching between OAuth and service account authentication."""
    print("\n=== Testing Authentication Method Switching ===")
    
    try:
        from api.services.google_drive import GoogleDriveService, GoogleDriveError
        
        # Test OAuth mode (should fail without credentials)
        with patch.dict(os.environ, {'GOOGLE_DRIVE_AUTH_METHOD': 'oauth'}):
            try:
                service = GoogleDriveService()
                print("✗ Should have failed without OAuth credentials")
                return False
            except GoogleDriveError as e:
                assert "OAuth authentication failed" in str(e)
                print("✓ OAuth mode correctly requires OAuth credentials")
        
        # Test service account mode (should fail without service account file)
        with patch.dict(os.environ, {'GOOGLE_DRIVE_AUTH_METHOD': 'service_account'}):
            try:
                service = GoogleDriveService()
                print("✗ Should have failed without service account file")
                return False
            except GoogleDriveError as e:
                assert "not found" in str(e) or "Service account authentication failed" in str(e)
                print("✓ Service account mode correctly requires service account file")
        
        print("✓ Authentication method switching working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Auth method switching test failed: {e}")
        return False


def main():
    """Run all OAuth integration tests."""
    print("OAuth Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_oauth_service_structure,
        test_oauth_configuration,
        test_oauth_flow_mocked,
        test_google_drive_oauth_integration,
        test_setup_script_components,
        test_auth_method_switching
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All OAuth integration tests passed!")
        print("\n🚀 OAuth Authentication is Ready!")
        print("\nNext steps:")
        print("1. Run: python setup_oauth.py")
        print("2. Follow the OAuth setup process")
        print("3. Test with: python api/services/google_oauth.py")
        return True
    else:
        print("❌ Some tests failed. Check the output above.")
        return False


if __name__ == "__main__":
    main()