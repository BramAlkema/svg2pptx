"""
API client fixtures for testing FastAPI endpoints.

Provides test clients and API-related fixtures.
"""
from typing import Generator
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create a FastAPI test client.
    
    Returns:
        TestClient instance for API testing.
    """
    from api.main import create_app
    
    app = create_app()
    return TestClient(app)


@pytest.fixture
def authenticated_client(client: TestClient) -> TestClient:
    """Create an authenticated FastAPI test client.
    
    Args:
        client: Base test client fixture
        
    Returns:
        TestClient with authentication headers set.
    """
    # Add authentication headers if needed
    client.headers["Authorization"] = "Bearer test-token"
    return client


@pytest.fixture
def batch_app():
    """Create a FastAPI app configured for batch processing.
    
    Returns:
        FastAPI application instance with batch endpoints.
    """
    from api.batch_app import create_batch_app
    
    return create_batch_app()


@pytest.fixture
def batch_client(batch_app) -> TestClient:
    """Create a test client for batch processing API.
    
    Args:
        batch_app: Batch processing FastAPI app
        
    Returns:
        TestClient for batch API testing.
    """
    return TestClient(batch_app)


@pytest.fixture
def simple_app():
    """Create a simplified FastAPI app for basic testing.
    
    Returns:
        Minimal FastAPI application instance.
    """
    from fastapi import FastAPI
    from api.routes import conversion
    
    app = FastAPI()
    app.include_router(conversion.router)
    
    return app


@pytest.fixture
def simple_client(simple_app) -> TestClient:
    """Create a test client for simplified API.
    
    Args:
        simple_app: Simple FastAPI app
        
    Returns:
        TestClient for simple API testing.
    """
    return TestClient(simple_app)


@pytest.fixture
def dual_mode_app():
    """Create a FastAPI app with dual mode functionality.
    
    Returns:
        FastAPI application with both sync and async endpoints.
    """
    from api.dual_mode_app import create_dual_mode_app
    
    return create_dual_mode_app()


@pytest.fixture
def dual_mode_client(dual_mode_app) -> TestClient:
    """Create a test client for dual mode API.
    
    Args:
        dual_mode_app: Dual mode FastAPI app
        
    Returns:
        TestClient for dual mode API testing.
    """
    return TestClient(dual_mode_app)


@pytest.fixture
def mock_google_drive_service():
    """Create a mock Google Drive service.
    
    Returns:
        Mock Google Drive service for testing Drive integration.
    """
    mock_service = Mock()
    
    # Mock file upload
    mock_service.upload_file = Mock(return_value={
        "id": "mock-file-id",
        "name": "test.pptx",
        "webViewLink": "https://drive.google.com/file/d/mock-file-id/view"
    })
    
    # Mock folder creation
    mock_service.create_folder = Mock(return_value={
        "id": "mock-folder-id",
        "name": "Test Folder"
    })
    
    return mock_service


@pytest.fixture
def mock_database_session():
    """Create a mock database session.
    
    Returns:
        Mock database session for testing database operations.
    """
    from unittest.mock import MagicMock
    
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.query = MagicMock()
    session.close = MagicMock()
    
    return session


@pytest.fixture
def api_response_validator():
    """Create an API response validator helper.
    
    Returns:
        Helper class for validating API responses.
    """
    class ResponseValidator:
        @staticmethod
        def validate_success(response, expected_status=200):
            assert response.status_code == expected_status
            return response.json()
        
        @staticmethod
        def validate_error(response, expected_status=400):
            assert response.status_code == expected_status
            data = response.json()
            assert "detail" in data or "error" in data
            return data
        
        @staticmethod
        def validate_schema(response, schema):
            data = response.json()
            for key in schema:
                assert key in data
            return data
    
    return ResponseValidator()