#!/usr/bin/env python3
"""
Google Slides Integration Tests

Pytest fixtures and integration tests for the Google Slides visual testing pipeline.
Provides comprehensive testing of authentication, conversion, publication, and validation.
"""

import os
import pytest
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Import our modules
from .authenticator import GoogleSlidesAuthenticator, AuthConfig
from .slides_converter import SlidesConverter
from .publisher import SlidesPublisher
from .screenshot_capture import SlidesScreenshotCapture
from .visual_validator import VisualValidator
from .test_runner import GoogleSlidesTestRunner, TestConfig


# Fixtures for testing

@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_svg_content():
    """Simple SVG content for testing."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="blue" stroke="black" stroke-width="2"/>
    <circle cx="50" cy="50" r="20" fill="red" opacity="0.7"/>
    <text x="50" y="90" text-anchor="middle" font-family="Arial" font-size="12">Test SVG</text>
</svg>'''


@pytest.fixture
def sample_svg_file(temp_dir, sample_svg_content):
    """Create sample SVG file for testing."""
    svg_path = temp_dir / "test_sample.svg"
    svg_path.write_text(sample_svg_content)
    return svg_path


@pytest.fixture
def test_config(temp_dir):
    """Test configuration for Google Slides testing."""
    return TestConfig(
        auth_method='service_account',
        credentials_path=None,  # Will be mocked
        cleanup_after_test=False,  # Keep for inspection during tests
        validation_tolerance=0.90,  # Lower threshold for testing
        screenshots_dir=temp_dir / "screenshots",
        references_dir=temp_dir / "references",
        reports_dir=temp_dir / "reports",
        temp_dir=temp_dir / "temp"
    )


@pytest.fixture
def mock_credentials():
    """Mock Google API credentials."""
    mock_creds = Mock()
    mock_creds.valid = True
    mock_creds.expired = False
    return mock_creds


@pytest.fixture
def mock_auth_config():
    """Mock authentication configuration."""
    return AuthConfig(
        method='service_account',
        credentials_path='/fake/path/to/credentials.json'
    )


# Unit Tests

class TestGoogleSlidesAuthenticator:
    """Test authentication functionality."""

    def test_init(self):
        """Test authenticator initialization."""
        auth = GoogleSlidesAuthenticator('service_account')
        assert auth.auth_method == 'service_account'
        assert not auth.is_authenticated

    @patch('tests.visual.google_slides.authenticator.ServiceAccountCredentials')
    @patch('tests.visual.google_slides.authenticator.build')
    def test_service_account_auth(self, mock_build, mock_service_creds, mock_auth_config, mock_credentials):
        """Test service account authentication."""
        # Setup mocks
        mock_service_creds.from_service_account_file.return_value = mock_credentials
        mock_build.return_value = Mock()

        # Create authenticator
        auth = GoogleSlidesAuthenticator('service_account')
        auth.configure(mock_auth_config)

        # Mock file existence
        with patch('os.path.exists', return_value=True):
            result = auth.authenticate()

        assert result is True
        assert auth.is_authenticated

    def test_invalid_auth_method(self):
        """Test invalid authentication method."""
        auth = GoogleSlidesAuthenticator('invalid_method')
        result = auth.authenticate()
        assert result is False


class TestSlidesConverter:
    """Test PPTX to Google Slides conversion."""

    @pytest.fixture
    def mock_authenticated_auth(self, mock_credentials):
        """Mock authenticated authenticator."""
        auth = Mock()
        auth.is_authenticated = True
        auth.get_drive_service.return_value = Mock()
        auth.get_slides_service.return_value = Mock()
        return auth

    def test_init_with_unauthenticated_auth(self):
        """Test initialization with unauthenticated authenticator."""
        auth = Mock()
        auth.is_authenticated = False

        with pytest.raises(ValueError, match="Authenticator must be authenticated"):
            SlidesConverter(auth)

    def test_init_with_authenticated_auth(self, mock_authenticated_auth):
        """Test initialization with authenticated authenticator."""
        converter = SlidesConverter(mock_authenticated_auth)
        assert converter.auth == mock_authenticated_auth

    def test_upload_nonexistent_file(self, mock_authenticated_auth, temp_dir):
        """Test uploading non-existent PPTX file."""
        converter = SlidesConverter(mock_authenticated_auth)
        nonexistent_file = temp_dir / "nonexistent.pptx"

        with pytest.raises(FileNotFoundError):
            converter.upload_pptx_to_drive(nonexistent_file)


class TestSlidesPublisher:
    """Test presentation publishing functionality."""

    @pytest.fixture
    def mock_authenticated_auth(self):
        """Mock authenticated authenticator."""
        auth = Mock()
        auth.is_authenticated = True
        auth.get_drive_service.return_value = Mock()
        auth.get_slides_service.return_value = Mock()
        return auth

    def test_init(self, mock_authenticated_auth):
        """Test publisher initialization."""
        publisher = SlidesPublisher(mock_authenticated_auth)
        assert publisher.auth == mock_authenticated_auth

    def test_get_embed_url(self, mock_authenticated_auth):
        """Test embed URL generation."""
        publisher = SlidesPublisher(mock_authenticated_auth)
        presentation_id = "test_presentation_id"

        embed_url = publisher.get_embed_url(presentation_id)
        expected_url = f"https://docs.google.com/presentation/d/{presentation_id}/embed"

        assert embed_url == expected_url

    def test_get_embed_url_with_slide(self, mock_authenticated_auth):
        """Test embed URL generation with specific slide."""
        publisher = SlidesPublisher(mock_authenticated_auth)
        presentation_id = "test_presentation_id"
        slide_id = "test_slide_id"

        embed_url = publisher.get_embed_url(presentation_id, slide_id)
        expected_url = f"https://docs.google.com/presentation/d/{presentation_id}/embed?slide=id.{slide_id}"

        assert embed_url == expected_url


class TestVisualValidator:
    """Test visual validation functionality."""

    def test_init(self):
        """Test validator initialization."""
        validator = VisualValidator(tolerance=0.95)
        assert validator.tolerance == 0.95

    def test_normalize_image_sizes(self, temp_dir):
        """Test image size normalization."""
        from PIL import Image

        validator = VisualValidator()

        # Create test images with different sizes
        img1 = Image.new('RGB', (100, 100), color='red')
        img2 = Image.new('RGB', (200, 150), color='blue')

        normalized_img1, normalized_img2 = validator._normalize_image_sizes(img1, img2)

        # Should be resized to smaller dimensions
        assert normalized_img1.size == (100, 100)
        assert normalized_img2.size == (100, 100)

    def test_compare_nonexistent_images(self, temp_dir):
        """Test comparison of non-existent images."""
        validator = VisualValidator()

        nonexistent1 = temp_dir / "fake1.png"
        nonexistent2 = temp_dir / "fake2.png"

        similarity = validator.compare_images(nonexistent1, nonexistent2)
        assert similarity == 0.0


class TestGoogleSlidesTestRunner:
    """Test the complete test runner."""

    def test_init_with_config_dict(self, temp_dir):
        """Test initialization with config dictionary."""
        config_dict = {
            'auth_method': 'service_account',
            'validation_tolerance': 0.95,
            'screenshots_dir': temp_dir / "screenshots"
        }

        runner = GoogleSlidesTestRunner(config_dict)
        assert runner.config.auth_method == 'service_account'
        assert runner.config.validation_tolerance == 0.95

    def test_init_with_config_object(self, test_config):
        """Test initialization with TestConfig object."""
        runner = GoogleSlidesTestRunner(test_config)
        assert runner.config == test_config

    @pytest.mark.asyncio
    async def test_initialize_without_credentials(self, test_config):
        """Test initialization without valid credentials."""
        runner = GoogleSlidesTestRunner(test_config)

        # Should fail without valid credentials
        result = await runner.initialize()
        assert result is False


# Integration Tests (require actual Google API credentials)

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv('GOOGLE_SLIDES_TEST_CREDENTIALS'),
    reason="Google Slides credentials not provided"
)
class TestGoogleSlidesIntegration:
    """Integration tests requiring actual Google API access."""

    @pytest.fixture
    def real_auth_config(self):
        """Real authentication configuration from environment."""
        creds_path = os.getenv('GOOGLE_SLIDES_TEST_CREDENTIALS')
        return AuthConfig(
            method='service_account',
            credentials_path=creds_path
        )

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self, real_auth_config):
        """Test complete authentication flow with real credentials."""
        auth = GoogleSlidesAuthenticator('service_account')
        auth.configure(real_auth_config)

        # Authenticate
        auth_result = auth.authenticate()
        assert auth_result is True
        assert auth.is_authenticated

        # Test API access
        test_result = auth.test_authentication()
        assert test_result['authenticated'] is True
        assert test_result['drive_access'] is True
        assert test_result['slides_access'] is True

    @pytest.mark.asyncio
    async def test_end_to_end_pipeline(self, sample_svg_file, test_config, real_auth_config):
        """Test complete end-to-end pipeline with real APIs."""
        # Update config with real credentials
        test_config.credentials_path = real_auth_config.credentials_path

        runner = GoogleSlidesTestRunner(test_config)

        # Initialize
        init_result = await runner.initialize()
        assert init_result is True

        try:
            # Run test
            result = await runner.run_test(sample_svg_file, "integration_test")

            # Verify results
            assert result.success is True
            assert result.pptx_path is not None
            assert result.presentation_id is not None
            assert result.public_url is not None
            assert len(result.screenshot_results) > 0

            # Check screenshots
            successful_screenshots = sum(1 for s in result.screenshot_results if s.success)
            assert successful_screenshots > 0

        finally:
            # Cleanup
            await runner.cleanup()


# Performance Tests

@pytest.mark.performance
class TestPerformance:
    """Performance tests for the visual testing pipeline."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires real API credentials and is slow")
    async def test_batch_processing_performance(self, temp_dir, test_config):
        """Test performance of batch processing multiple SVG files."""
        import time

        # Create multiple test SVG files
        svg_files = []
        for i in range(5):
            svg_path = temp_dir / f"test_performance_{i}.svg"
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="{i*10}" y="{i*10}" width="50" height="50" fill="blue"/>
</svg>'''
            svg_path.write_text(svg_content)
            svg_files.append(svg_path)

        runner = GoogleSlidesTestRunner(test_config)
        await runner.initialize()

        start_time = time.time()
        results = await runner.run_batch_tests(svg_files)
        total_time = time.time() - start_time

        # Performance assertions
        assert len(results) == 5
        assert total_time < 300  # Should complete within 5 minutes

        await runner.cleanup()


# Utility functions for testing

def create_mock_presentation_response():
    """Create mock Google Slides presentation response."""
    return {
        'presentationId': 'mock_presentation_id',
        'title': 'Mock Presentation',
        'slides': [
            {'objectId': 'slide_1'},
            {'objectId': 'slide_2'}
        ],
        'pageSize': {
            'magnitude': {'width': 10, 'height': 7.5},
            'unit': 'INCH'
        }
    }


def create_mock_drive_file_response():
    """Create mock Google Drive file response."""
    return {
        'id': 'mock_file_id',
        'name': 'Mock Presentation',
        'webViewLink': 'https://docs.google.com/presentation/d/mock_file_id/edit',
        'size': '1024'
    }


# Pytest configuration

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring API access"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test (slow)"
    )


# Test data creation helpers

def create_test_svg_files(output_dir: Path, count: int = 3) -> List[Path]:
    """Create test SVG files for batch testing."""
    svg_files = []

    templates = [
        # Simple shapes
        '''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
            <rect x="50" y="50" width="100" height="100" fill="blue"/>
        </svg>''',

        # Gradient
        '''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
                    <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
                </linearGradient>
            </defs>
            <ellipse cx="100" cy="100" rx="80" ry="40" fill="url(#grad1)" />
        </svg>''',

        # Text
        '''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
            <text x="100" y="100" text-anchor="middle" font-family="Arial" font-size="16">
                Hello World
            </text>
        </svg>'''
    ]

    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(count):
        template = templates[i % len(templates)]
        svg_path = output_dir / f"test_svg_{i+1:03d}.svg"
        svg_path.write_text(template)
        svg_files.append(svg_path)

    return svg_files