#!/usr/bin/env python3
"""
SVG URL Downloader for Batch Processing

Downloads SVG files from URLs to temporary storage for batch conversion.
"""

import logging
import tempfile
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Exception raised when SVG download fails"""
    pass


@dataclass
class DownloadResult:
    """Result of downloading SVG URLs"""
    success: bool
    file_paths: List[str]
    errors: List[Dict[str, Any]]
    temp_dir: Optional[str] = None


def download_svgs_to_temp(
    urls: List[str],
    timeout: int = 30,
    max_size_mb: int = 10,
    job_id: Optional[str] = None
) -> DownloadResult:
    """
    Download SVG files from URLs to temporary directory.

    Args:
        urls: List of HTTP(S) URLs to SVG files
        timeout: Request timeout in seconds (default 30)
        max_size_mb: Maximum file size in MB (default 10)
        job_id: Optional job ID for temp directory naming

    Returns:
        DownloadResult with file paths and any errors

    Raises:
        DownloadError: If all downloads fail

    Example:
        >>> urls = ['https://example.com/logo.svg', 'https://example.com/icon.svg']
        >>> result = download_svgs_to_temp(urls)
        >>> if result.success:
        ...     print(f"Downloaded {len(result.file_paths)} files")
        ...     # Process files...
        ...     cleanup_temp_directory(result.temp_dir)
    """
    # Create temp directory for this batch
    temp_dir = tempfile.mkdtemp(prefix=f'svg2pptx_batch_{job_id or "download"}_')
    logger.info(f"Created temp directory: {temp_dir}")

    file_paths = []
    errors = []
    max_size_bytes = max_size_mb * 1024 * 1024

    try:
        for i, url in enumerate(urls):
            try:
                logger.info(f"Downloading {i+1}/{len(urls)}: {url}")

                # Download with timeout and size limit
                response = requests.get(
                    url,
                    timeout=timeout,
                    stream=True,
                    headers={'User-Agent': 'svg2pptx/1.0'}
                )
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get('Content-Type', '')
                if not _is_svg_content_type(content_type):
                    logger.warning(f"Non-SVG content type for {url}: {content_type}")

                # Read content with size limit
                content_chunks = []
                total_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        total_size += len(chunk)
                        if total_size > max_size_bytes:
                            raise DownloadError(f"File exceeds {max_size_mb}MB limit")
                        content_chunks.append(chunk)

                content = b''.join(content_chunks)

                # Validate SVG content
                if not _is_valid_svg_content(content):
                    raise DownloadError("Downloaded content is not valid SVG")

                # Save to temp file
                filename = _get_safe_filename(url, i)
                file_path = Path(temp_dir) / filename
                file_path.write_bytes(content)

                file_paths.append(str(file_path))
                logger.info(f"✅ Downloaded {url} → {file_path} ({total_size} bytes)")

            except requests.RequestException as e:
                error_msg = f"HTTP error downloading {url}: {e}"
                logger.error(error_msg)
                errors.append({
                    'url': url,
                    'error_type': 'http_error',
                    'error_message': str(e)
                })

            except DownloadError as e:
                error_msg = f"Download error for {url}: {e}"
                logger.error(error_msg)
                errors.append({
                    'url': url,
                    'error_type': 'download_error',
                    'error_message': str(e)
                })

            except Exception as e:
                error_msg = f"Unexpected error downloading {url}: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append({
                    'url': url,
                    'error_type': 'unexpected_error',
                    'error_message': str(e)
                })

        # Check if any downloads succeeded
        if not file_paths:
            error_summary = f"All {len(urls)} downloads failed"
            logger.error(error_summary)
            raise DownloadError(error_summary)

        # Some downloads succeeded
        if errors:
            logger.warning(f"⚠️ Downloaded {len(file_paths)}/{len(urls)} files "
                         f"({len(errors)} failed)")
        else:
            logger.info(f"✅ Successfully downloaded all {len(file_paths)} files")

        return DownloadResult(
            success=True,
            file_paths=file_paths,
            errors=errors,
            temp_dir=temp_dir
        )

    except Exception as e:
        # Cleanup temp directory on complete failure
        logger.error(f"Download batch failed, cleaning up {temp_dir}")
        cleanup_temp_directory(temp_dir)

        return DownloadResult(
            success=False,
            file_paths=[],
            errors=errors or [{
                'error_type': 'batch_failure',
                'error_message': str(e)
            }],
            temp_dir=None
        )


def cleanup_temp_directory(temp_dir: str) -> None:
    """
    Clean up temporary download directory.

    Args:
        temp_dir: Path to temporary directory to remove
    """
    try:
        import shutil
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")


def _is_svg_content_type(content_type: str) -> bool:
    """Check if content type indicates SVG"""
    svg_types = ['image/svg+xml', 'text/xml', 'application/xml', 'text/plain']
    return any(t in content_type.lower() for t in svg_types)


def _is_valid_svg_content(content: bytes) -> bool:
    """
    Validate that content appears to be SVG.

    Checks for:
    - Starts with XML declaration or <svg
    - Contains <svg tag
    """
    try:
        # Decode first 1KB
        preview = content[:1024].decode('utf-8', errors='ignore')
        preview_lower = preview.lower()

        # Must contain <svg
        if '<svg' not in preview_lower:
            return False

        # Should start with <?xml or <svg
        preview_stripped = preview.lstrip()
        if not (preview_stripped.startswith('<?xml') or
                preview_stripped.startswith('<svg') or
                preview_stripped.startswith('<!DOCTYPE')):
            logger.warning("SVG content doesn't start with expected tags")
            # Don't fail - some valid SVGs have comments first

        return True

    except Exception as e:
        logger.error(f"Error validating SVG content: {e}")
        return False


def _get_safe_filename(url: str, index: int) -> str:
    """
    Generate safe filename from URL.

    Args:
        url: Source URL
        index: File index in batch

    Returns:
        Safe filename like 'file_0.svg' or 'logo_1.svg'
    """
    from urllib.parse import urlparse
    import re

    try:
        # Try to extract filename from URL
        parsed = urlparse(url)
        path = Path(parsed.path)
        name = path.stem or f'file_{index}'

        # Sanitize filename
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        safe_name = safe_name[:50]  # Limit length

        return f"{safe_name}_{index}.svg"

    except Exception:
        return f"file_{index}.svg"


def get_downloader_info() -> Dict[str, Any]:
    """
    Get information about the URL downloader.

    Returns:
        Dictionary with downloader capabilities and defaults
    """
    return {
        'downloader': 'svg_url_downloader',
        'version': '1.0.0',
        'capabilities': {
            'http_download': True,
            'https_download': True,
            'content_validation': True,
            'size_limiting': True,
            'batch_download': True,
            'error_recovery': True
        },
        'defaults': {
            'timeout_seconds': 30,
            'max_size_mb': 10
        },
        'supported_content_types': [
            'image/svg+xml',
            'text/xml',
            'application/xml',
            'text/plain'
        ]
    }
