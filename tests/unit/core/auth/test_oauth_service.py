#!/usr/bin/env python3
"""
Unit tests for GoogleOAuthService (core.auth.oauth_service).

Tests OAuth flow, CSRF protection, token management, and error handling.
"""

import secrets
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urlparse, parse_qs

import pytest
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError

from core.auth.oauth_service import GoogleOAuthService, OAuthError
from core.auth.token_store import TokenStore, TokenInfo


@pytest.fixture
def mock_token_store():
    """Mock TokenStore for testing."""
    store = Mock(spec=TokenStore)
    store.has_token = Mock(return_value=False)
    store.get_token_info = Mock(return_value=None)
    store.save_refresh_token = Mock()
    store.delete_token = Mock()
    return store


@pytest.fixture
def oauth_service(mock_token_store):
    """GoogleOAuthService instance with mock store."""
    return GoogleOAuthService(
        token_store=mock_token_store,
        client_id="test_client_id.apps.googleusercontent.com",
        client_secret="test_client_secret"
    )


@pytest.fixture
def mock_oauth_flow():
    """Mock OAuth Flow for testing OAuth flow interactions.

    Mocks google_auth_oauthlib.flow.Flow to avoid real OAuth calls and
    InsecureTransportError (HTTP vs HTTPS).

    Returns:
        tuple: (mock_flow_class, mock_flow_instance, mock_credentials)
    """
    with patch('core.auth.oauth_service.Flow') as mock_flow_class:
        # Create mock flow instance
        mock_flow = Mock()

        # Mock factory method - Flow.from_client_config()
        mock_flow_class.from_client_config.return_value = mock_flow

        # Mock authorization_url() - returns (url, state) tuple
        mock_flow.authorization_url.return_value = (
            'https://accounts.google.com/o/oauth2/auth?'
            'client_id=test&redirect_uri=http://localhost:8080/oauth2/callback&'
            'response_type=code&access_type=offline&include_granted_scopes=true&'
            'prompt=consent&state=test_state_token',
            'test_state_token'  # state value
        )

        # Mock fetch_token() - avoids InsecureTransportError
        mock_flow.fetch_token = Mock()

        # Mock credentials property with all required attributes
        mock_creds = Mock(spec=Credentials)
        mock_creds.token = 'mock_access_token_123'
        mock_creds.refresh_token = 'mock_refresh_token_456'
        mock_creds.token_uri = 'https://oauth2.googleapis.com/token'
        mock_creds.client_id = 'test_client_id.apps.googleusercontent.com'
        mock_creds.client_secret = 'test_client_secret'
        mock_creds.scopes = [
            'openid',
            'email',
            'profile',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/presentations'
        ]
        mock_creds.valid = True
        mock_creds.expired = False
        mock_flow.credentials = mock_creds

        yield mock_flow_class, mock_flow, mock_creds


class TestOAuthInitialization:
    """Test GoogleOAuthService initialization."""

    def test_initialization_with_valid_credentials(self, mock_token_store):
        """Service initializes with valid credentials."""
        service = GoogleOAuthService(
            token_store=mock_token_store,
            client_id="client_id",
            client_secret="client_secret"
        )

        assert service.token_store == mock_token_store
        assert service.client_id == "client_id"
        assert service.client_secret == "client_secret"

    def test_initialization_without_credentials_raises_error(self, mock_token_store):
        """Initialization without credentials raises ValueError."""
        with pytest.raises(ValueError, match="client_id and client_secret are required"):
            GoogleOAuthService(
                token_store=mock_token_store,
                client_id=None,
                client_secret="secret"
            )

    def test_scopes_configuration(self, oauth_service):
        """Service has correct OAuth scopes."""
        assert 'openid' in oauth_service.SCOPES
        assert 'email' in oauth_service.SCOPES
        assert 'profile' in oauth_service.SCOPES
        assert 'https://www.googleapis.com/auth/drive.file' in oauth_service.SCOPES
        assert 'https://www.googleapis.com/auth/presentations' in oauth_service.SCOPES


