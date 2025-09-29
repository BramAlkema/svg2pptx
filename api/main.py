#!/usr/bin/env python3
"""
Main FastAPI application for SVG to Google Drive conversion.
"""

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from typing import Optional

from .config import get_settings
from .auth import validate_api_key, extract_bearer_token, get_current_user
from .services.conversion_service import ConversionService, ConversionError
from .routes.previews import router as previews_router
from .routes.batch import router as batch_router
from src.svg2pptx import convert_svg_to_pptx

# Configure logging
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SVG to Google Drive API",
    description="Convert SVG files to PowerPoint format with multi-slide support and upload to Google Drive with PNG preview generation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include preview routes
app.include_router(previews_router)

# Include batch routes
app.include_router(batch_router)




@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "svg2pptx-api",
        "version": "1.0.0"
    }


@app.post("/convert")
async def convert_svg_to_drive(
    url: str,
    fileId: Optional[str] = None,
    preprocessing: Optional[str] = None,
    precision: Optional[int] = None,
    clean_slate: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Convert SVG from URL to PPTX and upload to Google Drive.

    Args:
        url: URL of the SVG file to convert
        fileId: Optional Google Drive file ID to update instead of creating new
        preprocessing: Optional preprocessing preset (minimal, default, aggressive)
        precision: Optional numeric precision for preprocessing (1-10)
        clean_slate: Optional flag to enable clean slate architecture (experimental)
        current_user: Authenticated user info (from dependency)

    Returns:
        JSON response with file information and preview data

    Raises:
        400: Bad Request - Invalid URL, conversion errors, or validation failures
        401: Unauthorized - Invalid API key
        500: Internal Server Error - Server-side errors
    """
    try:
        # Input validation
        if not url or not url.strip():
            raise HTTPException(
                status_code=400,
                detail="URL parameter is required and cannot be empty"
            )
        
        url = url.strip()
        
        # Basic URL validation
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid URL format. URL must include scheme (http/https) and domain"
                )
            if parsed.scheme.lower() not in ['http', 'https']:
                raise HTTPException(
                    status_code=400,
                    detail="Only HTTP and HTTPS URLs are supported"
                )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid URL format"
            )
        
        # Validate fileId if provided
        if fileId and not fileId.strip():
            raise HTTPException(
                status_code=400,
                detail="fileId cannot be empty string if provided"
            )
        
        if fileId:
            fileId = fileId.strip()
            # Basic Google Drive file ID validation (should be alphanumeric with some special chars)
            if not fileId.replace('-', '').replace('_', '').isalnum():
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Google Drive file ID format"
                )
        
        logger.info(f"Converting SVG from {url} for user {current_user.get('api_key', 'unknown')}")
        
        # Initialize conversion service with custom preprocessing options
        conversion_service = ConversionService()
        
        # Apply custom preprocessing settings if provided
        if preprocessing and preprocessing in ['minimal', 'default', 'aggressive']:
            conversion_service.settings.svg_preprocessing_preset = preprocessing
        if precision and 1 <= precision <= 10:
            conversion_service.settings.svg_preprocessing_precision = precision
        if clean_slate is not None:
            # Set clean slate mode if supported by conversion service
            if hasattr(conversion_service.settings, 'use_clean_slate'):
                conversion_service.settings.use_clean_slate = clean_slate
            else:
                # Log that clean slate option was requested but not supported
                logger.info(f"Clean slate option ({clean_slate}) requested but not supported by conversion service")
        
        # Perform conversion and upload
        result = conversion_service.convert_and_upload(svg_url=url, file_id=fileId)
        
        return JSONResponse(
            content=result,
            status_code=200
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ConversionError as e:
        logger.error(f"Conversion error for URL {url}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Conversion failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during conversion for URL {url}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during conversion. Please try again later."
        )


@app.post("/convert/multislide")
async def convert_svg_to_multislide(
    url: str,
    fileId: Optional[str] = None,
    animation_threshold: Optional[int] = 3,
    preprocessing: Optional[str] = None,
    precision: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Convert SVG from URL to multi-slide PPTX and upload to Google Drive.

    Args:
        url: URL of the SVG file to convert
        fileId: Optional Google Drive file ID to update instead of creating new
        animation_threshold: Minimum animations for slide sequence conversion (default: 3)
        preprocessing: Optional preprocessing preset (minimal, default, aggressive)
        precision: Optional numeric precision for preprocessing (1-10)
        current_user: Authenticated user info (from dependency)

    Returns:
        JSON response with conversion results, statistics, and file information

    Raises:
        400: Bad Request - Invalid URL, conversion errors, or validation failures
        401: Unauthorized - Invalid API key
        500: Internal Server Error - Server-side errors
    """
    try:
        # Input validation (reuse logic from /convert endpoint)
        if not url or not url.strip():
            raise HTTPException(
                status_code=400,
                detail="URL parameter is required and cannot be empty"
            )

        url = url.strip()

        # Basic URL validation
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid URL format. URL must include scheme (http/https) and domain"
                )
            if parsed.scheme.lower() not in ['http', 'https']:
                raise HTTPException(
                    status_code=400,
                    detail="Only HTTP and HTTPS URLs are supported"
                )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid URL format"
            )

        # Validate animation_threshold
        if animation_threshold is not None and (animation_threshold < 1 or animation_threshold > 100):
            raise HTTPException(
                status_code=400,
                detail="animation_threshold must be between 1 and 100"
            )

        # Validate fileId if provided
        if fileId and not fileId.strip():
            raise HTTPException(
                status_code=400,
                detail="fileId cannot be empty string if provided"
            )

        if fileId:
            fileId = fileId.strip()
            if not fileId.replace('-', '').replace('_', '').isalnum():
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Google Drive file ID format"
                )

        logger.info(f"Converting SVG to multi-slide from {url} for user {current_user.get('api_key', 'unknown')}")

        # Download SVG content
        import requests
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        svg_content = response.text

        # Convert to multi-slide PPTX
        result = convert_svg_to_multislide_pptx_api(
            svg_input=svg_content,
            output_path=None,  # Creates temp file
            animation_threshold=animation_threshold or 3,
            enable_multislide_detection=True
        )

        # Upload to Google Drive using existing conversion service
        conversion_service = ConversionService()

        # Read PPTX file content
        with open(result['output_path'], 'rb') as f:
            pptx_content = f.read()

        # Clean up temporary PPTX file
        import os
        try:
            os.unlink(result['output_path'])
        except OSError:
            pass

        # Upload to Google Drive
        filename = f"multislide_presentation_{animation_threshold or 3}.pptx"
        if fileId:
            upload_result = conversion_service.upload_manager.update_file_content(
                file_id=fileId,
                content=pptx_content,
                filename=filename
            )
        else:
            upload_result = conversion_service.upload_manager.upload_content_as_file(
                content=pptx_content,
                filename=filename,
                folder_id=conversion_service.settings.google_drive_folder_id
            )

        # Combine results
        combined_result = {
            **result,
            **upload_result,
            "conversion_type": "multislide",
            "animation_threshold": animation_threshold or 3
        }

        return JSONResponse(
            content=combined_result,
            status_code=200
        )

    except HTTPException:
        raise
    except ConversionError as e:
        logger.error(f"Multi-slide conversion error for URL {url}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Multi-slide conversion failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during multi-slide conversion for URL {url}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during multi-slide conversion. Please try again later."
        )


