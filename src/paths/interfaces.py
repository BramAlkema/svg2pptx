#!/usr/bin/env python3
"""
Path System Interfaces

This module contains the concrete interface definitions and base classes
for the path processing system components.
"""

from typing import List, Dict, Any, Tuple, Optional, Union
from abc import ABC, abstractmethod
import logging

from .architecture import (
    PathCommand, CoordinatePoint, BezierSegment, PathBounds,
    PathCommandType, PathSystemError, PathParseError,
    CoordinateTransformError, ArcConversionError, XMLGenerationError
)

logger = logging.getLogger(__name__)


class BasePathComponent(ABC):
    """Base class for all path system components with common functionality."""

    def __init__(self, enable_logging: bool = True):
        """Initialize base component with logging support."""
        self.enable_logging = enable_logging
        self.logger = logger if enable_logging else None

    def log_debug(self, message: str, **kwargs):
        """Log debug message if logging is enabled."""
        if self.logger:
            self.logger.debug(message, extra=kwargs)

    def log_error(self, message: str, **kwargs):
        """Log error message if logging is enabled."""
        if self.logger:
            self.logger.error(message, extra=kwargs)


class PathParser(BasePathComponent):
    """
    Concrete path parser implementation interface.

    Defines the contract for parsing SVG path data into structured commands
    without performing any coordinate transformations.
    """

    @abstractmethod
    def parse_path_data(self, path_data: str) -> List[PathCommand]:
        """
        Parse SVG path data string into structured path commands.

        Implementation must:
        1. Tokenize the path data string
        2. Identify command types and parameters
        3. Handle relative vs absolute commands
        4. Validate parameter counts for each command type
        5. Create PathCommand objects with original coordinates
        6. NOT perform any coordinate transformations

        Args:
            path_data: SVG path 'd' attribute string (e.g., "M10,20 L30,40 Z")

        Returns:
            List of PathCommand objects with original SVG coordinates

        Raises:
            PathParseError: If path data is malformed or invalid
        """
        pass

    @abstractmethod
    def validate_path_data(self, path_data: str) -> bool:
        """
        Validate SVG path data syntax without full parsing.

        Args:
            path_data: SVG path 'd' attribute string

        Returns:
            True if path data has valid syntax, False otherwise
        """
        pass

    def _validate_command_parameters(self, command_type: PathCommandType, parameters: List[float]) -> bool:
        """
        Validate parameter count for a specific command type.

        Args:
            command_type: The path command type
            parameters: List of parameters for the command

        Returns:
            True if parameter count is valid, False otherwise
        """
        expected_counts = {
            PathCommandType.MOVE_TO: [2],  # x, y
            PathCommandType.LINE_TO: [2],  # x, y
            PathCommandType.HORIZONTAL: [1],  # x
            PathCommandType.VERTICAL: [1],  # y
            PathCommandType.CUBIC_CURVE: [6],  # x1, y1, x2, y2, x, y
            PathCommandType.SMOOTH_CUBIC: [4],  # x2, y2, x, y
            PathCommandType.QUADRATIC: [4],  # x1, y1, x, y
            PathCommandType.SMOOTH_QUAD: [2],  # x, y
            PathCommandType.ARC: [7],  # rx, ry, x-axis-rotation, large-arc-flag, sweep-flag, x, y
            PathCommandType.CLOSE_PATH: [0]  # no parameters
        }

        return len(parameters) in expected_counts.get(command_type, [])


