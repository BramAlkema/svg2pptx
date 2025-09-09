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

# Configure logging
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SVG to Google Drive API",
    description="Convert SVG files to PowerPoint format and upload to Google Drive with PNG preview generation",
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
    current_user: dict = Depends(get_current_user)
):
    """
    Convert SVG from URL to PPTX and upload to Google Drive.
    
    Args:
        url: URL of the SVG file to convert
        fileId: Optional Google Drive file ID to update instead of creating new
        preprocessing: Optional preprocessing preset (minimal, default, aggressive)
        precision: Optional numeric precision for preprocessing (1-10)
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
        
        # Perform conversion and upload
        result = conversion_service.convert_and_upload(url, fileId)
        
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