@app.post("/convert/multiple")
async def convert_multiple_svgs_to_presentation(
    urls: list[str],
    fileId: Optional[str] = None,
    animation_threshold: Optional[int] = 3,
    preprocessing: Optional[str] = None,
    precision: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Convert multiple SVG files from URLs to single multi-slide PPTX and upload to Google Drive.

    Args:
        urls: List of URLs of SVG files to convert
        fileId: Optional Google Drive file ID to update instead of creating new
        animation_threshold: Minimum animations for slide sequence conversion (default: 3)
        preprocessing: Optional preprocessing preset (minimal, default, aggressive)
        precision: Optional numeric precision for preprocessing (1-10)
        current_user: Authenticated user info (from dependency)

    Returns:
        JSON response with conversion results, statistics, and file information

    Raises:
        400: Bad Request - Invalid URLs, conversion errors, or validation failures
        401: Unauthorized - Invalid API key
        500: Internal Server Error - Server-side errors
    """
    try:
        # Input validation
        if not urls or len(urls) == 0:
            raise HTTPException(
                status_code=400,
                detail="URLs list is required and cannot be empty"
            )

        if len(urls) > 20:  # Reasonable limit
            raise HTTPException(
                status_code=400,
                detail="Maximum 20 URLs allowed per request"
            )

        # Validate each URL
        import urllib.parse
        validated_urls = []
        for i, url in enumerate(urls):
            if not url or not url.strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"URL at index {i} is empty"
                )

            url = url.strip()
            try:
                parsed = urllib.parse.urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid URL format at index {i}. URL must include scheme (http/https) and domain"
                    )
                if parsed.scheme.lower() not in ['http', 'https']:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Only HTTP and HTTPS URLs are supported (URL at index {i})"
                    )
                validated_urls.append(url)
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid URL format at index {i}"
                )

        # Validate animation_threshold
        if animation_threshold is not None and (animation_threshold < 1 or animation_threshold > 100):
            raise HTTPException(
                status_code=400,
                detail="animation_threshold must be between 1 and 100"
            )

        # Validate fileId if provided
        if fileId and not fileId.strip():
            raise HTTPException(
                status_code=400,
                detail="fileId cannot be empty string if provided"
            )

        if fileId:
            fileId = fileId.strip()
            if not fileId.replace('-', '').replace('_', '').isalnum():
                raise HTTPException(
                    status_code=400,
                    detail="Invalid Google Drive file ID format"
                )

        logger.info(f"Converting {len(validated_urls)} SVGs to multi-slide presentation for user {current_user.get('api_key', 'unknown')}")

        # Download all SVG files and create temporary files
        import tempfile
        import requests
        import os

        temp_svg_paths = []
        try:
            for i, url in enumerate(validated_urls):
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                # Create temporary SVG file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False, encoding='utf-8') as f:
                    f.write(response.text)
                    temp_svg_paths.append(f.name)

            # Convert multiple SVGs to single PPTX
            result = convert_multiple_svgs_to_pptx_api(
                svg_paths=temp_svg_paths,
                output_path=None,  # Creates temp file
                animation_threshold=animation_threshold or 3
            )

            # Upload to Google Drive using existing conversion service
            conversion_service = ConversionService()

            # Read PPTX file content
            with open(result['output_path'], 'rb') as f:
                pptx_content = f.read()

            # Clean up temporary PPTX file
            try:
                os.unlink(result['output_path'])
            except OSError:
                pass

            # Upload to Google Drive
            filename = f"multiple_svgs_presentation_{len(validated_urls)}_files.pptx"
            if fileId:
                upload_result = conversion_service.upload_manager.update_file_content(
                    file_id=fileId,
                    content=pptx_content,
                    filename=filename
                )
            else:
                upload_result = conversion_service.upload_manager.upload_content_as_file(
                    content=pptx_content,
                    filename=filename,
                    folder_id=conversion_service.settings.google_drive_folder_id
                )

            # Combine results
            combined_result = {
                **result,
                **upload_result,
                "conversion_type": "multiple_files",
                "source_count": len(validated_urls),
                "animation_threshold": animation_threshold or 3
            }

            return JSONResponse(
                content=combined_result,
                status_code=200
            )

        finally:
            # Clean up temporary SVG files
            for temp_path in temp_svg_paths:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    except HTTPException:
        raise
    except ConversionError as e:
        logger.error(f"Multiple SVG conversion error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Multiple SVG conversion failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during multiple SVG conversion: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during multiple SVG conversion. Please try again later."
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler with detailed error responses."""
    logger.warning(f"HTTP {exc.status_code} error for {request.url}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "detail": exc.detail,  # Include detail field for consistency
            "path": str(request.url.path),
            "method": request.method
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unhandled errors."""
    logger.error(f"Unhandled exception for {request.url}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal server error. Please try again later.",
            "path": str(request.url.path),
            "method": request.method
        }
    )


@app.exception_handler(ConversionError)
async def conversion_exception_handler(request, exc):
    """Handle conversion-specific errors."""
    logger.error(f"Conversion error for {request.url}: {exc}")
    
    return JSONResponse(
        status_code=400,
        content={
            "error": True,
            "status_code": 400,
            "message": f"Conversion failed: {str(exc)}",
            "error_type": "conversion_error",
            "path": str(request.url.path),
            "method": request.method
        }
    )


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.environment == "development" else False
    )