#!/usr/bin/env python3
"""
Authentication utilities for SVG to Google Drive API.
"""

from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import get_settings


def extract_bearer_token(authorization_header: str) -> Optional[str]:
    """
    Extract bearer token from Authorization header.
    
    Args:
        authorization_header: The full Authorization header value
        
    Returns:
        The extracted token or None if invalid format
    """
    if not authorization_header:
        return None
    
    parts = authorization_header.split(" ")
    if len(parts) != 2:
        return None
    
    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    
    return token if token else None


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key against configured key.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not api_key:
        return False
    
    settings = get_settings()
    return api_key == settings.api_key


def get_api_key_from_header(authorization_header: Optional[str]) -> Optional[str]:
    """
    Extract and validate API key from Authorization header.
    
    Args:
        authorization_header: The Authorization header value
        
    Returns:
        The API key if valid, None otherwise
    """
    if not authorization_header:
        return None
    
    token = extract_bearer_token(authorization_header)
    if not token:
        return None
    
    if not validate_api_key(token):
        return None
    
    return token


class AuthError(Exception):
    """Custom exception for authentication errors."""
    
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# Security scheme
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Validate API key from Authorization header."""
    token = credentials.credentials
    if not validate_api_key(token):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"api_key": token}


if __name__ == "__main__":
    # Test authentication functions
    print("Testing authentication functions...")
    
    # Test token extraction
    valid_header = "Bearer test-api-key"
    token = extract_bearer_token(valid_header)
    print(f"Extracted token: {token}")
    
    # Test invalid headers
    invalid_headers = [
        "Basic test-api-key",
        "Bearer",
        "test-api-key",
        "",
        None
    ]
    
    for header in invalid_headers:
        token = extract_bearer_token(header)
        print(f"Header '{header}' -> Token: {token}")
    
    # Test validation
    from .config import get_settings
    settings = get_settings()
    print(f"Configured API key: {settings.api_key}")
    print(f"Validation test: {validate_api_key(settings.api_key)}")
    print(f"Invalid key test: {validate_api_key('invalid-key')}")