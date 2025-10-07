#!/usr/bin/env python3
"""
Unit tests for TokenStore (core.auth.token_store).

Tests encryption, storage, retrieval, and isolation of OAuth tokens.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
from cryptography.fernet import Fernet

from core.auth.token_store import TokenStore, TokenInfo


class TestTokenStoreInitialization:
    """Test TokenStore initialization and key generation."""

    def test_initialization_creates_env_file(self):
        """TokenStore creates .env file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            assert env_path.exists()
            assert store.env_path == env_path

    def test_initialization_generates_encryption_key(self):
        """TokenStore generates encryption key if not exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Key should be generated and stored in encryption.key file
            key_path = env_path.parent / "encryption.key"
            assert key_path.exists()
            key_content = key_path.read_text()
            assert len(key_content.strip()) > 0  # Has encryption key

    def test_initialization_uses_existing_key(self):
        """TokenStore uses existing encryption key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"

            # Pre-create with key
            existing_key = Fernet.generate_key().decode()
            env_path.write_text(f"TOKEN_ENCRYPTION_KEY={existing_key}\n")

            store = TokenStore(env_path)

            # Should use existing key
            env_content = env_path.read_text()
            assert f"TOKEN_ENCRYPTION_KEY={existing_key}" in env_content

    def test_file_permissions_set_to_600(self):
        """TokenStore sets file permissions to user-only (600)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Check file permissions (user read/write only)
            file_stat = env_path.stat()
            permissions = oct(file_stat.st_mode)[-3:]
            assert permissions == "600"


class TestTokenEncryption:
    """Test token encryption and decryption."""

    def test_token_encryption_decryption(self):
        """Tokens are encrypted and can be decrypted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Save encrypted token
            store.save_refresh_token(
                user_id="user1",
                refresh_token="secret_refresh_token_123",
                google_sub="google_sub_456",
                email="user1@example.com"
            )

            # Retrieve and verify decryption
            token = store.get_refresh_token("user1")
            assert token == "secret_refresh_token_123"

    def test_encrypted_token_not_plaintext_in_file(self):
        """Encrypted token is not stored as plaintext."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Save token
            store.save_refresh_token(
                user_id="user1",
                refresh_token="secret_refresh_token_123",
                google_sub="sub",
                email="user@example.com"
            )

            # Check file content - should NOT contain plaintext token
            file_content = env_path.read_text()
            assert "secret_refresh_token_123" not in file_content
            assert "GOOGLE_TOKEN_USER1_REFRESH_TOKEN=" in file_content

    def test_encryption_uses_fernet(self):
        """Encryption uses Fernet (AES-128)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Verify cipher is Fernet
            assert isinstance(store.cipher, Fernet)


