#!/usr/bin/env python3
"""
Unit tests for ColorProfileAssetLoader.

Tests secure asset loading, validation, caching, and policy enforcement
for ICC color profile files from various sources.
"""

import base64
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import urllib.error

from core.color.profile_asset_loader import (
    ColorProfileAssetLoader,
    AssetLoadingPolicy,
    AssetCacheEntry,
    ProfileAssetLoadingError,
    ProfileSecurityError,
    ProfileValidationError
)
from core.color.profile_model import ColorProfileRef


# Mock ICC profile data (minimal valid structure)
MOCK_ICC_DATA = (
    b'\x00\x00\x01\x00'  # Profile size (256 bytes)
    + b'\x00' * 32       # Reserved fields
    + b'acsp'            # Profile signature at offset 36
    + b'\x00' * 92       # Remaining header
    + b'\x00' * 128      # Profile data to reach 256 bytes
)

MOCK_DATA_URL = f"data:application/vnd.iccprofile;base64,{base64.b64encode(MOCK_ICC_DATA).decode()}"


class TestAssetLoadingPolicy:
    """Test AssetLoadingPolicy configuration."""

    def test_default_policy(self):
        """Test default policy values."""
        policy = AssetLoadingPolicy()
        assert policy.allow_remote_loading is False
        assert policy.allow_data_urls is True
        assert policy.max_file_size == 10 * 1024 * 1024
        assert policy.timeout_seconds == 30
        assert policy.cache_ttl_seconds == 3600
        assert 'application/vnd.iccprofile' in policy.allowed_mime_types
        assert policy.trusted_domains == ()
        assert policy.require_https is True

    def test_custom_policy(self):
        """Test custom policy configuration."""
        policy = AssetLoadingPolicy(
            allow_remote_loading=True,
            allow_data_urls=False,
            max_file_size=1024,
            timeout_seconds=10,
            trusted_domains=('example.com', 'trusted.org'),
            require_https=False
        )
        assert policy.allow_remote_loading is True
        assert policy.allow_data_urls is False
        assert policy.max_file_size == 1024
        assert policy.timeout_seconds == 10
        assert policy.trusted_domains == ('example.com', 'trusted.org')
        assert policy.require_https is False


class TestAssetCacheEntry:
    """Test AssetCacheEntry data structure."""

    def test_cache_entry_creation(self):
        """Test cache entry creation."""
        entry = AssetCacheEntry(
            data=b'test data',
            file_path=Path('/tmp/test.icc'),
            content_hash='abc123',
            load_time=1234567890.0,
            file_size=9,
            source_url='test://example'
        )
        assert entry.data == b'test data'
        assert entry.file_path == Path('/tmp/test.icc')
        assert entry.content_hash == 'abc123'
        assert entry.load_time == 1234567890.0
        assert entry.file_size == 9
        assert entry.source_url == 'test://example'


