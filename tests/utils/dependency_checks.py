#!/usr/bin/env python3
"""
Dependency availability checks for SVG2PPTX test suite.

Provides centralized functions for checking availability of optional dependencies
and external services, with consistent skip decorators and graceful fallbacks.
"""

import importlib
import pytest
from typing import Optional, Callable, Any
from functools import wraps


def check_module_available(module_name: str) -> bool:
    """
    Check if a Python module is available for import.

    Args:
        module_name: Full module name (e.g., 'src.svg2pptx_json_v2')

    Returns:
        True if module can be imported, False otherwise
    """
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def check_huey_available() -> bool:
    """Check if Huey task queue is available."""
    try:
        import huey
        return True
    except ImportError:
        return False


def check_redis_available() -> bool:
    """Check if Redis is available."""
    try:
        import redis
        return True
    except ImportError:
        return False


def check_numpy_available() -> bool:
    """Check if NumPy is available."""
    try:
        import numpy
        return True
    except ImportError:
        return False


def check_fastapi_available() -> bool:
    """Check if FastAPI is available."""
    try:
        import fastapi
        return True
    except ImportError:
        return False


def check_google_drive_available() -> bool:
    """Check if Google Drive dependencies are available."""
    try:
        import google.auth
        import googleapiclient.discovery
        return True
    except ImportError:
        return False


def check_tools_testing_available() -> bool:
    """Check if tools.testing module is available."""
    return check_module_available('tools.testing')


def check_svg2pptx_json_v2_available() -> bool:
    """Check if svg2pptx_json_v2 module is available."""
    return check_module_available('src.svg2pptx_json_v2')


def check_enhanced_converter_available() -> bool:
    """Check if enhanced_converter module is available."""
    return check_module_available('src.converters.shapes.enhanced_converter')


# Skip decorators for common dependencies
skip_if_no_huey = pytest.mark.skipif(
    not check_huey_available(),
    reason="Huey not available - install with: pip install huey"
)

skip_if_no_redis = pytest.mark.skipif(
    not check_redis_available(),
    reason="Redis not available - install with: pip install redis"
)

skip_if_no_numpy = pytest.mark.skipif(
    not check_numpy_available(),
    reason="NumPy not available - install with: pip install numpy"
)

skip_if_no_fastapi = pytest.mark.skipif(
    not check_fastapi_available(),
    reason="FastAPI not available - install with: pip install fastapi"
)

skip_if_no_google_drive = pytest.mark.skipif(
    not check_google_drive_available(),
    reason="Google Drive dependencies not available - install with: pip install google-auth google-api-python-client"
)

skip_if_no_tools_testing = pytest.mark.skipif(
    not check_tools_testing_available(),
    reason="tools.testing module not available - optional testing dependency"
)

skip_if_no_svg2pptx_json_v2 = pytest.mark.skipif(
    not check_svg2pptx_json_v2_available(),
    reason="svg2pptx_json_v2 module not available - optional module"
)

skip_if_no_enhanced_converter = pytest.mark.skipif(
    not check_enhanced_converter_available(),
    reason="enhanced_converter module not available - modern converter module"
)


def require_dependency(dependency_check: Callable[[], bool], reason: str):
    """
    Decorator factory for custom dependency requirements.

    Args:
        dependency_check: Function that returns True if dependency is available
        reason: Reason to show when skipping test

    Returns:
        Decorator that skips test if dependency is not available
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not dependency_check():
                pytest.skip(reason)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def conditional_import(module_name: str, skip_reason: Optional[str] = None):
    """
    Context manager for conditional imports with automatic pytest.skip.

    Args:
        module_name: Module to import
        skip_reason: Custom skip reason (optional)

    Usage:
        with conditional_import('src.svg2pptx_json_v2') as module:
            result = module.convert_svg_to_pptx_json(svg_content)
    """
    class ConditionalImportContext:
        def __init__(self, module_name: str, skip_reason: Optional[str] = None):
            self.module_name = module_name
            self.skip_reason = skip_reason or f"{module_name} not available"
            self.module = None

        def __enter__(self):
            try:
                self.module = importlib.import_module(self.module_name)
                return self.module
            except ImportError:
                pytest.skip(self.skip_reason)

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    return ConditionalImportContext(module_name, skip_reason)


# Environment detection
def is_ci_environment() -> bool:
    """Check if running in CI environment."""
    import os
    return any(key in os.environ for key in ['CI', 'GITHUB_ACTIONS', 'TRAVIS', 'JENKINS'])


def is_local_development() -> bool:
    """Check if running in local development environment."""
    return not is_ci_environment()


# Service availability checks
DEPENDENCY_STATUS = {
    'huey': check_huey_available(),
    'numpy': check_numpy_available(),
    'fastapi': check_fastapi_available(),
    'google_drive': check_google_drive_available(),
    'enhanced_converter': check_enhanced_converter_available(),
}


def get_dependency_status() -> dict:
    """Get current status of all dependencies."""
    return DEPENDENCY_STATUS.copy()


def print_dependency_report():
    """Print a report of available dependencies."""
    print("\nDependency Availability Report:")
    print("=" * 40)
    for dep_name, available in DEPENDENCY_STATUS.items():
        status = "✓ Available" if available else "✗ Missing"
        print(f"{dep_name:20} {status}")
    print("=" * 40)

    missing_count = sum(1 for available in DEPENDENCY_STATUS.values() if not available)
    total_count = len(DEPENDENCY_STATUS)
    print(f"Available: {total_count - missing_count}/{total_count}")