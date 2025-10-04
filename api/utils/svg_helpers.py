"""
SVG API Helper Functions.

Shared utilities for SVG API endpoints to eliminate code duplication.
"""

from typing import Optional, Union
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel


async def extract_svg_content(
    request: Optional[BaseModel],
    svg_file: Optional[UploadFile],
    max_size_mb: int = 10
) -> str:
    """
    Extract and validate SVG content from multiple sources.

    Supports three input methods with priority order:
    1. File upload (highest priority)
    2. Request body with svg_content
    3. Request body with svg_url (not yet implemented)

    Args:
        request: Pydantic request model with optional svg_content or svg_url fields
        svg_file: Optional uploaded file from multipart/form-data
        max_size_mb: Maximum allowed size in megabytes (default: 10)

    Returns:
        SVG content as UTF-8 string

    Raises:
        HTTPException:
            400 Bad Request - No input provided or invalid input
            413 Payload Too Large - Content exceeds max_size_mb
            501 Not Implemented - URL-based input requested

    Example:
        >>> # From file upload
        >>> content = await extract_svg_content(None, svg_file)
        >>>
        >>> # From request body
        >>> content = await extract_svg_content(request, None)
        >>>
        >>> # With custom size limit
        >>> content = await extract_svg_content(request, svg_file, max_size_mb=5)
    """
    svg_content = None

    # Priority 1: File upload takes precedence
    if svg_file:
        try:
            content_bytes = await svg_file.read()
            svg_content = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid file encoding. SVG files must be UTF-8 encoded."
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to read uploaded file: {str(e)}"
            )

    # Priority 2: Request body with svg_content
    elif request and hasattr(request, 'svg_content') and request.svg_content:
        svg_content = request.svg_content

    # Priority 3: Request body with svg_url (not implemented)
    elif request and hasattr(request, 'svg_url') and request.svg_url:
        raise HTTPException(
            status_code=501,
            detail="URL-based analysis not yet implemented. Please use svg_content or file upload."
        )

    # No input provided
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either svg_content, svg_url, or upload a file"
        )

    # Validate size (convert MB to bytes)
    max_size_bytes = max_size_mb * 1024 * 1024
    if len(svg_content) > max_size_bytes:
        actual_size_mb = len(svg_content) / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"SVG content too large ({actual_size_mb:.2f}MB). Maximum allowed: {max_size_mb}MB"
        )

    return svg_content
