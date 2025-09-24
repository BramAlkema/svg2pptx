#!/usr/bin/env python3
"""
Google Slides API integration with OAuth browser authentication.

Provides endpoints for OAuth flow and SVG conversion to Google Slides presentations
as a fallback when PPTX files are corrupted or need repair.
"""

import asyncio
import io
import base64
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field
import httpx

# Google API imports
from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from ..auth import get_current_user
from src.svg2pptx import SVGToPowerPointConverter

logger = logging.getLogger(__name__)

# Create APIRouter
router = APIRouter(prefix="/google-slides", tags=["google-slides"])


# Pydantic models
class OAuthInitiateRequest(BaseModel):
    """Request to initiate OAuth flow."""
    redirect_uri: str = Field(..., description="Where to redirect after OAuth")
    state: Optional[str] = Field(None, description="Optional state parameter")


class OAuthInitiateResponse(BaseModel):
    """Response with OAuth authorization URL."""
    auth_url: str = Field(..., description="URL to redirect user to for authorization")
    state: str = Field(..., description="State parameter to verify callback")


class GoogleSlidesConversionRequest(BaseModel):
    """Request to convert SVG to Google Slides."""
    svg_content: str = Field(..., description="SVG content to convert")
    presentation_title: Optional[str] = Field(None, description="Title for the presentation")
    slide_size: Optional[str] = Field("STANDARD", description="Slide size: STANDARD, WIDESCREEN")


class GoogleSlidesConversionResponse(BaseModel):
    """Response from Google Slides conversion."""
    success: bool
    presentation_id: Optional[str] = None
    presentation_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error_message: Optional[str] = None
    fallback_used: bool = True  # Always true for Google Slides


