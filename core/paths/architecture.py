#!/usr/bin/env python3
"""
Path System Architecture Design

This module defines the architectural components and their relationships for the
SVG path processing system. The design follows separation of concerns principles
to eliminate coordinate transformation issues and create a maintainable system.

Architecture Overview:
    SVG Path Input → PathParser → CoordinateSystem → ComponentConverters → DrawingMLGenerator → XML Output

Key Design Principles:
1. Single Responsibility: Each component has one clear purpose
2. Coordinate Isolation: All coordinate transformations happen in CoordinateSystem
3. Dependency Injection: Components are loosely coupled through interfaces
4. Error Propagation: Clear error handling chain through all components
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple


class PathCommandType(Enum):
    """SVG Path command types with their numeric identifiers."""
    MOVE_TO = 0
    LINE_TO = 1
    HORIZONTAL = 2
    VERTICAL = 3
    CUBIC_CURVE = 4
    SMOOTH_CUBIC = 5
    QUADRATIC = 6
    SMOOTH_QUAD = 7
    ARC = 8
    CLOSE_PATH = 9


@dataclass
class PathCommand:
    """Represents a single SVG path command with its parameters."""
    command_type: PathCommandType
    is_relative: bool
    parameters: list[float]
    original_command: str  # Original SVG command letter (M, L, C, etc.)


@dataclass
class CoordinatePoint:
    """Represents a coordinate point in a specific coordinate system."""
    x: float
    y: float
    coordinate_system: str  # 'svg', 'emu', 'relative'


@dataclass
class BezierSegment:
    """Represents a cubic bezier curve segment."""
    start_point: CoordinatePoint
    control_point_1: CoordinatePoint
    control_point_2: CoordinatePoint
    end_point: CoordinatePoint


@dataclass
class PathBounds:
    """Represents the bounding rectangle of a path."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    width: float
    height: float
    coordinate_system: str


class IPathParser(Protocol):
    """Interface for parsing SVG path data into structured commands."""

    def parse_path_data(self, path_data: str) -> list[PathCommand]:
        """
        Parse SVG path data string into structured path commands.

        Args:
            path_data: SVG path 'd' attribute string

        Returns:
            List of PathCommand objects

        Raises:
            PathParseError: If path data is malformed
        """
        ...

    def validate_path_data(self, path_data: str) -> bool:
        """
        Validate SVG path data without parsing.

        Args:
            path_data: SVG path 'd' attribute string

        Returns:
            True if valid, False otherwise
        """
        ...


class ICoordinateSystem(Protocol):
    """
    Interface for coordinate system transformations.

    Integrates with existing viewport/units systems rather than duplicating functionality.
    Leverages:
    - ViewportEngine from .viewbox for viewport/viewBox handling
    - UnitConverter from .units for SVG → EMU conversions
    - Existing coordinate transformation infrastructure
    """

    def get_viewport_engine(self) -> Any:  # ViewportEngine
        """Get the underlying viewport engine for viewport/viewBox operations."""
        ...

    def get_unit_converter(self) -> Any:  # UnitConverter
        """Get the underlying unit converter for SVG → EMU conversions."""
        ...

    def svg_to_relative(self, x: float, y: float, bounds: PathBounds) -> tuple[float, float]:
        """
        Convert SVG coordinates to PowerPoint relative coordinates (0-100000 range).

        This is the primary method that combines:
        1. ViewportEngine for viewport/viewBox transformations
        2. UnitConverter for SVG → EMU conversions
        3. Local logic for EMU → relative coordinate mapping
        """
        ...

    def calculate_path_bounds(self, commands: list[PathCommand]) -> PathBounds:
        """
        Calculate bounding box for a series of path commands.

        Uses UnitConverter for consistent EMU coordinate calculations.
        """
        ...

    def create_conversion_context(self, viewport_width: float, viewport_height: float,
                                 viewbox: tuple[float, float, float, float] | None = None,
                                 dpi: float = 96.0) -> Any:  # ConversionContext
        """
        Create a conversion context using existing UnitConverter infrastructure.

        Args:
            viewport_width, viewport_height: SVG viewport dimensions
            viewbox: Optional SVG viewBox (x, y, width, height)
            dpi: Display DPI for unit conversions

        Returns:
            ConversionContext for unit conversions
        """
        ...


class IArcConverter(Protocol):
    """Interface for converting SVG arcs to cubic bezier curves."""

    def arc_to_bezier_segments(self, start_x: float, start_y: float, rx: float, ry: float,
                              x_axis_rotation: float, large_arc_flag: int, sweep_flag: int,
                              end_x: float, end_y: float) -> list[BezierSegment]:
        """
        Convert SVG arc to cubic bezier segments using a2c algorithm.

        Args:
            start_x, start_y: Arc start point
            rx, ry: Arc radii
            x_axis_rotation: Rotation angle in degrees
            large_arc_flag: Large arc flag (0 or 1)
            sweep_flag: Sweep flag (0 or 1)
            end_x, end_y: Arc end point

        Returns:
            List of BezierSegment objects approximating the arc

        Raises:
            ArcConversionError: If arc parameters are invalid
        """
        ...

    def validate_arc_parameters(self, rx: float, ry: float, start_x: float, start_y: float,
                               end_x: float, end_y: float) -> bool:
        """Validate arc parameters for mathematical correctness."""
        ...


