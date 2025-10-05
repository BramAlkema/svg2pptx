"""
Services Module

Core services for SVG2PPTX conversion system including secure file operations,
conversion services, and utility services.
"""

from .conversion_services import ConversionServices
from .secure_file_service import (
    PathTraversalError,
    SecureFileOperationError,
    SecureFileService,
    SecureTempDir,
    SecureTempFile,
    default_secure_file_service,
)

__all__ = [
    'ConversionServices',
    'SecureFileService',
    'SecureTempFile',
    'SecureTempDir',
    'SecureFileOperationError',
    'PathTraversalError',
    'default_secure_file_service',
]