#!/usr/bin/env python3
"""
PathProcessor utility service for SVG2PPTX.

This module provides centralized path processing functionality,
eliminating duplicate path handling implementations across converters and preprocessors.

Consolidates:
- PathPoint and PathCommand data structures from multiple files
- Path data parsing logic from preprocessing modules
- Shape-to-path conversion utilities
- DrawingML path generation
"""

import re
import math
from typing import List, Tuple, Optional, Dict, Any, NamedTuple, Union
from dataclasses import dataclass
from lxml import etree as ET

# Integration with modern PathSystem
try:
    from ..paths import PathSystem, create_path_system
    PATH_SYSTEM_AVAILABLE = True
except ImportError:
    PATH_SYSTEM_AVAILABLE = False
    PathSystem = None
    create_path_system = None


@dataclass
class PathPoint:
    """
    Unified path point data structure.

    Consolidates PathPoint implementations from:
    - src/converters/path_generator.py (simple x,y)
    - src/converters/text_path.py (with angle, distance)
    """
    x: float
    y: float
    angle: Optional[float] = None        # Tangent angle in degrees (for text paths)
    distance: Optional[float] = None     # Distance along path from start (for text paths)

    def get_normal_point(self, offset: float) -> Tuple[float, float]:
        """Get point offset perpendicular to path (requires angle)."""
        if self.angle is None:
            raise ValueError("PathPoint angle required for normal calculation")
        angle_rad = math.radians(self.angle + 90)  # Perpendicular angle
        return (
            self.x + offset * math.cos(angle_rad),
            self.y + offset * math.sin(angle_rad)
        )

    def to_simple_tuple(self) -> Tuple[float, float]:
        """Convert to simple (x, y) tuple for basic operations."""
        return (self.x, self.y)


@dataclass
class PathCommand:
    """
    Unified path command data structure.

    Consolidates PathCommand implementations from:
    - src/converters/path_generator.py (DrawingML generation)
    - Various preprocessing modules (path parsing)
    """
    command: str  # moveTo, lineTo, curveTo, closePath, or SVG command letters
    points: List[PathPoint]
    relative: bool = False

    def to_drawingml(self, scale: float = 1.0) -> str:
        """Convert to DrawingML path command format."""
        scaled_points = [PathPoint(p.x * scale, p.y * scale, p.angle, p.distance) for p in self.points]

        if self.command == 'moveTo' or self.command.upper() == 'M':
            if scaled_points:
                return f'<a:moveTo><a:pt x="{int(scaled_points[0].x)}" y="{int(scaled_points[0].y)}"/></a:moveTo>'
        elif self.command == 'lineTo' or self.command.upper() == 'L':
            if scaled_points:
                return f'<a:lnTo><a:pt x="{int(scaled_points[0].x)}" y="{int(scaled_points[0].y)}"/></a:lnTo>'
        elif self.command == 'curveTo' or self.command.upper() == 'C':
            if len(scaled_points) == 3:
                cp1, cp2, end = scaled_points[:3]
                return f'''<a:cubicBezTo>
                    <a:pt x="{int(cp1.x)}" y="{int(cp1.y)}"/>
                    <a:pt x="{int(cp2.x)}" y="{int(cp2.y)}"/>
                    <a:pt x="{int(end.x)}" y="{int(end.y)}"/>
                </a:cubicBezTo>'''
        elif self.command == 'closePath' or self.command.upper() == 'Z':
            return '<a:close/>'

        return ''

    def to_svg_command(self) -> str:
        """Convert to SVG path command string."""
        cmd_char = self.command[0].upper() if len(self.command) > 1 else self.command.upper()
        if self.relative and cmd_char != 'Z':
            cmd_char = cmd_char.lower()

        coord_strs = []
        for point in self.points:
            coord_strs.extend([str(point.x), str(point.y)])

        if coord_strs:
            return f"{cmd_char} {' '.join(coord_strs)}"
        else:
            return cmd_char


