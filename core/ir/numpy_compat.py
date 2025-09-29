#!/usr/bin/env python3
"""
NumPy Compatibility Module

Provides optional numpy import for IR modules.
Falls back to basic types when numpy is not available.
"""

# Optional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    # Create dummy numpy module for type hints
    class DummyNumpy:
        ndarray = object

        @staticmethod
        def array(data, dtype=None):
            """Fallback array creation"""
            return list(data)

        @staticmethod
        def identity(n):
            """Fallback identity matrix"""
            return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

        @staticmethod
        def dot(a, b):
            """Fallback matrix multiplication"""
            return a  # Simplified fallback

    np = DummyNumpy()