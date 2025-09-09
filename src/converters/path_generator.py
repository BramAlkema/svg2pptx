"""
Path Generator for SVG Text-to-Path Conversion

This module converts font glyph outlines to PowerPoint DrawingML path format,
handling coordinate transformations, path optimization, and DrawingML compliance.

Key Features:
- Convert fontTools glyph outlines to SVG path format
- Transform SVG paths to PowerPoint DrawingML path syntax
- Coordinate system transformation and scaling
- Path optimization (curve smoothing, point reduction)
- Unicode and special character support
"""

import re
import math
from typing import List, Tuple, Optional, Dict, Any, NamedTuple
from dataclasses import dataclass
import logging

from .font_metrics import GlyphOutline, FontMetrics


logger = logging.getLogger(__name__)


class PathPoint(NamedTuple):
    """Represents a point in a path with coordinates"""
    x: float
    y: float


@dataclass
class PathCommand:
    """Represents a path command with operation and coordinates"""
    command: str  # moveTo, lineTo, curveTo, closePath
    points: List[PathPoint]
    
    def to_drawingml(self, scale: float = 1.0) -> str:
        """Convert to DrawingML path command format"""
        scaled_points = [PathPoint(p.x * scale, p.y * scale) for p in self.points]
        
        if self.command == 'moveTo':
            if scaled_points:
                return f'<a:moveTo><a:pt x="{int(scaled_points[0].x)}" y="{int(scaled_points[0].y)}"/></a:moveTo>'
        elif self.command == 'lineTo':
            if scaled_points:
                return f'<a:lnTo><a:pt x="{int(scaled_points[0].x)}" y="{int(scaled_points[0].y)}"/></a:lnTo>'
        elif self.command == 'curveTo':
            if len(scaled_points) == 3:
                # Cubic Bézier curve
                return f'''<a:cubicBezTo>
    <a:pt x="{int(scaled_points[0].x)}" y="{int(scaled_points[0].y)}"/>
    <a:pt x="{int(scaled_points[1].x)}" y="{int(scaled_points[1].y)}"/>
    <a:pt x="{int(scaled_points[2].x)}" y="{int(scaled_points[2].y)}"/>
</a:cubicBezTo>'''
            elif len(scaled_points) == 2:
                # Quadratic Bézier to cubic conversion
                # Q(t) = (1-t)²P₀ + 2(1-t)tP₁ + t²P₂
                # Convert to cubic: CP₁ = P₀ + 2/3(P₁ - P₀), CP₂ = P₂ + 2/3(P₁ - P₂)
                # For this we need the current point, which we don't have here
                # For now, treat as simple curve
                return f'''<a:cubicBezTo>
    <a:pt x="{int(scaled_points[0].x)}" y="{int(scaled_points[0].y)}"/>
    <a:pt x="{int(scaled_points[1].x)}" y="{int(scaled_points[1].y)}"/>
    <a:pt x="{int(scaled_points[1].x)}" y="{int(scaled_points[1].y)}"/>
</a:cubicBezTo>'''
        elif self.command == 'closePath':
            return '<a:close/>'
        
        return ''


