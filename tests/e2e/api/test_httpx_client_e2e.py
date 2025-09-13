#!/usr/bin/env python3
"""
E2E tests using httpx client for more realistic HTTP testing of FastAPI service.

Tests HTTP behavior, async operations, and real network patterns.
"""

import pytest
import httpx
import asyncio
import json
import time
from typing import Dict, Any
from unittest.mock import patch, Mock
from pathlib import Path
import sys

# Import the FastAPI app and ASGI transport
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from api.main import app
from api.auth import get_current_user


class TestHttpxClientE2E:
    """E2E tests using httpx async client for realistic HTTP testing."""
    
    @pytest.fixture
    def httpx_client(self):
        """Create httpx async test client."""
        # Mock authentication dependency  
        def mock_get_current_user():
            return {
                "user_id": "httpx_test_user",
                "email": "httpx@example.com", 
                "name": "HTTPX Test User",
                "api_key": "test_httpx_key"
            }
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        # Create httpx client with ASGI transport for FastAPI
        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        
        yield client
        
        # Clean up dependency overrides
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for httpx requests."""
        return {"Authorization": "Bearer test_httpx_api_key"}
    
    @pytest.fixture
    def mock_conversion_service(self):
        """Mock conversion service for httpx testing."""
        with patch('api.main.ConversionService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            # Mock successful conversion response
            mock_instance.convert_and_upload.return_value = {
                "success": True,
                "file_id": "httpx_test_file_123",
                "file_name": "httpx_converted.pptx", 
                "drive_link": "https://drive.google.com/file/d/httpx_test_file_123/view",
                "thumbnails": [
                    {
                        "slide_number": 1,
                        "thumbnail_url": "https://example.com/httpx_thumb1.png"
                    }
                ],
                "conversion_time": 1.8,
                "file_size": 54321
            }
            
            yield mock_instance

    @pytest.mark.asyncio
    async def test_async_health_check(self, httpx_client):
        """Test health check using async httpx client."""
        async with httpx_client as client:
            response = await client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "svg2pptx-api"
            assert data["version"] == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_async_api_documentation(self, httpx_client):
        """Test API documentation endpoints with async client."""
        async with httpx_client as client:
            # Test OpenAPI JSON schema
            response = await client.get("/openapi.json")
            assert response.status_code == 200
            
            schema = response.json()
            assert "openapi" in schema
            assert "info" in schema
            assert schema["info"]["title"] == "SVG to Google Drive API"
    
    @pytest.mark.asyncio
    async def test_async_conversion_workflow(self, httpx_client, auth_headers, mock_conversion_service):
        """Test complete conversion workflow using async httpx client."""
        svg_url = "https://example.com/httpx_test.svg"
        
        async with httpx_client as client:
            # Send conversion request
            response = await client.post(
                "/convert",
                params={"url": svg_url},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["file_id"] == "httpx_test_file_123"
            assert data["file_name"] == "httpx_converted.pptx"
            assert "drive_link" in data
            assert "thumbnails" in data
            assert "conversion_time" in data
            assert data["conversion_time"] == 1.8
            
            # Verify service was called correctly
            mock_conversion_service.convert_and_upload.assert_called_once()
            call_args = mock_conversion_service.convert_and_upload.call_args
            assert call_args[0][0] == svg_url
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, httpx_client, auth_headers, mock_conversion_service):
        """Test handling multiple concurrent requests with httpx."""
        urls = [
            "https://example.com/concurrent1.svg",
            "https://example.com/concurrent2.svg", 
            "https://example.com/concurrent3.svg",
            "https://example.com/concurrent4.svg",
            "https://example.com/concurrent5.svg"
        ]
        
        # Create concurrent conversion requests
        tasks = []
        for url in urls:
            task = httpx_client.post(
                "/convert",
                params={"url": url},
                headers=auth_headers
            )
            tasks.append(task)
        
        # Execute all requests concurrently
        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify all requests succeeded
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "file_id" in data
        
        # Verify concurrent execution was faster than sequential
        total_time = end_time - start_time
        assert total_time < 2.0  # Should be much faster than 5 sequential calls
        
        # Verify service was called for each request
        assert mock_conversion_service.convert_and_upload.call_count == 5
    
    @pytest.mark.asyncio
    async def test_request_timeout_handling(self, httpx_client, auth_headers):
        """Test httpx client timeout configuration."""
        # Test with very short timeout
        timeout_config = httpx.Timeout(0.001)  # 1ms timeout
        
        # This should timeout for most requests
        with pytest.raises((httpx.TimeoutException, httpx.ReadTimeout)):
            async with httpx.AsyncClient(
                app=app, 
                base_url="http://testserver",
                timeout=timeout_config
            ) as timeout_client:
                await timeout_client.get("/health")
    
    @pytest.mark.asyncio
    async def test_error_response_handling(self, httpx_client, auth_headers):
        """Test error response handling with httpx client."""
        # Test missing URL parameter
        response = await httpx_client.post(
            "/convert",
            params={},  # Missing required URL
            headers=auth_headers
        )
        
        assert response.status_code == 422  # FastAPI validation error
        error_data = response.json()
        assert "detail" in error_data
        
        # Test invalid URL
        response = await httpx_client.post(
            "/convert", 
            params={"url": "not-a-url"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "error" in error_data
        assert error_data["error"] is True
    
    @pytest.mark.asyncio
    async def test_http_method_restrictions(self, httpx_client, auth_headers):
        """Test HTTP method restrictions on endpoints."""
        # Test that GET is not allowed on /convert
        response = await httpx_client.get(
            "/convert",
            headers=auth_headers
        )
        assert response.status_code == 405  # Method Not Allowed
        
        # Test that POST is not allowed on /health
        response = await httpx_client.post("/health")
        assert response.status_code == 405  # Method Not Allowed
    
    @pytest.mark.asyncio
    async def test_cors_headers(self, httpx_client):
        """Test CORS headers in responses."""
        # Test OPTIONS request
        response = await httpx_client.options("/health")
        
        # Should have CORS headers configured
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
    
    @pytest.mark.asyncio
    async def test_request_response_headers(self, httpx_client, auth_headers, mock_conversion_service):
        """Test request and response headers with httpx."""
        # Custom headers in request
        custom_headers = {
            **auth_headers,
            "X-Test-Client": "httpx-e2e",
            "X-Request-ID": "test-123"
        }
        
        response = await httpx_client.post(
            "/convert",
            params={"url": "https://example.com/headers_test.svg"},
            headers=custom_headers
        )
        
        assert response.status_code == 200
        
        # Check response headers
        assert response.headers["content-type"] == "application/json"
        
        # Verify JSON response
        data = response.json()
        assert data["success"] is True


class TestHttpxRealWorldScenarios:
    """Real-world HTTP scenario testing with httpx client."""
    
    @pytest.fixture
    async def httpx_client(self):
        """Create httpx async test client with real-world configuration."""
        def mock_get_current_user():
            return {
                "user_id": "realworld_user",
                "email": "realworld@company.com",
                "name": "Real World User"
            }
        
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        # Configure httpx client with realistic settings
        timeout = httpx.Timeout(10.0, connect=5.0, read=30.0)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        
        async with httpx.AsyncClient(
            app=app,
            base_url="http://testserver",
            timeout=timeout,
            limits=limits,
            follow_redirects=True
        ) as client:
            yield client
        
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_batch_conversion_workflow(self, httpx_client):
        """Test batch conversion workflow simulating real usage."""
        with patch('api.main.ConversionService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            # Simulate varied response times and results
            conversion_results = [
                {
                    "success": True,
                    "file_id": f"batch_file_{i}",
                    "file_name": f"batch_{i}.pptx",
                    "conversion_time": 1.5 + (i * 0.3),
                    "file_size": 40000 + (i * 5000)
                }
                for i in range(1, 6)
            ]
            
            mock_instance.convert_and_upload.side_effect = conversion_results
            
            # Submit batch of conversions
            batch_urls = [
                f"https://design-tool.com/export_{i}.svg"
                for i in range(1, 6)
            ]
            
            results = []
            for url in batch_urls:
                response = await httpx_client.post(
                    "/convert",
                    params={"url": url},
                    headers={"Authorization": "Bearer batch_api_key"}
                )
                results.append(response.json())
            
            # Verify all conversions succeeded
            assert len(results) == 5
            for i, result in enumerate(results, 1):
                assert result["success"] is True
                assert result["file_id"] == f"batch_file_{i}"
                assert result["conversion_time"] >= 1.5
    
    @pytest.mark.asyncio
    async def test_api_usage_patterns(self, httpx_client):
        """Test realistic API usage patterns."""
        auth_headers = {"Authorization": "Bearer usage_pattern_key"}
        
        with patch('api.main.ConversionService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.convert_and_upload.return_value = {
                "success": True,
                "file_id": "pattern_test_123",
                "file_name": "pattern_test.pptx"
            }
            
            # Pattern 1: Quick health checks
            for _ in range(3):
                response = await httpx_client.get("/health")
                assert response.status_code == 200
            
            # Pattern 2: Single conversion
            response = await httpx_client.post(
                "/convert",
                params={"url": "https://app.figma.com/export123.svg"},
                headers=auth_headers
            )
            assert response.status_code == 200
            
            # Pattern 3: Conversion with options
            response = await httpx_client.post(
                "/convert", 
                params={
                    "url": "https://illustrator.adobe.com/export456.svg",
                    "preprocessing": "aggressive",
                    "precision": 9
                },
                headers=auth_headers
            )
            assert response.status_code == 200
            
            # Verify realistic call pattern
            assert mock_instance.convert_and_upload.call_count == 2