class TestOAuthFlowInitiation:
    """Test OAuth flow initiation (start_auth_flow)."""

    def test_start_auth_flow_cli_mode(self, oauth_service):
        """start_auth_flow returns correct URL for CLI mode."""
        auth_url = oauth_service.start_auth_flow(user_id="alice", is_cli=True)

        # Parse URL
        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)

        assert "accounts.google.com" in auth_url
        assert params['client_id'][0] == "test_client_id.apps.googleusercontent.com"
        assert params['redirect_uri'][0] == "http://localhost:8080/oauth2/callback"
        assert params['response_type'][0] == "code"
        assert params['access_type'][0] == "offline"
        assert params['include_granted_scopes'][0] == "true"
        assert params['prompt'][0] == "consent"
        assert 'state' in params

    def test_start_auth_flow_api_mode(self, oauth_service):
        """start_auth_flow returns correct URL for API mode."""
        auth_url = oauth_service.start_auth_flow(user_id="alice", is_cli=False)

        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)

        assert params['redirect_uri'][0] == "http://localhost:8080/oauth2/callback"

    def test_state_token_is_cryptographically_secure(self, oauth_service):
        """State token is cryptographically secure."""
        auth_url1 = oauth_service.start_auth_flow("alice")
        auth_url2 = oauth_service.start_auth_flow("alice")

        # Extract state tokens
        state1 = parse_qs(urlparse(auth_url1).query)['state'][0]
        state2 = parse_qs(urlparse(auth_url2).query)['state'][0]

        # Should be different (random)
        assert state1 != state2
        # Should be long enough (32 bytes urlsafe = ~43 chars)
        assert len(state1) >= 40

    def test_state_token_stored_for_validation(self, oauth_service):
        """State token is stored for later validation."""
        auth_url = oauth_service.start_auth_flow("alice")
        state = parse_qs(urlparse(auth_url).query)['state'][0]

        # State should be in _state_store
        assert state in oauth_service._state_store
        assert oauth_service._state_store[state] == "alice"


class TestCSRFProtection:
    """Test CSRF protection via state validation."""

    def test_invalid_state_raises_error(self, oauth_service):
        """Invalid state token raises OAuthError."""
        with pytest.raises(OAuthError, match="Invalid or expired state"):
            oauth_service.handle_callback(
                user_id="alice",
                authorization_response="http://callback?state=invalid_state&code=auth_code"
            )

    @patch('core.auth.oauth_service.Flow.from_client_config')
    def test_valid_state_accepted(self, mock_flow_class, oauth_service, mock_token_store):
        """Valid state token is accepted."""
        # Start flow to get valid state
        auth_url = oauth_service.start_auth_flow("alice")
        state = parse_qs(urlparse(auth_url).query)['state'][0]

        # Mock flow
        mock_flow = Mock()
        mock_flow.fetch_token = Mock()
        mock_flow.credentials = Mock(spec=Credentials)
        mock_flow.credentials.refresh_token = "refresh_token_123"
        mock_flow.credentials.token = "access_token"
        mock_flow.credentials.id_token = {'sub': 'google_sub', 'email': 'alice@example.com'}
        mock_flow_class.return_value = mock_flow

        # Should not raise error
        callback_url = f"http://callback?state={state}&code=auth_code"
        oauth_service.handle_callback("alice", callback_url)

        # State should be removed after use
        assert state not in oauth_service._state_store

    def test_state_removed_after_use(self, oauth_service):
        """State token is removed after successful use."""
        auth_url = oauth_service.start_auth_flow("alice")
        state = parse_qs(urlparse(auth_url).query)['state'][0]

        assert state in oauth_service._state_store

        # After callback (even if it fails), state should be cleaned up
        try:
            oauth_service.handle_callback("alice", f"http://callback?state={state}&code=code")
        except:
            pass

        # State should be removed
        assert state not in oauth_service._state_store


