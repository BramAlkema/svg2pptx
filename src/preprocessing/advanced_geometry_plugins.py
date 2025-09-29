"""
Advanced geometry optimization plugins using the high-performance geometry_simplify utility.
"""

import re
from lxml import etree as ET
from typing import Dict, List, Optional, Set, Tuple
from .base import PreprocessingPlugin, PreprocessingContext
from .geometry_simplify import simplify_polyline, simplify_to_cubics, Pt


class AdvancedPathSimplificationPlugin(PreprocessingPlugin):
    """Advanced path simplification using Ramer-Douglas-Peucker algorithm."""
    
    name = "advancedPathSimplification"
    description = "advanced path simplification using RDP algorithm with cubic smoothing"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return self._tag_matches(element, 'path') and 'd' in element.attrib
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        path_data = element.attrib.get('d', '')
        if not path_data:
            return False
        
        try:
            # Parse path data to extract coordinate sequences
            simplified_path = self._simplify_path_data(path_data, context.precision)
            
            if simplified_path != path_data:
                element.set('d', simplified_path)
                context.record_modification(self.name, "simplified_path_rdp")
                return True
                
        except Exception as e:
            print(f"Advanced path simplification failed: {e}")
        
        return False
    
    def _simplify_path_data(self, path_data: str, precision: int) -> str:
        """Simplify path data using RDP algorithm."""
        # Calculate tolerance based on precision
        tolerance = 10 ** (-precision + 1)  # More aggressive than basic precision
        
        # Parse path commands and coordinates
        commands = self._parse_path_commands(path_data)
        
        simplified_commands = []
        current_pos = (0.0, 0.0)
        
        for cmd_type, coords in commands:
            if cmd_type.upper() in 'ML' and len(coords) >= 4:  # Line sequences
                # Extract points for simplification
                points = []
                if cmd_type.upper() == 'M':
                    points.append(coords[:2])
                    coords = coords[2:]
                
                # Add line points
                for i in range(0, len(coords), 2):
                    if i + 1 < len(coords):
                        points.append((coords[i], coords[i + 1]))
                
                if len(points) > 2:
                    # Apply RDP simplification
                    simplified_points = simplify_polyline(points, tolerance)
                    
                    # Convert back to path commands
                    if simplified_points:
                        if cmd_type.upper() == 'M':
                            # Move to first point
                            simplified_commands.append((cmd_type, list(simplified_points[0])))
                            # Lines to remaining points
                            for pt in simplified_points[1:]:
                                simplified_commands.append(('L' if cmd_type.isupper() else 'l', list(pt)))
                        else:
                            # All as line commands
                            for pt in simplified_points:
                                simplified_commands.append((cmd_type, list(pt)))
                else:
                    # Keep original if too few points
                    simplified_commands.append((cmd_type, coords))
            else:
                # Keep non-line commands as-is
                simplified_commands.append((cmd_type, coords))
        
        # Convert back to path data string
        return self._commands_to_path_data(simplified_commands, precision)
    
    def _parse_path_commands(self, path_data: str) -> List[Tuple[str, List[float]]]:
        """Parse path data using consolidated PathProcessor service."""
        try:
            # Use the consolidated PathProcessor for consistent path parsing
            from ..utils.path_processor import path_processor

            path_commands = path_processor.parse_path_string(path_data)

            # Convert PathCommand objects to expected tuple format
            result = []
            for cmd in path_commands:
                command_char = cmd.command.upper()
                coordinates = []
                for point in cmd.points:
                    coordinates.extend([point.x, point.y])
                result.append((command_char, coordinates))

            return result

        except ImportError:
            # Fallback to legacy parsing if PathProcessor not available
            return self._legacy_parse_path_commands(path_data)
        except Exception:
            # Fallback to legacy parsing on any error
            return self._legacy_parse_path_commands(path_data)

    def _legacy_parse_path_commands(self, path_data: str) -> List[Tuple[str, List[float]]]:
        """Legacy path parsing - to be replaced once PathEngine integration is complete."""
        commands = []

        # Split path data into command segments
        pattern = r'([MmLlHhVvCcSsQqTtAaZz])'
        parts = re.split(pattern, path_data)

        current_command = ''
        for part in parts:
            part = part.strip()
            if not part:
                continue

            if re.match(r'[MmLlHhVvCcSsQqTtAaZz]', part):
                current_command = part
            else:
                # Parse coordinates
                coords = []
                for coord_str in re.findall(r'-?\d*\.?\d+', part):
                    try:
                        coords.append(float(coord_str))
                    except ValueError:
                        continue
                
                if coords and current_command:
                    commands.append((current_command, coords))
        
        return commands
    
    def _commands_to_path_data(self, commands: List[Tuple[str, List[float]]], precision: int) -> str:
        """Convert commands back to path data string using PathProcessor."""
        try:
            # Use PathProcessor for consistent path string generation
            from ..utils.path_processor import path_processor, PathCommand, PathPoint

            # Convert tuple format back to PathCommand objects
            path_commands = []
            for cmd_type, coords in commands:
                points = []
                # Group coordinates into point pairs
                for i in range(0, len(coords), 2):
                    if i + 1 < len(coords):
                        points.append(PathPoint(coords[i], coords[i + 1]))

                path_commands.append(PathCommand(cmd_type, points))

            # Use PathProcessor to generate clean path string
            return path_processor.commands_to_path_string(path_commands, precision)

        except ImportError:
            # Fallback to legacy implementation
            pass

        # Legacy implementation
        parts = []

        for cmd_type, coords in commands:
            coord_strs = []
            for coord in coords:
                if abs(coord) < 10**-precision:
                    coord_strs.append('0')
                elif coord == int(coord):
                    coord_strs.append(str(int(coord)))
                else:
                    formatted = f"{coord:.{precision}f}".rstrip('0').rstrip('.')
                    coord_strs.append(formatted if formatted else '0')

            parts.append(cmd_type + ' '.join(coord_strs))

        return ' '.join(parts)


