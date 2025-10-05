#!/usr/bin/env python3
"""
Google OAuth service for multi-user authentication.

Supports both CLI (local server) and API (redirect) OAuth flows.
"""

import logging
import secrets
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from .token_store import TokenStore

logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """OAuth-related errors."""
    pass


class GoogleOAuthService:
    """Multi-user OAuth service for Google Drive/Slides."""

    SCOPES = [
        'openid',
        'email',
        'profile',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/presentations',
    ]

    def __init__(
        self,
        token_store: TokenStore,
        client_id: str,
        client_secret: str,
        redirect_uri: str = None,
    ):
        """
        Initialize OAuth service.

        Args:
            token_store: Token storage backend
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: OAuth redirect URI (default: http://localhost:8080/oauth2/callback)
        """
        self.token_store = token_store
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri or "http://localhost:8080/oauth2/callback"

        # State storage for CSRF protection
        self._state_store = {}

    def _create_flow(self, is_cli: bool = False) -> Flow:
        """Create OAuth flow with proper configuration."""
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=self.SCOPES,
        )
        flow.redirect_uri = self.redirect_uri

        return flow

    def start_auth_flow(self, user_id: str, is_cli: bool = False) -> str:
        """
        Start OAuth flow and return authorization URL.

        Args:
            user_id: User identifier (system username for CLI, user ID for API)
            is_cli: Whether this is a CLI flow (uses local server)

        Returns:
            Authorization URL for user to visit
        """
        flow = self._create_flow(is_cli)

        # Generate CSRF state token
        state = secrets.token_urlsafe(32)
        self._state_store[state] = user_id

        # Build authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',  # Force consent to get refresh token
            state=state,
        )

        logger.info(f"OAuth flow started for user: {user_id}")
        return auth_url

    def handle_callback(
        self,
        user_id: str,
        authorization_response: str,
    ) -> Credentials:
        """
        Handle OAuth callback and exchange code for tokens.

        Args:
            user_id: User identifier
            authorization_response: Full callback URL with code and state

        Returns:
            Google credentials object

        Raises:
            OAuthError: If state validation fails or token exchange fails
        """
        flow = self._create_flow()

        try:
            # Fetch token (this validates state internally)
            flow.fetch_token(authorization_response=authorization_response)
            creds = flow.credentials

            # Validate state from URL
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(authorization_response)
            params = parse_qs(parsed.query)
            state = params.get('state', [None])[0]

            if not state or state not in self._state_store:
                raise OAuthError("Invalid state parameter - possible CSRF attack")

            # Verify user_id matches
            stored_user_id = self._state_store.pop(state)
            if stored_user_id != user_id:
                raise OAuthError("User ID mismatch in OAuth callback")

            # Parse ID token for user info
            id_token_data = self._parse_id_token(creds.id_token)
            google_sub = id_token_data.get('sub', '')
            email = id_token_data.get('email', '')

            # Save refresh token
            if creds.refresh_token:
                self.token_store.save_refresh_token(
                    user_id=user_id,
                    refresh_token=creds.refresh_token,
                    google_sub=google_sub,
                    email=email,
                    scopes=' '.join(self.SCOPES),
                )
                logger.info(f"Refresh token saved for user: {user_id} ({email})")
            else:
                logger.warning(f"No refresh token received for user: {user_id}")

            return creds

        except Exception as e:
            logger.error(f"OAuth callback failed: {e}")
            raise OAuthError(f"OAuth callback failed: {e}")

    def get_credentials(self, user_id: str) -> Credentials:
        """
        Get valid credentials for user (auto-refresh if needed).

        Args:
            user_id: User identifier

        Returns:
            Valid Google credentials

        Raises:
            OAuthError: If user not authenticated or refresh fails
        """
        refresh_token = self.token_store.get_refresh_token(user_id)
        if not refresh_token:
            raise OAuthError(
                f"User {user_id} not authenticated. Run OAuth flow first."
            )

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES,
        )

        # Auto-refresh if needed
        if not creds.valid:
            try:
                creds.refresh(Request())
                logger.debug(f"Access token refreshed for user: {user_id}")
            except Exception as e:
                # Handle invalid_grant (revoked token)
                if 'invalid_grant' in str(e):
                    logger.error(f"Refresh token revoked for user: {user_id}")
                    self.token_store.delete_token(user_id)
                    raise OAuthError(
                        f"Refresh token revoked. Please reconnect Google account."
                    )
                raise OAuthError(f"Failed to refresh token: {e}")

        return creds

    def _parse_id_token(self, id_token: str) -> dict:
        """Parse ID token JWT to extract user info."""
        import json
        import base64

        # ID token format: header.payload.signature
        parts = id_token.split('.')
        if len(parts) != 3:
            return {}

        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        try:
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception as e:
            logger.warning(f"Failed to parse ID token: {e}")
            return {}

    def revoke_access(self, user_id: str) -> None:
        """Revoke OAuth access and delete stored token."""
        self.token_store.delete_token(user_id)
        logger.info(f"OAuth access revoked for user: {user_id}")