class GoogleSlidesOAuthHandler:
    """Handle Google Slides OAuth authentication flow."""

    SCOPES = [
        'https://www.googleapis.com/auth/presentations',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.readonly'
    ]

    def __init__(self):
        self.client_secrets_file = "credentials/google_client_secret.json"

    def initiate_oauth_flow(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Initiate OAuth flow and return authorization URL.

        Args:
            redirect_uri: Where to redirect after authorization
            state: Optional state parameter for security

        Returns:
            Authorization URL for user to visit

        Raises:
            HTTPException: If OAuth setup fails
        """
        try:
            # Check if client secrets file exists
            if not Path(self.client_secrets_file).exists():
                raise HTTPException(
                    status_code=500,
                    detail="Google OAuth not configured. Missing client secrets file."
                )

            # Create OAuth flow
            flow = Flow.from_client_secrets_file(
                self.client_secrets_file,
                scopes=self.SCOPES
            )
            flow.redirect_uri = redirect_uri

            # Generate authorization URL
            auth_url, state_param = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state,
                prompt='consent'  # Force consent to ensure refresh token
            )

            return auth_url, state_param

        except Exception as e:
            logger.error(f"OAuth flow initiation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initiate OAuth flow: {str(e)}"
            )

    def handle_oauth_callback(self, auth_code: str, redirect_uri: str) -> dict:
        """
        Handle OAuth callback and return credentials.

        Args:
            auth_code: Authorization code from Google
            redirect_uri: Original redirect URI

        Returns:
            Credentials dictionary

        Raises:
            HTTPException: If callback handling fails
        """
        try:
            # Create flow with same parameters as initiation
            flow = Flow.from_client_secrets_file(
                self.client_secrets_file,
                scopes=self.SCOPES
            )
            flow.redirect_uri = redirect_uri

            # Exchange authorization code for credentials
            flow.fetch_token(code=auth_code)

            # Return credentials as dictionary
            credentials = flow.credentials
            return {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }

        except Exception as e:
            logger.error(f"OAuth callback handling failed: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"OAuth callback failed: {str(e)}"
            )


class GoogleSlidesConverter:
    """Convert SVG content to Google Slides presentations."""

    def __init__(self):
        self.svg_converter = SVGToPowerPointConverter()

    async def convert_svg_to_slides(
        self,
        svg_content: str,
        credentials_dict: dict,
        presentation_title: Optional[str] = None,
        slide_size: str = "STANDARD"
    ) -> Dict[str, Any]:
        """
        Convert SVG content to Google Slides presentation.

        Args:
            svg_content: SVG content to convert
            credentials_dict: Google OAuth credentials
            presentation_title: Title for presentation
            slide_size: Slide size (STANDARD or WIDESCREEN)

        Returns:
            Dictionary with presentation details
        """
        try:
            # Reconstruct credentials object
            from google.oauth2.credentials import Credentials
            credentials = Credentials(
                token=credentials_dict['token'],
                refresh_token=credentials_dict.get('refresh_token'),
                token_uri=credentials_dict['token_uri'],
                client_id=credentials_dict['client_id'],
                client_secret=credentials_dict['client_secret'],
                scopes=credentials_dict['scopes']
            )

            # Build Google Slides service
            slides_service = build('slides', 'v1', credentials=credentials)
            drive_service = build('drive', 'v3', credentials=credentials)

            # Create new presentation
            presentation_body = {
                'title': presentation_title or f'SVG Conversion {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            }

            presentation = slides_service.presentations().create(body=presentation_body).execute()
            presentation_id = presentation['presentationId']

            logger.info(f"Created Google Slides presentation: {presentation_id}")

            # Convert SVG to PNG for insertion
            png_data = await self._svg_to_png(svg_content)

            # Upload PNG to Drive
            media = MediaIoBaseUpload(
                io.BytesIO(png_data),
                mimetype='image/png',
                resumable=True
            )

            drive_file = drive_service.files().create(
                body={
                    'name': f'svg_conversion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png',
                    'parents': []  # Will be in user's Drive root
                },
                media_body=media,
                fields='id,webViewLink'
            ).execute()

            image_file_id = drive_file['id']
            logger.info(f"Uploaded image to Drive: {image_file_id}")

            # Get the first slide
            slide_id = presentation['slides'][0]['objectId']

            # Calculate image dimensions (fit to slide)
            image_width = 6 * 914400  # 6 inches in EMU
            image_height = 4.5 * 914400  # 4.5 inches in EMU

            # Insert image into slide
            requests = [{
                'createImage': {
                    'objectId': f'svg_image_{int(datetime.now().timestamp())}',
                    'url': f'https://drive.google.com/uc?id={image_file_id}',
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'width': {'magnitude': image_width, 'unit': 'EMU'},
                            'height': {'magnitude': image_height, 'unit': 'EMU'}
                        },
                        'transform': {
                            'scaleX': 1.0,
                            'scaleY': 1.0,
                            'translateX': 1 * 914400,  # 1 inch from left
                            'translateY': 1 * 914400,  # 1 inch from top
                            'unit': 'EMU'
                        }
                    }
                }
            }]

            # Apply the image insertion
            slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()

            logger.info(f"Successfully inserted image into presentation")

            # Generate presentation URL
            presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"

            # Generate thumbnail URL (if possible)
            thumbnail_url = f"https://drive.google.com/thumbnail?id={presentation_id}&sz=w400-h300"

            return {
                'success': True,
                'presentation_id': presentation_id,
                'presentation_url': presentation_url,
                'thumbnail_url': thumbnail_url,
                'image_file_id': image_file_id
            }

        except Exception as e:
            logger.error(f"Google Slides conversion failed: {str(e)}")
            return {
                'success': False,
                'error_message': str(e)
            }

    async def _svg_to_png(self, svg_content: str, width: int = 800, height: int = 600) -> bytes:
        """Convert SVG content to PNG bytes."""
        try:
            # Try using cairosvg for high-quality conversion
            import cairosvg
            png_bytes = cairosvg.svg2png(
                bytestring=svg_content.encode('utf-8'),
                output_width=width,
                output_height=height,
                background_color='white'
            )
            return png_bytes

        except ImportError:
            logger.warning("cairosvg not available, using fallback PNG generation")
            # Fallback: create a simple PNG with SVG info
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)

            # Draw simple representation
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()

            text = "SVG Content\n(Converted to Google Slides)"
            draw.multiline_text((50, 50), text, fill='black', font=font)

            # Add SVG content preview (first 200 chars)
            preview_text = svg_content[:200] + "..." if len(svg_content) > 200 else svg_content
            draw.multiline_text((50, 100), preview_text, fill='gray', font=font)

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            return img_bytes.getvalue()


# API Endpoints

@router.post("/oauth/initiate", response_model=OAuthInitiateResponse)
async def initiate_google_slides_oauth(request: OAuthInitiateRequest):
    """
    Initiate Google Slides OAuth flow.

    Returns authorization URL for user to visit in browser.
    """
    handler = GoogleSlidesOAuthHandler()

    try:
        auth_url, state = handler.initiate_oauth_flow(
            redirect_uri=request.redirect_uri,
            state=request.state
        )

        return OAuthInitiateResponse(
            auth_url=auth_url,
            state=state
        )

    except Exception as e:
        logger.error(f"OAuth initiation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate OAuth: {str(e)}"
        )


@router.get("/oauth/callback")
async def handle_google_slides_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    request: Request = None
):
    """
    Handle Google OAuth callback.

    This endpoint receives the authorization code and exchanges it for credentials.
    """
    if error:
        logger.error(f"OAuth error: {error}")
        raise HTTPException(
            status_code=400,
            detail=f"OAuth authorization failed: {error}"
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Authorization code not provided"
        )

    handler = GoogleSlidesOAuthHandler()

    try:
        # Reconstruct redirect URI
        redirect_uri = str(request.url).split('?')[0]  # Remove query parameters

        # Exchange code for credentials
        credentials_dict = handler.handle_oauth_callback(code, redirect_uri)

        # Store credentials securely (in production, encrypt and store in database)
        # For now, return them (NOT recommended for production)

        return {
            "success": True,
            "message": "OAuth successful",
            "credentials_id": "temp_" + str(hash(credentials_dict['token'])),  # Temp ID
            # "credentials": credentials_dict  # DON'T return in production
        }

    except Exception as e:
        logger.error(f"OAuth callback failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.post("/convert", response_model=GoogleSlidesConversionResponse)
async def convert_svg_to_google_slides(
    request: GoogleSlidesConversionRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user)
):
    """
    Convert SVG to Google Slides presentation.

    This endpoint converts SVG content to a Google Slides presentation
    as a fallback when PPTX generation fails or files are corrupted.
    """
    # For development, return mock response
    # TODO: Implement actual conversion when OAuth is fully set up

    try:
        # Simulate conversion process
        await asyncio.sleep(1)  # Simulate processing time

        # In production, use actual credentials:
        # converter = GoogleSlidesConverter()
        # result = await converter.convert_svg_to_slides(
        #     request.svg_content,
        #     credentials,
        #     request.presentation_title,
        #     request.slide_size
        # )

        # Mock successful conversion
        mock_presentation_id = f"mock_presentation_{int(datetime.now().timestamp())}"

        return GoogleSlidesConversionResponse(
            success=True,
            presentation_id=mock_presentation_id,
            presentation_url=f"https://docs.google.com/presentation/d/{mock_presentation_id}/edit",
            thumbnail_url=f"https://drive.google.com/thumbnail?id={mock_presentation_id}",
            fallback_used=True
        )

    except Exception as e:
        logger.error(f"Google Slides conversion failed: {str(e)}")

        return GoogleSlidesConversionResponse(
            success=False,
            error_message=str(e),
            fallback_used=True
        )


@router.get("/presentations/{presentation_id}/thumbnail")
async def get_presentation_thumbnail(
    presentation_id: str,
    user=Depends(get_current_user)
):
    """Get thumbnail image for a Google Slides presentation."""

    # Mock thumbnail for development
    # TODO: Implement actual thumbnail generation

    # Return mock image data
    from PIL import Image
    import io

    img = Image.new('RGB', (400, 300), color='lightblue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    return JSONResponse(
        content={
            "thumbnail_url": f"data:image/png;base64,{base64.b64encode(img_bytes.getvalue()).decode()}"
        }
    )


@router.get("/health")
async def google_slides_health_check():
    """Health check for Google Slides integration."""

    # Check if client secrets file exists
    handler = GoogleSlidesOAuthHandler()
    secrets_exist = Path(handler.client_secrets_file).exists()

    return {
        "status": "healthy" if secrets_exist else "misconfigured",
        "google_oauth_configured": secrets_exist,
        "available_endpoints": [
            "/google-slides/oauth/initiate",
            "/google-slides/oauth/callback",
            "/google-slides/convert",
            "/google-slides/presentations/{id}/thumbnail"
        ],
        "timestamp": datetime.now().isoformat()
    }


# Utility functions for integration with main conversion pipeline

async def convert_with_google_slides_fallback(
    svg_content: str,
    google_credentials: Optional[dict] = None,
    presentation_title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Utility function to convert SVG with Google Slides fallback.

    This can be used by other parts of the system when PPTX conversion
    fails or when the generated PPTX file is corrupted.
    """
    if not google_credentials:
        return {
            "success": False,
            "error_message": "Google Slides fallback requires OAuth credentials",
            "fallback_available": False
        }

    try:
        converter = GoogleSlidesConverter()
        result = await converter.convert_svg_to_slides(
            svg_content,
            google_credentials,
            presentation_title
        )

        return {
            **result,
            "fallback_used": True,
            "conversion_method": "google_slides"
        }

    except Exception as e:
        logger.error(f"Google Slides fallback failed: {str(e)}")
        return {
            "success": False,
            "error_message": str(e),
            "fallback_used": True,
            "fallback_failed": True
        }