#!/usr/bin/env python3
"""
Fractional EMU Error Classes

Custom exceptions for fractional EMU system.
"""


class CoordinateValidationError(ValueError):
    """Exception raised when coordinate validation fails."""
    pass


class PrecisionOverflowError(ValueError):
    """Exception raised when precision calculations cause overflow."""
    pass


class EMUBoundaryError(ValueError):
    """Exception raised when EMU values exceed PowerPoint boundaries."""
    pass