class TestColorProfileAssetLoader:
    """Test ColorProfileAssetLoader core functionality."""

    def test_initialization_default(self):
        """Test loader initialization with defaults."""
        loader = ColorProfileAssetLoader()
        assert loader.policy.allow_remote_loading is False
        assert loader.policy.allow_data_urls is True
        assert loader.cache_directory.exists()

    def test_initialization_custom_policy(self):
        """Test loader initialization with custom policy."""
        policy = AssetLoadingPolicy(allow_remote_loading=True)
        loader = ColorProfileAssetLoader(policy=policy)
        assert loader.policy.allow_remote_loading is True

    def test_initialization_custom_cache_dir(self):
        """Test loader initialization with custom cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "test_cache"
            loader = ColorProfileAssetLoader(cache_directory=cache_dir)
            assert loader.cache_directory == cache_dir
            assert cache_dir.exists()

    def test_builtin_profile_no_data(self):
        """Test that built-in profiles return None for data."""
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="srgb")  # No href = built-in

        result = loader.load_profile_data(profile)
        assert result is None


class TestDataURLLoading:
    """Test data: URL loading functionality."""

    def test_load_valid_data_url(self):
        """Test loading valid data URL."""
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href=MOCK_DATA_URL)

        result = loader.load_profile_data(profile)
        assert result == MOCK_ICC_DATA

    def test_load_data_url_disabled(self):
        """Test data URL loading when disabled by policy."""
        policy = AssetLoadingPolicy(allow_data_urls=False)
        loader = ColorProfileAssetLoader(policy=policy)
        profile = ColorProfileRef(name="test", href=MOCK_DATA_URL)

        with pytest.raises(ProfileSecurityError, match="Data URLs are disabled"):
            loader.load_profile_data(profile)

    def test_load_data_url_invalid_format(self):
        """Test loading invalid data URL format."""
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href="invalid:url")

        with pytest.raises(ProfileAssetLoadingError):
            loader.load_profile_data(profile)

    def test_load_data_url_wrong_mime_type(self):
        """Test data URL with disallowed MIME type."""
        data_url = "data:text/plain;base64," + base64.b64encode(MOCK_ICC_DATA).decode()
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href=data_url)

        with pytest.raises(ProfileSecurityError, match="MIME type not allowed"):
            loader.load_profile_data(profile)

    def test_load_data_url_size_limit(self):
        """Test data URL exceeding size limit."""
        large_data = b'x' * 1000
        data_url = f"data:application/vnd.iccprofile;base64,{base64.b64encode(large_data).decode()}"
        policy = AssetLoadingPolicy(max_file_size=500)
        loader = ColorProfileAssetLoader(policy=policy)
        profile = ColorProfileRef(name="test", href=data_url)

        with pytest.raises(ProfileSecurityError, match="size exceeds limit"):
            loader.load_profile_data(profile)

    def test_load_data_url_url_encoded(self):
        """Test data URL with URL encoding (non-base64)."""
        url_encoded_data = "Hello%20World"
        data_url = f"data:application/vnd.iccprofile,{url_encoded_data}"
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href=data_url)

        # This should fail validation due to invalid ICC data
        with pytest.raises(ProfileValidationError):
            loader.load_profile_data(profile)


class TestRemoteURLLoading:
    """Test remote HTTP/HTTPS URL loading."""

    def test_remote_loading_disabled(self):
        """Test remote loading when disabled by policy."""
        loader = ColorProfileAssetLoader()  # Default policy disables remote
        profile = ColorProfileRef(name="test", href="https://example.com/profile.icc")

        with pytest.raises(ProfileSecurityError, match="Remote loading is disabled"):
            loader.load_profile_data(profile)

    def test_remote_loading_requires_https(self):
        """Test HTTPS requirement for remote URLs."""
        policy = AssetLoadingPolicy(allow_remote_loading=True, require_https=True)
        loader = ColorProfileAssetLoader(policy=policy)
        profile = ColorProfileRef(name="test", href="http://example.com/profile.icc")

        with pytest.raises(ProfileSecurityError, match="HTTPS required"):
            loader.load_profile_data(profile)

    def test_remote_loading_untrusted_domain(self):
        """Test loading from untrusted domain."""
        policy = AssetLoadingPolicy(
            allow_remote_loading=True,
            trusted_domains=('trusted.com',),
            require_https=False
        )
        loader = ColorProfileAssetLoader(policy=policy)
        profile = ColorProfileRef(name="test", href="http://untrusted.com/profile.icc")

        with pytest.raises(ProfileSecurityError, match="Domain not trusted"):
            loader.load_profile_data(profile)

    @patch('urllib.request.urlopen')
    def test_remote_loading_success(self, mock_urlopen):
        """Test successful remote loading."""
        mock_response = Mock()
        mock_response.read.return_value = MOCK_ICC_DATA
        mock_response.getheader.return_value = 'application/vnd.iccprofile'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        policy = AssetLoadingPolicy(allow_remote_loading=True, require_https=False)
        loader = ColorProfileAssetLoader(policy=policy)
        profile = ColorProfileRef(name="test", href="http://example.com/profile.icc")

        result = loader.load_profile_data(profile)
        assert result == MOCK_ICC_DATA

    @patch('urllib.request.urlopen')
    def test_remote_loading_wrong_content_type(self, mock_urlopen):
        """Test remote loading with wrong content type."""
        mock_response = Mock()
        mock_response.read.return_value = MOCK_ICC_DATA
        mock_response.getheader.return_value = 'text/html'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        policy = AssetLoadingPolicy(allow_remote_loading=True, require_https=False)
        loader = ColorProfileAssetLoader(policy=policy)
        profile = ColorProfileRef(name="test", href="http://example.com/profile.icc")

        with pytest.raises(ProfileSecurityError, match="Content type not allowed"):
            loader.load_profile_data(profile)

    @patch('urllib.request.urlopen')
    def test_remote_loading_size_limit(self, mock_urlopen):
        """Test remote loading size limit enforcement."""
        large_data = b'x' * 1000
        mock_response = Mock()
        mock_response.read.return_value = large_data
        mock_response.getheader.return_value = 'application/vnd.iccprofile'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        policy = AssetLoadingPolicy(
            allow_remote_loading=True,
            require_https=False,
            max_file_size=500
        )
        loader = ColorProfileAssetLoader(policy=policy)
        profile = ColorProfileRef(name="test", href="http://example.com/profile.icc")

        with pytest.raises(ProfileSecurityError, match="size exceeds limit"):
            loader.load_profile_data(profile)

    @patch('urllib.request.urlopen')
    def test_remote_loading_network_error(self, mock_urlopen):
        """Test remote loading network error handling."""
        mock_urlopen.side_effect = urllib.error.URLError("Network error")

        policy = AssetLoadingPolicy(allow_remote_loading=True, require_https=False)
        loader = ColorProfileAssetLoader(policy=policy)
        profile = ColorProfileRef(name="test", href="http://example.com/profile.icc")

        with pytest.raises(ProfileAssetLoadingError, match="Remote loading failed"):
            loader.load_profile_data(profile)


class TestLocalFileLoading:
    """Test local file system loading."""

    def test_load_local_file_success(self):
        """Test successful local file loading."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(MOCK_ICC_DATA)
            tmp_path = tmp_file.name

        try:
            loader = ColorProfileAssetLoader()
            profile = ColorProfileRef(name="test", href=tmp_path)

            result = loader.load_profile_data(profile)
            assert result == MOCK_ICC_DATA
        finally:
            Path(tmp_path).unlink()

    def test_load_local_file_not_found(self):
        """Test loading non-existent local file."""
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href="/nonexistent/file.icc")

        with pytest.raises(ProfileAssetLoadingError, match="Local file loading failed"):
            loader.load_profile_data(profile)

    def test_load_local_file_size_limit(self):
        """Test local file size limit enforcement."""
        large_data = b'x' * 1000
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(large_data)
            tmp_path = tmp_file.name

        try:
            policy = AssetLoadingPolicy(max_file_size=500)
            loader = ColorProfileAssetLoader(policy=policy)
            profile = ColorProfileRef(name="test", href=tmp_path)

            with pytest.raises(ProfileSecurityError, match="size exceeds limit"):
                loader.load_profile_data(profile)
        finally:
            Path(tmp_path).unlink()


