#!/usr/bin/env python3
"""
Secure token storage for OAuth refresh tokens.

Stores encrypted refresh tokens in .env file for simplicity.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet


@dataclass
class TokenInfo:
    """Information about a stored OAuth token."""
    user_id: str
    google_sub: str
    email: str
    scopes: str
    created_at: datetime
    last_used: datetime


class TokenStore:
    """Environment-based token storage using .env file."""

    DEFAULT_SCOPES = "openid email profile https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/presentations"

    def __init__(self, env_path: Path, encryption_key: Optional[str] = None):
        """
        Initialize token store.

        Args:
            env_path: Path to .env file
            encryption_key: Base64-encoded Fernet key (auto-generated if None)
        """
        self.env_path = env_path
        self.encryption_key = encryption_key or self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key.encode())

        # Ensure .env file exists
        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        self.env_path.touch(exist_ok=True)

        # Set secure file permissions (user-only read/write)
        if os.name != 'nt':  # Unix-like systems
            os.chmod(self.env_path, 0o600)

    def _get_or_create_encryption_key(self) -> str:
        """Get existing encryption key or generate new one."""
        key_path = self.env_path.parent / 'encryption.key'

        if key_path.exists():
            with open(key_path, 'r') as f:
                return f.read().strip()

        # Generate new key
        key = Fernet.generate_key().decode()

        with open(key_path, 'w') as f:
            f.write(key)

        # Set secure permissions on key file
        if os.name != 'nt':
            os.chmod(key_path, 0o600)

        return key

    def _read_env(self) -> dict:
        """Read .env file as dictionary."""
        env_vars = {}
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        return env_vars

    def _write_env(self, env_vars: dict) -> None:
        """Write dictionary to .env file."""
        with open(self.env_path, 'w') as f:
            for key, value in sorted(env_vars.items()):
                f.write(f"{key}={value}\n")

        # Ensure secure permissions
        if os.name != 'nt':
            os.chmod(self.env_path, 0o600)

    def save_refresh_token(
        self,
        user_id: str,
        refresh_token: str,
        google_sub: str,
        email: str,
        scopes: str = None,
    ) -> None:
        """Save encrypted refresh token for user."""
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        encrypted_token = self.cipher.encrypt(refresh_token.encode()).decode()
        scopes = scopes or self.DEFAULT_SCOPES

        env_vars = self._read_env()

        # Store token data with user_id prefix
        prefix = f"GOOGLE_TOKEN_{user_id.upper().replace('-', '_')}"
        env_vars[f"{prefix}_REFRESH_TOKEN"] = encrypted_token
        env_vars[f"{prefix}_SUB"] = google_sub
        env_vars[f"{prefix}_EMAIL"] = email
        env_vars[f"{prefix}_SCOPES"] = scopes

        # Update timestamps
        now = datetime.now().isoformat()
        if f"{prefix}_CREATED_AT" not in env_vars:
            env_vars[f"{prefix}_CREATED_AT"] = now
        env_vars[f"{prefix}_LAST_USED"] = now

        self._write_env(env_vars)

    def get_refresh_token(self, user_id: str) -> Optional[str]:
        """Get decrypted refresh token for user."""
        env_vars = self._read_env()
        prefix = f"GOOGLE_TOKEN_{user_id.upper().replace('-', '_')}"

        encrypted_token = env_vars.get(f"{prefix}_REFRESH_TOKEN")
        if not encrypted_token:
            return None

        # Update last_used timestamp
        env_vars[f"{prefix}_LAST_USED"] = datetime.now().isoformat()
        self._write_env(env_vars)

        # Decrypt and return token
        return self.cipher.decrypt(encrypted_token.encode()).decode()

    def has_token(self, user_id: str) -> bool:
        """Check if user has a stored token."""
        env_vars = self._read_env()
        prefix = f"GOOGLE_TOKEN_{user_id.upper().replace('-', '_')}"
        return f"{prefix}_REFRESH_TOKEN" in env_vars

    def delete_token(self, user_id: str) -> None:
        """Delete stored token for user."""
        env_vars = self._read_env()
        prefix = f"GOOGLE_TOKEN_{user_id.upper().replace('-', '_')}"

        # Remove all keys with this prefix
        keys_to_remove = [k for k in env_vars if k.startswith(prefix)]
        for key in keys_to_remove:
            del env_vars[key]

        self._write_env(env_vars)

    def get_token_info(self, user_id: str) -> Optional[TokenInfo]:
        """Get token metadata without the token itself."""
        env_vars = self._read_env()
        prefix = f"GOOGLE_TOKEN_{user_id.upper().replace('-', '_')}"

        if f"{prefix}_REFRESH_TOKEN" not in env_vars:
            return None

        created_at_str = env_vars.get(f"{prefix}_CREATED_AT")
        last_used_str = env_vars.get(f"{prefix}_LAST_USED")

        return TokenInfo(
            user_id=user_id,
            google_sub=env_vars.get(f"{prefix}_SUB", ""),
            email=env_vars.get(f"{prefix}_EMAIL", ""),
            scopes=env_vars.get(f"{prefix}_SCOPES", self.DEFAULT_SCOPES),
            created_at=datetime.fromisoformat(created_at_str) if created_at_str else None,
            last_used=datetime.fromisoformat(last_used_str) if last_used_str else None,
        )


def get_cli_token_store() -> TokenStore:
    """Get token store for CLI usage."""
    env_path = Path.home() / '.svg2pptx' / '.env'
    return TokenStore(env_path)


def get_api_token_store() -> TokenStore:
    """Get token store for API usage (uses project .env)."""
    env_path = Path.cwd() / '.env'
    return TokenStore(env_path)


def get_system_username() -> str:
    """Get current system username for CLI user identification."""
    import getpass
    return getpass.getuser()
