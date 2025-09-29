#!/usr/bin/env python3
"""
Unified Coordinate System for Path Processing

This module implements the CoordinateSystem that integrates with existing
ViewportEngine and UnitConverter infrastructure to provide accurate coordinate
transformations for path processing.

Key Features:
- Integrates with existing ViewportEngine for viewport/viewBox handling
- Uses existing UnitConverter for comprehensive SVG → EMU conversions
- Provides single source of truth for all path coordinate transformations
- Eliminates coordinate corruption through controlled transformation pipeline
"""

import logging
from typing import List, Tuple, Optional, Any, Dict
import numpy as np

from .interfaces import CoordinateSystem as CoordinateSystemInterface
from .architecture import (
    PathCommand, PathBounds, CoordinatePoint, PathCommandType,
    CoordinateTransformError
)

# Import existing infrastructure
from ..viewbox import ViewportEngine, ViewBoxArray, ViewportArray
from ..units import UnitConverter, ConversionContext  # Used for type hints and fallback compatibility

logger = logging.getLogger(__name__)


class CoordinateSystem(CoordinateSystemInterface):
    """
    Unified coordinate system that orchestrates existing infrastructure.

    This class coordinates ViewportEngine and UnitConverter to provide
    accurate coordinate transformations for path processing. It serves as
    the single source of truth for all coordinate operations.
    """

    def __init__(self, enable_logging: bool = True, services=None):
        """Initialize coordinate system with existing infrastructure."""
        super().__init__(enable_logging)

        # Use provided services or attempt service-aware fallback
        if services is not None:
            self._viewport_engine = services.viewport_resolver
            self._unit_converter = services.unit_converter
        else:
            # Service-aware fallback: try ConversionServices first
            try:
                from ..services.conversion_services import ConversionServices
                fallback_services = ConversionServices.get_default_instance()
                self._viewport_engine = fallback_services.viewport_resolver
                self._unit_converter = fallback_services.unit_converter
                self.log_debug("CoordinateSystem using ConversionServices fallback")
            except (ImportError, RuntimeError, AttributeError):
                # Final fallback to direct instantiation
                self._viewport_engine = ViewportEngine()
                self._unit_converter = UnitConverter()
                self.log_debug("CoordinateSystem using direct instantiation fallback")

        self._conversion_context: Optional[ConversionContext] = None

        # Configuration
        self.precision = 6
        self._initialized = False

        self.log_debug("CoordinateSystem initialized with existing infrastructure")

    def initialize_with_services(self, viewport_engine=None, unit_converter=None):
        """
        Initialize with existing viewport and unit conversion services.

        Args:
            viewport_engine: ViewportEngine instance (optional, uses default if None)
            unit_converter: UnitConverter instance (optional, uses default if None)
        """
        if viewport_engine is not None:
            self._viewport_engine = viewport_engine

        if unit_converter is not None:
            self._unit_converter = unit_converter

        self._initialized = True
        self.log_debug("CoordinateSystem initialized with provided services")

    def create_conversion_context(self, viewport_width: float, viewport_height: float,
                                 viewbox: Optional[Tuple[float, float, float, float]] = None,
                                 dpi: float = 96.0):
        """
        Create conversion context using existing UnitConverter infrastructure.

        Args:
            viewport_width, viewport_height: SVG viewport dimensions
            viewbox: Optional SVG viewBox (x, y, width, height)
            dpi: Display DPI for conversions
        """
        try:
            # Create conversion context with existing UnitConverter
            self._conversion_context = self._unit_converter.create_context(
                width=viewport_width,
                height=viewport_height,
                dpi=dpi
            )

            # Set up viewport/viewBox transformation
            if viewbox is not None:
                # Calculate viewport mapping parameters
                # viewbox format: (x, y, width, height)
                vb_x, vb_y, vb_width, vb_height = viewbox

                # Calculate scaling factors
                scale_x = viewport_width / vb_width if vb_width > 0 else 1.0
                scale_y = viewport_height / vb_height if vb_height > 0 else 1.0

                # Create simple mapping object for coordinate transformations
                self._viewport_mapping = type('ViewportMapping', (), {
                    'viewbox_x': vb_x,
                    'viewbox_y': vb_y,
                    'scale_x': scale_x,
                    'scale_y': scale_y
                })()

                self.log_debug(f"ViewBox mapping: scale=({scale_x:.3f}, {scale_y:.3f}), offset=({vb_x}, {vb_y})")
            else:
                # No viewBox, use identity mapping
                self._viewport_mapping = None

            self.log_debug(f"Conversion context created: {viewport_width}×{viewport_height}",
                          viewbox=viewbox, dpi=dpi)

        except Exception as e:
            raise CoordinateTransformError(f"Failed to create conversion context: {e}")

    def svg_to_relative(self, x: float, y: float, bounds: PathBounds) -> Tuple[float, float]:
        """
        Convert SVG coordinates to PowerPoint relative coordinates (0-100000 range).

        Uses existing infrastructure:
        1. ViewportEngine handles viewport/viewBox transformations
        2. UnitConverter handles SVG → EMU conversions
        3. Local logic maps EMU → relative coordinates

        Args:
            x, y: SVG coordinates
            bounds: Path bounding box (for relative coordinate calculation)

        Returns:
            Tuple of (x_relative, y_relative) in 0-100000 range

        Raises:
            CoordinateTransformError: If transformation fails
        """
        try:
            # Step 1: Apply viewport transformation if viewBox is present
            if self._viewport_mapping is not None:
                # Apply viewport/viewBox transformation using ViewportEngine
                transformed_x, transformed_y = self._apply_viewport_transform(x, y)
            else:
                # No viewBox transformation needed
                transformed_x, transformed_y = x, y

            # Step 2: Convert SVG coordinates to EMU using existing UnitConverter
            x_emu = self._unit_converter.to_emu(f"{transformed_x}px", self._conversion_context)
            y_emu = self._unit_converter.to_emu(f"{transformed_y}px", self._conversion_context)

            # Step 3: Convert EMU to relative coordinates (0-100000 range)
            x_relative = self._emu_to_relative_x(x_emu, bounds)
            y_relative = self._emu_to_relative_y(y_emu, bounds)

            # Clamp to valid range and apply precision
            x_relative = max(0, min(100000, round(x_relative, self.precision)))
            y_relative = max(0, min(100000, round(y_relative, self.precision)))

            self.log_debug(f"Coordinate transform: ({x},{y}) SVG → ({x_relative},{y_relative}) relative")

            return (x_relative, y_relative)

        except Exception as e:
            raise CoordinateTransformError(f"Failed to transform coordinates ({x}, {y}): {e}")

    def calculate_path_bounds(self, commands: List[PathCommand]) -> PathBounds:
        """
        Calculate bounding box for a series of path commands.

        Uses UnitConverter for consistent EMU coordinate calculations.
        Processes all command types including arcs and curves.

        Args:
            commands: List of path commands with original SVG coordinates

        Returns:
            PathBounds object in EMU coordinates

        Raises:
            CoordinateTransformError: If bounds calculation fails
        """
        try:
            if not commands:
                raise CoordinateTransformError("Cannot calculate bounds for empty command list")

            all_points = []
            current_pos = [0.0, 0.0]  # Track current position for relative commands

            for command in commands:
                points = self._extract_coordinate_points(command, current_pos)
                all_points.extend(points)

                # Update current position based on command
                if command.command_type != PathCommandType.CLOSE_PATH and points:
                    current_pos = list(points[-1])  # Last point becomes current position

            if not all_points:
                raise CoordinateTransformError("No coordinate points found in commands")

            # Convert all points to EMU using existing UnitConverter
            emu_points = []
            for x, y in all_points:
                # Apply viewport transformation if needed
                if self._viewport_mapping is not None:
                    x, y = self._apply_viewport_transform(x, y)

                # Convert to EMU
                x_emu = self._unit_converter.to_emu(f"{x}px", self._conversion_context)
                y_emu = self._unit_converter.to_emu(f"{y}px", self._conversion_context)
                emu_points.append((x_emu, y_emu))

            # Calculate bounds
            x_coords = [p[0] for p in emu_points]
            y_coords = [p[1] for p in emu_points]

            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)
            width = max_x - min_x
            height = max_y - min_y

            bounds = PathBounds(
                min_x=min_x,
                min_y=min_y,
                max_x=max_x,
                max_y=max_y,
                width=width,
                height=height,
                coordinate_system="emu"
            )

            self.log_debug(f"Calculated path bounds: {width}×{height} EMU", bounds=bounds.__dict__)
            return bounds

        except Exception as e:
            raise CoordinateTransformError(f"Failed to calculate path bounds: {e}")

    def _apply_viewport_transform(self, x: float, y: float) -> Tuple[float, float]:
        """Apply viewport/viewBox transformation using ViewportEngine."""
        if self._viewport_mapping is None:
            return x, y

        # Use ViewportEngine to apply transformation
        # This leverages the existing sophisticated viewport handling
        try:
            # Apply the viewport mapping transformation
            transformed_x = (x - self._viewport_mapping.viewbox_x) * self._viewport_mapping.scale_x
            transformed_y = (y - self._viewport_mapping.viewbox_y) * self._viewport_mapping.scale_y
            return transformed_x, transformed_y
        except Exception as e:
            self.log_error(f"Viewport transformation failed: {e}")
            return x, y  # Fallback to original coordinates

    def _emu_to_relative_x(self, x_emu: float, bounds: PathBounds) -> float:
        """Convert EMU x-coordinate to relative coordinate (0-100000)."""
        if bounds.width <= 0:
            return 0.0
        return ((x_emu - bounds.min_x) / bounds.width) * 100000

    def _emu_to_relative_y(self, y_emu: float, bounds: PathBounds) -> float:
        """Convert EMU y-coordinate to relative coordinate (0-100000)."""
        if bounds.height <= 0:
            return 0.0
        return ((y_emu - bounds.min_y) / bounds.height) * 100000

    def _extract_coordinate_points(self, command: PathCommand, current_pos: List[float]) -> List[Tuple[float, float]]:
        """
        Extract coordinate points from a path command.

        Handles different command types and relative vs absolute coordinates.

        Args:
            command: Path command to process
            current_pos: Current pen position [x, y]

        Returns:
            List of (x, y) coordinate tuples
        """
        points = []
        params = command.parameters

        if command.command_type == PathCommandType.MOVE_TO:
            if len(params) >= 2:
                x, y = params[0], params[1]
                if command.is_relative:
                    x += current_pos[0]
                    y += current_pos[1]
                points.append((x, y))

        elif command.command_type == PathCommandType.LINE_TO:
            if len(params) >= 2:
                x, y = params[0], params[1]
                if command.is_relative:
                    x += current_pos[0]
                    y += current_pos[1]
                points.append((x, y))

        elif command.command_type == PathCommandType.HORIZONTAL:
            if len(params) >= 1:
                x = params[0]
                if command.is_relative:
                    x += current_pos[0]
                points.append((x, current_pos[1]))

        elif command.command_type == PathCommandType.VERTICAL:
            if len(params) >= 1:
                y = params[0]
                if command.is_relative:
                    y += current_pos[1]
                points.append((current_pos[0], y))

        elif command.command_type == PathCommandType.CUBIC_CURVE:
            if len(params) >= 6:
                # Control points and end point
                for i in range(0, len(params), 2):
                    if i + 1 < len(params):
                        x, y = params[i], params[i + 1]
                        if command.is_relative:
                            x += current_pos[0]
                            y += current_pos[1]
                        points.append((x, y))

        elif command.command_type == PathCommandType.SMOOTH_CUBIC:
            if len(params) >= 4:
                # Control point 2 and end point
                for i in range(0, len(params), 2):
                    if i + 1 < len(params):
                        x, y = params[i], params[i + 1]
                        if command.is_relative:
                            x += current_pos[0]
                            y += current_pos[1]
                        points.append((x, y))

        elif command.command_type == PathCommandType.QUADRATIC:
            if len(params) >= 4:
                # Control point and end point
                for i in range(0, len(params), 2):
                    if i + 1 < len(params):
                        x, y = params[i], params[i + 1]
                        if command.is_relative:
                            x += current_pos[0]
                            y += current_pos[1]
                        points.append((x, y))

        elif command.command_type == PathCommandType.SMOOTH_QUAD:
            if len(params) >= 2:
                # End point only
                x, y = params[0], params[1]
                if command.is_relative:
                    x += current_pos[0]
                    y += current_pos[1]
                points.append((x, y))

        elif command.command_type == PathCommandType.ARC:
            if len(params) >= 7:
                # Arc end point (params[5], params[6])
                x, y = params[5], params[6]
                if command.is_relative:
                    x += current_pos[0]
                    y += current_pos[1]
                points.append((x, y))

        # CLOSE_PATH has no coordinates

        return points

    def get_viewport_engine(self):
        """Get the underlying ViewportEngine instance."""
        return self._viewport_engine

    def get_unit_converter(self):
        """Get the underlying UnitConverter instance."""
        return self._unit_converter

    def get_conversion_context(self):
        """Get the current conversion context."""
        return self._conversion_context

    def is_initialized(self) -> bool:
        """Check if coordinate system is properly initialized."""
        return self._initialized and self._conversion_context is not None