"""
Path System Adapters for Boolean Operations

This module provides adapter functions that connect the boolean engine backends
to the existing SVG2PPTX path processing infrastructure. It handles the integration
between generic path operations and specific path parsers/serializers.

Key Functions:
- create_backend_factory(): Creates appropriate backend with system integration
- get_available_backends(): Returns list of available backend types
- BooleanEngineFactory: Factory class for creating configured engines
"""

from __future__ import annotations
from typing import List, Optional, Type, Protocol, Callable, Any, Tuple
import logging

from .path_boolean_engine import PathBooleanEngine, PathSpec
from .backends import (
    PathOpsBackend, PyClipperBackend,
    PATHOPS_AVAILABLE, PYCLIPPER_AVAILABLE
)

logger = logging.getLogger(__name__)


class PathParser(Protocol):
    """Protocol for path parsing systems."""
    def parse_path_commands(self, d_string: str) -> List[Any]:
        """Parse SVG d-string into command list."""
        ...


class PathSerializer(Protocol):
    """Protocol for path serialization systems."""
    def serialize_path(self, path_data: Any) -> str:
        """Serialize path data back to SVG d-string."""
        ...


class CurveApproximator(Protocol):
    """Protocol for curve approximation systems."""
    def approximate_curves(self, commands: List[Any], tolerance: float = 1.0) -> List[Any]:
        """Approximate curved commands with linear segments."""
        ...


class BooleanEngineFactory:
    """Factory for creating boolean operation engines with proper adapters."""

    def __init__(self,
                 path_parser: PathParser,
                 path_serializer: PathSerializer,
                 curve_approximator: Optional[CurveApproximator] = None):
        """
        Initialize factory with path processing components.

        Args:
            path_parser: Parser for SVG d-strings
            path_serializer: Serializer for path data
            curve_approximator: Optional curve approximator for polygon backends
        """
        self.path_parser = path_parser
        self.path_serializer = path_serializer
        self.curve_approximator = curve_approximator

    def create_pathops_backend(self) -> Optional[PathOpsBackend]:
        """Create PathOps backend if available."""
        if not PATHOPS_AVAILABLE:
            logger.debug("Skia PathOps not available, skipping backend creation")
            return None

        try:
            from .backends.pathops_backend import create_pathops_backend_with_adapters
            return create_pathops_backend_with_adapters(
                self.path_parser,
                self.path_serializer
            )
        except Exception as e:
            logger.warning(f"Failed to create PathOps backend: {e}")
            return None

    def create_pyclipper_backend(self, scale_factor: float = 1000.0) -> Optional[PyClipperBackend]:
        """Create PyClipper backend if available."""
        if not PYCLIPPER_AVAILABLE:
            logger.debug("PyClipper not available, skipping backend creation")
            return None

        if not self.curve_approximator:
            logger.warning("PyClipper backend requires curve approximator")
            return None

        try:
            from .backends.pyclipper_backend import create_pyclipper_backend_with_adapters
            return create_pyclipper_backend_with_adapters(
                self.path_parser,
                self.path_serializer,
                self.curve_approximator,
                scale_factor
            )
        except Exception as e:
            logger.warning(f"Failed to create PyClipper backend: {e}")
            return None

    def create_best_available_backend(self) -> Optional[PathBooleanEngine]:
        """Create the highest fidelity available backend."""
        # Try PathOps first (curve-faithful)
        backend = self.create_pathops_backend()
        if backend:
            logger.debug("Using Skia PathOps backend for boolean operations")
            return backend

        # Fallback to PyClipper (polygon-based)
        backend = self.create_pyclipper_backend()
        if backend:
            logger.debug("Using PyClipper backend for boolean operations")
            return backend

        logger.warning("No boolean operation backends available")
        return None

    def get_backend_priority_order(self) -> List[str]:
        """Get backends in order of preference."""
        available = []
        if PATHOPS_AVAILABLE:
            available.append("pathops")
        if PYCLIPPER_AVAILABLE:
            available.append("pyclipper")
        return available


def get_available_backends() -> List[str]:
    """Get list of available backend names."""
    available = []
    if PATHOPS_AVAILABLE:
        available.append("pathops")
    if PYCLIPPER_AVAILABLE:
        available.append("pyclipper")
    return available