class TestTokenHandling:
    """Test token handling in OAuth callback."""

    @patch('core.auth.oauth_service.Flow.from_client_config')
    def test_handle_callback_saves_token(self, mock_flow_class, oauth_service, mock_token_store):
        """handle_callback saves refresh token."""
        # Start flow
        auth_url = oauth_service.start_auth_flow("alice")
        state = parse_qs(urlparse(auth_url).query)['state'][0]

        # Mock flow
        mock_flow = Mock()
        mock_flow.fetch_token = Mock()
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.refresh_token = "refresh_token_abc"
        mock_credentials.token = "access_token_xyz"
        mock_credentials.id_token = {'sub': 'google_sub_123', 'email': 'alice@example.com'}
        mock_flow.credentials = mock_credentials
        mock_flow_class.return_value = mock_flow

        # Handle callback
        callback_url = f"http://callback?state={state}&code=auth_code"
        credentials = oauth_service.handle_callback("alice", callback_url)

        # Verify token saved
        mock_token_store.save_refresh_token.assert_called_once()
        call_args = mock_token_store.save_refresh_token.call_args
        assert call_args[1]['user_id'] == "alice"
        assert call_args[1]['refresh_token'] == "refresh_token_abc"
        assert call_args[1]['google_sub'] == "google_sub_123"
        assert call_args[1]['email'] == "alice@example.com"

    @patch('core.auth.oauth_service.Flow.from_client_config')
    def test_handle_callback_returns_credentials(self, mock_flow_class, oauth_service):
        """handle_callback returns valid credentials."""
        auth_url = oauth_service.start_auth_flow("alice")
        state = parse_qs(urlparse(auth_url).query)['state'][0]

        mock_flow = Mock()
        mock_flow.fetch_token = Mock()
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.refresh_token = "refresh"
        mock_credentials.id_token = {'sub': 'sub', 'email': 'alice@example.com'}
        mock_flow.credentials = mock_credentials
        mock_flow_class.return_value = mock_flow

        callback_url = f"http://callback?state={state}&code=code"
        credentials = oauth_service.handle_callback("alice", callback_url)

        assert credentials == mock_credentials


class TestCredentialRetrieval:
    """Test credential retrieval and refresh."""

    def test_get_credentials_no_token_raises_error(self, oauth_service, mock_token_store):
        """get_credentials raises error when no token exists."""
        mock_token_store.has_token.return_value = False

        with pytest.raises(OAuthError, match="User alice has no OAuth token"):
            oauth_service.get_credentials("alice")

    @patch('google.oauth2.credentials.Credentials')
    def test_get_credentials_with_valid_token(self, mock_creds_class, oauth_service, mock_token_store):
        """get_credentials returns credentials for valid token."""
        # Mock stored token
        token_info = TokenInfo(
            refresh_token="refresh_token_123",
            google_sub="sub",
            email="alice@example.com",
            scopes="openid email"
        )
        mock_token_store.has_token.return_value = True
        mock_token_store.get_token_info.return_value = token_info

        # Mock credentials
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.expired = False
        mock_credentials.valid = True
        mock_creds_class.return_value = mock_credentials

        credentials = oauth_service.get_credentials("alice")

        # Verify credentials created with refresh token
        mock_creds_class.assert_called_once()
        call_kwargs = mock_creds_class.call_args[1]
        assert call_kwargs['token'] == None  # No access token initially
        assert call_kwargs['refresh_token'] == "refresh_token_123"
        assert call_kwargs['client_id'] == "test_client_id.apps.googleusercontent.com"
        assert call_kwargs['client_secret'] == "test_client_secret"

    @patch('google.oauth2.credentials.Credentials')
    @patch('google.auth.transport.requests.Request')
    def test_get_credentials_auto_refresh(self, mock_request, mock_creds_class, oauth_service, mock_token_store):
        """get_credentials auto-refreshes expired tokens."""
        # Mock stored token
        token_info = TokenInfo(
            refresh_token="refresh",
            google_sub="sub",
            email="alice@example.com",
            scopes="openid"
        )
        mock_token_store.has_token.return_value = True
        mock_token_store.get_token_info.return_value = token_info

        # Mock credentials - expired
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.expired = True
        mock_credentials.valid = False
        mock_credentials.refresh = Mock()
        mock_creds_class.return_value = mock_credentials

        credentials = oauth_service.get_credentials("alice")

        # Verify refresh was called
        mock_credentials.refresh.assert_called_once()

    @patch('google.oauth2.credentials.Credentials')
    def test_get_credentials_invalid_grant_cleanup(self, mock_creds_class, oauth_service, mock_token_store):
        """get_credentials cleans up token on invalid_grant error."""
        token_info = TokenInfo(
            refresh_token="invalid_refresh",
            google_sub="sub",
            email="alice@example.com",
            scopes="openid"
        )
        mock_token_store.has_token.return_value = True
        mock_token_store.get_token_info.return_value = token_info

        # Mock credentials that fail to refresh
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.expired = True
        mock_credentials.refresh = Mock(side_effect=RefreshError("invalid_grant"))
        mock_creds_class.return_value = mock_credentials

        with pytest.raises(OAuthError, match="Token has been revoked"):
            oauth_service.get_credentials("alice")

        # Verify token was deleted
        mock_token_store.delete_token.assert_called_once_with("alice")