class PathProcessor:
    """
    Centralized path processing service.

    Provides unified path processing functionality to replace duplicate
    implementations across converters and preprocessing modules.
    """

    def __init__(self):
        """Initialize PathProcessor with optimization settings."""
        # Initialize high-performance engine if available
        # PathSystem will be created per-use with proper viewport configuration
        self.path_system = None

        # Pre-compile regex patterns for path parsing
        self.command_pattern = re.compile(r'([MmLlHhVvCcSsQqTtAaZz])')
        self.number_pattern = re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')

        # Shape-to-path conversion constants
        self.circle_segments = 8  # Number of segments for circle approximation

    def parse_path_string(self, path_data: str) -> List[PathCommand]:
        """
        Parse SVG path string into PathCommand objects.

        Consolidates path parsing logic from:
        - src/preprocessing/advanced_geometry_plugins.py:90 (_parse_path_commands)
        - src/preprocessing/advanced_geometry_plugins.py:116 (_legacy_parse_path_commands)

        Args:
            path_data: SVG path data string

        Returns:
            List of PathCommand objects
        """
        if not path_data or not path_data.strip():
            return []

        commands = []

        # Split path data into command tokens
        tokens = self.command_pattern.split(path_data.strip())

        current_pos = PathPoint(0, 0)
        current_command = None

        for i, token in enumerate(tokens):
            token = token.strip()
            if not token:
                continue

            # Check if token is a command letter
            if self.command_pattern.match(token):
                current_command = token
            elif current_command:
                # Parse coordinates for current command
                coords = [float(x) for x in self.number_pattern.findall(token)]
                cmd_obj = self._create_path_command(current_command, coords, current_pos)
                if cmd_obj:
                    commands.append(cmd_obj)
                    # Update current position
                    if cmd_obj.points:
                        current_pos = cmd_obj.points[-1]

        return commands

    def _create_path_command(self, command: str, coords: List[float],
                           current_pos: PathPoint) -> Optional[PathCommand]:
        """Create PathCommand from SVG command and coordinates."""
        if not coords and command.upper() != 'Z':
            return None

        is_relative = command.islower()
        cmd_upper = command.upper()
        points = []

        if cmd_upper == 'M':  # MoveTo
            if len(coords) >= 2:
                x, y = coords[0], coords[1]
                if is_relative:
                    x += current_pos.x
                    y += current_pos.y
                points = [PathPoint(x, y)]

        elif cmd_upper == 'L':  # LineTo
            if len(coords) >= 2:
                x, y = coords[0], coords[1]
                if is_relative:
                    x += current_pos.x
                    y += current_pos.y
                points = [PathPoint(x, y)]

        elif cmd_upper == 'C':  # CubeTo
            if len(coords) >= 6:
                cp1_x, cp1_y = coords[0], coords[1]
                cp2_x, cp2_y = coords[2], coords[3]
                end_x, end_y = coords[4], coords[5]

                if is_relative:
                    cp1_x += current_pos.x
                    cp1_y += current_pos.y
                    cp2_x += current_pos.x
                    cp2_y += current_pos.y
                    end_x += current_pos.x
                    end_y += current_pos.y

                points = [
                    PathPoint(cp1_x, cp1_y),
                    PathPoint(cp2_x, cp2_y),
                    PathPoint(end_x, end_y)
                ]

        elif cmd_upper == 'Z':  # ClosePath
            points = []

        # Add more command types as needed (H, V, S, Q, T, A)

        return PathCommand(command, points, is_relative)

    def commands_to_path_string(self, commands: List[PathCommand], precision: int = 3) -> str:
        """
        Convert PathCommand objects back to SVG path string.

        Consolidates path generation logic from:
        - src/preprocessing/advanced_geometry_plugins.py:146 (_commands_to_path_data)

        Args:
            commands: List of PathCommand objects
            precision: Decimal precision for coordinates

        Returns:
            SVG path data string
        """
        if not commands:
            return ""

        path_parts = []
        for cmd in commands:
            svg_cmd = cmd.to_svg_command()
            if svg_cmd:
                # Apply precision formatting
                if precision > 0:
                    svg_cmd = self._format_precision(svg_cmd, precision)
                path_parts.append(svg_cmd)

        return ' '.join(path_parts)

    def _format_precision(self, path_string: str, precision: int) -> str:
        """Format numeric values in path string to specified precision."""
        def format_number(match):
            num = float(match.group())
            return f"{num:.{precision}f}".rstrip('0').rstrip('.')

        return self.number_pattern.sub(format_number, path_string)

    def clean_path_data(self, path_data: str, precision: int = 3) -> str:
        """
        Clean and optimize path data.

        Consolidates path cleaning logic from:
        - src/preprocessing/plugins.py:88 (_clean_path_data)
        - src/preprocessing/advanced_plugins.py:43 (_optimize_path_data)

        Args:
            path_data: Raw SVG path data
            precision: Coordinate precision

        Returns:
            Cleaned path data string
        """
        if not path_data or not path_data.strip():
            return ""

        # Parse and reconstruct to clean format
        commands = self.parse_path_string(path_data)
        cleaned = self.commands_to_path_string(commands, precision)

        # Additional cleanup
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
        cleaned = cleaned.strip()

        return cleaned

    def rect_to_path(self, x: float, y: float, width: float, height: float,
                     rx: float = 0, ry: float = 0, precision: int = 3) -> str:
        """
        Convert rectangle to path data.

        Consolidates from: src/preprocessing/plugins.py:310 (_rect_to_path)

        Args:
            x, y: Rectangle position
            width, height: Rectangle dimensions
            rx, ry: Corner radius
            precision: Coordinate precision

        Returns:
            SVG path data string
        """
        if rx == 0 and ry == 0:
            # Simple rectangle
            commands = [
                PathCommand('M', [PathPoint(x, y)]),
                PathCommand('L', [PathPoint(x + width, y)]),
                PathCommand('L', [PathPoint(x + width, y + height)]),
                PathCommand('L', [PathPoint(x, y + height)]),
                PathCommand('Z', [])
            ]
        else:
            # Rounded rectangle (simplified implementation)
            rx = min(rx, width / 2)
            ry = min(ry, height / 2)

            commands = [
                PathCommand('M', [PathPoint(x + rx, y)]),
                PathCommand('L', [PathPoint(x + width - rx, y)]),
                # Add arc commands for corners (simplified as lines for now)
                PathCommand('L', [PathPoint(x + width, y + ry)]),
                PathCommand('L', [PathPoint(x + width, y + height - ry)]),
                PathCommand('L', [PathPoint(x + width - rx, y + height)]),
                PathCommand('L', [PathPoint(x + rx, y + height)]),
                PathCommand('L', [PathPoint(x, y + height - ry)]),
                PathCommand('L', [PathPoint(x, y + ry)]),
                PathCommand('Z', [])
            ]

        return self.commands_to_path_string(commands, precision)

    def circle_to_path(self, cx: float, cy: float, r: float, precision: int = 3) -> str:
        """
        Convert circle to path data using Bezier approximation.

        Consolidates from: src/preprocessing/plugins.py:336 (_circle_to_path)

        Args:
            cx, cy: Circle center
            r: Circle radius
            precision: Coordinate precision

        Returns:
            SVG path data string
        """
        # Use 4 cubic Bezier curves to approximate circle
        # Control point distance for 90-degree arc
        k = 0.552284749831  # Magic number for circle approximation

        commands = [
            PathCommand('M', [PathPoint(cx + r, cy)]),
            PathCommand('C', [
                PathPoint(cx + r, cy + r * k),
                PathPoint(cx + r * k, cy + r),
                PathPoint(cx, cy + r)
            ]),
            PathCommand('C', [
                PathPoint(cx - r * k, cy + r),
                PathPoint(cx - r, cy + r * k),
                PathPoint(cx - r, cy)
            ]),
            PathCommand('C', [
                PathPoint(cx - r, cy - r * k),
                PathPoint(cx - r * k, cy - r),
                PathPoint(cx, cy - r)
            ]),
            PathCommand('C', [
                PathPoint(cx + r * k, cy - r),
                PathPoint(cx + r, cy - r * k),
                PathPoint(cx + r, cy)
            ]),
            PathCommand('Z', [])
        ]

        return self.commands_to_path_string(commands, precision)

    def ellipse_to_path(self, cx: float, cy: float, rx: float, ry: float,
                       precision: int = 3) -> str:
        """
        Convert ellipse to path data.

        Consolidates from: src/preprocessing/plugins.py:355 (_ellipse_to_path)

        Args:
            cx, cy: Ellipse center
            rx, ry: Ellipse radii
            precision: Coordinate precision

        Returns:
            SVG path data string
        """
        # Use 4 cubic Bezier curves to approximate ellipse
        kx = 0.552284749831 * rx
        ky = 0.552284749831 * ry

        commands = [
            PathCommand('M', [PathPoint(cx + rx, cy)]),
            PathCommand('C', [
                PathPoint(cx + rx, cy + ky),
                PathPoint(cx + kx, cy + ry),
                PathPoint(cx, cy + ry)
            ]),
            PathCommand('C', [
                PathPoint(cx - kx, cy + ry),
                PathPoint(cx - rx, cy + ky),
                PathPoint(cx - rx, cy)
            ]),
            PathCommand('C', [
                PathPoint(cx - rx, cy - ky),
                PathPoint(cx - kx, cy - ry),
                PathPoint(cx, cy - ry)
            ]),
            PathCommand('C', [
                PathPoint(cx + kx, cy - ry),
                PathPoint(cx + rx, cy - ky),
                PathPoint(cx + rx, cy)
            ]),
            PathCommand('Z', [])
        ]

        return self.commands_to_path_string(commands, precision)

    def line_to_path(self, x1: float, y1: float, x2: float, y2: float,
                    precision: int = 3) -> str:
        """
        Convert line to path data.

        Consolidates from: src/preprocessing/plugins.py:375 (_line_to_path)

        Args:
            x1, y1: Line start point
            x2, y2: Line end point
            precision: Coordinate precision

        Returns:
            SVG path data string
        """
        commands = [
            PathCommand('M', [PathPoint(x1, y1)]),
            PathCommand('L', [PathPoint(x2, y2)])
        ]

        return self.commands_to_path_string(commands, precision)

    def optimize_path_data(self, path_data: str, precision: int = 3) -> str:
        """
        Optimize path data by removing redundant commands and simplifying curves.

        Consolidates optimization logic from multiple preprocessing modules.

        Args:
            path_data: SVG path data to optimize
            precision: Coordinate precision

        Returns:
            Optimized path data string
        """
        if not path_data or not path_data.strip():
            return ""

        # Parse path into commands
        commands = self.parse_path_string(path_data)

        # Apply optimizations
        commands = self._remove_redundant_commands(commands)
        commands = self._merge_consecutive_lines(commands)

        # Reconstruct optimized path
        return self.commands_to_path_string(commands, precision)

    def _remove_redundant_commands(self, commands: List[PathCommand]) -> List[PathCommand]:
        """Remove redundant move and line commands."""
        if not commands:
            return commands

        optimized = []
        prev_point = None

        for cmd in commands:
            # Skip redundant moves to same position
            if (cmd.command.upper() == 'M' and cmd.points and prev_point and
                abs(cmd.points[0].x - prev_point.x) < 0.01 and
                abs(cmd.points[0].y - prev_point.y) < 0.01):
                continue

            # Skip zero-length lines
            if (cmd.command.upper() == 'L' and cmd.points and prev_point and
                abs(cmd.points[0].x - prev_point.x) < 0.01 and
                abs(cmd.points[0].y - prev_point.y) < 0.01):
                continue

            optimized.append(cmd)
            if cmd.points:
                prev_point = cmd.points[-1]

        return optimized

    def _merge_consecutive_lines(self, commands: List[PathCommand]) -> List[PathCommand]:
        """Merge consecutive line commands in same direction."""
        if len(commands) < 2:
            return commands

        merged = [commands[0]]

        for i in range(1, len(commands)):
            current = commands[i]
            previous = merged[-1]

            # Check if both are line commands
            if (current.command.upper() == 'L' and previous.command.upper() == 'L' and
                current.points and previous.points):

                # Check if they are collinear (simplified check)
                if len(merged) >= 2:
                    prev_prev = merged[-2]
                    if (prev_prev.points and self._are_collinear(
                        prev_prev.points[-1], previous.points[-1], current.points[-1])):
                        # Replace previous line with extended line
                        merged[-1] = PathCommand(current.command, current.points, current.relative)
                        continue

            merged.append(current)

        return merged

    def _are_collinear(self, p1: PathPoint, p2: PathPoint, p3: PathPoint,
                      tolerance: float = 0.1) -> bool:
        """Check if three points are approximately collinear."""
        # Calculate cross product to check collinearity
        cross_product = ((p2.x - p1.x) * (p3.y - p1.y) -
                        (p2.y - p1.y) * (p3.x - p1.x))
        return abs(cross_product) < tolerance

    def generate_drawingml_path(self, commands: List[PathCommand], scale: float = 1.0) -> str:
        """
        Generate complete DrawingML path XML from PathCommand objects.

        Consolidates DrawingML generation from path_generator.py.

        Args:
            commands: List of PathCommand objects
            scale: Scale factor for coordinates

        Returns:
            Complete DrawingML path XML
        """
        if not commands:
            return ""

        path_elements = []
        for cmd in commands:
            drawingml = cmd.to_drawingml(scale)
            if drawingml:
                path_elements.append(drawingml)

        if not path_elements:
            return ""

        return f'''<a:path w="1" h="1">
            <a:pathLst>
                <a:path>
                    {''.join(path_elements)}
                </a:path>
            </a:pathLst>
        </a:path>'''

    def optimize_path(self, path_data: str) -> str:
        """
        Optimize path data - adapter compatibility alias.

        Args:
            path_data: SVG path data string

        Returns:
            Optimized path data string
        """
        return self.optimize_path_data(path_data)


# Global path processor instance for convenience
path_processor = PathProcessor()


def parse_path_string(path_data: str) -> List[PathCommand]:
    """Convenience function for path parsing."""
    return path_processor.parse_path_string(path_data)


def clean_path_data(path_data: str, precision: int = 3) -> str:
    """Convenience function for path cleaning."""
    return path_processor.clean_path_data(path_data, precision)


def rect_to_path(x: float, y: float, width: float, height: float,
                rx: float = 0, ry: float = 0, precision: int = 3) -> str:
    """Convenience function for rectangle to path conversion."""
    return path_processor.rect_to_path(x, y, width, height, rx, ry, precision)


def circle_to_path(cx: float, cy: float, r: float, precision: int = 3) -> str:
    """Convenience function for circle to path conversion."""
    return path_processor.circle_to_path(cx, cy, r, precision)