#!/usr/bin/env python3
"""
Configuration management for SVG to Google Drive API.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    api_key: str = Field(default="dev-api-key-12345", description="API authentication key")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    
    # Google Drive Configuration
    google_drive_auth_method: str = Field(
        default="oauth",
        description="Authentication method: 'oauth' or 'service_account'"
    )
    google_drive_credentials_path: str = Field(
        default="credentials/service-account.json",
        description="Path to Google Drive service account JSON file (for service_account method)"
    )
    google_drive_client_id: Optional[str] = Field(
        default=None,
        description="Google Drive OAuth client ID (for oauth method)"
    )
    google_drive_client_secret: Optional[str] = Field(
        default=None,
        description="Google Drive OAuth client secret (for oauth method)"
    )
    google_drive_token_file: str = Field(
        default="credentials/oauth-token.json",
        description="Path to store OAuth token (for oauth method)"
    )
    google_drive_folder_id: Optional[str] = Field(
        default=None,
        description="Optional default folder ID for Google Drive uploads"
    )
    
    # API Server Configuration
    host: str = Field(default="127.0.0.1", description="API server host")
    port: int = Field(default=8000, description="API server port")
    workers: int = Field(default=1, description="Number of worker processes")
    
    # Processing Configuration
    max_svg_file_size: int = Field(default=10_000_000, description="Maximum SVG file size in bytes (10MB)")
    temp_dir: str = Field(default="/tmp", description="Temporary directory for file processing")
    
    # SVG Preprocessing Configuration
    svg_preprocessing_enabled: bool = Field(default=True, description="Enable SVG preprocessing optimizations")
    svg_preprocessing_preset: str = Field(default="default", description="Preprocessing preset: minimal, default, aggressive")
    svg_preprocessing_precision: int = Field(default=3, description="Numeric precision for preprocessing")
    svg_preprocessing_multipass: bool = Field(default=False, description="Enable multiple preprocessing passes")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def validate_settings() -> bool:
    """Validate that all required settings are properly configured."""
    settings = get_settings()
    
    # Check Google Drive credentials file exists
    if not os.path.exists(settings.google_drive_credentials_path):
        print(f"Warning: Google Drive credentials file not found: {settings.google_drive_credentials_path}")
        return False
    
    # Check temp directory exists and is writable
    if not os.path.exists(settings.temp_dir):
        try:
            os.makedirs(settings.temp_dir, exist_ok=True)
        except Exception as e:
            print(f"Error: Cannot create temp directory {settings.temp_dir}: {e}")
            return False
    
    return True


if __name__ == "__main__":
    # Test configuration loading
    settings = get_settings()
    print("Current configuration:")
    print(f"  Environment: {settings.environment}")
    print(f"  API Key: {settings.api_key[:10]}..." if len(settings.api_key) > 10 else f"  API Key: {settings.api_key}")
    print(f"  Google Drive Credentials: {settings.google_drive_credentials_path}")
    print(f"  Host: {settings.host}:{settings.port}")
    print(f"  Max SVG Size: {settings.max_svg_file_size / 1_000_000:.1f}MB")
    
    # Validate settings
    if validate_settings():
        print("✅ Configuration validation passed")
    else:
        print("❌ Configuration validation failed")