class AdvancedPolygonSimplificationPlugin(PreprocessingPlugin):
    """Enhanced polygon simplification with RDP algorithm and cubic smoothing options."""
    
    name = "advancedPolygonSimplification"
    description = "advanced polygon simplification with RDP algorithm and optional cubic smoothing"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return self._tag_matches(element, ('polygon', 'polyline')) and 'points' in element.attrib
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        points_str = element.attrib.get('points', '')
        if not points_str:
            return False
        
        try:
            # Parse points
            points = self._parse_points(points_str)
            if len(points) < 3:
                return False
            
            # Calculate tolerance
            tolerance = 10 ** (-context.precision + 1)
            
            # Apply advanced simplification
            simplified_points = simplify_polyline(points, tolerance, collinear_deg=1.0)
            
            # Check if we achieved significant reduction
            reduction = len(points) - len(simplified_points)
            if reduction >= 2:  # Only apply if we save at least 2 points
                new_points_str = self._points_to_string(simplified_points, context.precision)
                element.set('points', new_points_str)
                context.record_modification(self.name, f"simplified_polygon_rdp_{reduction}_points")
                return True
                
        except Exception as e:
            print(f"Advanced polygon simplification failed: {e}")
        
        return False
    
    def _parse_points(self, points_str: str) -> List[Pt]:
        """Parse points string into coordinate pairs using consolidated PreprocessorUtilities."""
        try:
            # Use PreprocessorUtilities for consistent points parsing
            from ..utils.preprocessor_utilities import preprocessor_utilities
            result = preprocessor_utilities.parse_points_string(points_str)
            return result.data if result.success else []
        except ImportError:
            # Fallback to legacy implementation
            pass

        # Legacy implementation
        coords = [x for x in re.split(r'[\s,]+', points_str.strip()) if x]

        points = []
        for i in range(0, len(coords) - 1, 2):
            try:
                x = float(coords[i])
                y = float(coords[i + 1])
                points.append((x, y))
            except (ValueError, IndexError):
                break

        return points
    
    def _points_to_string(self, points: List[Pt], precision: int) -> str:
        """Convert points back to string representation."""
        formatted_points = []
        for x, y in points:
            x_str = self._format_number(x, precision)
            y_str = self._format_number(y, precision)
            formatted_points.append(f"{x_str},{y_str}")
        
        return ' '.join(formatted_points)

    def _format_number(self, num: float, precision: int) -> str:
        """Format number with appropriate precision using consolidated PreprocessorUtilities."""
        try:
            # Use PreprocessorUtilities for consistent number formatting
            from ..utils.preprocessor_utilities import preprocessor_utilities
            return preprocessor_utilities.format_number(num, precision)
        except ImportError:
            # Fallback to legacy implementation
            pass

        # Legacy implementation
        if abs(num) < 10**-precision:
            return '0'
        if abs(num - round(num)) < 10**-precision:
            return str(int(round(num)))
        else:
            formatted = f"{num:.{precision}f}".rstrip('0').rstrip('.')
            return formatted if formatted else '0'