class IDrawingMLGenerator(Protocol):
    """Interface for generating PowerPoint DrawingML XML."""

    def generate_path_xml(self, commands: list[PathCommand], bounds: PathBounds,
                         coordinate_system: ICoordinateSystem, arc_converter: IArcConverter) -> str:
        """
        Generate DrawingML XML for a series of path commands.

        Args:
            commands: List of path commands to convert
            bounds: Path bounding box
            coordinate_system: Coordinate transformation system
            arc_converter: Arc to bezier converter

        Returns:
            DrawingML XML string

        Raises:
            XMLGenerationError: If XML generation fails
        """
        ...

    def generate_shape_xml(self, path_xml: str, bounds: PathBounds, style_attributes: dict[str, Any]) -> str:
        """
        Generate complete PowerPoint shape XML with path and styling.

        Args:
            path_xml: Generated path XML
            bounds: Shape bounds
            style_attributes: SVG style attributes (fill, stroke, etc.)

        Returns:
            Complete PowerPoint shape XML
        """
        ...


class PathSystemError(Exception):
    """Base exception for path system errors."""
    pass


class PathParseError(PathSystemError):
    """Raised when path data cannot be parsed."""
    pass


class CoordinateTransformError(PathSystemError):
    """Raised when coordinate transformation fails."""
    pass


class ArcConversionError(PathSystemError):
    """Raised when arc conversion fails."""
    pass


class XMLGenerationError(PathSystemError):
    """Raised when XML generation fails."""
    pass


@dataclass
class PathSystemContext:
    """Dependency injection container for path system components."""
    parser: IPathParser
    coordinate_system: ICoordinateSystem
    arc_converter: IArcConverter
    xml_generator: IDrawingMLGenerator

    # Configuration
    enable_logging: bool = True
    coordinate_precision: int = 6
    arc_segment_angle: float = 90.0  # Degrees for arc segmentation

    def __post_init__(self):
        """Validate all required components are provided."""
        if not all([self.parser, self.coordinate_system, self.arc_converter, self.xml_generator]):
            raise ValueError("All path system components must be provided")


class PathSystemArchitecture:
    """
    Main architectural coordinator for the path processing system.

    This class defines the data flow and component interactions but doesn't
    implement the actual processing - that's handled by the concrete components.
    """

    @staticmethod
    def get_data_flow_description() -> str:
        """
        Return a description of the data flow through the system.

        This documents how data flows and transforms through each component.
        """
        return """
        Path System Data Flow:

        1. SVG Input: Raw SVG path 'd' attribute string
           └─ Contains: Command letters (M, L, C, A, Z) + parameters

        2. PathParser: Parse and structure path data
           ├─ Input: Raw path string
           ├─ Process: Tokenize commands, validate syntax, extract parameters
           └─ Output: List[PathCommand] with structured data

        3. CoordinateSystem: Calculate bounds and coordinate transformations
           ├─ Input: List[PathCommand] with SVG coordinates
           ├─ Process: Calculate bounding box, prepare transformation matrices
           └─ Output: PathBounds + transformation functions

        4. Component Processing: Handle special command types
           ├─ ArcConverter: SVG arcs → BezierSegment sequences
           ├─ Other converters: Handle curves, lines, etc.
           └─ Output: Standardized bezier representations

        5. CoordinateSystem: Transform all coordinates
           ├─ Input: All path points in SVG coordinates
           ├─ Process: SVG → EMU → Relative (0-100000 range)
           └─ Output: All coordinates in PowerPoint relative format

        6. DrawingMLGenerator: Generate XML
           ├─ Input: Commands with relative coordinates
           ├─ Process: Create PowerPoint XML structure
           └─ Output: Valid DrawingML XML string

        Critical Design Points:
        - Coordinates are transformed ONCE in CoordinateSystem
        - No coordinate calculations in other components
        - All arc processing uses industry-standard a2c algorithm
        - Error handling propagates through the entire chain
        """

    @staticmethod
    def get_component_responsibilities() -> dict[str, str]:
        """Return detailed component responsibility matrix."""
        return {
            "PathParser": """
                - Parse SVG path 'd' attribute strings
                - Tokenize path commands and parameters
                - Handle relative vs absolute commands
                - Validate path syntax
                - Convert to structured PathCommand objects
                - NO coordinate transformations
            """,

            "CoordinateSystem": """
                - Calculate path bounding boxes
                - Handle viewport and viewBox settings
                - Perform ALL coordinate transformations
                - SVG → EMU conversions
                - EMU → Relative (0-100000) conversions
                - Manage coordinate precision
                - Validate coordinate ranges
            """,

            "ArcConverter": """
                - Implement a2c arc-to-bezier algorithm
                - Handle center parameterization conversion
                - Segment large arcs (>90°) for smoothness
                - Process all SVG arc parameters correctly
                - Generate accurate BezierSegment sequences
                - Handle edge cases (zero radius, same start/end)
            """,

            "DrawingMLGenerator": """
                - Generate PowerPoint XML structure
                - Create proper XML namespacing
                - Handle shape bounds and transformations
                - Apply styling attributes (fill, stroke)
                - Ensure XML schema compliance
                - NO coordinate calculations
            """,

            "PathSystemContext": """
                - Dependency injection container
                - Configuration management
                - Component lifecycle management
                - Error handling coordination
                - Logging and debugging support
            """,
        }