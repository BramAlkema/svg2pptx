#!/usr/bin/env python3
"""
Authentication commands for Google OAuth.
"""

import click
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import logging

from core.auth import (
    GoogleOAuthService,
    get_cli_token_store,
    get_system_username,
    OAuthError,
)

logger = logging.getLogger(__name__)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    oauth_service = None
    user_id = None
    success = False

    def do_GET(self):
        """Handle OAuth callback."""
        try:
            # Parse callback URL
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            if 'error' in params:
                error = params['error'][0]
                self.send_error_response(f"OAuth error: {error}")
                return

            if 'code' not in params or 'state' not in params:
                self.send_error_response("Missing code or state parameter")
                return

            # Full callback URL
            callback_url = f"http://localhost:8080{self.path}"

            # Handle callback
            credentials = self.oauth_service.handle_callback(
                user_id=self.user_id,
                authorization_response=callback_url
            )

            OAuthCallbackHandler.success = True

            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            html = """
            <html>
            <head><title>Authentication Successful</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: green;">✅ Authentication Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())

        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            self.send_error_response(str(e))

    def send_error_response(self, error_msg):
        """Send error response to browser."""
        self.send_response(400)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        html = f"""
        <html>
        <head><title>Authentication Failed</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: red;">❌ Authentication Failed</h1>
            <p>{error_msg}</p>
            <p>Please return to the terminal and try again.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress default log messages."""
        pass


@click.group()
def auth():
    """Manage Google authentication."""
    pass


@auth.command()
@click.option('--status', is_flag=True, help='Check authentication status')
@click.option('--revoke', is_flag=True, help='Revoke authentication')
def google(status, revoke):
    """
    Authenticate with Google Drive/Slides.

    Examples:
        svg2pptx auth google              # Authenticate
        svg2pptx auth google --status     # Check status
        svg2pptx auth google --revoke     # Revoke access
    """
    try:
        user_id = get_system_username()
        token_store = get_cli_token_store()

        # Check status
        if status:
            if token_store.has_token(user_id):
                info = token_store.get_token_info(user_id)
                click.echo(f"✅ Authenticated as: {info.email}")
                click.echo(f"   Google Sub: {info.google_sub}")
                click.echo(f"   Created: {info.created_at}")
                click.echo(f"   Last used: {info.last_used}")
            else:
                click.echo(f"❌ Not authenticated. Run 'svg2pptx auth google' to authenticate.")
            return

        # Revoke access
        if revoke:
            if not token_store.has_token(user_id):
                click.echo("❌ Not authenticated")
                return

            if click.confirm("Are you sure you want to revoke Google access?"):
                token_store.delete_token(user_id)
                click.echo("✅ Google access revoked")
            return

        # Authenticate
        if token_store.has_token(user_id):
            info = token_store.get_token_info(user_id)
            click.echo(f"Already authenticated as: {info.email}")
            if not click.confirm("Re-authenticate?"):
                return

        # Get OAuth credentials from environment
        import os
        client_id = os.getenv('GOOGLE_DRIVE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_DRIVE_CLIENT_SECRET')

        if not client_id or not client_secret:
            click.echo("❌ OAuth not configured. Please set:")
            click.echo("   GOOGLE_DRIVE_CLIENT_ID")
            click.echo("   GOOGLE_DRIVE_CLIENT_SECRET")
            return

        # Create OAuth service
        oauth_service = GoogleOAuthService(
            token_store=token_store,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://localhost:8080/oauth2/callback"
        )

        # Start OAuth flow
        auth_url = oauth_service.start_auth_flow(user_id, is_cli=True)

        # Setup callback server
        OAuthCallbackHandler.oauth_service = oauth_service
        OAuthCallbackHandler.user_id = user_id
        OAuthCallbackHandler.success = False

        server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)

        # Open browser
        click.echo("🌐 Opening browser for authentication...")
        click.echo(f"   If browser doesn't open, visit: {auth_url}")
        webbrowser.open(auth_url)

        # Wait for callback
        click.echo("⏳ Waiting for authentication... (listening on http://localhost:8080)")

        # Handle single request
        server.handle_request()

        if OAuthCallbackHandler.success:
            click.echo("✅ Successfully authenticated with Google!")
        else:
            click.echo("❌ Authentication failed. Check browser for details.")

    except OAuthError as e:
        click.echo(f"❌ OAuth error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        click.echo(f"❌ Error: {e}")