class CoordinateSystem(BasePathComponent):
    """
    Concrete coordinate system implementation interface.

    Integrates with existing SVG2PPTX infrastructure:
    - ViewportEngine from src.viewbox for viewport/viewBox transformations
    - UnitConverter from src.units for SVG → EMU conversions

    This component coordinates the existing systems rather than reimplementing them.
    """

    def __init__(self, enable_logging: bool = True):
        """Initialize coordinate system with existing infrastructure."""
        super().__init__(enable_logging)
        self._viewport_engine = None  # Will be initialized with ViewportEngine
        self._unit_converter = None   # Will be initialized with UnitConverter
        self._conversion_context = None  # ConversionContext for current operation
        self.precision: int = 6

    @abstractmethod
    def initialize_with_services(self, viewport_engine, unit_converter):
        """
        Initialize with existing viewport and unit conversion services.

        Args:
            viewport_engine: ViewportEngine instance from src.viewbox
            unit_converter: UnitConverter instance from src.units
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    def get_viewport_engine(self):
        """Get the underlying ViewportEngine instance."""
        return self._viewport_engine

    def get_unit_converter(self):
        """Get the underlying UnitConverter instance."""
        return self._unit_converter

    def set_precision(self, precision: int):
        """Set coordinate precision for rounding operations."""
        self.precision = max(0, min(precision, 10))


class ArcConverter(BasePathComponent):
    """
    Concrete arc converter implementation interface.

    Implements the industry-standard a2c algorithm for converting SVG arcs
    to cubic bezier curve approximations.
    """

    @abstractmethod
    def arc_to_bezier_segments(self, start_x: float, start_y: float, rx: float, ry: float,
                              x_axis_rotation: float, large_arc_flag: int, sweep_flag: int,
                              end_x: float, end_y: float) -> List[BezierSegment]:
        """
        Convert SVG arc to cubic bezier segments using a2c algorithm.

        Implementation must:
        1. Use the proven a2c algorithm from fontello/svgpath
        2. Convert endpoint to center parameterization
        3. Split arcs >90° into multiple segments
        4. Generate accurate cubic bezier approximations
        5. Handle all SVG arc edge cases

        Args:
            start_x, start_y: Arc start point in SVG coordinates
            rx, ry: Arc radii
            x_axis_rotation: Rotation angle in degrees
            large_arc_flag: Large arc flag (0 or 1)
            sweep_flag: Sweep flag (0 or 1)
            end_x, end_y: Arc end point in SVG coordinates

        Returns:
            List of BezierSegment objects with SVG coordinates

        Raises:
            ArcConversionError: If arc parameters are invalid or conversion fails
        """
        pass

    @abstractmethod
    def validate_arc_parameters(self, rx: float, ry: float, start_x: float, start_y: float,
                               end_x: float, end_y: float) -> bool:
        """
        Validate arc parameters for mathematical correctness.

        Args:
            rx, ry: Arc radii (must be positive)
            start_x, start_y: Arc start point
            end_x, end_y: Arc end point

        Returns:
            True if parameters are valid, False otherwise
        """
        pass


class DrawingMLGenerator(BasePathComponent):
    """
    Concrete DrawingML generator implementation interface.

    Generates PowerPoint-compatible XML from processed path commands.
    This component must NOT perform any coordinate transformations.
    """

    @abstractmethod
    def generate_path_xml(self, commands: List[PathCommand], bounds: PathBounds,
                         coordinate_system: CoordinateSystem, arc_converter: ArcConverter) -> str:
        """
        Generate DrawingML path XML for a series of path commands.

        Implementation must:
        1. Use coordinate_system for ALL coordinate transformations
        2. Use arc_converter for arc processing
        3. Generate valid PowerPoint XML structure
        4. Handle all path command types
        5. NOT perform coordinate calculations directly

        Args:
            commands: List of path commands with SVG coordinates
            bounds: Path bounding box (for coordinate transformations)
            coordinate_system: Coordinate transformation system
            arc_converter: Arc to bezier converter

        Returns:
            DrawingML path XML string (e.g., "<a:path>...</a:path>")

        Raises:
            XMLGenerationError: If XML generation fails
        """
        pass

    @abstractmethod
    def generate_shape_xml(self, path_xml: str, bounds: PathBounds, style_attributes: Dict[str, Any]) -> str:
        """
        Generate complete PowerPoint shape XML with path and styling.

        Args:
            path_xml: Generated path XML from generate_path_xml()
            bounds: Shape bounds in EMU coordinates
            style_attributes: SVG style attributes (fill, stroke, etc.)

        Returns:
            Complete PowerPoint shape XML string

        Raises:
            XMLGenerationError: If XML generation fails
        """
        pass

    def _escape_xml_attribute(self, value: str) -> str:
        """Escape special characters in XML attribute values."""
        return (value
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))

    def _format_coordinate(self, value: float, precision: int = 0) -> str:
        """Format coordinate value for XML output."""
        if precision > 0:
            return f"{value:.{precision}f}"
        return str(int(round(value)))


# Type aliases for cleaner code
PathCommandList = List[PathCommand]
BezierSegmentList = List[BezierSegment]
StyleAttributes = Dict[str, Any]
CoordinatePair = Tuple[float, float]