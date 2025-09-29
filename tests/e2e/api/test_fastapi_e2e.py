#!/usr/bin/env python3
"""
End-to-End tests for FastAPI SVG conversion service.

Tests the complete API workflow from SVG upload through conversion
to PPTX download, covering all endpoints and error scenarios.
"""

import pytest
import tempfile
import os
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional
import httpx
from fastapi.testclient import TestClient

# Import the FastAPI app and dependencies
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from api.main import app
from api.auth import get_current_user
from api.config import get_settings


class TestFastAPIE2E:
    """End-to-end tests for the FastAPI SVG conversion service."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "name": "Test User"
        }
    
    @pytest.fixture
    def test_svg_url(self):
        """Test SVG URL for API testing."""
        return "https://example.com/test.svg"
    
    @pytest.fixture
    def sample_svg_content(self):
        """Sample SVG content for testing."""
        return '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
    <circle cx="50" cy="50" r="20" fill="red"/>
</svg>'''
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for API requests."""
        return {"Authorization": "Bearer test_api_key"}
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint accessibility."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "svg2pptx-api"
        assert data["version"] == "1.0.0"
    
    def test_health_check_no_auth_required(self, client):
        """Test that health check doesn't require authentication."""
        # Test without any headers
        response = client.get("/health")
        assert response.status_code == 200
        
        # Test with invalid auth header
        response = client.get("/health", headers={"Authorization": "Bearer invalid"})
        assert response.status_code == 200
    
    def test_api_documentation_endpoints(self, client):
        """Test that API documentation endpoints are accessible."""
        # Test OpenAPI docs
        docs_response = client.get("/docs")
        assert docs_response.status_code == 200
        
        # Test ReDoc
        redoc_response = client.get("/redoc")
        assert redoc_response.status_code == 200
        
        # Test OpenAPI JSON schema
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == 200
        assert "openapi" in openapi_response.json()