class TestProfileValidation:
    """Test ICC profile data validation."""

    def test_validate_valid_profile(self):
        """Test validation of valid ICC profile."""
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href=MOCK_DATA_URL)

        # Should not raise any exceptions
        result = loader.load_profile_data(profile)
        assert result == MOCK_ICC_DATA

    def test_validate_too_small(self):
        """Test validation of too-small profile."""
        small_data = b'tiny'
        data_url = f"data:application/vnd.iccprofile;base64,{base64.b64encode(small_data).decode()}"
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href=data_url)

        with pytest.raises(ProfileValidationError, match="too small"):
            loader.load_profile_data(profile)

    def test_validate_invalid_signature(self):
        """Test validation of invalid ICC signature."""
        invalid_data = b'\x00\x00\x01\x00' + b'\x00' * 32 + b'XXXX' + b'\x00' * 220
        data_url = f"data:application/vnd.iccprofile;base64,{base64.b64encode(invalid_data).decode()}"
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href=data_url)

        with pytest.raises(ProfileValidationError, match="Invalid ICC profile signature"):
            loader.load_profile_data(profile)


class TestCaching:
    """Test caching functionality."""

    def test_cache_hit(self):
        """Test cache hit on second load."""
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href=MOCK_DATA_URL)

        # First load
        result1 = loader.load_profile_data(profile)
        assert result1 == MOCK_ICC_DATA

        # Second load should hit cache
        result2 = loader.load_profile_data(profile)
        assert result2 == MOCK_ICC_DATA

        # Verify cache statistics
        stats = loader.get_cache_stats()
        assert stats['cached_profiles'] == 1

    def test_cache_ttl_expiry(self):
        """Test cache TTL expiry."""
        policy = AssetLoadingPolicy(cache_ttl_seconds=0)  # Immediate expiry
        loader = ColorProfileAssetLoader(policy=policy)
        profile = ColorProfileRef(name="test", href=MOCK_DATA_URL)

        # First load
        result1 = loader.load_profile_data(profile)
        assert result1 == MOCK_ICC_DATA

        # Second load should miss cache due to TTL
        result2 = loader.load_profile_data(profile)
        assert result2 == MOCK_ICC_DATA

        # Cache should be empty due to TTL expiry
        stats = loader.get_cache_stats()
        assert stats['cached_profiles'] == 1  # New entry added

    def test_clear_cache(self):
        """Test cache clearing."""
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href=MOCK_DATA_URL)

        # Load to populate cache
        loader.load_profile_data(profile)
        assert loader.get_cache_stats()['cached_profiles'] == 1

        # Clear cache
        cleared_count = loader.clear_cache()
        assert cleared_count == 1
        assert loader.get_cache_stats()['cached_profiles'] == 0

    def test_preload_profile(self):
        """Test profile preloading."""
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href=MOCK_DATA_URL)

        # Preload should succeed
        result = loader.preload_profile(profile)
        assert result is True

        # Cache should contain the profile
        stats = loader.get_cache_stats()
        assert stats['cached_profiles'] == 1

    def test_preload_profile_failure(self):
        """Test profile preloading failure."""
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href="/nonexistent/file.icc")

        # Preload should fail gracefully
        result = loader.preload_profile(profile)
        assert result is False

        # Cache should remain empty
        stats = loader.get_cache_stats()
        assert stats['cached_profiles'] == 0


