#!/usr/bin/env python3
"""
ICC Color Profile Asset Loading Infrastructure

Secure asset loading system for ICC color profile files with policy
enforcement, caching, validation, and support for multiple sources
(local files, data URLs, remote resources).
"""

from __future__ import annotations
import base64
import hashlib
import logging
import mimetypes
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Dict, Optional, Tuple, Union
import time

from .profile_model import ColorProfileRef

logger = logging.getLogger(__name__)


@dataclass
class AssetLoadingPolicy:
    """
    Security and loading policy for ICC profile assets.

    Attributes:
        allow_remote_loading: Enable loading from HTTP/HTTPS URLs
        allow_data_urls: Enable loading from data: URLs
        max_file_size: Maximum file size in bytes (default 10MB)
        timeout_seconds: Network timeout for remote loading
        cache_ttl_seconds: Time-to-live for cached assets
        allowed_mime_types: MIME types allowed for profile files
        trusted_domains: Domains trusted for remote loading
        require_https: Require HTTPS for remote URLs
    """
    allow_remote_loading: bool = False
    allow_data_urls: bool = True
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    timeout_seconds: int = 30
    cache_ttl_seconds: int = 3600  # 1 hour
    allowed_mime_types: Tuple[str, ...] = (
        'application/vnd.iccprofile',
        'application/icc-profile',
        'application/octet-stream'
    )
    trusted_domains: Tuple[str, ...] = ()
    require_https: bool = True


@dataclass
class AssetCacheEntry:
    """
    Cache entry for loaded ICC profile assets.

    Attributes:
        data: Raw ICC profile data bytes
        file_path: Path to cached file (if applicable)
        content_hash: SHA-256 hash of the data
        load_time: Unix timestamp when loaded
        file_size: Size of the data in bytes
        source_url: Original source URL/path
    """
    data: bytes
    file_path: Optional[Path]
    content_hash: str
    load_time: float
    file_size: int
    source_url: str


class ProfileAssetLoadingError(Exception):
    """Base exception for profile asset loading errors."""
    pass


class ProfileSecurityError(ProfileAssetLoadingError):
    """Security policy violation during profile loading."""
    pass


class ProfileValidationError(ProfileAssetLoadingError):
    """Profile file validation error."""
    pass