class TestTokenStorage:
    """Test token storage and retrieval."""

    def test_save_refresh_token(self):
        """save_refresh_token stores token correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            store.save_refresh_token(
                user_id="alice",
                refresh_token="token123",
                google_sub="sub456",
                email="alice@example.com",
                scopes="openid email profile"
            )

            # Verify token stored
            assert store.has_token("alice")
            assert store.get_refresh_token("alice") == "token123"

    def test_get_refresh_token_not_exists(self):
        """get_refresh_token returns None for non-existent user."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            token = store.get_refresh_token("nonexistent")
            assert token is None

    def test_has_token_true_when_exists(self):
        """has_token returns True when token exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            store.save_refresh_token("user1", "token", "sub", "user@example.com")
            assert store.has_token("user1") is True

    def test_has_token_false_when_not_exists(self):
        """has_token returns False when token doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            assert store.has_token("nonexistent") is False

    def test_delete_token(self):
        """delete_token removes token."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Save and verify
            store.save_refresh_token("user1", "token", "sub", "user@example.com")
            assert store.has_token("user1")

            # Delete and verify
            store.delete_token("user1")
            assert not store.has_token("user1")


class TestTokenInfo:
    """Test TokenInfo retrieval."""

    def test_get_token_info_complete(self):
        """get_token_info returns complete TokenInfo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            store.save_refresh_token(
                user_id="alice",
                refresh_token="token123",
                google_sub="sub456",
                email="alice@example.com",
                scopes="openid email profile"
            )

            info = store.get_token_info("alice")

            assert isinstance(info, TokenInfo)
            # TokenInfo doesn't include refresh_token (security: not in metadata)
            assert info.user_id == "alice"
            assert info.google_sub == "sub456"
            assert info.email == "alice@example.com"
            assert info.scopes == "openid email profile"

    def test_get_token_info_not_exists(self):
        """get_token_info returns None for non-existent user."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            info = store.get_token_info("nonexistent")
            assert info is None


class TestUserIsolation:
    """Test per-user token isolation."""

    def test_multiple_users_isolated(self):
        """Multiple users have isolated tokens."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Save tokens for multiple users
            store.save_refresh_token("alice", "token_alice", "sub_alice", "alice@example.com")
            store.save_refresh_token("bob", "token_bob", "sub_bob", "bob@example.com")
            store.save_refresh_token("charlie", "token_charlie", "sub_charlie", "charlie@example.com")

            # Verify isolation
            assert store.get_refresh_token("alice") == "token_alice"
            assert store.get_refresh_token("bob") == "token_bob"
            assert store.get_refresh_token("charlie") == "token_charlie"

    def test_user_id_normalization(self):
        """User IDs are normalized (uppercase, underscore-separated)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Save with various formats
            store.save_refresh_token("alice-bob", "token1", "sub", "alice@example.com")

            # Check normalization in file
            content = env_path.read_text()
            assert "GOOGLE_TOKEN_ALICE_BOB_REFRESH_TOKEN=" in content

    def test_delete_one_user_keeps_others(self):
        """Deleting one user's token doesn't affect others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Create multiple users
            store.save_refresh_token("alice", "token_alice", "sub_alice", "alice@example.com")
            store.save_refresh_token("bob", "token_bob", "sub_bob", "bob@example.com")

            # Delete one
            store.delete_token("alice")

            # Verify others intact
            assert not store.has_token("alice")
            assert store.has_token("bob")
            assert store.get_refresh_token("bob") == "token_bob"


class TestHelperFunctions:
    """Test helper functions like get_cli_token_store."""

    @patch('core.auth.token_store.Path.home')
    def test_get_cli_token_store_path(self, mock_home):
        """get_cli_token_store uses ~/.svg2pptx/.env."""
        from core.auth import get_cli_token_store

        mock_home.return_value = Path("/mock/home")

        with patch('core.auth.token_store.TokenStore') as mock_store_class:
            get_cli_token_store()

            # Verify path
            call_args = mock_store_class.call_args
            assert call_args[0][0] == Path("/mock/home/.svg2pptx/.env")

    def test_get_api_token_store_path(self):
        """get_api_token_store uses project .env."""
        from core.auth import get_api_token_store

        with patch('core.auth.token_store.TokenStore') as mock_store_class:
            get_api_token_store()

            # Verify path (uses absolute path to current directory .env)
            call_args = mock_store_class.call_args
            assert call_args[0][0] == Path.cwd() / ".env"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_user_id_raises_error(self):
        """Empty user_id raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            with pytest.raises(ValueError, match="user_id cannot be empty"):
                store.save_refresh_token("", "token", "sub", "email@example.com")

    def test_special_characters_in_user_id(self):
        """Special characters in user_id are handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Should normalize special chars to underscore
            store.save_refresh_token("user@domain.com", "token", "sub", "user@example.com")

            # Should be retrievable
            assert store.has_token("user@domain.com")
            assert store.get_refresh_token("user@domain.com") == "token"

    def test_update_existing_token(self):
        """Updating existing token overwrites previous value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Save initial token
            store.save_refresh_token("user1", "token_old", "sub", "user@example.com")
            assert store.get_refresh_token("user1") == "token_old"

            # Update token
            store.save_refresh_token("user1", "token_new", "sub", "user@example.com")
            assert store.get_refresh_token("user1") == "token_new"

    def test_corrupted_encrypted_token(self):
        """Corrupted encrypted token raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            store = TokenStore(env_path)

            # Manually corrupt the token by appending to file
            with open(env_path, 'a') as f:
                f.write("GOOGLE_TOKEN_USER1_REFRESH_TOKEN=corrupted_invalid_base64!!!\n")

            # Should handle gracefully
            with pytest.raises(Exception):  # Fernet raises InvalidToken
                store.get_refresh_token("user1")
