"""
Geometry-focused preprocessing plugins for advanced shape optimization.
"""

import re
import math
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set, Tuple, Union
from .base import PreprocessingPlugin, PreprocessingContext


class ConvertEllipseToCirclePlugin(PreprocessingPlugin):
    """Convert non-eccentric ellipses to circles."""
    
    name = "convertEllipseToCircle"
    description = "converts non-eccentric <ellipse>s to <circle>s"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return element.tag.endswith('ellipse')
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        rx = float(element.get('rx', 0))
        ry = float(element.get('ry', 0))
        
        # Check if rx and ry are equal (within precision tolerance)
        tolerance = 10 ** -context.precision
        if abs(rx - ry) < tolerance and rx > 0:
            # Convert ellipse to circle
            element.tag = element.tag.replace('ellipse', 'circle')
            element.set('r', str(rx))
            
            # Remove rx and ry attributes
            if 'rx' in element.attrib:
                del element.attrib['rx']
            if 'ry' in element.attrib:
                del element.attrib['ry']
            
            context.record_modification(self.name, "converted_ellipse_to_circle")
            return True
        
        return False


class SimplifyPolygonPlugin(PreprocessingPlugin):
    """Simplify polygon and polyline points."""
    
    name = "simplifyPolygon"
    description = "simplifies polygon and polyline points by removing redundant points"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return element.tag.endswith(('polygon', 'polyline')) and 'points' in element.attrib
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        points_str = element.attrib.get('points', '')
        if not points_str:
            return False
        
        try:
            points = self._parse_points(points_str)
            simplified_points = self._simplify_points(points, context.precision)
            
            if len(simplified_points) < len(points):
                new_points_str = self._points_to_string(simplified_points, context.precision)
                element.set('points', new_points_str)
                context.record_modification(self.name, "simplified_polygon")
                return True
        except Exception as e:
            print(f"Polygon simplification failed: {e}")
        
        return False
    
    def _parse_points(self, points_str: str) -> List[Tuple[float, float]]:
        """Parse points string into coordinate pairs."""
        # Split by whitespace and commas, filter empty strings
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
    
    def _simplify_points(self, points: List[Tuple[float, float]], precision: int) -> List[Tuple[float, float]]:
        """Simplify points using Douglas-Peucker algorithm."""
        if len(points) <= 2:
            return points
        
        tolerance = 10 ** (-precision)
        return self._douglas_peucker(points, tolerance)
    
    def _douglas_peucker(self, points: List[Tuple[float, float]], tolerance: float) -> List[Tuple[float, float]]:
        """Douglas-Peucker line simplification algorithm."""
        if len(points) <= 2:
            return points
        
        # Find the point with the maximum distance from the line
        max_distance = 0
        index = 0
        end_index = len(points) - 1
        
        for i in range(1, end_index):
            distance = self._perpendicular_distance(points[i], points[0], points[end_index])
            if distance > max_distance:
                index = i
                max_distance = distance
        
        # If max distance is greater than tolerance, recursively simplify
        if max_distance > tolerance:
            # Recursive call
            left_results = self._douglas_peucker(points[:index + 1], tolerance)
            right_results = self._douglas_peucker(points[index:], tolerance)
            
            # Build the result list
            return left_results[:-1] + right_results
        else:
            # Return just the endpoints
            return [points[0], points[end_index]]
    
    def _perpendicular_distance(self, point: Tuple[float, float], 
                               line_start: Tuple[float, float], 
                               line_end: Tuple[float, float]) -> float:
        """Calculate perpendicular distance from point to line."""
        x, y = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Calculate the perpendicular distance
        A = x - x1
        B = y - y1
        C = x2 - x1
        D = y2 - y1
        
        dot = A * C + B * D
        len_sq = C * C + D * D
        
        if len_sq == 0:
            # Line start and end are the same point
            return math.sqrt(A * A + B * B)
        
        param = dot / len_sq
        
        if param < 0:
            xx, yy = x1, y1
        elif param > 1:
            xx, yy = x2, y2
        else:
            xx = x1 + param * C
            yy = y1 + param * D
        
        dx = x - xx
        dy = y - yy
        
        return math.sqrt(dx * dx + dy * dy)
    
    def _points_to_string(self, points: List[Tuple[float, float]], precision: int) -> str:
        """Convert points back to string representation."""
        formatted_points = []
        for x, y in points:
            x_str = self._format_number(x, precision)
            y_str = self._format_number(y, precision)
            formatted_points.append(f"{x_str},{y_str}")
        
        return ' '.join(formatted_points)
    
    def _format_number(self, num: float, precision: int) -> str:
        """Format number with appropriate precision."""
        if abs(num) < 10**-precision:
            return '0'
        if num == int(num):
            return str(int(num))
        else:
            formatted = f"{num:.{precision}f}".rstrip('0').rstrip('.')
            return formatted if formatted else '0'