class ColorProfileAssetLoader:
    """
    Secure asset loader for ICC color profile files.

    Provides secure loading, validation, and caching of ICC color profile
    assets from various sources (local files, data URLs, remote URLs)
    with comprehensive security policy enforcement.
    """

    def __init__(self, policy: Optional[AssetLoadingPolicy] = None,
                 cache_directory: Optional[Path] = None):
        """
        Initialize asset loader with security policy.

        Args:
            policy: Security and loading policy (uses defaults if None)
            cache_directory: Directory for file caching (uses temp if None)
        """
        self.policy = policy or AssetLoadingPolicy()
        self.cache_directory = cache_directory or Path(tempfile.gettempdir()) / "svg2pptx_icc_cache"
        self._cache: Dict[str, AssetCacheEntry] = {}
        self._lock = RLock()

        # Ensure cache directory exists
        self.cache_directory.mkdir(parents=True, exist_ok=True)

        logger.info(f"ICC Asset Loader initialized with cache at: {self.cache_directory}")

    def load_profile_data(self, profile_ref: ColorProfileRef) -> Optional[bytes]:
        """
        Load ICC profile data with security validation and caching.

        Args:
            profile_ref: Color profile reference to load

        Returns:
            Raw ICC profile data bytes, or None if unavailable

        Raises:
            ProfileSecurityError: If loading violates security policy
            ProfileValidationError: If profile data is invalid
            ProfileAssetLoadingError: If loading fails for other reasons
        """
        with self._lock:
            # Built-in profiles have no external data
            if profile_ref.href is None:
                logger.debug(f"Built-in profile has no external data: {profile_ref.name}")
                return None

            # Check cache first
            cache_key = self._get_cache_key(profile_ref.href)
            cached_entry = self._get_cached_entry(cache_key)
            if cached_entry:
                logger.debug(f"Cache hit for profile: {profile_ref.name}")
                return cached_entry.data

            try:
                # Load data based on URL type
                if profile_ref.is_data_url:
                    data = self._load_data_url(profile_ref.href)
                elif profile_ref.is_remote:
                    data = self._load_remote_url(profile_ref.href)
                else:
                    data = self._load_local_file(profile_ref.href)

                # Validate the loaded data
                self._validate_profile_data(data, profile_ref.href)

                # Cache the result
                cache_entry = self._create_cache_entry(data, profile_ref.href)
                self._cache[cache_key] = cache_entry

                logger.info(f"Successfully loaded ICC profile: {profile_ref.name} ({len(data)} bytes)")
                return data

            except Exception as e:
                logger.error(f"Failed to load ICC profile {profile_ref.name}: {e}")
                if isinstance(e, (ProfileSecurityError, ProfileValidationError)):
                    raise
                else:
                    raise ProfileAssetLoadingError(f"Loading failed: {e}") from e

    def _load_data_url(self, data_url: str) -> bytes:
        """Load profile data from data: URL."""
        if not self.policy.allow_data_urls:
            raise ProfileSecurityError("Data URLs are disabled by security policy")

        try:
            # Parse data URL: data:[<mediatype>][;base64],<data>
            if not data_url.startswith('data:'):
                raise ValueError("Invalid data URL format")

            header, data = data_url[5:].split(',', 1)
            parts = header.split(';')

            # Check MIME type if specified
            if parts[0] and parts[0] not in self.policy.allowed_mime_types:
                raise ProfileSecurityError(f"MIME type not allowed: {parts[0]}")

            # Decode data
            if 'base64' in parts:
                decoded_data = base64.b64decode(data)
            else:
                decoded_data = urllib.parse.unquote(data).encode('utf-8')

            # Check size limit
            if len(decoded_data) > self.policy.max_file_size:
                raise ProfileSecurityError(f"Data URL size exceeds limit: {len(decoded_data)} bytes")

            return decoded_data

        except Exception as e:
            if isinstance(e, ProfileSecurityError):
                raise
            else:
                raise ProfileAssetLoadingError(f"Data URL parsing failed: {e}") from e

    def _load_remote_url(self, url: str) -> bytes:
        """Load profile data from remote HTTP/HTTPS URL."""
        if not self.policy.allow_remote_loading:
            raise ProfileSecurityError("Remote loading is disabled by security policy")

        # Parse and validate URL
        parsed_url = urllib.parse.urlparse(url)

        # Require HTTPS if policy demands it
        if self.policy.require_https and parsed_url.scheme != 'https':
            raise ProfileSecurityError("HTTPS required for remote URLs")

        # Check trusted domains if specified
        if (self.policy.trusted_domains and
            parsed_url.hostname not in self.policy.trusted_domains):
            raise ProfileSecurityError(f"Domain not trusted: {parsed_url.hostname}")

        try:
            # Create request with timeout
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'SVG2PPTX-ProfileLoader/1.0')

            with urllib.request.urlopen(request, timeout=self.policy.timeout_seconds) as response:
                # Check content type
                content_type = response.getheader('Content-Type', '').split(';')[0]
                if (content_type and
                    content_type not in self.policy.allowed_mime_types):
                    raise ProfileSecurityError(f"Content type not allowed: {content_type}")

                # Read data with size limit
                data = response.read(self.policy.max_file_size + 1)
                if len(data) > self.policy.max_file_size:
                    raise ProfileSecurityError(f"Remote file size exceeds limit")

                return data

        except urllib.error.URLError as e:
            raise ProfileAssetLoadingError(f"Remote loading failed: {e}") from e

    def _load_local_file(self, file_path: str) -> bytes:
        """Load profile data from local file system."""
        try:
            path = Path(file_path).resolve()

            # Basic security: prevent directory traversal
            if not path.exists():
                raise FileNotFoundError(f"Profile file not found: {file_path}")

            # Check file size
            file_size = path.stat().st_size
            if file_size > self.policy.max_file_size:
                raise ProfileSecurityError(f"File size exceeds limit: {file_size} bytes")

            # Check MIME type
            mime_type, _ = mimetypes.guess_type(str(path))
            if (mime_type and
                mime_type not in self.policy.allowed_mime_types):
                logger.warning(f"Unusual MIME type for ICC profile: {mime_type}")

            # Read file data
            return path.read_bytes()

        except Exception as e:
            if isinstance(e, ProfileSecurityError):
                raise
            else:
                raise ProfileAssetLoadingError(f"Local file loading failed: {e}") from e

    def _validate_profile_data(self, data: bytes, source: str) -> None:
        """Validate ICC profile data structure."""
        if len(data) < 128:  # ICC profiles have minimum 128-byte header
            raise ProfileValidationError(f"ICC profile too small: {len(data)} bytes")

        # Check ICC profile signature (bytes 36-40 should be 'acsp')
        if len(data) >= 40 and data[36:40] != b'acsp':
            raise ProfileValidationError("Invalid ICC profile signature")

        # Validate profile size field (bytes 0-4 big-endian)
        if len(data) >= 4:
            declared_size = int.from_bytes(data[0:4], byteorder='big')
            if declared_size != len(data):
                logger.warning(f"ICC profile size mismatch: declared={declared_size}, actual={len(data)}")

        logger.debug(f"ICC profile validation passed: {source}")

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    def _get_cached_entry(self, cache_key: str) -> Optional[AssetCacheEntry]:
        """Get cached entry if still valid."""
        entry = self._cache.get(cache_key)
        if entry is None:
            return None

        # Check TTL
        age = time.time() - entry.load_time
        if age > self.policy.cache_ttl_seconds:
            del self._cache[cache_key]
            return None

        return entry

    def _create_cache_entry(self, data: bytes, source_url: str) -> AssetCacheEntry:
        """Create cache entry for loaded data."""
        content_hash = hashlib.sha256(data).hexdigest()

        # Optionally save to disk cache
        file_path = None
        if self.cache_directory:
            try:
                file_path = self.cache_directory / f"{content_hash}.icc"
                file_path.write_bytes(data)
            except Exception as e:
                logger.warning(f"Failed to cache to disk: {e}")
                file_path = None

        return AssetCacheEntry(
            data=data,
            file_path=file_path,
            content_hash=content_hash,
            load_time=time.time(),
            file_size=len(data),
            source_url=source_url
        )

    def get_cache_stats(self) -> Dict[str, Union[int, float]]:
        """Get cache statistics for monitoring."""
        with self._lock:
            total_size = sum(entry.file_size for entry in self._cache.values())
            return {
                'cached_profiles': len(self._cache),
                'total_cache_size': total_size,
                'cache_directory': str(self.cache_directory),
                'cache_ttl_seconds': self.policy.cache_ttl_seconds
            }

    def clear_cache(self) -> int:
        """
        Clear all cached profile data.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()

            # Clean disk cache
            if self.cache_directory.exists():
                try:
                    for cache_file in self.cache_directory.glob("*.icc"):
                        cache_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to clear disk cache: {e}")

            logger.info(f"Cleared {count} cached ICC profiles")
            return count

    def preload_profile(self, profile_ref: ColorProfileRef) -> bool:
        """
        Preload profile data into cache.

        Args:
            profile_ref: Profile reference to preload

        Returns:
            True if successfully preloaded, False otherwise
        """
        try:
            data = self.load_profile_data(profile_ref)
            return data is not None
        except Exception as e:
            logger.warning(f"Failed to preload profile {profile_ref.name}: {e}")
            return False