class PathGenerator:
    """
    Generates PowerPoint DrawingML paths from font glyph outlines.
    
    Handles the conversion from fontTools glyph data to PowerPoint-compatible
    vector paths with proper coordinate transformations and optimizations.
    """
    
    # DrawingML coordinate system constants
    EMU_PER_INCH = 914400
    POINTS_PER_INCH = 72
    EMU_PER_POINT = EMU_PER_INCH / POINTS_PER_INCH  # ~12700 EMUs per point
    
    def __init__(self, optimization_level: int = 1):
        """
        Initialize PathGenerator with optimization settings.
        
        Args:
            optimization_level: Path optimization level (0=none, 1=basic, 2=aggressive)
        """
        self.optimization_level = optimization_level
    
    def generate_path_from_glyph(self, glyph_outline: GlyphOutline, x_offset: float = 0, 
                                y_offset: float = 0, scale: float = 1.0) -> Optional[str]:
        """
        Generate DrawingML path from glyph outline.
        
        Args:
            glyph_outline: GlyphOutline object from FontMetricsAnalyzer
            x_offset: X coordinate offset in points
            y_offset: Y coordinate offset in points
            scale: Additional scaling factor
            
        Returns:
            DrawingML path string or None if generation fails
        """
        if not glyph_outline or not glyph_outline.path_data:
            return None
        
        try:
            # Convert glyph outline to path commands
            path_commands = self._convert_glyph_to_commands(glyph_outline.path_data)
            
            if not path_commands:
                return None
            
            # Apply transformations
            transformed_commands = self._apply_transformations(
                path_commands, x_offset, y_offset, scale
            )
            
            # Optimize paths if requested
            if self.optimization_level > 0:
                transformed_commands = self._optimize_path_commands(transformed_commands)
            
            # Generate DrawingML
            return self._generate_drawingml_path(transformed_commands)
            
        except Exception as e:
            logger.error(f"Failed to generate path for glyph {glyph_outline.glyph_name}: {e}")
            return None
    
    def generate_text_path(self, text: str, font_metrics_analyzer, font_family: str,
                          font_size: float, x: float = 0, y: float = 0,
                          font_style: str = 'normal', font_weight: int = 400) -> Optional[str]:
        """
        Generate DrawingML path for entire text string.
        
        Args:
            text: Text to convert to path
            font_metrics_analyzer: FontMetricsAnalyzer instance
            font_family: Font family name
            font_size: Font size in points
            x: X position in points
            y: Y position in points
            font_style: Font style ('normal', 'italic', 'oblique')
            font_weight: Font weight (100-900)
            
        Returns:
            DrawingML group shape with text paths or None if generation fails
        """
        if not text:
            return None
        
        try:
            # Get font metrics for proper positioning
            font_metrics = font_metrics_analyzer.get_font_metrics(font_family, font_style, font_weight)
            if not font_metrics:
                logger.warning(f"Could not get metrics for font {font_family}")
                return None
            
            # Calculate baseline offset
            baseline_offset = y + (font_metrics.ascender * font_size / font_metrics.units_per_em)
            
            # Generate paths for each character
            char_paths = []
            current_x = x
            
            for char in text:
                if char.isspace():
                    # Handle spaces with advance width
                    space_width = font_size * 0.25  # Approximate space width
                    current_x += space_width
                    continue
                
                # Get glyph outline
                glyph_outline = font_metrics_analyzer.get_glyph_outline(
                    font_family, char, font_size, font_style, font_weight
                )
                
                if glyph_outline:
                    # Generate path for this character
                    char_path = self.generate_path_from_glyph(
                        glyph_outline, current_x, baseline_offset
                    )
                    
                    if char_path:
                        char_paths.append(char_path)
                    
                    # Advance to next character position
                    current_x += glyph_outline.advance_width
                else:
                    logger.warning(f"Could not get glyph outline for character '{char}'")
                    # Use approximate advance for missing characters
                    current_x += font_size * 0.6
            
            # Combine all character paths into a group
            if char_paths:
                return self._create_text_group_shape(char_paths, x, y, current_x - x, font_size)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate text path for '{text}': {e}")
            return None
    
    def _convert_glyph_to_commands(self, glyph_path_data: List[Tuple[str, Tuple]]) -> List[PathCommand]:
        """Convert fontTools glyph path data to PathCommand objects."""
        commands = []
        
        for operation, coords in glyph_path_data:
            if operation == 'moveTo':
                if coords:
                    commands.append(PathCommand('moveTo', [PathPoint(coords[0][0], coords[0][1])]))
            
            elif operation == 'lineTo':
                if coords:
                    commands.append(PathCommand('lineTo', [PathPoint(coords[0][0], coords[0][1])]))
            
            elif operation == 'curveTo':
                if len(coords) >= 3:
                    # Cubic Bézier curve
                    points = [PathPoint(pt[0], pt[1]) for pt in coords]
                    commands.append(PathCommand('curveTo', points))
                elif len(coords) == 2:
                    # Quadratic Bézier curve (convert to cubic later)
                    points = [PathPoint(pt[0], pt[1]) for pt in coords]
                    commands.append(PathCommand('curveTo', points))
            
            elif operation == 'qCurveTo':
                # Quadratic curve
                if len(coords) >= 2:
                    points = [PathPoint(pt[0], pt[1]) for pt in coords]
                    commands.append(PathCommand('curveTo', points))
            
            elif operation == 'closePath':
                commands.append(PathCommand('closePath', []))
        
        return commands
    
    def _apply_transformations(self, commands: List[PathCommand], x_offset: float, 
                              y_offset: float, scale: float) -> List[PathCommand]:
        """Apply coordinate transformations to path commands."""
        transformed = []
        
        for cmd in commands:
            if cmd.command == 'closePath':
                transformed.append(cmd)
            else:
                # Apply offset and scaling
                new_points = []
                for point in cmd.points:
                    new_x = (point.x * scale) + x_offset
                    new_y = (point.y * scale) + y_offset
                    new_points.append(PathPoint(new_x, new_y))
                
                transformed.append(PathCommand(cmd.command, new_points))
        
        return transformed
    
    def _optimize_path_commands(self, commands: List[PathCommand]) -> List[PathCommand]:
        """Optimize path commands based on optimization level."""
        if self.optimization_level == 0:
            return commands
        
        optimized = []
        
        # Basic optimization: remove redundant points
        prev_cmd = None
        for cmd in commands:
            if cmd.command == 'closePath':
                optimized.append(cmd)
            elif cmd.command in ['moveTo', 'lineTo'] and prev_cmd:
                # Skip if same point as previous
                if (prev_cmd.command in ['moveTo', 'lineTo'] and 
                    cmd.points and prev_cmd.points and
                    self._points_equal(cmd.points[0], prev_cmd.points[0])):
                    continue
                optimized.append(cmd)
            else:
                optimized.append(cmd)
            
            prev_cmd = cmd
        
        # Advanced optimization for level 2
        if self.optimization_level >= 2:
            optimized = self._advanced_path_optimization(optimized)
        
        return optimized
    
    def _advanced_path_optimization(self, commands: List[PathCommand]) -> List[PathCommand]:
        """Advanced path optimization techniques."""
        # Implement curve smoothing and point reduction
        # This is a simplified version - more sophisticated algorithms could be added
        optimized = []
        
        for i, cmd in enumerate(commands):
            if cmd.command == 'curveTo' and len(cmd.points) >= 3:
                # Simplify curves with minimal curvature
                p1, p2, p3 = cmd.points[:3]
                if self._is_nearly_straight_curve(p1, p2, p3):
                    # Convert to line
                    optimized.append(PathCommand('lineTo', [p3]))
                else:
                    optimized.append(cmd)
            else:
                optimized.append(cmd)
        
        return optimized
    
    def _generate_drawingml_path(self, commands: List[PathCommand]) -> str:
        """Generate final DrawingML path string."""
        if not commands:
            return ""
        
        # Calculate bounding box for path dimensions
        min_x, min_y, max_x, max_y = self._calculate_path_bounds(commands)
        
        # Convert coordinates to EMUs
        scale_factor = self.EMU_PER_POINT
        
        # Generate path elements
        path_elements = []
        for cmd in commands:
            element = cmd.to_drawingml(scale_factor)
            if element:
                path_elements.append(element)
        
        # Create complete DrawingML path shape
        width_emu = int((max_x - min_x) * scale_factor)
        height_emu = int((max_y - min_y) * scale_factor)
        x_emu = int(min_x * scale_factor)
        y_emu = int(min_y * scale_factor)
        
        return f'''<a:sp>
    <a:nvSpPr>
        <a:cNvPr id="{{shape_id}}" name="TextPath"/>
        <a:cNvSpPr/>
    </a:nvSpPr>
    <a:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
        <a:custGeom>
            <a:avLst/>
            <a:gdLst/>
            <a:ahLst/>
            <a:cxnLst/>
            <a:rect l="0" t="0" r="0" b="0"/>
            <a:pathLst>
                <a:path w="{width_emu}" h="{height_emu}">
                    {''.join(path_elements)}
                </a:path>
            </a:pathLst>
        </a:custGeom>
        {{fill_style}}
        <a:ln><a:noFill/></a:ln>
    </a:spPr>
</a:sp>'''
    
    def _create_text_group_shape(self, char_paths: List[str], x: float, y: float, 
                                width: float, height: float) -> str:
        """Create a group shape containing all character paths."""
        # Convert to EMUs
        x_emu = int(x * self.EMU_PER_POINT)
        y_emu = int(y * self.EMU_PER_POINT)
        width_emu = int(width * self.EMU_PER_POINT)
        height_emu = int(height * self.EMU_PER_POINT)
        
        # Replace placeholders in character paths
        numbered_paths = []
        for i, path in enumerate(char_paths):
            numbered_path = path.replace('{shape_id}', f'{{shape_id}}_{i}')
            numbered_path = numbered_path.replace('{fill_style}', '<a:solidFill><a:srgbClr val="{fill_color}"/></a:solidFill>')
            numbered_paths.append(numbered_path)
        
        return f'''<a:grpSp>
    <a:nvGrpSpPr>
        <a:cNvPr id="{{shape_id}}" name="TextGroup"/>
        <a:cNvGrpSpPr/>
    </a:nvGrpSpPr>
    <a:grpSpPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
            <a:chOff x="0" y="0"/>
            <a:chExt cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
    </a:grpSpPr>
    {''.join(numbered_paths)}
</a:grpSp>'''
    
    def _calculate_path_bounds(self, commands: List[PathCommand]) -> Tuple[float, float, float, float]:
        """Calculate bounding box of path commands."""
        if not commands:
            return 0, 0, 100, 100
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for cmd in commands:
            for point in cmd.points:
                min_x = min(min_x, point.x)
                max_x = max(max_x, point.x)
                min_y = min(min_y, point.y)
                max_y = max(max_y, point.y)
        
        # Ensure positive dimensions
        if min_x == float('inf'):
            return 0, 0, 100, 100
        
        return min_x, min_y, max_x, max_y
    
    def _points_equal(self, p1: PathPoint, p2: PathPoint, tolerance: float = 0.1) -> bool:
        """Check if two points are equal within tolerance."""
        return abs(p1.x - p2.x) < tolerance and abs(p1.y - p2.y) < tolerance
    
    def _is_nearly_straight_curve(self, p1: PathPoint, p2: PathPoint, p3: PathPoint, 
                                 tolerance: float = 1.0) -> bool:
        """Check if a cubic curve is nearly straight."""
        # Calculate distance from control point to line between endpoints
        line_length = math.sqrt((p3.x - p1.x)**2 + (p3.y - p1.y)**2)
        
        if line_length < 1e-6:  # Avoid division by zero
            return True
        
        # Distance from p2 to line p1-p3
        distance = abs((p3.y - p1.y) * p2.x - (p3.x - p1.x) * p2.y + p3.x * p1.y - p3.y * p1.x) / line_length
        
        return distance < tolerance
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get statistics about path optimization."""
        return {
            'optimization_level': self.optimization_level,
            'emu_per_point': self.EMU_PER_POINT,
            'points_per_inch': self.POINTS_PER_INCH,
            'emu_per_inch': self.EMU_PER_INCH
        }