class CubicSmoothingPlugin(PreprocessingPlugin):
    """Convert simplified polygons to smooth cubic Bezier curves where beneficial."""
    
    name = "cubicSmoothing"
    description = "convert simplified polygons to smooth cubic Bezier curves using Catmull-Rom"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        # Only apply to polygons/polylines with sufficient points
        if not (self._tag_matches(element, ('polygon', 'polyline')) and 'points' in element.attrib):
            return False
        
        points_str = element.attrib.get('points', '')
        points = self._parse_points(points_str)
        return len(points) >= 4  # Need at least 4 points for cubic smoothing
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        points_str = element.attrib.get('points', '')
        if not points_str:
            return False
        
        try:
            points = self._parse_points(points_str)
            if len(points) < 4:
                return False
            
            # Check if smoothing would be beneficial
            if not self._should_apply_smoothing(points):
                return False
            
            # Calculate tolerance for simplification
            tolerance = 10 ** (-context.precision + 1)
            
            # Generate cubic curves
            cubics = simplify_to_cubics(points, tolerance, step=1)
            
            if cubics and len(cubics) > 0:
                # Convert to path element with cubic curves
                path_data = self._cubics_to_path_data(cubics, context.precision)
                
                # Change element to path
                element.tag = element.tag.replace('polygon', 'path').replace('polyline', 'path')
                element.set('d', path_data)
                
                # Remove points attribute
                if 'points' in element.attrib:
                    del element.attrib['points']
                
                context.record_modification(self.name, f"converted_to_cubic_{len(cubics)}_curves")
                return True
                
        except Exception as e:
            print(f"Cubic smoothing failed: {e}")
        
        return False
    
    def _parse_points(self, points_str: str) -> List[Pt]:
        """Parse points string into coordinate pairs using consolidated PreprocessorUtilities."""
        try:
            # Use PreprocessorUtilities for consistent points parsing
            from ..utils.preprocessor_utilities import preprocessor_utilities
            result = preprocessor_utilities.parse_points_string(points_str)
            return result.data if result.success else []
        except ImportError:
            # Fallback to legacy implementation
            pass

        # Legacy implementation
        coords = [x for x in re.split(r'[\s,]+', points_str.strip()) if x]

        points = []
        for i in range(0, len(coords) - 1, 2):
            try:
                x = float(coords[i])
                y = float(coords[i + 1])
                points.append((x, y))
            except (ValueError, IndexError):
                break

        return points
    
    def _should_apply_smoothing(self, points: List[Pt]) -> bool:
        """Determine if cubic smoothing would be beneficial."""
        # Apply smoothing if the polygon has curves or would benefit from smoothing
        # Check for angular changes that suggest curves
        
        if len(points) < 4:
            return False
        
        # Calculate average turn angles
        total_turn = 0.0
        turn_count = 0
        
        for i in range(1, len(points) - 1):
            p1, p2, p3 = points[i-1], points[i], points[i+1]
            
            # Calculate vectors
            v1x, v1y = p1[0] - p2[0], p1[1] - p2[1]
            v2x, v2y = p3[0] - p2[0], p3[1] - p2[1]
            
            # Calculate angle between vectors
            from math import hypot, atan2, degrees
            
            if hypot(v1x, v1y) > 0 and hypot(v2x, v2y) > 0:
                angle1 = atan2(v1y, v1x)
                angle2 = atan2(v2y, v2x)
                turn = abs(degrees(angle2 - angle1))
                if turn > 180:
                    turn = 360 - turn
                
                total_turn += turn
                turn_count += 1
        
        if turn_count == 0:
            return False
        
        average_turn = total_turn / turn_count
        
        # Apply smoothing if there are moderate curves (not too angular, not too straight)
        return 10 < average_turn < 160
    
    def _cubics_to_path_data(self, cubics: List[Tuple[Pt, Pt, Pt, Pt]], precision: int) -> str:
        """Convert cubic curves to SVG path data."""
        if not cubics:
            return ''
        
        parts = []
        
        # Move to first point
        p0 = cubics[0][0]
        parts.append(f"M{self._format_number(p0[0], precision)},{self._format_number(p0[1], precision)}")
        
        # Add cubic curves
        for p0, p1, p2, p3 in cubics:
            parts.append(f"C{self._format_number(p1[0], precision)},{self._format_number(p1[1], precision)} "
                        f"{self._format_number(p2[0], precision)},{self._format_number(p2[1], precision)} "
                        f"{self._format_number(p3[0], precision)},{self._format_number(p3[1], precision)}")
        
        return ' '.join(parts)

    def _format_number(self, num: float, precision: int) -> str:
        """Format number with appropriate precision using consolidated PreprocessorUtilities."""
        try:
            # Use PreprocessorUtilities for consistent number formatting
            from ..utils.preprocessor_utilities import preprocessor_utilities
            return preprocessor_utilities.format_number(num, precision)
        except ImportError:
            # Fallback to legacy implementation
            pass

        # Legacy implementation
        if abs(num) < 10**-precision:
            return '0'
        if abs(num - round(num)) < 10**-precision:
            return str(int(round(num)))
        else:
            formatted = f"{num:.{precision}f}".rstrip('0').rstrip('.')
            return formatted if formatted else '0'


class GeometryOptimizationStatsPlugin(PreprocessingPlugin):
    """Collect statistics on geometry optimization effectiveness."""
    
    name = "geometryOptimizationStats"
    description = "collect statistics on geometry optimization effectiveness"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return self._tag_matches(element, ('path', 'polygon', 'polyline'))
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        # This plugin doesn't modify elements, just collects stats
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        # Count geometric complexity
        if tag == 'path':
            path_data = element.attrib.get('d', '')
            command_count = len(re.findall(r'[MmLlHhVvCcSsQqTtAaZz]', path_data))
            coord_count = len(re.findall(r'-?\d*\.?\d+', path_data))
            context.record_modification(self.name, f"path_complexity_{command_count}cmd_{coord_count}coords")
            
        elif tag in ['polygon', 'polyline']:
            points_str = element.attrib.get('points', '')
            point_count = len(re.findall(r'-?\d*\.?\d+', points_str)) // 2
            context.record_modification(self.name, f"{tag}_complexity_{point_count}points")
        
        return False  # Never modifies elements