class OptimizeViewBoxPlugin(PreprocessingPlugin):
    """Optimize viewBox values and remove unnecessary viewBox."""
    
    name = "optimizeViewBox"
    description = "optimizes viewBox values and removes unnecessary viewBox"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return element.tag.endswith('svg') and 'viewBox' in element.attrib
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        viewbox_str = element.attrib.get('viewBox', '')
        if not viewbox_str:
            return False
        
        try:
            viewbox_values = [float(x) for x in viewbox_str.split()]
            if len(viewbox_values) != 4:
                return False
            
            x, y, width, height = viewbox_values
            
            # Check if viewBox is equivalent to width/height attributes
            svg_width = element.get('width', '')
            svg_height = element.get('height', '')
            
            # Remove units for comparison
            svg_width_num = self._parse_dimension(svg_width)
            svg_height_num = self._parse_dimension(svg_height)
            
            tolerance = 10 ** -context.precision
            
            # If viewBox matches width/height and starts at origin, it might be redundant
            if (abs(x) < tolerance and abs(y) < tolerance and 
                svg_width_num is not None and svg_height_num is not None and
                abs(width - svg_width_num) < tolerance and 
                abs(height - svg_height_num) < tolerance):
                
                # ViewBox is redundant, remove it
                del element.attrib['viewBox']
                context.record_modification(self.name, "removed_redundant_viewbox")
                return True
            
            # Otherwise, optimize the viewBox values
            optimized_values = []
            for value in viewbox_values:
                if abs(value) < tolerance:
                    optimized_values.append('0')
                elif value == int(value):
                    optimized_values.append(str(int(value)))
                else:
                    formatted = f"{value:.{context.precision}f}".rstrip('0').rstrip('.')
                    optimized_values.append(formatted if formatted else '0')
            
            optimized_viewbox = ' '.join(optimized_values)
            if optimized_viewbox != viewbox_str:
                element.set('viewBox', optimized_viewbox)
                context.record_modification(self.name, "optimized_viewbox_values")
                return True
                
        except (ValueError, IndexError) as e:
            print(f"ViewBox optimization failed: {e}")
        
        return False
    
    def _parse_dimension(self, dimension_str: str) -> Optional[float]:
        """Parse dimension string (e.g., '100px', '50%') to numeric value."""
        if not dimension_str:
            return None
        
        # Remove units
        numeric_str = re.sub(r'[a-zA-Z%]+$', '', dimension_str.strip())
        try:
            return float(numeric_str)
        except ValueError:
            return None


