#!/usr/bin/env python3
"""
OAuth API routes for Google authentication.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
import logging

from core.auth import (
    GoogleOAuthService,
    OAuthError,
    get_api_token_store,
)
from ..config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth2", tags=["OAuth"])


class OAuthStartRequest(BaseModel):
    """Request model for starting OAuth flow."""
    user_id: str


class OAuthStatusResponse(BaseModel):
    """Response model for OAuth status."""
    authenticated: bool
    email: str = None
    google_sub: str = None
    scopes: str = None
    created_at: str = None
    last_used: str = None


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


@router.post("/start")
async def start_oauth_flow(request: OAuthStartRequest):
    """
    Start OAuth flow for a user.

    Returns authorization URL for user to visit.
    """
    try:
        oauth_service = get_oauth_service()
        auth_url = oauth_service.start_auth_flow(
            user_id=request.user_id,
            is_cli=False
        )

        return JSONResponse(
            content={
                "auth_url": auth_url,
                "user_id": request.user_id,
                "message": "Visit auth_url to authorize access"
            },
            status_code=200
        )

    except Exception as e:
        logger.error(f"Failed to start OAuth flow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start OAuth flow: {str(e)}"
        )


@router.get("/callback")
async def oauth_callback(request: Request):
    """
    Handle OAuth callback from Google.

    This endpoint is called by Google after user authorization.
    """
    try:
        # Get full callback URL
        callback_url = str(request.url)

        # Extract state to get user_id
        state = request.query_params.get('state')
        if not state:
            raise HTTPException(
                status_code=400,
                detail="Missing state parameter"
            )

        oauth_service = get_oauth_service()

        # Get user_id from state store
        if state not in oauth_service._state_store:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired state parameter"
            )

        user_id = oauth_service._state_store[state]

        # Handle callback and save tokens
        credentials = oauth_service.handle_callback(
            user_id=user_id,
            authorization_response=callback_url
        )

        # Success response
        return JSONResponse(
            content={
                "success": True,
                "message": "Authentication successful",
                "user_id": user_id,
                "email": credentials.id_token.get('email') if credentials.id_token else None
            },
            status_code=200
        )

    except OAuthError as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"OAuth callback failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.get("/status/{user_id}")
async def get_oauth_status(user_id: str):
    """
    Get OAuth authentication status for a user.
    """
    try:
        token_store = get_api_token_store()
        token_info = token_store.get_token_info(user_id)

        if not token_info:
            return JSONResponse(
                content={
                    "authenticated": False,
                    "user_id": user_id
                },
                status_code=200
            )

        return JSONResponse(
            content={
                "authenticated": True,
                "user_id": user_id,
                "email": token_info.email,
                "google_sub": token_info.google_sub,
                "scopes": token_info.scopes,
                "created_at": token_info.created_at.isoformat() if token_info.created_at else None,
                "last_used": token_info.last_used.isoformat() if token_info.last_used else None
            },
            status_code=200
        )

    except Exception as e:
        logger.error(f"Failed to get OAuth status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get OAuth status: {str(e)}"
        )


@router.delete("/revoke/{user_id}")
async def revoke_oauth_access(user_id: str):
    """
    Revoke OAuth access for a user.

    Deletes stored refresh token.
    """
    try:
        oauth_service = get_oauth_service()
        oauth_service.revoke_access(user_id)

        return JSONResponse(
            content={
                "success": True,
                "message": f"OAuth access revoked for user: {user_id}"
            },
            status_code=200
        )

    except Exception as e:
        logger.error(f"Failed to revoke OAuth access: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke OAuth access: {str(e)}"
        )
