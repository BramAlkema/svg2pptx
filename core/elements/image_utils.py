"""
Utility helpers for image processing.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional
from urllib.parse import urlparse

from lxml import etree as ET

from .image_models import ImageFormat


def extract_image_href(element: ET.Element) -> Optional[str]:
    """Extract image href from various possible attributes."""
    href_attrs = [
        '{http://www.w3.org/1999/xlink}href',
        'href',
        'xlink:href',
    ]

    for attr in href_attrs:
        href = element.get(attr)
        if href:
            return href.strip()

    return None


def determine_image_format(href: str) -> ImageFormat:
    """Determine image format from href."""
    if href.startswith('data:'):
        match = re.match(r'data:image/([^;]+)', href)
        if match:
            mime_type = match.group(1).lower()
            format_map = {
                'png': ImageFormat.PNG,
                'jpeg': ImageFormat.JPEG,
                'jpg': ImageFormat.JPEG,
                'svg+xml': ImageFormat.SVG,
                'gif': ImageFormat.GIF,
                'bmp': ImageFormat.BMP,
                'tiff': ImageFormat.TIFF,
            }
            return format_map.get(mime_type, ImageFormat.UNKNOWN)
    else:
        parsed = urlparse(href)
        path = parsed.path.lower()

        if path.endswith('.png'):
            return ImageFormat.PNG
        if path.endswith(('.jpg', '.jpeg')):
            return ImageFormat.JPEG
        if path.endswith('.svg'):
            return ImageFormat.SVG
        if path.endswith('.gif'):
            return ImageFormat.GIF
        if path.endswith('.bmp'):
            return ImageFormat.BMP
        if path.endswith(('.tif', '.tiff')):
            return ImageFormat.TIFF

    return ImageFormat.UNKNOWN


def is_embedded_image(href: str) -> bool:
    """Check if image is embedded as data URL."""
    return href.startswith('data:')


def estimate_file_size(href: str) -> Optional[int]:
    """Estimate file size for embedded images."""
    if not is_embedded_image(href):
        return None

    if ',base64,' in href:
        base64_part = href.split(',base64,')[1]
        return int(len(base64_part) * 0.75)
    return None


def generate_cache_key(element: ET.Element) -> str:
    """Generate a stable cache key for an image element."""
    href = extract_image_href(element) or ""
    width = element.get('width', '')
    height = element.get('height', '')
    transform = element.get('transform', '')

    key_data = f"{href}:{width}:{height}:{transform}"
    return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()


__all__ = [
    "extract_image_href",
    "determine_image_format",
    "is_embedded_image",
    "estimate_file_size",
    "generate_cache_key",
]
