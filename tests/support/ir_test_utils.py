#!/usr/bin/env python3
"""
IR Test Utilities

Utilities for testing Intermediate Representation components.
"""

import json
import time
import random
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import Mock

try:
    from core.ir import Scene, Path, TextFrame, Group, Image
    CORE_IR_AVAILABLE = True
except ImportError:
    CORE_IR_AVAILABLE = False


class IRTestUtils:
    """Utility class for IR testing"""

    @staticmethod
    def create_test_path_data(complexity: str = "simple") -> str:
        """Generate test path data of varying complexity"""
        if complexity == "simple":
            return "M 0 0 L 10 10 L 20 0 Z"
        elif complexity == "moderate":
            return "M 10 10 C 20 20, 40 20, 50 10 S 80 0, 90 10 Q 100 20, 110 10 T 130 10 L 140 0 Z"
        elif complexity == "complex":
            return ("M 50 50 "
                    "C 50 22.385763, 27.614237 0, 0 0 "
                    "S -50 22.385763, -50 50 "
                    "C -50 77.614237, -27.614237 100, 0 100 "
                    "S 50 77.614237, 50 50 "
                    "M 25 25 "
                    "A 25 25 0 0 1 75 25 "
                    "A 25 25 0 0 1 75 75 "
                    "A 25 25 0 0 1 25 75 "
                    "A 25 25 0 0 1 25 25 Z")
        else:
            return "M 0 0"

    @staticmethod
    def measure_ir_operation(operation_func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure execution time of IR operation"""
        start_time = time.perf_counter()
        result = operation_func(*args, **kwargs)
        end_time = time.perf_counter()

        execution_time_ms = (end_time - start_time) * 1000
        return result, execution_time_ms


class MockIRFactory:
    """Factory for creating mock IR components for testing"""

    @staticmethod
    def create_mock_scene() -> Mock:
        """Create mock Scene"""
        scene = Mock()
        scene.elements = []
        scene.viewbox = (0, 0, 100, 100)
        scene.width = 100
        scene.height = 100
        return scene

    @staticmethod
    def create_mock_path() -> Mock:
        """Create mock Path"""
        path = Mock()
        path.segments = []
        path.fill = None
        path.stroke = None
        path.is_closed = False
        path.data = "M 0 0"
        return path


# Export main utilities
__all__ = [
    'IRTestUtils',
    'MockIRFactory',
    'CORE_IR_AVAILABLE'
]