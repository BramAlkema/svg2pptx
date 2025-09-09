#!/usr/bin/env python3
"""
API routes for presentation preview functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from typing import Optional
import logging

from ..services.conversion_service import ConversionService, ConversionError
from ..services.google_slides import GoogleSlidesService, GoogleSlidesError
from ..auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/previews", tags=["previews"])


@router.get("/{file_id}/info")
async def get_preview_info(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get preview information for a converted presentation.
    
    Args:
        file_id: Google Drive file ID
        current_user: Authenticated user info
    
    Returns:
        JSON response with presentation and preview information
    
    Raises:
        400: Bad Request - Invalid file ID or presentation not found
        401: Unauthorized - Invalid API key
        500: Internal Server Error - Server-side errors
    """
    try:
        # Input validation
        if not file_id or not file_id.strip():
            raise HTTPException(
                status_code=400,
                detail="File ID is required and cannot be empty"
            )
        
        file_id = file_id.strip()
        
        # Basic file ID validation
        if not file_id.replace('-', '').replace('_', '').isalnum():
            raise HTTPException(
                status_code=400,
                detail="Invalid file ID format. File ID should contain only letters, numbers, hyphens, and underscores"
            )
        
        logger.info(f"Getting preview info for file: {file_id}")
        
        # Initialize services
        conversion_service = ConversionService()
        
        # Get preview summary
        preview_info = conversion_service.slides_service.generate_preview_summary(file_id)
        
        return JSONResponse(
            content={
                "success": True,
                "fileId": file_id,
                "presentation": preview_info["presentation"],
                "previews": preview_info["previews"],
                "urls": preview_info["urls"]
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except GoogleSlidesError as e:
        logger.error(f"Slides API error for file {file_id}: {e}")
        if e.error_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Presentation not found: {e.message}"
            )
        elif e.error_code == 403:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to presentation: {e.message}"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Could not get presentation info: {e.message}"
            )
    except Exception as e:
        logger.error(f"Failed to get preview info for {file_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error getting preview info"
        )


@router.get("/{file_id}/thumbnails")
async def get_presentation_thumbnails(
    file_id: str,
    size: str = Query(default="MEDIUM", regex="^(SMALL|MEDIUM|LARGE)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get thumbnail URLs for all slides in a presentation.
    
    Args:
        file_id: Google Drive file ID / Presentation ID
        size: Thumbnail size (SMALL, MEDIUM, LARGE)
        current_user: Authenticated user info
    
    Returns:
        JSON response with thumbnail URLs for each slide
    """
    try:
        logger.info(f"Getting thumbnails for presentation: {file_id} (size: {size})")
        
        # Initialize Slides service
        slides_service = GoogleSlidesService()
        
        # Get thumbnails
        thumbnails = slides_service.get_slide_thumbnails(file_id, size)
        
        return JSONResponse(
            content={
                "success": True,
                "presentationId": file_id,
                "thumbnailSize": size,
                "slideCount": len(thumbnails),
                "thumbnails": thumbnails
            }
        )
        
    except GoogleSlidesError as e:
        logger.error(f"Failed to get thumbnails for {file_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Could not get thumbnails: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting thumbnails for {file_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error getting thumbnails"
        )


@router.get("/{file_id}/download")
async def download_presentation_previews(
    file_id: str,
    size: str = Query(default="LARGE", regex="^(SMALL|MEDIUM|LARGE)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Download PNG previews for all slides in a presentation.
    
    Args:
        file_id: Google Drive file ID / Presentation ID
        size: Thumbnail size (SMALL, MEDIUM, LARGE)
        current_user: Authenticated user info
    
    Returns:
        JSON response with download results and image data
    """
    try:
        logger.info(f"Downloading previews for presentation: {file_id}")
        
        # Initialize services
        conversion_service = ConversionService()
        
        # Download previews
        preview_results = await conversion_service.get_presentation_previews(file_id)
        
        if not preview_results.get('success'):
            raise HTTPException(
                status_code=400,
                detail=preview_results.get('error', 'Failed to download previews')
            )
        
        # Convert binary image data to base64 for JSON response
        previews = preview_results['previews']['downloads']
        for preview in previews:
            if preview.get('success') and 'imageData' in preview:
                import base64
                preview['imageDataBase64'] = base64.b64encode(preview['imageData']).decode('utf-8')
                # Remove binary data to keep response size manageable
                del preview['imageData']
        
        return JSONResponse(
            content={
                "success": True,
                "fileId": file_id,
                "presentationId": preview_results['presentationId'],
                "presentation": preview_results['presentation'],
                "previews": {
                    "successful": preview_results['previews']['successful'],
                    "total": preview_results['previews']['total'],
                    "downloads": previews
                },
                "urls": preview_results['urls']
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download previews for {file_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error downloading previews"
        )


@router.get("/{file_id}/slide/{slide_number}/image")
async def get_slide_image(
    file_id: str,
    slide_number: int,
    size: str = Query(default="LARGE", regex="^(SMALL|MEDIUM|LARGE)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get PNG image for a specific slide.
    
    Args:
        file_id: Google Drive file ID / Presentation ID
        slide_number: Slide number (1-based)
        size: Thumbnail size (SMALL, MEDIUM, LARGE)
        current_user: Authenticated user info
    
    Returns:
        PNG image data as binary response
    """
    try:
        logger.info(f"Getting slide {slide_number} image for presentation: {file_id}")
        
        # Initialize services
        conversion_service = ConversionService()
        
        # Download previews
        preview_results = await conversion_service.get_presentation_previews(file_id)
        
        if not preview_results.get('success'):
            raise HTTPException(
                status_code=400,
                detail=preview_results.get('error', 'Failed to get slide previews')
            )
        
        # Find the requested slide
        previews = preview_results['previews']['downloads']
        slide_preview = None
        
        for preview in previews:
            if preview.get('slideNumber') == slide_number and preview.get('success'):
                slide_preview = preview
                break
        
        if not slide_preview:
            raise HTTPException(
                status_code=404,
                detail=f"Slide {slide_number} not found or failed to generate"
            )
        
        # Return the image as binary response
        image_data = slide_preview.get('imageData')
        if not image_data:
            raise HTTPException(
                status_code=500,
                detail="Image data not available"
            )
        
        return Response(
            content=image_data,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=slide_{slide_number:02d}.png"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get slide image for {file_id}, slide {slide_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error getting slide image"
        )