def create_backend_factory_from_services(services) -> BooleanEngineFactory:
    """
    Create BooleanEngineFactory from SVG2PPTX ConversionServices.

    This function integrates with the existing service dependency injection
    system to create properly configured boolean operation backends.

    Args:
        services: ConversionServices instance with path processing components

    Returns:
        Configured BooleanEngineFactory instance

    Example:
        >>> from src.services.conversion_services import ConversionServices
        >>> services = ConversionServices.create_default()
        >>> factory = create_backend_factory_from_services(services)
        >>> engine = factory.create_best_available_backend()
    """
    # Extract components from services
    # These would be the actual service interfaces once integrated
    path_parser = getattr(services, 'path_parser', None)
    path_serializer = getattr(services, 'path_serializer', None)
    curve_approximator = getattr(services, 'curve_approximator', None)

    # For now, we'll create minimal adapters
    # TODO: Replace with actual service integration in Task 5
    if not path_parser:
        path_parser = _create_minimal_path_parser()
    if not path_serializer:
        path_serializer = _create_minimal_path_serializer()
    if not curve_approximator:
        curve_approximator = _create_minimal_curve_approximator()

    return BooleanEngineFactory(
        path_parser=path_parser,
        path_serializer=path_serializer,
        curve_approximator=curve_approximator
    )


class _MinimalPathParser:
    """Minimal path parser implementation for testing."""

    def parse_path_commands(self, d_string: str) -> List[Any]:
        """Basic path command parsing."""
        # This is a simplified parser for proof-of-concept
        # Real implementation would integrate with existing path parsing
        commands = []
        if not d_string:
            return commands

        # Very basic parsing - just extract command letters and numbers
        import re
        pattern = r'([MmLlHhVvCcSsQqTtAaZz])\s*((?:[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?\s*,?\s*)*)'

        for match in re.finditer(pattern, d_string):
            cmd_letter = match.group(1)
            numbers_str = match.group(2)

            # Parse numbers
            numbers = []
            if numbers_str:
                number_pattern = r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?'
                numbers = [float(n) for n in re.findall(number_pattern, numbers_str)]

            commands.append([cmd_letter] + numbers)

        return commands


class _MinimalPathSerializer:
    """Minimal path serializer implementation."""

    def serialize_path(self, path_data: Any) -> str:
        """Basic path serialization."""
        if hasattr(path_data, 'asPath'):  # Skia path
            # For Skia paths, we'd use proper serialization
            # This is a placeholder
            return str(path_data)
        return str(path_data)


class _MinimalCurveApproximator:
    """Minimal curve approximator implementation."""

    def approximate_curves(self, commands: List[Any], tolerance: float = 1.0) -> List[Any]:
        """Basic curve approximation - converts curves to line segments."""
        linear_commands = []

        for cmd in commands:
            if not cmd:
                continue

            cmd_type = cmd[0].upper()

            if cmd_type in ('M', 'L', 'Z'):
                # Keep linear commands as-is
                linear_commands.append(cmd)
            elif cmd_type == 'C':
                # Convert cubic bezier to line segments
                # This is very simplified - real implementation would be more sophisticated
                if len(cmd) >= 7:
                    # Just add the endpoint as a line
                    linear_commands.append(['L', cmd[5], cmd[6]])
            elif cmd_type == 'Q':
                # Convert quadratic bezier to line
                if len(cmd) >= 5:
                    linear_commands.append(['L', cmd[3], cmd[4]])
            elif cmd_type == 'A':
                # Convert arc to line
                if len(cmd) >= 8:
                    linear_commands.append(['L', cmd[6], cmd[7]])

        return linear_commands


def _create_minimal_path_parser() -> PathParser:
    """Create minimal path parser for testing."""
    return _MinimalPathParser()


def _create_minimal_path_serializer() -> PathSerializer:
    """Create minimal path serializer for testing."""
    return _MinimalPathSerializer()


def _create_minimal_curve_approximator() -> CurveApproximator:
    """Create minimal curve approximator for testing."""
    return _MinimalCurveApproximator()


# Convenience function for direct usage
def create_boolean_engine(services=None, backend_preference: Optional[str] = None) -> Optional[PathBooleanEngine]:
    """
    Create a boolean operation engine with sensible defaults.

    Args:
        services: Optional ConversionServices instance
        backend_preference: Optional backend preference ("pathops" or "pyclipper")

    Returns:
        Boolean engine instance or None if none available
    """
    factory = create_backend_factory_from_services(services) if services else BooleanEngineFactory(
        _create_minimal_path_parser(),
        _create_minimal_path_serializer(),
        _create_minimal_curve_approximator()
    )

    if backend_preference == "pathops":
        return factory.create_pathops_backend()
    elif backend_preference == "pyclipper":
        return factory.create_pyclipper_backend()
    else:
        return factory.create_best_available_backend()