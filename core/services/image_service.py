#!/usr/bin/env python3
"""
ImageService for handling image processing, validation, and metadata extraction.

Provides centralized image management for SVG to PPTX conversion including:
- Image format validation and conversion
- Metadata extraction (dimensions, format, file size)
- Base64 data URL processing
- File path resolution and validation
- Image optimization and caching
"""

import base64
import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

# Optional PIL import for image processing
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger(__name__)


@dataclass
class ImageInfo:
    """Container for image metadata and content."""
    width: int
    height: int
    format: str
    file_size: int
    content: bytes | None = None
    temp_path: str | None = None
    embed_id: str | None = None


class ImageService:
    """Service for managing image resources in SVG to PPTX conversion."""

    def __init__(self, enable_caching: bool = True):
        self.enable_caching = enable_caching
        self._image_cache: dict[str, ImageInfo] = {}
        self._temp_files: set = set()

    def process_image_source(self, image_source: str, base_path: str | None = None) -> ImageInfo | None:
        """Process image source and return ImageInfo with metadata.

        Args:
            image_source: Image source (data URL, file path, or web URL)
            base_path: Base directory for resolving relative paths

        Returns:
            ImageInfo object with metadata and content, or None if processing failed
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(image_source, base_path)
            if self.enable_caching and cache_key in self._image_cache:
                return self._image_cache[cache_key]

            image_info = None

            if image_source.startswith('data:'):
                image_info = self._process_data_url(image_source)
            elif image_source.startswith(('http://', 'https://')):
                image_info = self._process_web_url(image_source)
            else:
                image_info = self._process_file_path(image_source, base_path)

            # Cache successful result
            if image_info and self.enable_caching:
                self._image_cache[cache_key] = image_info

            return image_info

        except Exception as e:
            logger.error(f"Failed to process image source '{image_source}': {e}")
            return None

    def _process_data_url(self, data_url: str) -> ImageInfo | None:
        """Process data URL and extract image content."""
        try:
            if ';base64,' not in data_url:
                logger.warning(f"Unsupported data URL format: {data_url[:50]}...")
                return None

            # Parse data URL: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...
            header, data = data_url.split(';base64,', 1)
            mime_type = header.split(':', 1)[1]

            # Decode base64 data
            image_data = base64.b64decode(data)
            file_size = len(image_data)

            # Determine format from MIME type
            format_map = {
                'image/png': 'PNG',
                'image/jpeg': 'JPEG',
                'image/jpg': 'JPEG',
                'image/gif': 'GIF',
                'image/bmp': 'BMP',
                'image/webp': 'WEBP',
            }
            image_format = format_map.get(mime_type, 'UNKNOWN')

            # Get dimensions using PIL if available
            width, height = self._get_image_dimensions_from_bytes(image_data)

            # Create temporary file
            extension = self._get_extension_for_format(image_format)
            temp_path = self._create_temp_file(image_data, extension)

            return ImageInfo(
                width=width,
                height=height,
                format=image_format,
                file_size=file_size,
                content=image_data,
                temp_path=temp_path,
            )

        except Exception as e:
            logger.error(f"Failed to process data URL: {e}")
            return None

    def _process_file_path(self, file_path: str, base_path: str | None = None) -> ImageInfo | None:
        """Process local file path and extract image metadata."""
        try:
            # Resolve relative paths
            if base_path and not os.path.isabs(file_path):
                full_path = os.path.join(base_path, file_path)
            else:
                full_path = file_path

            if not os.path.exists(full_path):
                logger.warning(f"Image file not found: {full_path}")
                return None

            # Get file info
            file_size = os.path.getsize(full_path)

            # Get image dimensions and format
            width, height, image_format = self._get_image_info_from_file(full_path)

            # Read file content
            with open(full_path, 'rb') as f:
                content = f.read()

            return ImageInfo(
                width=width,
                height=height,
                format=image_format,
                file_size=file_size,
                content=content,
                temp_path=full_path,  # Use original path
            )

        except Exception as e:
            logger.error(f"Failed to process file path '{file_path}': {e}")
            return None

    def _process_web_url(self, url: str) -> ImageInfo | None:
        """Process web URL image source."""
        # For now, web URL downloading is not implemented
        # This would require requests library and proper error handling
        logger.warning(f"Web URL image download not implemented: {url}")
        return None

    def _get_image_dimensions_from_bytes(self, image_data: bytes) -> tuple[int, int]:
        """Get image dimensions from raw bytes."""
        if HAS_PIL:
            try:
                import io
                with Image.open(io.BytesIO(image_data)) as img:
                    return img.size
            except Exception as e:
                logger.warning(f"PIL failed to get dimensions: {e}")

        # Fallback to default dimensions
        return (800, 600)

    def _get_image_info_from_file(self, file_path: str) -> tuple[int, int, str]:
        """Get image dimensions and format from file."""
        if HAS_PIL:
            try:
                with Image.open(file_path) as img:
                    return img.width, img.height, img.format or 'UNKNOWN'
            except Exception as e:
                logger.warning(f"PIL failed to read image '{file_path}': {e}")

        # Fallback based on file extension
        ext = Path(file_path).suffix.lower()
        format_map = {
            '.png': 'PNG',
            '.jpg': 'JPEG',
            '.jpeg': 'JPEG',
            '.gif': 'GIF',
            '.bmp': 'BMP',
            '.webp': 'WEBP',
        }
        image_format = format_map.get(ext, 'UNKNOWN')

        return (800, 600, image_format)

    def _get_extension_for_format(self, image_format: str) -> str:
        """Get file extension for image format."""
        format_ext_map = {
            'PNG': '.png',
            'JPEG': '.jpg',
            'GIF': '.gif',
            'BMP': '.bmp',
            'WEBP': '.webp',
        }
        return format_ext_map.get(image_format, '.png')

    def _create_temp_file(self, content: bytes, extension: str) -> str:
        """Create temporary file with image content using secure method."""
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
            tmp.write(content)
            temp_path = tmp.name
        self._temp_files.add(temp_path)
        return temp_path

    def _get_cache_key(self, image_source: str, base_path: str | None) -> str:
        """Generate cache key for image source."""
        key_data = f"{image_source}:{base_path or ''}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()

    def generate_embed_id(self, image_info: ImageInfo) -> str:
        """Generate relationship embed ID for image."""
        if image_info.embed_id:
            return image_info.embed_id

        # Generate based on content hash for consistency
        if image_info.content:
            content_hash = hashlib.md5(image_info.content, usedforsecurity=False).hexdigest()[:8]
        else:
            content_hash = hashlib.md5(str(image_info.temp_path, usedforsecurity=False).encode()).hexdigest()[:8]

        embed_id = f"rId_img_{content_hash}"
        image_info.embed_id = embed_id
        return embed_id

    def cleanup(self):
        """Clean up temporary files."""
        for temp_path in self._temp_files:
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file '{temp_path}': {e}")
        self._temp_files.clear()
        self._image_cache.clear()

    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup()