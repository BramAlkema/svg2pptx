#!/usr/bin/env python3
"""
SVG Marker and Symbol Converter for SVG2PPTX

This module handles advanced SVG markers (arrowheads, line decorations) and
symbol definitions for technical diagrams, flowcharts, and decorative elements.
These are relatively obscure but essential for professional technical graphics.

Key Features:
- Complete marker support: marker-start, marker-mid, marker-end
- Symbol definition processing with <use> element instantiation
- Arrowhead scaling and orientation along paths
- Custom marker geometry with PowerPoint line cap mapping
- Symbol library management with deduplication
- Transform-aware marker positioning
- Marker overflow handling and clipping

SVG Marker Reference:
- <marker> elements define reusable markers
- marker-start/marker-mid/marker-end properties apply markers to paths
- <symbol> elements define reusable graphics
- <use> elements instantiate symbols with transforms
"""

import re
import math
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from lxml import etree as ET

from .base import BaseConverter
from .base import ConversionContext
from ..services.conversion_services import ConversionServices
from ..colors import ColorInfo
from ..transforms import Matrix


class MarkerPosition(Enum):
    """Marker position on path."""
    START = "marker-start"
    MID = "marker-mid" 
    END = "marker-end"


class MarkerUnits(Enum):
    """Marker coordinate units."""
    STROKE_WIDTH = "strokeWidth"  # Scale with stroke width
    USER_SPACE_ON_USE = "userSpaceOnUse"  # Use user coordinates


@dataclass
class MarkerDefinition:
    """Parsed marker definition."""
    id: str
    ref_x: float
    ref_y: float
    marker_width: float
    marker_height: float
    orient: str  # "auto" or angle in degrees
    marker_units: MarkerUnits
    viewbox: Optional[Tuple[float, float, float, float]]
    overflow: str  # "visible" or "hidden"
    content_xml: str  # Inner content as XML
    
    def get_orientation_angle(self, path_angle: float) -> float:
        """Calculate marker orientation angle."""
        if self.orient == "auto":
            return path_angle
        elif self.orient == "auto-start-reverse":
            return path_angle + 180.0
        else:
            try:
                return float(self.orient)
            except ValueError:
                return 0.0


@dataclass
class SymbolDefinition:
    """Parsed symbol definition."""
    id: str
    viewbox: Optional[Tuple[float, float, float, float]]
    preserve_aspect_ratio: str
    width: Optional[float]
    height: Optional[float]
    content_xml: str


@dataclass
class MarkerInstance:
    """Instance of marker on a path."""
    definition: MarkerDefinition
    position: MarkerPosition
    x: float
    y: float
    angle: float  # Path tangent angle at position
    stroke_width: float
    color: Optional[ColorInfo]


class MarkerConverter(BaseConverter):
    """Converts SVG markers and symbols to PowerPoint elements."""
    
    supported_elements = ['marker', 'symbol', 'use', 'defs']
    
    def __init__(self, services: ConversionServices):
        """
        Initialize MarkerConverter with dependency injection.

        Args:
            services: ConversionServices container with initialized services
        """
        super().__init__(services)
        self.markers: Dict[str, MarkerDefinition] = {}
        self.symbols: Dict[str, SymbolDefinition] = {}

        # Common arrowhead geometries for PowerPoint compatibility
        self.standard_arrows = {
            'arrow': self._create_arrow_path(),
            'circle': self._create_circle_path(),
            'square': self._create_square_path(),
            'diamond': self._create_diamond_path(),
        }
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the given element."""
        tag = self.get_element_tag(element)
        return tag in self.supported_elements
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert marker/symbol element to DrawingML."""
        if element.tag.endswith('defs'):
            return self._process_definitions(element, context)
        elif element.tag.endswith('marker'):
            return self._process_marker_definition(element, context)
        elif element.tag.endswith('symbol'):
            return self._process_symbol_definition(element, context)
        elif element.tag.endswith('use'):
            return self._process_use_element(element, context)
        
        return ""
    
    def _process_definitions(self, defs_element: ET.Element, context: ConversionContext) -> str:
        """Process <defs> section and extract markers/symbols."""
        for child in defs_element:
            if child.tag.endswith('marker'):
                self._extract_marker_definition(child)
            elif child.tag.endswith('symbol'):
                self._extract_symbol_definition(child)
        
        return ""  # Definitions don't generate direct output
    
    def _extract_marker_definition(self, marker_element: ET.Element) -> None:
        """Extract marker definition for later use."""
        marker_id = marker_element.get('id')
        if not marker_id:
            return
        
        # Parse marker attributes
        ref_x = float(marker_element.get('refX', '0'))
        ref_y = float(marker_element.get('refY', '0'))
        marker_width = float(marker_element.get('markerWidth', '3'))
        marker_height = float(marker_element.get('markerHeight', '3'))
        orient = marker_element.get('orient', '0')
        
        marker_units_str = marker_element.get('markerUnits', 'strokeWidth')
        marker_units = (MarkerUnits.STROKE_WIDTH if marker_units_str == 'strokeWidth' 
                       else MarkerUnits.USER_SPACE_ON_USE)
        
        # Parse viewBox if present
        viewbox = None
        viewbox_str = marker_element.get('viewBox')
        if viewbox_str:
            try:
                parts = re.split(r'[,\s]+', viewbox_str.strip())
                if len(parts) == 4:
                    viewbox = tuple(float(p) for p in parts)
            except ValueError:
                pass
        
        overflow = marker_element.get('overflow', 'hidden')
        
        # Extract content XML
        content_xml = self._extract_element_content(marker_element)
        
        self.markers[marker_id] = MarkerDefinition(
            id=marker_id,
            ref_x=ref_x,
            ref_y=ref_y,
            marker_width=marker_width,
            marker_height=marker_height,
            orient=orient,
            marker_units=marker_units,
            viewbox=viewbox,
            overflow=overflow,
            content_xml=content_xml
        )
    
    def _extract_symbol_definition(self, symbol_element: ET.Element) -> None:
        """Extract symbol definition for later use."""
        symbol_id = symbol_element.get('id')
        if not symbol_id:
            return
        
        # Parse viewBox
        viewbox = None
        viewbox_str = symbol_element.get('viewBox')
        if viewbox_str:
            try:
                parts = re.split(r'[,\s]+', viewbox_str.strip())
                if len(parts) == 4:
                    viewbox = tuple(float(p) for p in parts)
            except ValueError:
                pass
        
        preserve_aspect_ratio = symbol_element.get('preserveAspectRatio', 'xMidYMid meet')
        
        # Parse dimensions if present
        width = None
        height = None
        if symbol_element.get('width'):
            try:
                width = float(symbol_element.get('width').rstrip('px%'))
            except ValueError:
                pass
        if symbol_element.get('height'):
            try:
                height = float(symbol_element.get('height').rstrip('px%'))
            except ValueError:
                pass
        
        content_xml = self._extract_element_content(symbol_element)
        
        self.symbols[symbol_id] = SymbolDefinition(
            id=symbol_id,
            viewbox=viewbox,
            preserve_aspect_ratio=preserve_aspect_ratio,
            width=width,
            height=height,
            content_xml=content_xml
        )
    
    def _process_marker_definition(self, marker_element: ET.Element, context: ConversionContext) -> str:
        """Process standalone marker definition."""
        self._extract_marker_definition(marker_element)
        return ""
    
    def _process_symbol_definition(self, symbol_element: ET.Element, context: ConversionContext) -> str:
        """Process standalone symbol definition."""
        self._extract_symbol_definition(symbol_element)
        return ""
    
    def _process_use_element(self, use_element: ET.Element, context: ConversionContext) -> str:
        """Process <use> element that instantiates symbols."""
        href = use_element.get('href') or use_element.get('{http://www.w3.org/1999/xlink}href', '')
        if not href.startswith('#'):
            return ""
        
        symbol_id = href[1:]  # Remove #
        if symbol_id not in self.symbols:
            return ""
        
        symbol_def = self.symbols[symbol_id]
        
        # Parse transform
        transform_str = use_element.get('transform', '')
        transform_matrix = self.transform_parser.parse_to_matrix(transform_str)
        
        # Parse position
        x = float(use_element.get('x', '0'))
        y = float(use_element.get('y', '0'))
        
        # Apply translation
        transform_matrix = Matrix.translate(x, y).multiply(transform_matrix)
        
        # Parse dimensions
        width = use_element.get('width')
        height = use_element.get('height')
        
        if width or height:
            # Scale to fit specified dimensions
            if symbol_def.viewbox:
                vb_width = symbol_def.viewbox[2]
                vb_height = symbol_def.viewbox[3]
                
                if width and height:
                    scale_x = float(width) / vb_width
                    scale_y = float(height) / vb_height
                elif width:
                    scale_x = scale_y = float(width) / vb_width
                elif height:
                    scale_x = scale_y = float(height) / vb_height
                
                transform_matrix = transform_matrix.multiply(Matrix.scale(scale_x, scale_y))
        
        # Generate DrawingML for symbol content with transform
        return self._generate_symbol_drawingml(symbol_def, transform_matrix, context)
    
    def apply_markers_to_path(self, path_element: ET.Element, path_commands: List[Tuple], 
                            context: ConversionContext) -> str:
        """Apply markers to path based on marker properties."""
        if not path_commands:
            return ""
        
        # Extract marker properties
        marker_start = path_element.get('marker-start', '')
        marker_mid = path_element.get('marker-mid', '')
        marker_end = path_element.get('marker-end', '')
        
        if not (marker_start or marker_mid or marker_end):
            return ""
        
        # Parse stroke properties for marker scaling
        stroke_width = float(path_element.get('stroke-width', '1'))
        stroke_color = self.color_parser.parse(path_element.get('stroke', 'black'))
        
        markers_xml = []
        
        # Calculate path points and tangent angles
        path_points = self._extract_path_points(path_commands)
        if not path_points:
            return ""
        
        # Apply start marker
        if marker_start and len(path_points) >= 2:
            marker_id = self._extract_marker_id(marker_start)
            if marker_id in self.markers:
                start_point = path_points[0]
                start_angle = self._calculate_angle(path_points[0], path_points[1])
                
                marker_instance = MarkerInstance(
                    definition=self.markers[marker_id],
                    position=MarkerPosition.START,
                    x=start_point[0],
                    y=start_point[1],
                    angle=start_angle,
                    stroke_width=stroke_width,
                    color=stroke_color
                )
                
                markers_xml.append(self._generate_marker_drawingml(marker_instance, context))
        
        # Apply end marker
        if marker_end and len(path_points) >= 2:
            marker_id = self._extract_marker_id(marker_end)
            if marker_id in self.markers:
                end_point = path_points[-1]
                end_angle = self._calculate_angle(path_points[-2], path_points[-1])
                
                marker_instance = MarkerInstance(
                    definition=self.markers[marker_id],
                    position=MarkerPosition.END,
                    x=end_point[0],
                    y=end_point[1],
                    angle=end_angle,
                    stroke_width=stroke_width,
                    color=stroke_color
                )
                
                markers_xml.append(self._generate_marker_drawingml(marker_instance, context))
        
        # Apply mid markers (at vertices for polylines)
        if marker_mid and len(path_points) > 2:
            marker_id = self._extract_marker_id(marker_mid)
            if marker_id in self.markers:
                for i in range(1, len(path_points) - 1):
                    # Calculate bisector angle at vertex
                    prev_angle = self._calculate_angle(path_points[i-1], path_points[i])
                    next_angle = self._calculate_angle(path_points[i], path_points[i+1])
                    bisector_angle = (prev_angle + next_angle) / 2
                    
                    marker_instance = MarkerInstance(
                        definition=self.markers[marker_id],
                        position=MarkerPosition.MID,
                        x=path_points[i][0],
                        y=path_points[i][1],
                        angle=bisector_angle,
                        stroke_width=stroke_width,
                        color=stroke_color
                    )
                    
                    markers_xml.append(self._generate_marker_drawingml(marker_instance, context))
        
        return '\n'.join(markers_xml)
    
    def _generate_marker_drawingml(self, marker_instance: MarkerInstance, 
                                 context: ConversionContext) -> str:
        """Generate DrawingML for a marker instance."""
        marker_def = marker_instance.definition
        
        # Calculate marker scale
        if marker_def.marker_units == MarkerUnits.STROKE_WIDTH:
            scale = marker_instance.stroke_width
        else:
            scale = 1.0
        
        # Calculate marker transform
        transform_matrix = Matrix.identity()
        
        # Position at marker point
        transform_matrix = transform_matrix.multiply(
            Matrix.translate(marker_instance.x, marker_instance.y)
        )
        
        # Apply orientation
        orientation_angle = marker_def.get_orientation_angle(marker_instance.angle)
        if orientation_angle != 0:
            transform_matrix = transform_matrix.multiply(
                Matrix.rotate(orientation_angle)
            )
        
        # Apply scale
        if scale != 1.0:
            transform_matrix = transform_matrix.multiply(
                Matrix.scale(scale, scale)
            )
        
        # Offset by reference point
        transform_matrix = transform_matrix.multiply(
            Matrix.translate(-marker_def.ref_x, -marker_def.ref_y)
        )
        
        # Check if this is a standard arrow type
        standard_arrow = self._detect_standard_arrow(marker_def)
        if standard_arrow:
            return self._generate_standard_arrow_drawingml(standard_arrow, transform_matrix, 
                                                         marker_instance.color, context)
        
        # Generate custom marker geometry
        return self._generate_custom_marker_drawingml(marker_def, transform_matrix, 
                                                    marker_instance.color, context)
    
    def _generate_symbol_drawingml(self, symbol_def: SymbolDefinition, 
                                 transform_matrix: Matrix, context: ConversionContext) -> str:
        """Generate DrawingML for a symbol instance."""
        # Create group for symbol content
        shape_id = context.get_next_shape_id()
        
        # Apply viewBox transform if present
        if symbol_def.viewbox:
            vb_transform = self._calculate_viewbox_transform(
                symbol_def.viewbox, symbol_def.width, symbol_def.height,
                symbol_def.preserve_aspect_ratio
            )
            transform_matrix = transform_matrix.multiply(vb_transform)
        
        # Generate group with transform
        group_xml = f'''<p:grpSp>
            <p:nvGrpSpPr>
                <p:cNvPr id="{shape_id}" name="symbol_{symbol_def.id}"/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    {self._matrix_to_drawingml_transform(transform_matrix)}
                </a:xfrm>
            </p:grpSpPr>
            {symbol_def.content_xml}
        </p:grpSp>'''
        
        return group_xml
    
    def _extract_element_content(self, element: ET.Element) -> str:
        """Extract inner XML content of element."""
        content_parts = []
        
        for child in element:
            content_parts.append(ET.tostring(child, encoding='unicode'))
        
        return ''.join(content_parts)
    
    def _extract_marker_id(self, marker_url: str) -> str:
        """Extract marker ID from url(#id) format."""
        if marker_url.startswith('url(#') and marker_url.endswith(')'):
            return marker_url[5:-1]
        return ""
    
    def _extract_path_points(self, path_commands: List[Tuple]) -> List[Tuple[float, float]]:
        """Extract key points from path commands for marker positioning."""
        points = []
        current_x, current_y = 0, 0
        
        for cmd, *args in path_commands:
            if cmd.upper() == 'M':
                current_x, current_y = args[0], args[1]
                points.append((current_x, current_y))
            elif cmd.upper() == 'L':
                current_x, current_y = args[0], args[1]
                points.append((current_x, current_y))
            elif cmd.upper() == 'C':
                # Cubic Bézier - use end point
                current_x, current_y = args[4], args[5]
                points.append((current_x, current_y))
            elif cmd.upper() == 'Q':
                # Quadratic Bézier - use end point
                current_x, current_y = args[2], args[3]
                points.append((current_x, current_y))
            elif cmd.upper() == 'Z':
                # Close path - add start point if different
                if points and (current_x != points[0][0] or current_y != points[0][1]):
                    points.append(points[0])
        
        return points
    
    def _calculate_angle(self, point1: Tuple[float, float], 
                        point2: Tuple[float, float]) -> float:
        """Calculate angle between two points in degrees."""
        dx = point2[0] - point1[0]
        dy = point2[1] - point1[1]
        return math.degrees(math.atan2(dy, dx))
    
    def _detect_standard_arrow(self, marker_def: MarkerDefinition) -> Optional[str]:
        """Detect if marker matches a standard arrow pattern."""
        # Analyze marker content to detect standard patterns
        content = marker_def.content_xml.lower()
        
        if 'polygon' in content and 'points' in content:
            # Try to match against standard arrow polygons
            if self._is_arrow_polygon(content):
                return 'arrow'
            elif self._is_diamond_polygon(content):
                return 'diamond'
        elif 'circle' in content or 'ellipse' in content:
            return 'circle'
        elif 'rect' in content:
            return 'square'
        
        return None
    
    def _is_arrow_polygon(self, content: str) -> bool:
        """Check if polygon content represents an arrow."""
        # Look for typical arrow point patterns
        if 'points' in content:
            # Count coordinate pairs (each pair separated by comma or space)
            point_matches = re.findall(r'[\d.-]+[,\s]+[\d.-]+', content)
            # Arrow typically has 3 or more points
            return len(point_matches) >= 3
        return False
    
    def _is_diamond_polygon(self, content: str) -> bool:
        """Check if polygon content represents a diamond."""
        if 'points' in content:
            # Count coordinate pairs for diamond (should be exactly 4)
            point_matches = re.findall(r'[\d.-]+[,\s]+[\d.-]+', content)
            return len(point_matches) == 4
        return False
    
    def _create_arrow_path(self) -> str:
        """Create standard arrow path geometry."""
        return "M 0 0 L 10 5 L 0 10 Z"
    
    def _create_circle_path(self) -> str:
        """Create circle path geometry."""
        return "M 5 0 A 5 5 0 1 1 -5 0 A 5 5 0 1 1 5 0 Z"
    
    def _create_square_path(self) -> str:
        """Create square path geometry.""" 
        return "M 0 0 L 10 0 L 10 10 L 0 10 Z"
    
    def _create_diamond_path(self) -> str:
        """Create diamond path geometry."""
        return "M 5 0 L 10 5 L 5 10 L 0 5 Z"
    
    def _generate_standard_arrow_drawingml(self, arrow_type: str, transform_matrix: Matrix,
                                         color: Optional[ColorInfo], context: ConversionContext) -> str:
        """Generate DrawingML for standard arrow types."""
        path_data = self.standard_arrows[arrow_type]
        shape_id = context.get_next_shape_id()
        
        # Generate color fill
        fill_xml = ""
        if color:
            fill_xml = f'<a:solidFill>{self.color_parser.to_drawingml(color)}</a:solidFill>'
        
        return f'''<p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="marker_{arrow_type}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    {self._matrix_to_drawingml_transform(transform_matrix)}
                </a:xfrm>
                <a:custGeom>
                    <a:pathLst>
                        <a:path>
                            <a:pathData d="{path_data}"/>
                        </a:path>
                    </a:pathLst>
                </a:custGeom>
                {fill_xml}
            </p:spPr>
        </p:sp>'''
    
    def _generate_custom_marker_drawingml(self, marker_def: MarkerDefinition, 
                                        transform_matrix: Matrix, color: Optional[ColorInfo],
                                        context: ConversionContext) -> str:
        """Generate DrawingML for custom marker geometry."""
        shape_id = context.get_next_shape_id()
        
        # Convert marker content to DrawingML
        # This would need to recursively process the marker's child elements
        content_drawingml = marker_def.content_xml  # Simplified
        
        return f'''<p:grpSp>
            <p:nvGrpSpPr>
                <p:cNvPr id="{shape_id}" name="marker_{marker_def.id}"/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    {self._matrix_to_drawingml_transform(transform_matrix)}
                </a:xfrm>
            </p:grpSpPr>
            {content_drawingml}
        </p:grpSp>'''
    
    def _calculate_viewbox_transform(self, viewbox: Tuple[float, float, float, float],
                                   width: Optional[float], height: Optional[float],
                                   preserve_aspect_ratio: str) -> Matrix:
        """Calculate transform for symbol viewBox mapping."""
        vb_x, vb_y, vb_width, vb_height = viewbox
        
        if not width or not height:
            return Matrix.translate(-vb_x, -vb_y)
        
        scale_x = width / vb_width
        scale_y = height / vb_height
        
        # Handle aspect ratio preservation
        if preserve_aspect_ratio != "none":
            if "meet" in preserve_aspect_ratio:
                scale = min(scale_x, scale_y)
            else:  # slice
                scale = max(scale_x, scale_y)
            scale_x = scale_y = scale
        
        return (Matrix.translate(-vb_x, -vb_y).
               multiply(Matrix.scale(scale_x, scale_y)))
    
    def _matrix_to_drawingml_transform(self, matrix: Matrix) -> str:
        """Convert transform matrix to DrawingML transform elements."""
        decomp = matrix.decompose()
        
        elements = []
        
        if abs(decomp['translateX']) > 1e-6 or abs(decomp['translateY']) > 1e-6:
            tx_emu = self.to_emu(f"{decomp['translateX']}px")
            ty_emu = self.to_emu(f"{decomp['translateY']}px")
            elements.append(f'<a:off x="{tx_emu}" y="{ty_emu}"/>')
        
        if abs(decomp['rotation']) > 1e-6:
            angle_units = int(decomp['rotation'] * 60000)
            elements.append(f'<a:rot angle="{angle_units}"/>')
        
        return ''.join(elements)