class SimplifyTransformMatrixPlugin(PreprocessingPlugin):
    """Simplify transform matrices to simpler transform functions."""
    
    name = "simplifyTransformMatrix"
    description = "converts transform matrices to simpler transform functions when possible"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return 'transform' in element.attrib and 'matrix(' in element.attrib['transform']
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        transform_str = element.attrib.get('transform', '')
        if 'matrix(' not in transform_str:
            return False
        
        try:
            simplified = self._simplify_matrix_transforms(transform_str, context.precision)
            if simplified != transform_str:
                element.set('transform', simplified)
                context.record_modification(self.name, "simplified_matrix")
                return True
        except Exception as e:
            print(f"Matrix simplification failed: {e}")
        
        return False
    
    def _simplify_matrix_transforms(self, transform_str: str, precision: int) -> str:
        """Simplify matrix transforms to basic transform functions."""
        # Find matrix functions
        matrix_pattern = r'matrix\(\s*([^)]+)\s*\)'
        
        def replace_matrix(match):
            matrix_params = match.group(1)
            params = [float(p.strip()) for p in matrix_params.split(',')]
            
            if len(params) != 6:
                return match.group(0)  # Return original if invalid
            
            a, b, c, d, e, f = params
            tolerance = 10 ** -precision
            
            # Check for identity matrix
            if (abs(a - 1) < tolerance and abs(b) < tolerance and 
                abs(c) < tolerance and abs(d - 1) < tolerance and 
                abs(e) < tolerance and abs(f) < tolerance):
                return ''  # Remove identity transform
            
            # Check for pure translation
            if (abs(a - 1) < tolerance and abs(b) < tolerance and 
                abs(c) < tolerance and abs(d - 1) < tolerance):
                if abs(f) < tolerance:
                    return f'translate({self._format_number(e, precision)})'
                else:
                    return f'translate({self._format_number(e, precision)},{self._format_number(f, precision)})'
            
            # Check for pure scaling
            if (abs(b) < tolerance and abs(c) < tolerance and 
                abs(e) < tolerance and abs(f) < tolerance):
                if abs(a - d) < tolerance:
                    return f'scale({self._format_number(a, precision)})'
                else:
                    return f'scale({self._format_number(a, precision)},{self._format_number(d, precision)})'
            
            # Check for pure rotation (no translation)
            if (abs(e) < tolerance and abs(f) < tolerance and 
                abs(a - d) < tolerance and abs(b + c) < tolerance):
                # Calculate angle from cos(θ) = a
                angle_rad = math.acos(max(-1, min(1, a)))
                if b < 0:
                    angle_rad = -angle_rad
                angle_deg = math.degrees(angle_rad)
                
                if abs(angle_deg) > tolerance:
                    return f'rotate({self._format_number(angle_deg, precision)})'
            
            # If we can't simplify, return original
            return match.group(0)
        
        result = re.sub(matrix_pattern, replace_matrix, transform_str)
        
        # Clean up empty transforms
        result = re.sub(r'\s+', ' ', result.strip())
        result = re.sub(r'^\s*$', '', result)
        
        return result
    
    def _format_number(self, num: float, precision: int) -> str:
        """Format number with appropriate precision."""
        if abs(num) < 10**-precision:
            return '0'
        if abs(num - round(num)) < 10**-precision:
            return str(int(round(num)))
        else:
            formatted = f"{num:.{precision}f}".rstrip('0').rstrip('.')
            return formatted if formatted else '0'


class RemoveEmptyDefsPlugin(PreprocessingPlugin):
    """Remove empty <defs> elements."""
    
    name = "removeEmptyDefs"
    description = "removes empty <defs> elements"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return element.tag.endswith('defs')
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        # Check if defs is empty (no children)
        if len(element) == 0:
            context.mark_for_removal(element)
            context.record_modification(self.name, "removed_empty_defs")
            return True
        
        # Check if defs contains only empty or whitespace-only text
        has_content = False
        for child in element:
            if child.tag or (child.text and child.text.strip()):
                has_content = True
                break
        
        if not has_content:
            context.mark_for_removal(element)
            context.record_modification(self.name, "removed_empty_defs")
            return True
        
        return False


class ConvertStyleToAttrsPlugin(PreprocessingPlugin):
    """Convert style attributes to presentation attributes."""
    
    name = "convertStyleToAttrs"
    description = "converts style to attributes"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return 'style' in element.attrib
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        style_attr = element.attrib.get('style', '')
        if not style_attr:
            return False
        
        try:
            # Parse style attribute
            style_props = self._parse_style(style_attr)
            
            # Convert to presentation attributes
            converted_any = False
            remaining_props = {}
            
            for prop, value in style_props.items():
                if self._can_convert_to_attr(prop):
                    # Convert to presentation attribute
                    element.set(prop, value)
                    converted_any = True
                else:
                    # Keep in style attribute
                    remaining_props[prop] = value
            
            # Update or remove style attribute
            if remaining_props:
                new_style = ';'.join([f"{k}:{v}" for k, v in remaining_props.items()])
                element.set('style', new_style)
            else:
                # Remove style attribute entirely
                del element.attrib['style']
            
            if converted_any:
                context.record_modification(self.name, "converted_style_to_attrs")
                return True
                
        except Exception as e:
            print(f"Style conversion failed: {e}")
        
        return False
    
    def _parse_style(self, style_str: str) -> Dict[str, str]:
        """Parse CSS style string into property-value dictionary."""
        props = {}
        
        for declaration in style_str.split(';'):
            declaration = declaration.strip()
            if ':' in declaration:
                prop, value = declaration.split(':', 1)
                prop = prop.strip()
                value = value.strip()
                if prop and value:
                    props[prop] = value
        
        return props
    
    def _can_convert_to_attr(self, prop: str) -> bool:
        """Check if CSS property can be converted to presentation attribute."""
        convertible_props = {
            'fill', 'stroke', 'stroke-width', 'stroke-opacity', 'fill-opacity',
            'opacity', 'stroke-dasharray', 'stroke-linecap', 'stroke-linejoin',
            'stroke-miterlimit', 'font-family', 'font-size', 'font-weight',
            'text-anchor', 'dominant-baseline', 'alignment-baseline'
        }
        
        return prop in convertible_props