class TestTokenRevocation:
    """Test token revocation."""

    def test_revoke_token_success(self, oauth_service, mock_token_store):
        """revoke_token deletes token from store."""
        mock_token_store.has_token.return_value = True

        oauth_service.revoke_token("alice")

        mock_token_store.delete_token.assert_called_once_with("alice")

    def test_revoke_token_not_exists(self, oauth_service, mock_token_store):
        """revoke_token handles non-existent token gracefully."""
        mock_token_store.has_token.return_value = False

        # Should not raise error
        oauth_service.revoke_token("alice")

        # Should not call delete
        mock_token_store.delete_token.assert_not_called()


class TestHelperMethods:
    """Test helper methods."""

    def test_is_authenticated_true(self, oauth_service, mock_token_store):
        """is_authenticated returns True when token exists."""
        mock_token_store.has_token.return_value = True

        assert oauth_service.is_authenticated("alice") is True

    def test_is_authenticated_false(self, oauth_service, mock_token_store):
        """is_authenticated returns False when no token."""
        mock_token_store.has_token.return_value = False

        assert oauth_service.is_authenticated("alice") is False

    def test_get_user_info(self, oauth_service, mock_token_store):
        """get_user_info returns user information."""
        token_info = TokenInfo(
            refresh_token="token",
            google_sub="sub123",
            email="alice@example.com",
            scopes="openid email"
        )
        mock_token_store.get_token_info.return_value = token_info

        user_info = oauth_service.get_user_info("alice")

        assert user_info['email'] == "alice@example.com"
        assert user_info['google_sub'] == "sub123"
        assert user_info['authenticated'] is True

    def test_get_user_info_not_authenticated(self, oauth_service, mock_token_store):
        """get_user_info returns unauthenticated state."""
        mock_token_store.get_token_info.return_value = None

        user_info = oauth_service.get_user_info("alice")

        assert user_info['authenticated'] is False


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_user_id_raises_error(self, oauth_service):
        """Empty user_id raises ValueError."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            oauth_service.start_auth_flow("")

    @patch('core.auth.oauth_service.Flow.from_client_config')
    def test_missing_refresh_token_in_callback(self, mock_flow_class, oauth_service):
        """Missing refresh token in callback raises error."""
        auth_url = oauth_service.start_auth_flow("alice")
        state = parse_qs(urlparse(auth_url).query)['state'][0]

        # Mock flow without refresh token
        mock_flow = Mock()
        mock_flow.fetch_token = Mock()
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.refresh_token = None  # No refresh token!
        mock_credentials.id_token = {'sub': 'sub', 'email': 'alice@example.com'}
        mock_flow.credentials = mock_credentials
        mock_flow_class.return_value = mock_flow

        callback_url = f"http://callback?state={state}&code=code"

        with pytest.raises(OAuthError, match="No refresh token received"):
            oauth_service.handle_callback("alice", callback_url)

    def test_concurrent_auth_flows_same_user(self, oauth_service):
        """Concurrent auth flows for same user maintain separate states."""
        url1 = oauth_service.start_auth_flow("alice")
        url2 = oauth_service.start_auth_flow("alice")

        state1 = parse_qs(urlparse(url1).query)['state'][0]
        state2 = parse_qs(urlparse(url2).query)['state'][0]

        # Different states
        assert state1 != state2

        # Both stored
        assert state1 in oauth_service._state_store
        assert state2 in oauth_service._state_store