class TestCacheStatistics:
    """Test cache statistics and monitoring."""

    def test_get_cache_stats_empty(self):
        """Test cache statistics when empty."""
        loader = ColorProfileAssetLoader()
        stats = loader.get_cache_stats()

        assert stats['cached_profiles'] == 0
        assert stats['total_cache_size'] == 0
        assert 'cache_directory' in stats
        assert 'cache_ttl_seconds' in stats

    def test_get_cache_stats_with_data(self):
        """Test cache statistics with cached data."""
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href=MOCK_DATA_URL)

        # Load to populate cache
        loader.load_profile_data(profile)

        stats = loader.get_cache_stats()
        assert stats['cached_profiles'] == 1
        assert stats['total_cache_size'] == len(MOCK_ICC_DATA)


class TestErrorHandling:
    """Test error handling and exception types."""

    def test_profile_security_error_inheritance(self):
        """Test ProfileSecurityError inheritance."""
        assert issubclass(ProfileSecurityError, ProfileAssetLoadingError)

    def test_profile_validation_error_inheritance(self):
        """Test ProfileValidationError inheritance."""
        assert issubclass(ProfileValidationError, ProfileAssetLoadingError)

    def test_error_context_preservation(self):
        """Test that error context is preserved in exceptions."""
        loader = ColorProfileAssetLoader()
        profile = ColorProfileRef(name="test", href="/nonexistent/file.icc")

        try:
            loader.load_profile_data(profile)
        except ProfileAssetLoadingError as e:
            assert "Local file loading failed" in str(e)
            assert e.__cause__ is not None  # Original exception preserved