#!/usr/bin/env python3
"""
Export to Google Slides API routes.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import logging
import io

from core.auth import (
    GoogleOAuthService,
    GoogleDriveService,
    OAuthError,
    DriveError,
    get_api_token_store,
)
from ..config import get_settings
from ..auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])


class ExportToSlidesRequest(BaseModel):
    """Request model for exporting to Google Slides."""
    user_id: str
    pptx_url: Optional[str] = None
    pptx_base64: Optional[str] = None
    title: str = "SVG Presentation"
    parent_folder_id: Optional[str] = None


class ExportToSlidesResponse(BaseModel):
    """Response model for export to Slides."""
    success: bool
    slides_id: str
    slides_url: str
    web_view_link: str
    title: str


def get_oauth_service() -> GoogleOAuthService:
    """Get OAuth service instance from settings."""
    settings = get_settings()

    if not settings.google_drive_client_id or not settings.google_drive_client_secret:
        raise HTTPException(
            status_code=500,
            detail="OAuth credentials not configured. Set GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET"
        )

    token_store = get_api_token_store()

    return GoogleOAuthService(
        token_store=token_store,
        client_id=settings.google_drive_client_id,
        client_secret=settings.google_drive_client_secret,
        redirect_uri="http://localhost:8000/oauth2/callback",
    )


@router.post("/to-slides", response_model=ExportToSlidesResponse)
async def export_to_slides(
    request: ExportToSlidesRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Export PPTX to Google Slides.

    Requires user to be authenticated via OAuth first.

    Args:
        request: Export request with user_id, PPTX data, and options
        current_user: Authenticated API user

    Returns:
        Export results with Slides URL

    Raises:
        400: Bad Request - Missing PPTX data or invalid parameters
        401: Unauthorized - User not authenticated with Google
        500: Internal Server Error - Export failed
    """
    try:
        # Validate input
        if not request.pptx_url and not request.pptx_base64:
            raise HTTPException(
                status_code=400,
                detail="Either pptx_url or pptx_base64 must be provided"
            )

        if request.pptx_url and request.pptx_base64:
            raise HTTPException(
                status_code=400,
                detail="Provide only one of pptx_url or pptx_base64, not both"
            )

        # Get PPTX bytes
        pptx_bytes = None

        if request.pptx_url:
            # Download from URL
            import requests
            try:
                response = requests.get(request.pptx_url, timeout=60)
                response.raise_for_status()
                pptx_bytes = response.content
            except requests.RequestException as e:
                logger.error(f"Failed to download PPTX from URL: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to download PPTX from URL: {str(e)}"
                )

        elif request.pptx_base64:
            # Decode base64
            import base64
            try:
                pptx_bytes = base64.b64decode(request.pptx_base64)
            except Exception as e:
                logger.error(f"Failed to decode base64 PPTX: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid base64 PPTX data: {str(e)}"
                )

        if not pptx_bytes:
            raise HTTPException(
                status_code=400,
                detail="Failed to obtain PPTX data"
            )

        # Get OAuth credentials for user
        oauth_service = get_oauth_service()

        try:
            credentials = oauth_service.get_credentials(request.user_id)
        except OAuthError as e:
            logger.error(f"User {request.user_id} not authenticated: {e}")
            raise HTTPException(
                status_code=401,
                detail=f"User not authenticated with Google. Please authenticate first: {str(e)}"
            )

        # Upload and convert to Slides
        drive_service = GoogleDriveService(credentials)

        try:
            result = drive_service.upload_and_convert_to_slides(
                pptx_bytes=pptx_bytes,
                title=request.title,
                parent_folder_id=request.parent_folder_id
            )

            logger.info(
                f"Successfully exported to Slides for user {request.user_id}: {result['slides_id']}"
            )

            return JSONResponse(
                content={
                    "success": True,
                    "slides_id": result['slides_id'],
                    "slides_url": result['slides_url'],
                    "web_view_link": result['web_view_link'],
                    "title": request.title
                },
                status_code=200
            )

        except DriveError as e:
            logger.error(f"Drive export failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to export to Slides: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during export: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )
