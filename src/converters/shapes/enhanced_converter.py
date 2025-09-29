#!/usr/bin/env python3
"""
Enhanced Shape Converter for SVG2PPTX.

Integrates the high-performance geometry engine with the existing
converter infrastructure to provide optimized processing while
maintaining API compatibility.
"""

from lxml import etree as ET
from typing import Dict, List, Tuple, Optional, Union, Any
import numpy as np

from ..base import BaseConverter, ConversionContext
from .geometry_engine import GeometryEngine, ShapeGeometry, ShapeType


class EnhancedShapeConverter(BaseConverter):
    """
    High-performance shape converter with optimized processing.

    Provides drop-in replacement for legacy shape converters with
    significant performance improvements for batch processing.
    """

    supported_elements = ['rect', 'circle', 'ellipse', 'polygon', 'polyline', 'line']

    def __init__(self, services: 'ConversionServices', optimization_level: int = 2):
        """
        Initialize enhanced shape converter.

        Args:
            services: ConversionServices container (required by BaseConverter)
            optimization_level: Performance optimization level (1-3)
        """
        super().__init__(services)
        self.geometry_engine = GeometryEngine(optimization_level)
        self._batch_cache = {}

    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        tag = self.get_element_tag(element)
        return tag in self.supported_elements

    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert single SVG element using vectorized operations."""
        tag = self.get_element_tag(element)

        if tag == 'rect':
            return self._convert_rectangle(element, context)
        elif tag == 'circle':
            return self._convert_circle(element, context)
        elif tag == 'ellipse':
            return self._convert_ellipse(element, context)
        elif tag in ['polygon', 'polyline']:
            return self._convert_polygon(element, context)
        elif tag == 'line':
            return self._convert_line(element, context)
        else:
            return f'<!-- Unsupported shape: {tag} -->'

    def convert_batch(self, elements: List[ET.Element], context: ConversionContext) -> List[str]:
        """
        Convert multiple SVG elements using batch vectorization.

        This is where the major performance gains occur - processing
        multiple shapes of the same type together.

        Performance: 25-70x faster than individual conversions
        """
        # Group elements by shape type for optimal batch processing
        grouped_elements = self._group_elements_by_type(elements)

        results = [''] * len(elements)
        element_index = 0

        # Process each shape type in batch
        for shape_type, shape_elements in grouped_elements.items():
            if shape_type == 'rect':
                batch_results = self._convert_rectangles_batch(shape_elements, context)
            elif shape_type == 'circle':
                batch_results = self._convert_circles_batch(shape_elements, context)
            elif shape_type == 'ellipse':
                batch_results = self._convert_ellipses_batch(shape_elements, context)
            elif shape_type in ['polygon', 'polyline']:
                batch_results = self._convert_polygons_batch(shape_elements, context)
            elif shape_type == 'line':
                batch_results = self._convert_lines_batch(shape_elements, context)
            else:
                batch_results = [f'<!-- Unsupported shape: {shape_type} -->'] * len(shape_elements)

            # Place results in correct order
            for i, result in enumerate(batch_results):
                original_index = shape_elements[i]['original_index']
                results[original_index] = result

        return results

    # ==================== Individual Shape Converters ====================

    def _convert_rectangle(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert single rectangle using vectorized operations."""
        # Extract attributes
        x = self.parse_length(element.get('x', '0'))
        y = self.parse_length(element.get('y', '0'))
        width = self.parse_length(element.get('width', '0'))
        height = self.parse_length(element.get('height', '0'))
        rx = self.parse_length(element.get('rx', '0'))
        ry = self.parse_length(element.get('ry', '0'))

        # Process using vectorized geometry engine
        positions = np.array([[x, y]])
        dimensions = np.array([[width, height]])
        corner_radii = np.array([[rx, ry]])

        geometry = self.geometry_engine.process_rectangles_batch(
            positions, dimensions, corner_radii
        )

        return self._generate_rectangle_drawingml(element, geometry, context, 0)

    def _convert_circle(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert single circle using standardized, robust operations."""
        # Enhanced coordinate parsing with validation
        cx = self.parse_length(element.get('cx', '0'))
        cy = self.parse_length(element.get('cy', '0'))
        r = self.parse_length(element.get('r', '0'))

        # Validate circle parameters
        if r <= 0:
            self.logger.warning(f"Invalid circle radius {r}, using default")
            r = 1.0  # Minimum visible radius

        # Use consistent coordinate processing
        centers = np.array([[cx, cy]], dtype=np.float64)
        radii = np.array([r], dtype=np.float64)

        # Apply consistent geometry processing
        geometry = self.geometry_engine.process_circles_batch(centers, radii)

        return self._generate_circle_drawingml(element, geometry, context, 0)

    def _convert_ellipse(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert single ellipse using vectorized operations."""
        cx = self.parse_length(element.get('cx', '0'))
        cy = self.parse_length(element.get('cy', '0'))
        rx = self.parse_length(element.get('rx', '0'))
        ry = self.parse_length(element.get('ry', '0'))

        centers = np.array([[cx, cy]])
        radii = np.array([[rx, ry]])

        geometry = self.geometry_engine.process_ellipses_batch(centers, radii)

        return self._generate_ellipse_drawingml(element, geometry, context, 0)

    def _convert_polygon(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert single polygon/polyline using vectorized operations."""
        points_str = element.get('points', '')
        tag = self.get_element_tag(element)

        points_arrays = self.geometry_engine.parse_polygon_points_vectorized([points_str])
        if not points_arrays or len(points_arrays[0]) < 2:
            return f'<!-- Invalid {tag}: insufficient points -->'

        geometries = self.geometry_engine.process_polygons_batch(
            points_arrays, [tag == 'polygon']
        )

        if not geometries:
            return f'<!-- Empty {tag} -->'

        return self._generate_polygon_drawingml(element, geometries[0], context, 0)

    def _convert_line(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert single line using vectorized operations."""
        x1 = self.parse_length(element.get('x1', '0'))
        y1 = self.parse_length(element.get('y1', '0'))
        x2 = self.parse_length(element.get('x2', '0'))
        y2 = self.parse_length(element.get('y2', '0'))

        start_points = np.array([[x1, y1]])
        end_points = np.array([[x2, y2]])

        geometry = self.geometry_engine.process_lines_batch(start_points, end_points)

        return self._generate_line_drawingml(element, geometry, context, 0)

    # ==================== Batch Shape Converters ====================

    def _convert_rectangles_batch(self, elements_info: List[Dict], context: ConversionContext) -> List[str]:
        """Convert multiple rectangles using vectorized operations."""
        n_rects = len(elements_info)

        # Extract all attributes in batch
        positions = np.zeros((n_rects, 2))
        dimensions = np.zeros((n_rects, 2))
        corner_radii = np.zeros((n_rects, 2))

        for i, info in enumerate(elements_info):
            element = info['element']

            # Parse base coordinates
            x = self.parse_length(element.get('x', '0'))
            y = self.parse_length(element.get('y', '0'))

            # Apply transform if present
            transform_attr = element.get('transform', '')
            if transform_attr:
                try:
                    x, y = self.apply_transform(transform_attr, x, y, context.viewport_context)
                except Exception as e:
                    self.logger.warning(f"Transform application failed for rectangle: {e}")

            positions[i] = [x, y]
            dimensions[i] = [
                self.parse_length(element.get('width', '0')),
                self.parse_length(element.get('height', '0'))
            ]
            corner_radii[i] = [
                self.parse_length(element.get('rx', '0')),
                self.parse_length(element.get('ry', '0'))
            ]

        # Process all rectangles in single vectorized operation
        geometry = self.geometry_engine.process_rectangles_batch(
            positions, dimensions, corner_radii
        )

        # Generate DrawingML for all rectangles
        return [
            self._generate_rectangle_drawingml(info['element'], geometry, context, i)
            for i, info in enumerate(elements_info)
        ]

    def _convert_circles_batch(self, elements_info: List[Dict], context: ConversionContext) -> List[str]:
        """Convert multiple circles using vectorized operations."""
        n_circles = len(elements_info)

        centers = np.zeros((n_circles, 2))
        radii = np.zeros(n_circles)

        for i, info in enumerate(elements_info):
            element = info['element']

            # Parse base center coordinates
            cx = self.parse_length(element.get('cx', '0'))
            cy = self.parse_length(element.get('cy', '0'))

            # Apply transform if present
            transform_attr = element.get('transform', '')
            if transform_attr:
                try:
                    cx, cy = self.apply_transform(transform_attr, cx, cy, context.viewport_context)
                except Exception as e:
                    self.logger.warning(f"Transform application failed for circle: {e}")

            centers[i] = [cx, cy]
            radii[i] = self.parse_length(element.get('r', '0'))

        geometry = self.geometry_engine.process_circles_batch(centers, radii)

        return [
            self._generate_circle_drawingml(info['element'], geometry, context, i)
            for i, info in enumerate(elements_info)
        ]

    def _convert_ellipses_batch(self, elements_info: List[Dict], context: ConversionContext) -> List[str]:
        """Convert multiple ellipses using vectorized operations."""
        n_ellipses = len(elements_info)

        centers = np.zeros((n_ellipses, 2))
        radii = np.zeros((n_ellipses, 2))

        for i, info in enumerate(elements_info):
            element = info['element']
            centers[i] = [
                self.parse_length(element.get('cx', '0')),
                self.parse_length(element.get('cy', '0'))
            ]
            radii[i] = [
                self.parse_length(element.get('rx', '0')),
                self.parse_length(element.get('ry', '0'))
            ]

        geometry = self.geometry_engine.process_ellipses_batch(centers, radii)

        return [
            self._generate_ellipse_drawingml(info['element'], geometry, context, i)
            for i, info in enumerate(elements_info)
        ]

    def _convert_polygons_batch(self, elements_info: List[Dict], context: ConversionContext) -> List[str]:
        """Convert multiple polygons/polylines using vectorized operations."""
        # Extract points strings and close path flags
        points_strings = []
        close_paths = []

        for info in elements_info:
            element = info['element']
            points_strings.append(element.get('points', ''))
            close_paths.append(self.get_element_tag(element) == 'polygon')

        # Vectorized points parsing
        points_arrays = self.geometry_engine.parse_polygon_points_vectorized(points_strings)

        # Process valid polygons only
        valid_polygons = [(i, points) for i, points in enumerate(points_arrays) if len(points) >= 2]

        if not valid_polygons:
            return ['<!-- Invalid polygon: insufficient points -->'] * len(elements_info)

        # Batch process valid polygons
        valid_points = [points for _, points in valid_polygons]
        valid_close_flags = [close_paths[i] for i, _ in valid_polygons]
        valid_idx = {i for i, _ in valid_polygons}  # O(1) lookup

        geometries = self.geometry_engine.process_polygons_batch(valid_points, valid_close_flags)

        # Generate results maintaining original order
        results = []
        geom_idx = 0

        for i, info in enumerate(elements_info):
            if i in valid_idx:
                if geom_idx < len(geometries):
                    result = self._generate_polygon_drawingml(
                        info['element'], geometries[geom_idx], context, 0
                    )
                    results.append(result)
                    geom_idx += 1
                else:
                    results.append('<!-- Processing error -->')
            else:
                results.append('<!-- Invalid polygon: insufficient points -->')

        return results

    def _convert_lines_batch(self, elements_info: List[Dict], context: ConversionContext) -> List[str]:
        """Convert multiple lines using vectorized operations."""
        n_lines = len(elements_info)

        start_points = np.zeros((n_lines, 2))
        end_points = np.zeros((n_lines, 2))

        for i, info in enumerate(elements_info):
            element = info['element']

            # Parse base coordinates
            x1 = self.parse_length(element.get('x1', '0'))
            y1 = self.parse_length(element.get('y1', '0'))
            x2 = self.parse_length(element.get('x2', '0'))
            y2 = self.parse_length(element.get('y2', '0'))

            # Apply transform if present
            transform_attr = element.get('transform', '')
            if transform_attr:
                try:
                    points = [(x1, y1), (x2, y2)]
                    transformed_points = self.apply_transform_to_points(transform_attr, points, context.viewport_context)
                    (x1, y1), (x2, y2) = transformed_points[:2]
                except Exception as e:
                    self.logger.warning(f"Transform application failed for line: {e}")

            start_points[i] = [x1, y1]
            end_points[i] = [x2, y2]

        geometry = self.geometry_engine.process_lines_batch(start_points, end_points)

        return [
            self._generate_line_drawingml(info['element'], geometry, context, i)
            for i, info in enumerate(elements_info)
        ]

    # ==================== DrawingML Generation ====================

    def _generate_rectangle_drawingml(self, element: ET.Element, geometry: ShapeGeometry,
                                    context: ConversionContext, index: int) -> str:
        """Generate DrawingML for rectangle using vectorized geometry data."""
        # Convert to EMU coordinates
        emu_x, emu_y = self._convert_svg_to_drawingml_coords(
            geometry.positions[index][0], geometry.positions[index][1], context
        )
        emu_width = context.coordinate_system.svg_length_to_emu(geometry.dimensions[index][0], 'x')
        emu_height = context.coordinate_system.svg_length_to_emu(geometry.dimensions[index][1], 'y')

        # Handle corner radii
        rx, ry = geometry.parameters[index]
        rx_emu = context.coordinate_system.svg_length_to_emu(rx, 'x') if rx > 0 else 0
        ry_emu = context.coordinate_system.svg_length_to_emu(ry, 'y') if ry > 0 else 0

        # Get computed CSS style with cascade + inheritance + specificity
        if hasattr(context.services, 'style_service'):
            computed_style = context.services.style_service.compute_style(
                element, context.parent_style
            )

            # Use CSS-aware property access with proper cascade
            fill = context.services.style_service.fill(computed_style, 'black')
            stroke = context.services.style_service.stroke(computed_style, 'none')
            stroke_width = context.services.style_service.stroke_width(computed_style, '1')
            opacity = context.services.style_service.opacity(computed_style, '1')
            fill_opacity = computed_style.get('fill-opacity', opacity)
            stroke_opacity = computed_style.get('stroke-opacity', opacity)
        else:
            # Fallback to legacy attribute parsing
            fill = self.get_attribute_with_style(element, 'fill', 'black')
            stroke = self.get_attribute_with_style(element, 'stroke', 'none')
            stroke_width = self.get_attribute_with_style(element, 'stroke-width', '1')
            opacity = self.get_attribute_with_style(element, 'opacity', '1')
            fill_opacity = self.get_attribute_with_style(element, 'fill-opacity', opacity)
            stroke_opacity = self.get_attribute_with_style(element, 'stroke-opacity', opacity)

        # Generate shape preset
        if rx_emu > 0 or ry_emu > 0:
            width, height = geometry.dimensions[index]
            corner_radius_x = min(50, (rx / width) * 100) if width > 0 else 0
            corner_radius_y = min(50, (ry / height) * 100) if height > 0 else 0
            corner_radius = max(corner_radius_x, corner_radius_y)

            shape_preset = f'''<a:prstGeom prst="roundRect">
                    <a:avLst>
                        <a:gd name="adj" fmla="val {int(corner_radius * 1000)}"/>
                    </a:avLst>
                </a:prstGeom>'''
        else:
            shape_preset = '''<a:prstGeom prst="rect">
                    <a:avLst/>
                </a:prstGeom>'''

        shape_id = context.get_next_shape_id()

        base_content = f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Rectangle {shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_width}" cy="{emu_height}"/>
                </a:xfrm>
                {shape_preset}
                {self.generate_fill(fill, fill_opacity, context)}
                {self.generate_stroke(stroke, stroke_width, stroke_opacity, context)}
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:pPr/>
                    <a:endParaRPr/>
                </a:p>
            </p:txBody>
        </p:sp>'''

        # Apply filter effects
        shape_bounds = {
            'x': float(emu_x),
            'y': float(emu_y),
            'width': float(emu_width),
            'height': float(emu_height)
        }

        return self.apply_filter_to_shape(element, shape_bounds, base_content, context)

    def _generate_circle_drawingml(self, element: ET.Element, geometry: ShapeGeometry,
                                 context: ConversionContext, index: int) -> str:
        """Generate DrawingML for circle using standardized, robust geometry data."""
        # Enhanced coordinate conversion with validation
        emu_x, emu_y = context.coordinate_system.svg_to_emu(
            geometry.positions[index][0], geometry.positions[index][1]
        )

        # Consistent diameter calculation with validation
        diameter = geometry.dimensions[index][0]  # Both width and height should be diameter
        if diameter <= 0:
            self.logger.warning(f"Invalid circle diameter {diameter}, using minimum")
            diameter = 2.0  # Minimum visible diameter

        # Use consistent EMU conversion for both axes to ensure perfect circles
        emu_diameter_x = context.coordinate_system.svg_length_to_emu(diameter, 'x')
        emu_diameter_y = context.coordinate_system.svg_length_to_emu(diameter, 'y')

        # Ensure perfect circle by using consistent diameter
        emu_diameter = max(emu_diameter_x, emu_diameter_y)
        if abs(emu_diameter_x - emu_diameter_y) > 1000:  # More than ~0.07pt difference
            self.logger.debug(f"Circle diameter discrepancy: x={emu_diameter_x}, y={emu_diameter_y}, using max")

        # Get computed CSS style with cascade + inheritance + specificity
        if hasattr(context.services, 'style_service'):
            computed_style = context.services.style_service.compute_style(
                element, context.parent_style
            )

            # Use CSS-aware property access with proper cascade
            fill = context.services.style_service.fill(computed_style, 'black')
            stroke = context.services.style_service.stroke(computed_style, 'none')
            stroke_width = context.services.style_service.stroke_width(computed_style, '1')
            opacity = context.services.style_service.opacity(computed_style, '1')
            fill_opacity = computed_style.get('fill-opacity', opacity)
            stroke_opacity = computed_style.get('stroke-opacity', opacity)
        else:
            # Fallback to legacy attribute parsing
            fill = self.get_attribute_with_style(element, 'fill', 'black')
            stroke = self.get_attribute_with_style(element, 'stroke', 'none')
            stroke_width = self.get_attribute_with_style(element, 'stroke-width', '1')
            opacity = self.get_attribute_with_style(element, 'opacity', '1')
            fill_opacity = self.get_attribute_with_style(element, 'fill-opacity', opacity)
            stroke_opacity = self.get_attribute_with_style(element, 'stroke-opacity', opacity)

        shape_id = context.get_next_shape_id()

        # Generate enhanced circle DrawingML with improved consistency
        base_content = f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Circle {shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_diameter}" cy="{emu_diameter}"/>
                </a:xfrm>
                <a:prstGeom prst="ellipse">
                    <a:avLst/>
                </a:prstGeom>
                {self.generate_fill(fill, fill_opacity, context)}
                {self.generate_stroke(stroke, stroke_width, stroke_opacity, context)}
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:pPr/>
                    <a:endParaRPr/>
                </a:p>
            </p:txBody>
        </p:sp>'''

        # Apply filter effects
        shape_bounds = {
            'x': float(emu_x),
            'y': float(emu_y),
            'width': float(emu_diameter),
            'height': float(emu_diameter)
        }

        return self.apply_filter_to_shape(element, shape_bounds, base_content, context)

    def _generate_ellipse_drawingml(self, element: ET.Element, geometry: ShapeGeometry,
                                  context: ConversionContext, index: int) -> str:
        """Generate DrawingML for ellipse using vectorized geometry data."""
        # Convert to EMU coordinates
        emu_x, emu_y = self._convert_svg_to_drawingml_coords(
            geometry.positions[index][0], geometry.positions[index][1], context
        )
        width, height = geometry.dimensions[index]
        emu_width = context.coordinate_system.svg_length_to_emu(width, 'x')
        emu_height = context.coordinate_system.svg_length_to_emu(height, 'y')

        # Get computed CSS style with cascade + inheritance + specificity
        if hasattr(context.services, 'style_service'):
            computed_style = context.services.style_service.compute_style(
                element, context.parent_style
            )

            # Use CSS-aware property access with proper cascade
            fill = context.services.style_service.fill(computed_style, 'black')
            stroke = context.services.style_service.stroke(computed_style, 'none')
            stroke_width = context.services.style_service.stroke_width(computed_style, '1')
            opacity = context.services.style_service.opacity(computed_style, '1')
            fill_opacity = computed_style.get('fill-opacity', opacity)
            stroke_opacity = computed_style.get('stroke-opacity', opacity)
        else:
            # Fallback to legacy attribute parsing
            fill = self.get_attribute_with_style(element, 'fill', 'black')
            stroke = self.get_attribute_with_style(element, 'stroke', 'none')
            stroke_width = self.get_attribute_with_style(element, 'stroke-width', '1')
            opacity = self.get_attribute_with_style(element, 'opacity', '1')
            fill_opacity = self.get_attribute_with_style(element, 'fill-opacity', opacity)
            stroke_opacity = self.get_attribute_with_style(element, 'stroke-opacity', opacity)

        shape_id = context.get_next_shape_id()

        return f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Ellipse {shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_width}" cy="{emu_height}"/>
                </a:xfrm>
                <a:prstGeom prst="ellipse">
                    <a:avLst/>
                </a:prstGeom>
                {self.generate_fill(fill, fill_opacity, context)}
                {self.generate_stroke(stroke, stroke_width, stroke_opacity, context)}
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:pPr/>
                    <a:endParaRPr/>
                </a:p>
            </p:txBody>
        </p:sp>'''

    def _generate_polygon_drawingml(self, element: ET.Element, geometry: ShapeGeometry,
                                  context: ConversionContext, index: int) -> str:
        """Generate DrawingML for polygon using vectorized geometry data."""
        # Validate geometry type for polygon rendering
        if not hasattr(geometry, 'shape_type') or geometry.shape_type not in ['polygon', 'polyline']:
            return '<!-- Unexpected geometry type for polygon rendering -->'

        # Convert to EMU coordinates
        emu_x, emu_y = self._convert_svg_to_drawingml_coords(
            geometry.positions[index][0], geometry.positions[index][1], context
        )
        width, height = geometry.dimensions[index]
        emu_width = context.coordinate_system.svg_length_to_emu(width, 'x')
        emu_height = context.coordinate_system.svg_length_to_emu(height, 'y')

        # Generate path using vectorized operations
        path_xml = self.geometry_engine.generate_drawingml_paths_batch([geometry])[0]

        # Get style attributes
        tag = self.get_element_tag(element)
        fill = self.get_attribute_with_style(element, 'fill', 'black' if tag == 'polygon' else 'none')
        stroke = self.get_attribute_with_style(element, 'stroke', 'none' if tag == 'polygon' else 'black')
        stroke_width = self.get_attribute_with_style(element, 'stroke-width', '1')
        opacity = self.get_attribute_with_style(element, 'opacity', '1')
        fill_opacity = self.get_attribute_with_style(element, 'fill-opacity', opacity)
        stroke_opacity = self.get_attribute_with_style(element, 'stroke-opacity', opacity)

        shape_id = context.get_next_shape_id()

        return f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="{tag.capitalize()} {shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_width}" cy="{emu_height}"/>
                </a:xfrm>
                <a:custGeom>
                    <a:avLst/>
                    <a:gdLst/>
                    <a:ahLst/>
                    <a:cxnLst/>
                    <a:rect l="0" t="0" r="{emu_width}" b="{emu_height}"/>
                    <a:pathLst>
                        {path_xml}
                    </a:pathLst>
                </a:custGeom>
                {self.generate_fill(fill, fill_opacity, context)}
                {self.generate_stroke(stroke, stroke_width, stroke_opacity, context)}
            </p:spPr>
            <p:txBody>
                <a:bodyPr/>
                <a:lstStyle/>
                <a:p>
                    <a:pPr/>
                    <a:endParaRPr/>
                </a:p>
            </p:txBody>
        </p:sp>'''

    def _generate_line_drawingml(self, element: ET.Element, geometry: ShapeGeometry,
                               context: ConversionContext, index: int) -> str:
        """Generate DrawingML for line using actual coordinates for straight lines."""
        # Extract actual line coordinates from element
        x1 = self.parse_length(element.get('x1', '0'))
        y1 = self.parse_length(element.get('y1', '0'))
        x2 = self.parse_length(element.get('x2', '0'))
        y2 = self.parse_length(element.get('y2', '0'))

        # Calculate line position and dimensions
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        # Convert to EMU coordinates - fix: unpack single call
        emu_x, emu_y = context.coordinate_system.svg_to_emu(min_x, min_y)

        # Line dimensions (minimum 1 unit to ensure visibility)
        line_width = max(max_x - min_x, 1)
        line_height = max(max_y - min_y, 1)
        emu_width = context.coordinate_system.svg_length_to_emu(line_width, 'x')
        emu_height = context.coordinate_system.svg_length_to_emu(line_height, 'y')

        # Calculate normalized path coordinates relative to bounding box
        if line_width == 1:  # Vertical line
            start_x, start_y = 10800, 0
            end_x, end_y = 10800, 21600
        elif line_height == 1:  # Horizontal line
            start_x, start_y = 0, 10800
            end_x, end_y = 21600, 10800
        else:  # Diagonal line
            # Map actual coordinates to 21600 coordinate system
            start_x = int(((x1 - min_x) / line_width) * 21600)
            start_y = int(((y1 - min_y) / line_height) * 21600)
            end_x = int(((x2 - min_x) / line_width) * 21600)
            end_y = int(((y2 - min_y) / line_height) * 21600)

        # Get computed CSS style with cascade + inheritance + specificity
        if hasattr(context.services, 'style_service'):
            computed_style = context.services.style_service.compute_style(
                element, context.parent_style
            )
            stroke = context.services.style_service.stroke(computed_style, 'purple')
            stroke_width = context.services.style_service.stroke_width(computed_style, '3')
            opacity = context.services.style_service.opacity(computed_style, '1')
            stroke_opacity = computed_style.get('stroke-opacity', opacity)
        else:
            # Fallback to legacy attribute parsing
            stroke = self.get_attribute_with_style(element, 'stroke', 'purple')
            stroke_width = self.get_attribute_with_style(element, 'stroke-width', '3')
            opacity = self.get_attribute_with_style(element, 'opacity', '1')
            stroke_opacity = self.get_attribute_with_style(element, 'stroke-opacity', opacity)

        shape_id = context.get_next_shape_id()

        # Use regular shape (p:sp) instead of connection shape for better accuracy
        return f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{shape_id}" name="Line {shape_id}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{emu_x}" y="{emu_y}"/>
                    <a:ext cx="{emu_width}" cy="{emu_height}"/>
                </a:xfrm>
                <a:custGeom>
                    <a:avLst/>
                    <a:gdLst/>
                    <a:ahLst/>
                    <a:cxnLst/>
                    <a:rect l="0" t="0" r="0" b="0"/>
                    <a:pathLst>
                        <a:path w="21600" h="21600">
                            <a:moveTo>
                                <a:pt x="{start_x}" y="{start_y}"/>
                            </a:moveTo>
                            <a:lnTo>
                                <a:pt x="{end_x}" y="{end_y}"/>
                            </a:lnTo>
                        </a:path>
                    </a:pathLst>
                </a:custGeom>
                {self.generate_stroke(stroke, stroke_width, stroke_opacity, context)}
            </p:spPr>
        </p:sp>'''

    # ==================== Utility Methods ====================

    def _group_elements_by_type(self, elements: List[ET.Element]) -> Dict[str, List[Dict]]:
        """Group SVG elements by shape type for batch processing optimization."""
        grouped = {}

        for i, element in enumerate(elements):
            tag = self.get_element_tag(element)
            if tag not in grouped:
                grouped[tag] = []

            grouped[tag].append({
                'element': element,
                'original_index': i
            })

        return grouped

    def _convert_svg_to_drawingml_coords(self, x: float, y: float, context: ConversionContext) -> Tuple[int, int]:
        """Convert SVG coordinates to DrawingML EMUs using viewport-aware mapping."""
        if hasattr(context, 'viewport_mapping') and context.viewport_mapping is not None:
            return context.viewport_mapping.svg_to_emu(x, y)

        return context.coordinate_system.svg_to_emu(x, y)

    def benchmark_performance(self, n_shapes: int = 1000) -> Dict[str, float]:
        """Benchmark the performance of the NumPy shape converter."""
        return self.geometry_engine.benchmark_performance(n_shapes)

    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage of the converter and geometry engine."""
        base_memory = self.geometry_engine.get_memory_usage()

        import sys
        converter_bytes = sys.getsizeof(self) + sum(sys.getsizeof(v) for v in self._batch_cache.values())

        return {
            'total_bytes': base_memory['total_bytes'] + converter_bytes,
            'total_mb': (base_memory['total_bytes'] + converter_bytes) / (1024 * 1024),
            'geometry_engine_bytes': base_memory['total_bytes'],
            'converter_cache_bytes': converter_bytes
        }


# ==================== Factory Functions ====================

def create_enhanced_shape_converter(services: 'ConversionServices',
                                    optimization_level: int = 2) -> EnhancedShapeConverter:
    """Create an enhanced shape converter with specified optimization level."""
    return EnhancedShapeConverter(services=services, optimization_level=optimization_level)

def register_enhanced_converters(converter_registry: Any,
                                 services: 'ConversionServices',
                                 optimization_level: int = 2) -> None:
    """Register enhanced shape converters with the main converter registry."""
    enhanced_converter = EnhancedShapeConverter(services=services, optimization_level=optimization_level)

    # Register for all supported shape types
    for shape_type in enhanced_converter.supported_elements:
        converter_registry.register(shape_type, enhanced_converter)