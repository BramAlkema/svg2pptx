#!/usr/bin/env python3
"""
Text Converter Service

High-level service that orchestrates text preprocessing, layout,
and DrawingML generation for the conversion pipeline.

Features:
- Preprocessing integration
- Layout engine coordination
- DrawingML generation
- Font strategy integration
"""

import logging
from typing import Dict, Any, Optional, List
from lxml import etree as ET

from ..pre.text_layout_prep import TextLayoutPrepPreprocessor
from .layout_engine import TextLayoutEngine
from ..services.conversion_services import ConversionServices

logger = logging.getLogger(__name__)


class TextConverterService:
    """
    Service that orchestrates text conversion with preprocessing integration.

    Coordinates between preprocessing, layout engine, and DrawingML generation
    to provide comprehensive text conversion capabilities.
    """

    def __init__(self, services: ConversionServices):
        """
        Initialize text converter service.

        Args:
            services: ConversionServices container
        """
        self.services = services
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.preprocessor = TextLayoutPrepPreprocessor()
        self.layout_engine = TextLayoutEngine(services)

        # Text fixes from documented issues
        self.documented_fixes = {
            'raw_anchor_handling': True,
            'per_tspan_styling': True,
            'conservative_baseline': True,
            'coordinate_pipeline': True
        }

    def convert_text_element(self, element: ET.Element, context: Any,
                           apply_preprocessing: bool = True) -> str:
        """
        Convert text element to DrawingML with full preprocessing support.

        Args:
            element: SVG text element
            context: Conversion context
            apply_preprocessing: Whether to apply preprocessing (default: True)

        Returns:
            DrawingML XML string
        """
        try:
            # Step 1: Apply preprocessing if enabled
            if apply_preprocessing:
                processed_element = self._apply_preprocessing(element)
            else:
                processed_element = element

            # Step 2: Generate layout information using layout engine
            layout_info = self.layout_engine.process_preprocessed_text(processed_element, context)

            # Step 3: Convert to DrawingML based on layout type
            if layout_info['type'] == 'single-run':
                return self._generate_single_run_drawingml(layout_info, context)
            elif layout_info['type'] == 'multi-run':
                return self._generate_multi_run_drawingml(layout_info, context)
            else:
                return self._generate_fallback_drawingml(layout_info, context)

        except Exception as e:
            self.logger.error(f"Text conversion failed: {e}")
            return self._generate_error_fallback(element, context)

    def _apply_preprocessing(self, element: ET.Element) -> ET.Element:
        """Apply text preprocessing to element."""
        # Clone element to avoid modifying original
        cloned_element = self._clone_element(element)

        # Create temporary SVG root for preprocessing
        temp_svg = ET.Element('{http://www.w3.org/2000/svg}svg')
        temp_svg.append(cloned_element)

        # Apply preprocessing
        processed_svg = self.preprocessor.process(temp_svg)

        # Extract processed text element
        processed_elements = processed_svg.xpath(".//svg:text",
                                               namespaces={'svg': 'http://www.w3.org/2000/svg'})

        if processed_elements:
            return processed_elements[0]
        else:
            self.logger.warning("Preprocessing failed to return text element")
            return cloned_element

    def _generate_single_run_drawingml(self, layout_info: Dict[str, Any], context: Any) -> str:
        """Generate DrawingML for single-run text."""
        # Extract layout information
        content = layout_info['content']
        position = layout_info['position']
        font_info = layout_info['font']
        anchor = layout_info['anchor']

        if not content.strip():
            return ""

        # Apply documented fixes
        position_emu = self._apply_coordinate_pipeline_fix(position, context)
        anchor_alignment = self._apply_raw_anchor_handling_fix(anchor)
        baseline_adjusted_y = self._apply_conservative_baseline_fix(
            position_emu['y'], font_info['size']
        ) if layout_info.get('baseline_adjusted', False) else position_emu['y']

        # Calculate text dimensions
        text_dimensions = self._calculate_text_dimensions(content, font_info)

        # Generate DrawingML
        drawingml = self._create_text_shape_xml(
            content=content,
            x_emu=position_emu['x'],
            y_emu=baseline_adjusted_y,
            width_emu=text_dimensions['width'],
            height_emu=text_dimensions['height'],
            font_family=font_info['family'],
            font_size=font_info['size'],
            alignment=anchor_alignment,
            context=context
        )

        self.logger.debug(f"Generated single-run DrawingML for '{content[:20]}...'")
        return drawingml

    def _generate_multi_run_drawingml(self, layout_info: Dict[str, Any], context: Any) -> str:
        """Generate DrawingML for multi-run text with per-tspan styling."""
        runs = layout_info['runs']
        if not runs:
            return ""

        # Apply per-tspan styling fix
        styled_runs = self._apply_per_tspan_styling_fix(runs)

        # Calculate overall text bounds
        overall_bounds = self._calculate_multi_run_bounds(styled_runs, layout_info)

        # Create text shape with multiple runs
        drawingml = self._create_multi_run_text_shape_xml(
            runs=styled_runs,
            bounds=overall_bounds,
            base_font=layout_info['font'],
            alignment=self._apply_raw_anchor_handling_fix(layout_info['anchor']),
            context=context
        )

        self.logger.debug(f"Generated multi-run DrawingML with {len(styled_runs)} runs")
        return drawingml

    def _generate_fallback_drawingml(self, layout_info: Dict[str, Any], context: Any) -> str:
        """Generate fallback DrawingML for non-preprocessed text."""
        self.logger.debug("Using fallback DrawingML generation")
        return self._generate_single_run_drawingml(layout_info, context)

    def _generate_error_fallback(self, element: ET.Element, context: Any) -> str:
        """Generate minimal DrawingML when conversion fails."""
        content = element.text or "Error"
        x = float(element.get('x', '0'))
        y = float(element.get('y', '0'))

        # Convert to EMU (basic conversion)
        x_emu = int(x * 9525)
        y_emu = int(y * 9525)

        return self._create_text_shape_xml(
            content=content,
            x_emu=x_emu,
            y_emu=y_emu,
            width_emu=int(len(content) * 12 * 9525 * 0.6),  # Rough estimate
            height_emu=int(12 * 9525 * 1.2),
            font_family="Arial",
            font_size=12,
            alignment="l",
            context=context
        )

    # Documented Fixes Implementation

    def _apply_raw_anchor_handling_fix(self, anchor: str) -> str:
        """Apply Fix #1: Raw anchor handling."""
        anchor_map = {
            'start': 'l',     # left
            'middle': 'ctr',  # center
            'end': 'r'        # right
        }
        return anchor_map.get(anchor, 'l')

    def _apply_per_tspan_styling_fix(self, runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply Fix #2: Per-tspan styling."""
        styled_runs = []

        for run in runs:
            styled_run = run.copy()

            # Ensure explicit styling from inherited data
            inherited_styles = run.get('inherited_styles', {})

            # Apply inherited font properties
            if 'font-family' in inherited_styles:
                styled_run['font_family'] = inherited_styles['font-family']
            if 'font-size' in inherited_styles:
                try:
                    styled_run['font_size'] = float(inherited_styles['font-size'])
                except (ValueError, TypeError):
                    pass

            # Apply inherited formatting
            styled_run['bold'] = self._extract_bold_from_styles(inherited_styles)
            styled_run['italic'] = self._extract_italic_from_styles(inherited_styles)
            styled_run['color'] = self._extract_color_from_styles(inherited_styles)

            styled_runs.append(styled_run)

        return styled_runs

    def _apply_conservative_baseline_fix(self, y_emu: int, font_size: float) -> int:
        """Apply Fix #3: Conservative baseline adjustment."""
        # Apply conservative 5% baseline shift as calculated during preprocessing
        baseline_adjustment = int(font_size * 0.05 * 9525)
        return y_emu + baseline_adjustment

    def _apply_coordinate_pipeline_fix(self, position: Dict[str, float], context: Any) -> Dict[str, int]:
        """Apply Fix #4: Coordinate pipeline integration."""
        x, y = position['x'], position['y']

        try:
            # Use services coordinate transformer if available
            if hasattr(self.services, 'coordinate_transformer'):
                result = self.services.coordinate_transformer.transform_point(x, y, 'svg-user')
                x_emu = int(result.get('x_emu', x * 9525))
                y_emu = int(result.get('y_emu', y * 9525))
            else:
                # Fallback to basic transformation
                x_emu = int(x * 9525)
                y_emu = int(y * 9525)

            return {'x': x_emu, 'y': y_emu}

        except Exception as e:
            self.logger.debug(f"Coordinate transformation failed: {e}, using fallback")
            return {'x': int(x * 9525), 'y': int(y * 9525)}

    # DrawingML Generation

    def _create_text_shape_xml(self, content: str, x_emu: int, y_emu: int,
                              width_emu: int, height_emu: int, font_family: str,
                              font_size: float, alignment: str, context: Any) -> str:
        """Create DrawingML text shape XML."""
        shape_id = getattr(context, 'next_shape_id', 1)
        if hasattr(context, 'get_next_shape_id'):
            shape_id = context.get_next_shape_id()

        # Escape XML content
        escaped_content = self._escape_xml(content)

        # Font size in 1/100 points
        font_size_hundredths = int(font_size * 100)

        xml = f'''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="Text {shape_id}"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="{x_emu}" y="{y_emu}"/>
            <a:ext cx="{width_emu}" cy="{height_emu}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
        <a:ln>
            <a:noFill/>
        </a:ln>
    </p:spPr>
    <p:txBody>
        <a:bodyPr vertOverflow="ellipsis" wrap="square" rtlCol="0" anchor="t"/>
        <a:lstStyle/>
        <a:p>
            <a:pPr algn="{alignment}"/>
            <a:r>
                <a:rPr lang="en-US" sz="{font_size_hundredths}" dirty="0">
                    <a:solidFill>
                        <a:srgbClr val="000000"/>
                    </a:solidFill>
                    <a:latin typeface="{font_family}"/>
                </a:rPr>
                <a:t>{escaped_content}</a:t>
            </a:r>
            <a:endParaRPr/>
        </a:p>
    </p:txBody>
</p:sp>'''

        return xml

    def _create_multi_run_text_shape_xml(self, runs: List[Dict[str, Any]], bounds: Dict[str, int],
                                        base_font: Dict[str, Any], alignment: str, context: Any) -> str:
        """Create DrawingML text shape with multiple runs."""
        shape_id = getattr(context, 'next_shape_id', 1)
        if hasattr(context, 'get_next_shape_id'):
            shape_id = context.get_next_shape_id()

        # Generate runs XML
        runs_xml = []
        for run in runs:
            run_xml = self._create_text_run_xml(run)
            runs_xml.append(run_xml)

        runs_content = '\n            '.join(runs_xml)

        xml = f'''<p:sp>
    <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="Text {shape_id}"/>
        <p:cNvSpPr/>
        <p:nvPr/>
    </p:nvSpPr>
    <p:spPr>
        <a:xfrm>
            <a:off x="{bounds['x']}" y="{bounds['y']}"/>
            <a:ext cx="{bounds['width']}" cy="{bounds['height']}"/>
        </a:xfrm>
        <a:prstGeom prst="rect">
            <a:avLst/>
        </a:prstGeom>
        <a:ln>
            <a:noFill/>
        </a:ln>
    </p:spPr>
    <p:txBody>
        <a:bodyPr vertOverflow="ellipsis" wrap="square" rtlCol="0" anchor="t"/>
        <a:lstStyle/>
        <a:p>
            <a:pPr algn="{alignment}"/>
            {runs_content}
            <a:endParaRPr/>
        </a:p>
    </p:txBody>
</p:sp>'''

        return xml

    def _create_text_run_xml(self, run: Dict[str, Any]) -> str:
        """Create XML for a single text run."""
        content = self._escape_xml(run.get('text', ''))
        font_family = run.get('font_family', 'Arial')
        font_size = run.get('font_size', 12)
        bold = run.get('bold', False)
        italic = run.get('italic', False)
        color = run.get('color', '000000')

        font_size_hundredths = int(font_size * 100)
        bold_attr = '1' if bold else '0'
        italic_attr = '1' if italic else '0'

        return f'''<a:r>
                <a:rPr lang="en-US" sz="{font_size_hundredths}" b="{bold_attr}" i="{italic_attr}" dirty="0">
                    <a:solidFill>
                        <a:srgbClr val="{color}"/>
                    </a:solidFill>
                    <a:latin typeface="{font_family}"/>
                </a:rPr>
                <a:t>{content}</a:t>
            </a:r>'''

    # Utility Methods

    def _calculate_text_dimensions(self, content: str, font_info: Dict[str, Any]) -> Dict[str, int]:
        """Calculate text dimensions in EMU."""
        font_size = font_info['size']

        # Estimate text width (improved estimation)
        char_width = font_size * 0.6
        text_width = len(content) * char_width
        text_width = max(text_width, 100)  # Minimum width

        # Text height with line spacing
        text_height = font_size * 1.2

        return {
            'width': int(text_width * 9525),
            'height': int(text_height * 9525)
        }

    def _calculate_multi_run_bounds(self, runs: List[Dict[str, Any]], layout_info: Dict[str, Any]) -> Dict[str, int]:
        """Calculate bounding box for multi-run text."""
        if not runs:
            return {'x': 0, 'y': 0, 'width': 100 * 9525, 'height': 100 * 9525}

        # Find text bounds
        min_x = min(run['position']['x'] for run in runs)
        min_y = min(run['position']['y'] for run in runs)

        # Calculate maximum dimensions
        max_width = 0
        total_height = 0

        for run in runs:
            run_width = len(run.get('text', '')) * run.get('font_size', 12) * 0.6
            max_width = max(max_width, run_width)

            if run.get('line_break', False):
                total_height += run.get('font_size', 12) * 1.2

        # Ensure minimum dimensions
        width = max(max_width, 100)
        height = max(total_height, layout_info['font']['size'] * 1.2)

        return {
            'x': int(min_x * 9525),
            'y': int(min_y * 9525),
            'width': int(width * 9525),
            'height': int(height * 9525)
        }

    def _extract_bold_from_styles(self, styles: Dict[str, str]) -> bool:
        """Extract bold flag from styles."""
        font_weight = styles.get('font-weight', 'normal')
        return font_weight in ['bold', '700', '800', '900']

    def _extract_italic_from_styles(self, styles: Dict[str, str]) -> bool:
        """Extract italic flag from styles."""
        font_style = styles.get('font-style', 'normal')
        return font_style in ['italic', 'oblique']

    def _extract_color_from_styles(self, styles: Dict[str, str]) -> str:
        """Extract color value from styles."""
        fill = styles.get('fill', '#000000')
        if fill.startswith('#'):
            return fill[1:]
        # Handle named colors
        color_map = {
            'black': '000000', 'white': 'FFFFFF', 'red': 'FF0000',
            'green': '008000', 'blue': '0000FF', 'yellow': 'FFFF00'
        }
        return color_map.get(fill.lower(), '000000')

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))

    def _clone_element(self, element: ET.Element) -> ET.Element:
        """Create a deep copy of an element."""
        cloned = ET.Element(element.tag, element.attrib)
        cloned.text = element.text
        cloned.tail = element.tail

        for child in element:
            cloned.append(self._clone_element(child))

        return cloned


def create_text_converter_service(services: ConversionServices) -> TextConverterService:
    """
    Create a text converter service with services.

    Args:
        services: ConversionServices container

    Returns:
        Configured TextConverterService
    """
    return TextConverterService(services)