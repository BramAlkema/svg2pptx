#!/usr/bin/env python3
"""
SVG Path Element Converter for SVG2PPTX (New Implementation)

This converter handles SVG <path> elements using the new modular PathSystem
architecture. It replaces the legacy PathConverter with a clean implementation
that leverages the industry-standard arc conversion and coordinate transformation.

Key Features:
- Uses the new PathSystem for complete path processing pipeline
- Industry-standard arc-to-bezier conversion (a2c algorithm)
- Proper coordinate transformation through CoordinateSystem
- Clean separation of concerns with modular architecture
- Comprehensive error handling and validation
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from lxml import etree as ET
import logging

from .base import BaseConverter, ConversionContext
from ..paths import PathSystem, PathProcessingResult, create_path_system

if TYPE_CHECKING:
    from ..services.conversion_services import ConversionServices

logger = logging.getLogger(__name__)


class PathConverter(BaseConverter):
    """
    Converts SVG <path> elements to PowerPoint DrawingML using the new PathSystem.

    This converter provides a clean interface between the SVG conversion pipeline
    and the new modular path processing system. It handles viewport configuration,
    coordinate transformation, and PowerPoint XML generation.
    """

    supported_elements = ['path']

    def __init__(self, services: 'ConversionServices'):
        """
        Initialize PathConverter with dependency injection.

        Args:
            services: ConversionServices container with dependencies
        """
        super().__init__(services)

        # Initialize the new path system (will be configured per conversion)
        self._path_system = None

        # Track conversion statistics
        self._paths_converted = 0
        self._total_commands = 0
        self._arc_conversions = 0
        self._processing_time_ms = 0.0

        logger.debug("PathConverter initialized with new PathSystem architecture")

    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the given element."""
        tag = self.get_element_tag(element)
        return tag == 'path' and element.get('d') is not None

    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Convert SVG path element to PowerPoint DrawingML.

        Args:
            element: SVG path element with 'd' attribute
            context: Conversion context with coordinate system and settings

        Returns:
            PowerPoint DrawingML XML string
        """
        try:
            # Extract path data
            path_data = element.get('d', '')
            if not path_data.strip():
                logger.warning("Empty path data encountered")
                return ""

            # Configure path system for this conversion context
            self._configure_path_system(context)

            # Extract style attributes
            style_attributes = self._extract_style_attributes(element)

            # Process path using the new system
            result = self._path_system.process_path(path_data, style_attributes)

            # Update statistics
            self._update_conversion_statistics(result)

            # Return the generated PowerPoint XML
            return result.shape_xml

        except Exception as e:
            logger.error(f"Failed to convert path element: {e}")
            return f"<!-- Error converting path: {e} -->"

    def _configure_path_system(self, context: ConversionContext):
        """
        Configure the path system based on the conversion context.

        Args:
            context: Conversion context with viewport and coordinate information
        """
        try:
            # Extract viewport information from context
            viewport_width = 800  # Default values
            viewport_height = 600
            viewbox = None

            if context.coordinate_system:
                # Get actual dimensions from coordinate system
                if hasattr(context.coordinate_system, 'slide_width'):
                    # Convert from EMU to pixels (approximate)
                    viewport_width = context.coordinate_system.slide_width / 12700
                    viewport_height = context.coordinate_system.slide_height / 12700

                if hasattr(context.coordinate_system, 'viewbox'):
                    viewbox = context.coordinate_system.viewbox

            # Create and configure path system
            self._path_system = create_path_system(
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                viewbox=viewbox,
                enable_logging=False  # Disable for performance
            )

            logger.debug(f"Path system configured: {viewport_width}×{viewport_height}, viewbox={viewbox}")

        except Exception as e:
            logger.warning(f"Failed to configure path system from context: {e}")
            # Fallback to default configuration
            self._path_system = create_path_system(800, 600, enable_logging=False)

    def _extract_style_attributes(self, element: ET.Element) -> Dict[str, Any]:
        """
        Extract style attributes from SVG element for PowerPoint styling.

        Args:
            element: SVG path element

        Returns:
            Dictionary of style attributes
        """
        style_attrs = {}

        # Extract common styling attributes
        style_attrs['fill'] = self.get_attribute_with_style(element, 'fill', 'black')
        style_attrs['stroke'] = self.get_attribute_with_style(element, 'stroke', 'none')
        style_attrs['stroke-width'] = self.get_attribute_with_style(element, 'stroke-width', '1')
        style_attrs['opacity'] = self.get_attribute_with_style(element, 'opacity', '1')

        # Additional attributes that might be useful
        stroke_dasharray = self.get_attribute_with_style(element, 'stroke-dasharray', 'none')
        if stroke_dasharray != 'none':
            style_attrs['stroke-dasharray'] = stroke_dasharray

        stroke_linecap = self.get_attribute_with_style(element, 'stroke-linecap', 'butt')
        if stroke_linecap != 'butt':
            style_attrs['stroke-linecap'] = stroke_linecap

        stroke_linejoin = self.get_attribute_with_style(element, 'stroke-linejoin', 'miter')
        if stroke_linejoin != 'miter':
            style_attrs['stroke-linejoin'] = stroke_linejoin

        return style_attrs

    def _update_conversion_statistics(self, result: PathProcessingResult):
        """
        Update conversion statistics based on processing result.

        Args:
            result: Path processing result from PathSystem
        """
        self._paths_converted += 1
        self._total_commands += result.processing_stats['command_count']
        self._arc_conversions += result.processing_stats['arc_count']
        self._processing_time_ms += result.processing_stats['processing_time_ms']

    def get_conversion_statistics(self) -> Dict[str, Any]:
        """
        Get conversion statistics for performance monitoring.

        Returns:
            Dictionary with conversion statistics
        """
        avg_processing_time = (
            self._processing_time_ms / self._paths_converted
            if self._paths_converted > 0 else 0.0
        )

        return {
            'paths_converted': self._paths_converted,
            'total_commands': self._total_commands,
            'arc_conversions': self._arc_conversions,
            'total_processing_time_ms': self._processing_time_ms,
            'average_processing_time_ms': avg_processing_time,
            'commands_per_path': (
                self._total_commands / self._paths_converted
                if self._paths_converted > 0 else 0.0
            )
        }

    def reset_statistics(self):
        """Reset conversion statistics."""
        self._paths_converted = 0
        self._total_commands = 0
        self._arc_conversions = 0
        self._processing_time_ms = 0.0

    def validate_path_before_conversion(self, path_data: str) -> bool:
        """
        Validate path data before attempting conversion.

        Args:
            path_data: SVG path 'd' attribute content

        Returns:
            True if path data is valid, False otherwise
        """
        try:
            # Use a temporary path system for validation
            if not self._path_system:
                temp_system = create_path_system(800, 600, enable_logging=False)
                return temp_system.validate_path_data(path_data)
            else:
                return self._path_system.validate_path_data(path_data)
        except Exception:
            return False

    def get_supported_path_commands(self) -> list:
        """
        Get list of supported SVG path commands.

        Returns:
            List of supported command letters
        """
        if not self._path_system:
            temp_system = create_path_system(800, 600, enable_logging=False)
            return temp_system.get_supported_commands()
        else:
            return self._path_system.get_supported_commands()

    def configure_arc_quality(self, max_segment_angle: float = 90.0, error_tolerance: float = 0.01):
        """
        Configure arc conversion quality parameters.

        Args:
            max_segment_angle: Maximum angle per arc segment in degrees
            error_tolerance: Maximum acceptable error in coordinate units
        """
        if self._path_system:
            self._path_system.configure_arc_quality(max_segment_angle, error_tolerance)
        else:
            logger.warning("Path system not configured yet - arc quality will be set on next conversion")

    def process_batch_paths(self, path_specs: list) -> list:
        """
        Process multiple paths in batch for efficiency.

        Args:
            path_specs: List of dictionaries with 'path_data' and optional 'style_attributes'

        Returns:
            List of PowerPoint XML strings
        """
        if not self._path_system:
            logger.error("Path system not configured - configure with conversion context first")
            return []

        try:
            results = self._path_system.process_multiple_paths(path_specs)

            # Update statistics for batch
            for result in results:
                self._update_conversion_statistics(result)

            # Extract shape XML from results
            return [result.shape_xml for result in results]

        except Exception as e:
            logger.error(f"Batch path processing failed: {e}")
            return []

    def get_path_system_info(self) -> Dict[str, Any]:
        """
        Get information about the configured path system.

        Returns:
            Dictionary with path system information
        """
        if not self._path_system:
            return {'configured': False}

        return {
            'configured': True,
            'is_ready': self._path_system.is_configured(),
            'supported_commands': len(self._path_system.get_supported_commands()),
            'system_stats': self._path_system.get_processing_statistics()
        }

    def cleanup(self):
        """Clean up resources when converter is no longer needed."""
        if self._path_system:
            # Reset system statistics to free memory
            self._path_system.reset_statistics()
            self._path_system = None

        logger.debug("PathConverter cleaned up")


# Compatibility alias for existing code
PathConverterNew = PathConverter