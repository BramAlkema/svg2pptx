#!/usr/bin/env python3
"""
Integrated Path Processing System

This module provides the PathSystem class that integrates all path processing
components into a unified, easy-to-use interface. It orchestrates the parser,
coordinate system, arc converter, and XML generator to provide end-to-end
SVG path to PowerPoint DrawingML conversion.

Key Features:
- Single interface for complete path processing
- Automatic component coordination and data flow
- Comprehensive error handling and validation
- Optimal performance through component reuse
- Clean separation of concerns
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .parser import PathParser
from .coordinate_system import CoordinateSystem
from .arc_converter import ArcConverter
from .drawingml_generator import DrawingMLGenerator
from .architecture import (
    PathCommand, PathBounds, PathSystemError, PathSystemContext,
    PathParseError, CoordinateTransformError, ArcConversionError, XMLGenerationError
)

logger = logging.getLogger(__name__)


@dataclass
class PathProcessingResult:
    """Result of complete path processing operation."""
    path_xml: str
    shape_xml: str
    bounds: PathBounds
    commands: List[PathCommand]
    processing_stats: Dict[str, Any]


class PathSystem:
    """
    Integrated path processing system for SVG to PowerPoint conversion.

    This system orchestrates all path processing components to provide
    a unified interface for converting SVG path data to PowerPoint DrawingML.
    It handles the complete pipeline from SVG path parsing through coordinate
    transformation to XML generation.

    Example Usage:
        ```python
        # Create system with default components
        system = PathSystem()

        # Configure for a specific viewport
        system.configure_viewport(800, 600, viewbox=(0, 0, 400, 300))

        # Process an SVG path
        result = system.process_path(
            "M 100 200 C 100 100 400 100 400 200 Z",
            style_attributes={'fill': '#FF0000', 'stroke': '#000000'}
        )

        # Use the generated XML
        print(result.path_xml)
        print(result.shape_xml)
        ```
    """

    def __init__(self, enable_logging: bool = True):
        """
        Initialize the integrated path system.

        Args:
            enable_logging: Whether to enable debug logging
        """
        self.enable_logging = enable_logging
        self.logger = logging.getLogger(__name__) if enable_logging else None

        # Initialize all components
        self._parser = PathParser(enable_logging)
        self._coordinate_system = CoordinateSystem(enable_logging)
        self._arc_converter = ArcConverter(enable_logging)
        self._xml_generator = DrawingMLGenerator(enable_logging)

        # System state
        self._viewport_configured = False
        self._processing_stats = {
            'paths_processed': 0,
            'commands_processed': 0,
            'arcs_converted': 0,
            'errors_encountered': 0
        }

        self.log_debug("PathSystem initialized with all components")

    def configure_viewport(self, viewport_width: float, viewport_height: float,
                          viewbox: Optional[Tuple[float, float, float, float]] = None,
                          dpi: float = 96.0):
        """
        Configure the viewport and coordinate system for path processing.

        Args:
            viewport_width, viewport_height: SVG viewport dimensions
            viewbox: Optional SVG viewBox (x, y, width, height)
            dpi: Display DPI for conversions (default: 96.0)

        Raises:
            CoordinateTransformError: If viewport configuration fails
        """
        try:
            self._coordinate_system.create_conversion_context(
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                viewbox=viewbox,
                dpi=dpi
            )
            self._viewport_configured = True

            self.log_debug(f"Viewport configured: {viewport_width}×{viewport_height}")
            if viewbox:
                self.log_debug(f"ViewBox: {viewbox}")

        except Exception as e:
            raise CoordinateTransformError(f"Failed to configure viewport: {e}")

    def process_path(self, path_data: str, style_attributes: Optional[Dict[str, Any]] = None) -> PathProcessingResult:
        """
        Process a complete SVG path from string to PowerPoint XML.

        This is the main entry point for path processing. It coordinates all
        components to transform SVG path data into PowerPoint-compatible XML.

        Args:
            path_data: SVG path 'd' attribute string
            style_attributes: Optional SVG style attributes for shape styling

        Returns:
            PathProcessingResult with generated XML and processing information

        Raises:
            PathSystemError: If any step of the processing fails
        """
        if not self._viewport_configured:
            raise PathSystemError("Viewport must be configured before processing paths")

        if style_attributes is None:
            style_attributes = {}

        processing_start_time = self._get_current_time()

        try:
            # Step 1: Parse SVG path data
            self.log_debug(f"Parsing path data: {path_data[:50]}...")
            commands = self._parser.parse_path_data(path_data)

            if not commands:
                raise PathSystemError("No path commands found in path data")

            self.log_debug(f"Parsed {len(commands)} path commands")

            # Step 2: Calculate path bounds
            self.log_debug("Calculating path bounds...")
            bounds = self._coordinate_system.calculate_path_bounds(commands)
            self.log_debug(f"Path bounds: {bounds.width}×{bounds.height} {bounds.coordinate_system}")

            # Step 3: Generate path XML
            self.log_debug("Generating DrawingML path XML...")
            path_xml = self._xml_generator.generate_path_xml(
                commands=commands,
                bounds=bounds,
                coordinate_system=self._coordinate_system,
                arc_converter=self._arc_converter
            )

            # Step 4: Generate complete shape XML
            self.log_debug("Generating complete shape XML...")
            shape_xml = self._xml_generator.generate_shape_xml(
                path_xml=path_xml,
                bounds=bounds,
                style_attributes=style_attributes
            )

            # Step 5: Create processing result
            processing_time = self._get_current_time() - processing_start_time

            # Count arcs for statistics
            arc_count = sum(1 for cmd in commands if cmd.command_type.value == 8)  # ARC = 8

            # Update statistics
            self._processing_stats['paths_processed'] += 1
            self._processing_stats['commands_processed'] += len(commands)
            self._processing_stats['arcs_converted'] += arc_count

            processing_stats = {
                'processing_time_ms': processing_time * 1000,
                'command_count': len(commands),
                'arc_count': arc_count,
                'bounds_emu': {
                    'width': bounds.width,
                    'height': bounds.height,
                    'min_x': bounds.min_x,
                    'min_y': bounds.min_y
                }
            }

            result = PathProcessingResult(
                path_xml=path_xml,
                shape_xml=shape_xml,
                bounds=bounds,
                commands=commands,
                processing_stats=processing_stats
            )

            self.log_debug(f"Path processing completed in {processing_time*1000:.2f}ms")
            return result

        except (PathParseError, CoordinateTransformError, ArcConversionError, XMLGenerationError) as e:
            self._processing_stats['errors_encountered'] += 1
            raise PathSystemError(f"Path processing failed: {e}")

        except Exception as e:
            self._processing_stats['errors_encountered'] += 1
            raise PathSystemError(f"Unexpected error during path processing: {e}")

    def process_multiple_paths(self, path_specs: List[Dict[str, Any]]) -> List[PathProcessingResult]:
        """
        Process multiple SVG paths in batch.

        Args:
            path_specs: List of dictionaries with 'path_data' and optional 'style_attributes'

        Returns:
            List of PathProcessingResult objects

        Raises:
            PathSystemError: If batch processing setup fails
        """
        if not self._viewport_configured:
            raise PathSystemError("Viewport must be configured before processing paths")

        results = []
        errors = []

        self.log_debug(f"Processing batch of {len(path_specs)} paths")

        for i, spec in enumerate(path_specs):
            try:
                if 'path_data' not in spec:
                    raise ValueError(f"Path spec {i} missing 'path_data' field")

                result = self.process_path(
                    path_data=spec['path_data'],
                    style_attributes=spec.get('style_attributes', {})
                )
                results.append(result)

            except Exception as e:
                error_info = {
                    'index': i,
                    'path_data': spec.get('path_data', ''),
                    'error': str(e)
                }
                errors.append(error_info)
                self.log_error(f"Failed to process path {i}: {e}")

        if errors:
            self.log_debug(f"Batch processing completed with {len(errors)} errors")

        return results

    def validate_path_data(self, path_data: str) -> bool:
        """
        Validate SVG path data without full processing.

        Args:
            path_data: SVG path 'd' attribute string

        Returns:
            True if path data is valid, False otherwise
        """
        try:
            return self._parser.validate_path_data(path_data)
        except Exception:
            return False

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics for performance monitoring."""
        return self._processing_stats.copy()

    def reset_statistics(self):
        """Reset processing statistics."""
        self._processing_stats = {
            'paths_processed': 0,
            'commands_processed': 0,
            'arcs_converted': 0,
            'errors_encountered': 0
        }
        self.log_debug("Processing statistics reset")

    def get_system_components(self) -> PathSystemContext:
        """
        Get access to individual system components.

        Returns:
            PathSystemContext with references to all components
        """
        return PathSystemContext(
            parser=self._parser,
            coordinate_system=self._coordinate_system,
            arc_converter=self._arc_converter,
            xml_generator=self._xml_generator
        )

    def configure_arc_quality(self, max_segment_angle: float = 90.0, error_tolerance: float = 0.01):
        """
        Configure arc conversion quality parameters.

        Args:
            max_segment_angle: Maximum angle per arc segment in degrees
            error_tolerance: Maximum acceptable error in coordinate units
        """
        self._arc_converter.set_quality_parameters(max_segment_angle, error_tolerance)
        self.log_debug(f"Arc quality configured: max_angle={max_segment_angle}°, tolerance={error_tolerance}")

    def is_configured(self) -> bool:
        """Check if the system is properly configured for processing."""
        return self._viewport_configured

    def get_supported_commands(self) -> List[str]:
        """Get list of supported SVG path commands."""
        return self._parser.get_supported_commands()

    def _get_current_time(self) -> float:
        """Get current time for performance measurement."""
        import time
        return time.perf_counter()

    def log_debug(self, message: str, **kwargs):
        """Log debug message if logging is enabled."""
        if self.logger:
            self.logger.debug(message, extra=kwargs)

    def log_error(self, message: str, **kwargs):
        """Log error message if logging is enabled."""
        if self.logger:
            self.logger.error(message, extra=kwargs)


# Factory function for easy system creation
def create_path_system(viewport_width: float = None, viewport_height: float = None,
                      viewbox: Optional[Tuple[float, float, float, float]] = None,
                      enable_logging: bool = True) -> PathSystem:
    """
    Factory function to create and optionally configure a PathSystem.

    Args:
        viewport_width, viewport_height: Optional viewport dimensions
        viewbox: Optional SVG viewBox
        enable_logging: Whether to enable debug logging

    Returns:
        Configured PathSystem instance
    """
    system = PathSystem(enable_logging=enable_logging)

    if viewport_width is not None and viewport_height is not None:
        system.configure_viewport(viewport_width, viewport_height, viewbox)

    return system