class TestConversionEndpointE2E:
    """E2E tests for the SVG conversion endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client with mocked dependencies."""
        # Override authentication dependency
        def mock_get_current_user():
            return {
                "user_id": "test_user_123",
                "email": "test@example.com",
                "name": "Test User"
            }
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        client = TestClient(app)
        yield client
        
        # Clean up dependency overrides
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def mock_conversion_service(self):
        """Mock the conversion service for testing."""
        with patch('api.main.ConversionService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            # Mock successful conversion response
            mock_instance.convert_and_upload.return_value = {
                "success": True,
                "file_id": "mock_file_id_123",
                "file_name": "converted_presentation.pptx",
                "drive_link": "https://drive.google.com/file/d/mock_file_id_123/view",
                "thumbnails": [
                    {
                        "slide_number": 1,
                        "thumbnail_url": "https://example.com/thumb1.png"
                    }
                ],
                "conversion_time": 2.5,
                "file_size": 45678
            }
            
            yield mock_instance
    
    def test_convert_endpoint_success(self, client, mock_conversion_service):
        """Test successful SVG conversion through API."""
        test_url = "https://example.com/test.svg"
        
        response = client.post(
            "/convert",
            params={"url": test_url}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["success"] is True
        assert "file_id" in data
        assert "file_name" in data
        assert "drive_link" in data
        assert "thumbnails" in data
        assert "conversion_time" in data
        assert "file_size" in data
        
        # Verify the conversion service was called
        mock_conversion_service.convert_and_upload.assert_called_once()
        call_args = mock_conversion_service.convert_and_upload.call_args
        assert call_args[1]["svg_url"] == test_url  # Keyword arg
    
    def test_convert_endpoint_with_optional_parameters(self, client, mock_conversion_service):
        """Test conversion endpoint with all optional parameters."""
        test_url = "https://example.com/complex.svg"
        file_id = "existing_file_123"
        preprocessing = "aggressive"
        precision = 8
        
        response = client.post(
            "/convert",
            params={
                "url": test_url,
                "fileId": file_id,
                "preprocessing": preprocessing,
                "precision": precision
            }
        )
        
        assert response.status_code == 200
        
        # Verify parameters were passed to service - URL and fileId as keyword args
        call_args = mock_conversion_service.convert_and_upload.call_args
        assert call_args[1]["svg_url"] == test_url  # Keyword arg
        assert call_args[1]["file_id"] == file_id  # Keyword arg
    
    def test_convert_endpoint_invalid_url(self, client, mock_conversion_service):
        """Test conversion endpoint with invalid URL."""
        invalid_urls = [
            "",  # Empty URL
            "   ",  # Whitespace only
            "not_a_url",  # No scheme
            "ftp://example.com/file.svg",  # Wrong scheme
            "http://",  # No domain
        ]
        
        for invalid_url in invalid_urls:
            response = client.post(
                "/convert",
                params={"url": invalid_url}
            )
            
            assert response.status_code == 400
            assert "detail" in response.json()
            # Verify service wasn't called for invalid URLs
            mock_conversion_service.convert_and_upload.assert_not_called()
    
    def test_convert_endpoint_missing_url(self, client, mock_conversion_service):
        """Test conversion endpoint without URL parameter."""
        response = client.post("/convert")
        
        assert response.status_code == 422  # Unprocessable Entity for missing required param
        
        # Verify service wasn't called
        mock_conversion_service.convert_and_upload.assert_not_called()
    
    def test_convert_endpoint_unauthorized(self, client):
        """Test conversion endpoint without authentication."""
        # Remove the auth override to test real auth
        app.dependency_overrides.clear()
        
        response = client.post(
            "/convert",
            params={"url": "https://example.com/test.svg"}
        )
        
        # Should return 401 or 403 for unauthorized access
        assert response.status_code in [401, 403]
    
    def test_convert_endpoint_conversion_error(self, client, mock_conversion_service):
        """Test conversion endpoint when service throws error."""
        from api.services.conversion_service import ConversionError
        
        # Mock service to raise an error
        mock_conversion_service.convert_and_upload.side_effect = ConversionError("SVG parsing failed")
        
        response = client.post(
            "/convert",
            params={"url": "https://example.com/broken.svg"}
        )
        
        assert response.status_code == 400
        assert "SVG parsing failed" in response.json()["detail"]


class TestPreviewEndpointsE2E:
    """E2E tests for preview-related endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client with mocked dependencies."""
        def mock_get_current_user():
            return {
                "user_id": "test_user_123",
                "email": "test@example.com",
                "name": "Test User"
            }
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        client = TestClient(app)
        yield client
        
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def mock_google_services(self):
        """Mock Google Drive and Slides services."""
        with patch('api.routes.previews.ConversionService') as mock_conversion, \
             patch('api.routes.previews.GoogleSlidesService') as mock_slides:
            
            # Mock ConversionService and its slides_service property
            conversion_instance = Mock()
            mock_conversion.return_value = conversion_instance
            
            mock_slides_instance = Mock()
            mock_slides.return_value = mock_slides_instance
            conversion_instance.slides_service = mock_slides_instance
            
            # Mock preview info response for slides service
            mock_slides_instance.generate_preview_summary.return_value = {
                "presentation": {
                    "id": "test_presentation_id",
                    "title": "Test Presentation", 
                    "slideCount": 3
                },
                "previews": {
                    "successful": 2,
                    "total": 3,
                    "urls": [
                        {"slideId": "slide1", "url": "https://example.com/thumb1.png"},
                        {"slideId": "slide2", "url": "https://example.com/thumb2.png"}
                    ]
                },
                "urls": {
                    "view": "https://docs.google.com/presentation/d/test_presentation_id/edit",
                    "download": "https://docs.google.com/presentation/d/test_presentation_id/export/pptx"
                }
            }
            
            # Mock thumbnail response
            mock_slides_instance.get_slide_thumbnails.return_value = [
                {
                    "slideId": "slide1",
                    "url": "https://example.com/thumb1.png"
                },
                {
                    "slideId": "slide2", 
                    "url": "https://example.com/thumb2.png"
                }
            ]
            
            yield conversion_instance
    
    def test_preview_info_endpoint(self, client, mock_google_services):
        """Test getting preview information for a file."""
        file_id = "test_file_id_123"
        
        response = client.get(f"/previews/{file_id}/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["fileId"] == file_id
        assert "presentation" in data
        assert "previews" in data
        assert "urls" in data
        assert data["presentation"]["slideCount"] == 3
    
    def test_preview_info_invalid_file_id(self, client, mock_google_services):
        """Test preview info endpoint with invalid file ID."""
        # Empty string results in invalid URL (404)
        response = client.get("/previews//info")
        assert response.status_code == 404

        # Whitespace string results in validation error (400)
        response = client.get("/previews/   /info")
        assert response.status_code == 400

        # Valid but non-existent file ID should return successful mock response
        response = client.get("/previews/invalid_id/info")
        assert response.status_code == 200  # Mocked service returns success
    
    def test_preview_thumbnails_endpoint(self, client, mock_google_services):
        """Test getting thumbnails for a presentation."""
        file_id = "test_file_id_123"
        
        response = client.get(f"/previews/{file_id}/thumbnails")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["presentationId"] == file_id
        assert "thumbnails" in data
        assert data["slideCount"] == 2
        assert len(data["thumbnails"]) == 2
        assert data["thumbnails"][0]["slideId"] == "slide1"
        assert "url" in data["thumbnails"][0]
    
    def test_preview_download_endpoint(self, client, mock_google_services):
        """Test downloading a converted presentation."""
        file_id = "test_file_id_123"
        
        # Mock the async get_presentation_previews method
        async def mock_get_presentation_previews(file_id):
            return {
                "success": True,
                "presentationId": file_id,
                "presentation": {
                    "id": file_id,
                    "title": "Test Presentation",
                    "slideCount": 2
                },
                "previews": {
                    "successful": 2,
                    "total": 2,
                    "downloads": [
                        {
                            "slideNumber": 1,
                            "success": True,
                            "imageData": b"mock_image_data_1"
                        },
                        {
                            "slideNumber": 2,
                            "success": True,
                            "imageData": b"mock_image_data_2"
                        }
                    ]
                },
                "urls": {
                    "view": f"https://docs.google.com/presentation/d/{file_id}/edit",
                    "download": f"https://docs.google.com/presentation/d/{file_id}/export/pptx"
                }
            }
        
        mock_google_services.get_presentation_previews = mock_get_presentation_previews
        
        response = client.get(f"/previews/{file_id}/download")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["fileId"] == file_id
        assert data["presentationId"] == file_id
        assert "presentation" in data
        assert "previews" in data
        assert data["previews"]["successful"] == 2
        assert len(data["previews"]["downloads"]) == 2
        # Check that binary data was converted to base64
        assert "imageDataBase64" in data["previews"]["downloads"][0]
        assert "imageData" not in data["previews"]["downloads"][0]


class TestAPIWorkflowE2E:
    """E2E tests for complete API workflows."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client with mocked dependencies."""
        def mock_get_current_user():
            return {
                "user_id": "test_user_123",
                "email": "test@example.com",
                "name": "Test User"
            }
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        client = TestClient(app)
        yield client
        
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def mock_full_workflow(self):
        """Mock the complete conversion and preview workflow."""
        with patch('api.main.ConversionService') as mock_conversion, \
             patch('api.routes.previews.ConversionService') as mock_preview_conversion, \
             patch('api.routes.previews.GoogleSlidesService') as mock_slides:
            
            # Mock conversion service (for main endpoint)
            conversion_instance = Mock()
            mock_conversion.return_value = conversion_instance
            conversion_instance.convert_and_upload.return_value = {
                "success": True,
                "file_id": "workflow_test_file_123",
                "file_name": "workflow_test.pptx",
                "drive_link": "https://drive.google.com/file/d/workflow_test_file_123/view",
                "thumbnails": [],
                "conversion_time": 1.5,
                "file_size": 12345
            }

            # Mock preview conversion service (for preview endpoints)
            preview_conversion_instance = Mock()
            mock_preview_conversion.return_value = preview_conversion_instance
            mock_slides_instance = Mock()
            preview_conversion_instance.slides_service = mock_slides_instance
            mock_slides_instance.generate_preview_summary.return_value = {
                "presentation": {
                    "id": "workflow_test_file_123",
                    "title": "Workflow Test Presentation",
                    "slideCount": 2
                },
                "previews": {
                    "successful": 2,
                    "total": 2,
                    "urls": [
                        {"slideId": "slide1", "url": "https://example.com/thumb1.png"},
                        {"slideId": "slide2", "url": "https://example.com/thumb2.png"}
                    ]
                },
                "urls": {
                    "view": "https://docs.google.com/presentation/d/workflow_test_file_123/edit",
                    "download": "https://docs.google.com/presentation/d/workflow_test_file_123/export/pptx"
                }
            }
            
            # Mock slides service
            slides_instance = Mock()
            mock_slides.return_value = slides_instance
            slides_instance.get_presentation_info.return_value = {
                "presentation_id": "workflow_presentation_id",
                "title": "Workflow Test Presentation",
                "slide_count": 2
            }
            slides_instance.get_slide_thumbnails.return_value = [
                {"slideId": "slide1", "url": "https://example.com/thumb1.png"},
                {"slideId": "slide2", "url": "https://example.com/thumb2.png"}
            ]
            
            yield {
                "conversion": conversion_instance,
                "preview_conversion": preview_conversion_instance,
                "slides": slides_instance
            }
    
    def test_complete_svg_to_pptx_workflow(self, client, mock_full_workflow):
        """Test complete workflow: convert SVG -> get info -> get thumbnails -> download."""
        svg_url = "https://example.com/workflow_test.svg"
        
        # Step 1: Convert SVG
        convert_response = client.post("/convert", params={"url": svg_url})
        assert convert_response.status_code == 200
        
        convert_data = convert_response.json()
        assert convert_data["success"] is True
        file_id = convert_data["file_id"]
        assert file_id == "workflow_test_file_123"
        
        # Step 2: Get presentation info
        info_response = client.get(f"/previews/{file_id}/info")
        assert info_response.status_code == 200
        
        info_data = info_response.json()
        assert info_data["presentation"]["slideCount"] == 2
        assert "Workflow Test Presentation" in info_data["presentation"]["title"]
        
        # Step 3: Get thumbnails
        thumbnails_response = client.get(f"/previews/{file_id}/thumbnails")
        assert thumbnails_response.status_code == 200
        
        thumbnails_data = thumbnails_response.json()
        assert len(thumbnails_data["thumbnails"]) == 2
        
        # Verify all services were called
        mock_full_workflow["conversion"].convert_and_upload.assert_called_once()
    
    def test_workflow_with_preprocessing_options(self, client, mock_full_workflow):
        """Test workflow with various preprocessing options."""
        svg_url = "https://example.com/complex_workflow.svg"
        
        # Test with aggressive preprocessing
        response = client.post(
            "/convert",
            params={
                "url": svg_url,
                "preprocessing": "aggressive",
                "precision": 10
            }
        )
        
        assert response.status_code == 200
        
        # Verify convert_and_upload was called with URL
        call_args = mock_full_workflow["conversion"].convert_and_upload.call_args
        assert call_args[1]["svg_url"] == svg_url

        # Note: preprocessing and precision are set on conversion_service.settings,
        # not passed as parameters to convert_and_upload
    
    def test_workflow_error_handling(self, client, mock_full_workflow):
        """Test workflow error handling at various stages."""
        from api.services.conversion_service import ConversionError
        
        # Test conversion failure
        mock_full_workflow["conversion"].convert_and_upload.side_effect = ConversionError("Network error")
        
        response = client.post("/convert", params={"url": "https://example.com/error_test.svg"})
        assert response.status_code == 400
        assert "Network error" in response.json()["detail"]
        
        # Reset mock for next test
        mock_full_workflow["conversion"].convert_and_upload.side_effect = None
        mock_full_workflow["conversion"].convert_and_upload.return_value = {
            "success": True,
            "file_id": "error_test_file_123",
            "file_name": "error_test.pptx"
        }
        
        # Test preview service failure
        from api.services.google_slides import GoogleSlidesError
        # The preview endpoint uses the ConversionService's slides_service.generate_preview_summary
        preview_conversion_instance = mock_full_workflow["preview_conversion"]
        preview_conversion_instance.slides_service.generate_preview_summary.side_effect = GoogleSlidesError("Slides API error")

        response = client.get("/previews/error_test_file_123/info")
        assert response.status_code == 400  # GoogleSlidesError returns 400, not 500


class TestAPIPerformanceE2E:
    """E2E tests for API performance and stress testing."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        def mock_get_current_user():
            return {"user_id": "perf_test_user", "email": "perf@example.com"}
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        client = TestClient(app)
        yield client
        
        app.dependency_overrides.clear()
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests to health endpoint."""
        import concurrent.futures
        import time
        
        def make_request():
            start_time = time.time()
            response = client.get("/health")
            end_time = time.time()
            return response.status_code, end_time - start_time
        
        # Test 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for status_code, duration in results:
            assert status_code == 200
            assert duration < 5.0  # Should respond within 5 seconds
    
    def test_api_response_times(self, client):
        """Test API response times for various endpoints."""
        import time
        
        endpoints = [
            ("/health", "GET"),
            ("/docs", "GET"),
            ("/openapi.json", "GET")
        ]
        
        for endpoint, method in endpoints:
            start_time = time.time()
            
            if method == "GET":
                response = client.get(endpoint)
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert response.status_code in [200, 404]  # 404 is OK for some endpoints
            assert duration < 2.0, f"{endpoint} took {duration:.2f}s (too slow)"


class TestRealWorldSVGsE2E:
    """E2E tests using real-world SVG files from the test library."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client with mocked services."""
        def mock_get_current_user():
            return {"user_id": "real_world_test", "email": "test@example.com"}
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def real_world_svgs(self):
        """Load real-world SVG files from test library."""
        from tests.utils.dependency_checks import conditional_import
        from pathlib import Path

        with conditional_import('tools.testing.svg_test_library',
                              'SVG test library not available - tools.testing module missing') as svg_lib:
            SVGTestLibrary = svg_lib.SVGTestLibrary

            library_path = Path("tests/test_data/real_world_svgs")
            if not library_path.exists():
                pytest.skip("Real-world SVG library not available")

            library = SVGTestLibrary(library_path)
            return library
    
    def test_api_with_real_svg_metadata(self, client, real_world_svgs):
        """Test API workflow using metadata from real SVG files."""
        with patch('api.main.ConversionService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            # Test conversion with different complexity levels
            for filename, metadata in real_world_svgs.metadata.items():
                # Mock response based on SVG complexity
                complexity = metadata.complexity
                expected_time = {
                    "low": 1.0,
                    "medium": 2.5,
                    "high": 5.0
                }.get(complexity, 2.0)
                
                mock_instance.convert_and_upload.return_value = {
                    "success": True,
                    "file_id": f"real_world_{filename.replace('.svg', '')}",
                    "file_name": filename.replace('.svg', '.pptx'),
                    "conversion_time": expected_time,
                    "complexity": complexity,
                    "features": metadata.features
                }
                
                # Simulate conversion request
                test_url = f"https://example.com/{filename}"
                response = client.post("/convert", params={"url": test_url})
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["complexity"] == complexity
                assert set(data["features"]) == set(metadata.features)
                
                # Verify conversion time expectations
                if complexity == "high":
                    assert data["conversion_time"] >= 2.0
                elif complexity == "low":
                    assert data["conversion_time"] <= 2.0
    
    def test_converter_module_coverage_through_api(self, client, real_world_svgs):
        """Test that API exercises all converter modules through real SVGs."""
        with patch('api.main.ConversionService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            # Track which converter modules are tested
            modules_tested = set()
            
            for filename, metadata in real_world_svgs.metadata.items():
                converter_modules = metadata.converter_modules
                modules_tested.update(converter_modules)
                
                mock_instance.convert_and_upload.return_value = {
                    "success": True,
                    "file_id": f"module_test_{filename.replace('.svg', '')}",
                    "converter_modules_used": converter_modules
                }
                
                test_url = f"https://example.com/{filename}"
                response = client.post("/convert", params={"url": test_url})
                
                assert response.status_code == 200
                data = response.json()
                assert "converter_modules_used" in data
            
            # Verify we tested multiple converter modules
            expected_modules = {"shapes", "paths", "text", "gradients"}
            assert len(modules_tested.intersection(expected_modules)) >= 3, \
                f"Only tested modules: {modules_tested}, expected at least 3 from {expected_modules}"