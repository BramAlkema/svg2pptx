#!/usr/bin/env python3
"""
SVG Parser

Parses SVG content into normalized DOM structure for clean slate processing.
"""

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

from lxml import etree as ET

from ..xml.safe_iter import children, walk
from .safe_svg_normalization import SafeSVGNormalizer as SVGNormalizer

logger = logging.getLogger(__name__)

# Parser constants
FONT_WEIGHT_BOLD_THRESHOLD = 700  # CSS font-weight threshold for bold
MIN_PATH_COORDS_FOR_LINE = 2  # Minimum coords for line commands (L, l)
MIN_PATH_COORDS_FOR_CURVE = 3  # Minimum coords for curves (Q)
MIN_PATH_COORDS_FOR_CUBIC = 6  # Minimum coords for cubic curves (C)
MIN_PATH_COORDS_FOR_ARC = 4  # Minimum coords for arc (A)
MAX_SIMPLE_PATH_SEGMENTS = 10  # Maximum segments for simple path


@dataclass
class ParseResult:
    """Result of SVG parsing"""
    success: bool
    svg_root: Any | None = None  # ET.Element is not a type, it's a factory
    error: str | None = None
    processing_time_ms: float = 0.0

    # Parse statistics
    element_count: int = 0
    namespace_count: int = 0
    has_external_references: bool = False

    # Normalization results
    normalization_applied: bool = False
    normalization_changes: dict[str, Any] = None

    def __post_init__(self):
        if self.normalization_changes is None:
            self.normalization_changes = {}


class SVGParser:
    """
    Parses SVG content into normalized DOM structure.

    This parser handles malformed SVG gracefully and applies basic
    normalization to prepare content for the clean slate pipeline.
    """

    def __init__(self, enable_normalization: bool = True):
        """
        Initialize SVG parser.

        Args:
            enable_normalization: Whether to apply normalization during parsing
        """
        self.enable_normalization = enable_normalization
        self.normalizer = SVGNormalizer() if enable_normalization else None
        self.logger = logging.getLogger(__name__)

        # Parser configuration
        self.parser_config = {
            'recover': True,  # Recover from errors
            'strip_cdata': False,  # Preserve CDATA sections
            'remove_blank_text': False,  # Preserve whitespace for text elements
            'remove_comments': False,  # Keep comments for debugging
            'resolve_entities': True,  # Resolve XML entities
        }

    def parse(self, svg_content: str) -> ParseResult:
        """
        Parse SVG string into normalized DOM structure.

        Args:
            svg_content: SVG content as string

        Returns:
            ParseResult with success status and parsed SVG root
        """
        start_time = time.perf_counter()

        try:
            # Clean and prepare content
            cleaned_content = self._prepare_content(svg_content)

            # Parse with lxml
            svg_root = self._parse_xml(cleaned_content)

            # Validate SVG structure
            self._validate_svg_structure(svg_root)

            # Apply normalization if enabled
            normalization_changes = {}
            if self.enable_normalization and self.normalizer:
                svg_root, normalization_changes = self.normalizer.normalize(svg_root)

            # Collect statistics
            element_count = len(list(walk(svg_root)))
            namespace_count = len(self._extract_namespaces(svg_root))
            has_external_refs = self._has_external_references(svg_root)

            processing_time = (time.perf_counter() - start_time) * 1000

            result = ParseResult(
                success=True,
                svg_root=svg_root,
                processing_time_ms=processing_time,
                element_count=element_count,
                namespace_count=namespace_count,
                has_external_references=has_external_refs,
                normalization_applied=self.enable_normalization,
                normalization_changes=normalization_changes,
            )

            self.logger.debug(f"SVG parsed successfully in {processing_time:.2f}ms, "
                            f"elements: {element_count}, namespaces: {namespace_count}")

            return result

        except ET.XMLSyntaxError as e:
            processing_time = (time.perf_counter() - start_time) * 1000
            error_msg = f"XML syntax error: {str(e)}"
            self.logger.error(error_msg)

            return ParseResult(
                success=False,
                error=error_msg,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = (time.perf_counter() - start_time) * 1000
            error_msg = f"Parse error: {str(e)}"
            self.logger.error(error_msg)

            return ParseResult(
                success=False,
                error=error_msg,
                processing_time_ms=processing_time,
            )

    def _prepare_content(self, svg_content: str) -> str:
        """Clean and prepare SVG content for parsing"""
        # Remove BOM if present
        if svg_content.startswith('\ufeff'):
            svg_content = svg_content[1:]

        # Ensure content is not empty
        svg_content = svg_content.strip()
        if not svg_content:
            raise ValueError("Empty SVG content")

        # Basic validation - must contain SVG element
        if '<svg' not in svg_content.lower():
            raise ValueError("Content does not appear to be SVG")

        # Handle common encoding issues
        svg_content = self._fix_encoding_issues(svg_content)

        # Add XML declaration if missing (helps with parsing)
        if not svg_content.startswith('<?xml'):
            svg_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_content

        return svg_content

    def _fix_encoding_issues(self, content: str) -> str:
        """Fix common encoding issues in SVG content"""
        # Replace common problematic characters
        replacements = {
            '\x00': '',  # Null bytes
            '\x0b': ' ',  # Vertical tab
            '\x0c': ' ',  # Form feed
        }

        for old, new in replacements.items():
            content = content.replace(old, new)

        return content

    def _parse_xml(self, content: str) -> ET.Element:
        """Parse XML content with error recovery following existing codebase patterns"""
        try:
            # Use configured parser settings
            base_parser = ET.XMLParser(
                recover=self.parser_config['recover'],
                strip_cdata=self.parser_config['strip_cdata'],
                remove_blank_text=self.parser_config['remove_blank_text'],
                remove_comments=self.parser_config['remove_comments'],
                resolve_entities=self.parser_config['resolve_entities'],
                no_network=True,
            )

            if isinstance(content, str):
                root = ET.fromstring(content.encode('utf-8'), base_parser)
            else:
                root = ET.fromstring(content, base_parser)

            return root

        except ET.XMLSyntaxError as e:
            # Try with more aggressive error recovery using lxml parser options
            self.logger.warning(f"Initial parse failed, trying recovery mode: {e}")

            try:
                # More permissive parser following existing patterns
                recovery_parser = ET.XMLParser(
                    recover=True,
                    strip_cdata=False,
                    remove_blank_text=False,
                    remove_comments=True,  # Remove comments that might cause issues
                    resolve_entities=False,  # Don't resolve entities
                    no_network=True,  # Don't fetch external resources
                )

                if isinstance(content, str) and content.strip().startswith('<?xml'):
                    svg_bytes = content.encode('utf-8')
                    root = ET.fromstring(svg_bytes, recovery_parser)
                else:
                    root = ET.fromstring(content, recovery_parser)

                self.logger.info("SVG parsed successfully with recovery mode")
                return root

            except Exception as recovery_error:
                self.logger.error(f"Recovery parse also failed: {recovery_error}")
                raise e  # Re-raise original error

    def _validate_svg_structure(self, svg_root: ET.Element) -> None:
        """Validate basic SVG structure"""
        # Check if root is SVG element
        root_tag = self._get_local_tag(svg_root.tag)
        if root_tag != 'svg':
            raise ValueError(f"Root element is '{root_tag}', expected 'svg'")

        # Check for required namespace
        if 'http://www.w3.org/2000/svg' not in str(svg_root.nsmap if hasattr(svg_root, 'nsmap') else {}):
            self.logger.warning("SVG namespace not found, adding default namespace")
            # Note: We could add the namespace here if needed

        # Validate basic structure
        if not self._has_valid_svg_attributes(svg_root):
            self.logger.warning("SVG element missing standard attributes (width, height, viewBox)")

    def _has_valid_svg_attributes(self, svg_root: ET.Element) -> bool:
        """Check if SVG has basic required attributes"""
        # Check for width/height or viewBox
        has_dimensions = (
            svg_root.get('width') is not None and svg_root.get('height') is not None
        ) or svg_root.get('viewBox') is not None

        return has_dimensions

    def _extract_namespaces(self, svg_root: ET.Element) -> dict[str, str]:
        """Extract namespaces from SVG"""
        namespaces = {}

        # Get namespaces from nsmap if available
        if hasattr(svg_root, 'nsmap') and svg_root.nsmap:
            namespaces.update(svg_root.nsmap)

        # Common SVG namespaces
        default_namespaces = {
            None: 'http://www.w3.org/2000/svg',
            'xlink': 'http://www.w3.org/1999/xlink',
        }

        # Add missing default namespaces
        for prefix, uri in default_namespaces.items():
            if prefix not in namespaces:
                namespaces[prefix] = uri

        return namespaces

    def _has_external_references(self, svg_root: ET.Element) -> bool:
        """Check if SVG has external references (images, fonts, etc.)"""
        for element in walk(svg_root):
            # Check for external image references
            href = element.get('href') or element.get('{http://www.w3.org/1999/xlink}href')
            if href and (href.startswith('http://') or href.startswith('https://') or href.startswith('file://')):
                return True

            # Check for external font references
            if element.get('font-family') and 'url(' in str(element.get('font-family')):
                return True

            # Check for external stylesheets
            if self._get_local_tag(element.tag) == 'style':
                style_content = element.text or ''
                if '@import' in style_content or 'url(' in style_content:
                    return True

        return False

    def _get_local_tag(self, tag: str) -> str:
        """Extract local tag name from namespaced tag"""
        if '}' in tag:
            return tag.split('}')[1]
        return tag

    def parse_from_file(self, file_path: str) -> ParseResult:
        """
        Parse SVG from file.

        Args:
            file_path: Path to SVG file

        Returns:
            ParseResult with success status and parsed SVG root
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.parse(content)

        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                self.logger.warning(f"File {file_path} parsed with latin-1 encoding")
                return self.parse(content)
            except Exception as e:
                return ParseResult(
                    success=False,
                    error=f"Failed to read file {file_path}: {e}",
                )

        except Exception as e:
            return ParseResult(
                success=False,
                error=f"Failed to read file {file_path}: {e}",
            )

    def parse_to_ir(self, svg_content: str) -> tuple[list, 'ParseResult']:
        """
        Parse SVG content directly to Clean Slate IR.

        Args:
            svg_content: SVG content as string

        Returns:
            Tuple[SceneGraph, ParseResult] where SceneGraph is a list of IRElements
            Always returns a list (possibly empty) - never None
        """
        # First parse to DOM
        parse_result = self.parse(svg_content)

        if not parse_result.success:
            # Return empty SceneGraph (list) with the error
            return [], parse_result

        # Convert DOM to IR
        try:
            scene = self._convert_dom_to_ir(parse_result.svg_root)
            # Ensure a list is always returned
            scene = scene or []
            return scene, parse_result
        except Exception as e:
            # Update parse result with conversion error
            parse_result.success = False
            parse_result.error = f"IR conversion failed: {e}"
            return [], parse_result

    def _convert_dom_to_ir(self, svg_root: ET.Element):
        """Convert SVG DOM to Clean Slate IR using existing parsing logic"""

        # Leverage existing SVG extraction logic from src/svg2drawingml.py
        elements = []
        self._extract_recursive_to_ir(svg_root, elements)

        return elements

    def _convert_hyperlink_to_ir(self, hyperlink_element: ET.Element, ir_elements: list) -> None:
        """
        Convert SVG <a> element to IR elements with navigation metadata.

        Args:
            hyperlink_element: SVG <a> element
            ir_elements: List to append converted IR elements to

        Process:
        1. Extract href attribute (including xlink:href)
        2. Extract data-* attributes for PowerPoint-specific navigation
        3. Extract tooltip from nested <title> elements
        4. Convert child elements to IR with navigation metadata attached
        5. Store NavigationSpec in element metadata for later processing

        Supports:
        - data-slide="N" for slide jumps
        - data-jump="next|previous|first|last|endshow" for presentation actions
        - data-bookmark="name" for same-slide anchors
        - data-custom-show="name" for custom show navigation
        - href fallback for external links and legacy slide references
        """
        # Extract href attribute - check both href and xlink:href
        href = (
            hyperlink_element.get('href') or
            hyperlink_element.get('{http://www.w3.org/1999/xlink}href')
        )

        # Extract navigation data attributes
        element_attrs = self._extract_navigation_attributes(hyperlink_element)

        # Extract tooltip from nested <title> element
        tooltip = self._extract_hyperlink_tooltip(hyperlink_element)

        # Parse navigation using enhanced NavigationSpec system
        navigation_spec = self._parse_navigation_attributes(href, element_attrs, tooltip)

        if not navigation_spec:
            # No valid navigation found, just process children without navigation metadata
            if href or any(element_attrs.values()):
                self.logger.warning(f"Invalid navigation attributes: href={href}, attrs={element_attrs}")
            for child in children(hyperlink_element):
                self._extract_recursive_to_ir(child, ir_elements)
            return

        # Store navigation context for child elements (maintaining backward compatibility)
        old_navigation = getattr(self, '_current_navigation', None)
        old_hyperlink = getattr(self, '_current_hyperlink', None)

        self._current_navigation = navigation_spec
        # Backward compatibility: also set as hyperlink for existing code
        if navigation_spec.kind.value in ('external', 'slide'):
            # Convert to legacy HyperlinkSpec for backward compatibility
            from ..pipeline.hyperlinks import HyperlinkSpec
            if navigation_spec.kind.value == 'external':
                self._current_hyperlink = HyperlinkSpec(
                    href=navigation_spec.href,
                    tooltip=navigation_spec.tooltip,
                    visited=navigation_spec.visited,
                )
            elif navigation_spec.kind.value == 'slide':
                self._current_hyperlink = HyperlinkSpec(
                    href=f"slide:{navigation_spec.slide.index}",
                    tooltip=navigation_spec.tooltip,
                    visited=navigation_spec.visited,
                )

        # Convert child elements to IR - they will inherit the navigation
        for child in children(hyperlink_element):
            self._extract_recursive_to_ir(child, ir_elements)

        # Restore previous navigation context
        self._current_navigation = old_navigation
        self._current_hyperlink = old_hyperlink

        self.logger.debug(f"Processed navigation {navigation_spec.get_target_description()} with {len(ir_elements)} child elements")

    def _extract_hyperlink_tooltip(self, hyperlink_element: ET.Element) -> str:
        """
        Extract tooltip text from nested <title> element in SVG <a>.

        Args:
            hyperlink_element: SVG <a> element to search

        Returns:
            Tooltip text or None if no <title> element found
        """
        # Look for <title> element as direct child
        for child in children(hyperlink_element):
            if self._get_local_tag(child.tag) == 'title':
                title_text = self._extract_text_content(child)
                if title_text and title_text.strip():
                    return title_text.strip()

        return None

    def _extract_navigation_attributes(self, hyperlink_element: ET.Element) -> dict:
        """
        Extract navigation data attributes from SVG <a> element.

        Args:
            hyperlink_element: SVG <a> element to extract attributes from

        Returns:
            Dictionary of navigation attributes (data-slide, data-jump, etc.)
        """
        navigation_attrs = {}

        # Extract PowerPoint-specific navigation attributes
        data_attributes = [
            'data-slide',
            'data-jump',
            'data-bookmark',
            'data-custom-show',
        ]

        for attr_name in data_attributes:
            attr_value = hyperlink_element.get(attr_name)
            if attr_value is not None:
                navigation_attrs[attr_name] = attr_value

        return navigation_attrs

    def _parse_navigation_attributes(self, href: str, element_attrs: dict, tooltip: str) -> Any | None:
        """
        Parse SVG navigation attributes to create navigation spec.

        Args:
            href: Value of href or xlink:href attribute
            element_attrs: Dictionary of data-* navigation attributes
            tooltip: Tooltip text from <title> element

        Returns:
            Navigation spec if valid navigation found, None otherwise
        """
        from ..pipeline.navigation import parse_svg_navigation

        try:
            return parse_svg_navigation(href, element_attrs, tooltip)
        except Exception as e:
            self.logger.warning(f"Failed to parse navigation attributes: {e}")
            return None

    def _extract_recursive_to_ir(self, element: ET.Element, ir_elements: list) -> None:
        """Recursively extract SVG elements and convert to IR, adapting from svg2drawingml.py"""

        # Handle namespace-aware tag extraction (from existing code)
        try:
            tag_str = str(element.tag) if hasattr(element.tag, 'split') else element.tag
            tag = tag_str.split('}')[-1] if '}' in tag_str else tag_str
        except (TypeError, AttributeError):
            tag = getattr(element, 'tag', 'unknown')
            if hasattr(tag, '__call__'):
                tag = str(tag)
            tag = tag.split('}')[-1] if '}' in str(tag) else str(tag)

        # Convert specific element types to IR
        if tag == 'rect':
            ir_element = self._convert_rect_to_ir(element)
            if ir_element:
                ir_elements.append(ir_element)

        elif tag == 'circle':
            ir_element = self._convert_circle_to_ir(element)
            if ir_element:
                ir_elements.append(ir_element)

        elif tag == 'ellipse':
            ir_element = self._convert_ellipse_to_ir(element)
            if ir_element:
                ir_elements.append(ir_element)

        elif tag == 'line':
            ir_element = self._convert_line_to_ir(element)
            if ir_element:
                ir_elements.append(ir_element)

        elif tag == 'path':
            ir_element = self._convert_path_to_ir(element)
            if ir_element:
                ir_elements.append(ir_element)

        elif tag == 'polygon' or tag == 'polyline':
            ir_element = self._convert_polygon_to_ir(element, closed=(tag == 'polygon'))
            if ir_element:
                ir_elements.append(ir_element)

        elif tag == 'text':
            ir_element = self._convert_text_to_ir(element)
            if ir_element:
                ir_elements.append(ir_element)

        elif tag == 'image':
            ir_element = self._convert_image_to_ir(element)
            if ir_element:
                ir_elements.append(ir_element)

        elif tag == 'g':
            ir_element = self._convert_group_to_ir(element)
            if ir_element:
                ir_elements.append(ir_element)

        elif tag == 'a':
            # Handle SVG hyperlink elements
            self._convert_hyperlink_to_ir(element, ir_elements)

        elif tag == 'foreignObject':
            # Handle SVG foreignObject elements
            ir_element = self._convert_foreignobject_to_ir(element)
            if ir_element:
                ir_elements.append(ir_element)

        else:
            # For other elements, recurse into children
            for child in children(element):
                self._extract_recursive_to_ir(child, ir_elements)

    def _convert_rect_to_ir(self, element: ET.Element):
        """Convert SVG rect to IR Path"""
        from ..ir import LineSegment, Path, Point

        # Extract rectangle attributes
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        width = float(element.get('width', 0))
        height = float(element.get('height', 0))

        if width <= 0 or height <= 0:
            return None

        # Create rectangle as closed path
        segments = [
            LineSegment(start=Point(x, y), end=Point(x + width, y)),
            LineSegment(start=Point(x + width, y), end=Point(x + width, y + height)),
            LineSegment(start=Point(x + width, y + height), end=Point(x, y + height)),
            LineSegment(start=Point(x, y + height), end=Point(x, y)),
        ]

        # Extract styling
        fill, stroke, opacity = self._extract_styling(element)

        # Get hyperlink from current context if any
        getattr(self, '_current_hyperlink', None)

        return Path(
            segments=segments,
            fill=fill,
            stroke=stroke,
            opacity=opacity,
        )

    def _convert_circle_to_ir(self, element: ET.Element):
        """Convert SVG circle to IR Path with Bezier curves"""
        from ..ir import BezierSegment, Path, Point

        # Extract circle attributes
        cx = float(element.get('cx', 0))
        cy = float(element.get('cy', 0))
        r = float(element.get('r', 0))

        if r <= 0:
            return None

        # Create circle using 4 Bezier curves (standard approach)
        # Magic constant for circle approximation with Bezier curves
        k = 0.552284749831

        segments = [
            # Top right quadrant
            BezierSegment(
                start=Point(cx + r, cy),
                control1=Point(cx + r, cy - k * r),
                control2=Point(cx + k * r, cy - r),
                end=Point(cx, cy - r),
            ),
            # Top left quadrant
            BezierSegment(
                start=Point(cx, cy - r),
                control1=Point(cx - k * r, cy - r),
                control2=Point(cx - r, cy - k * r),
                end=Point(cx - r, cy),
            ),
            # Bottom left quadrant
            BezierSegment(
                start=Point(cx - r, cy),
                control1=Point(cx - r, cy + k * r),
                control2=Point(cx - k * r, cy + r),
                end=Point(cx, cy + r),
            ),
            # Bottom right quadrant
            BezierSegment(
                start=Point(cx, cy + r),
                control1=Point(cx + k * r, cy + r),
                control2=Point(cx + r, cy + k * r),
                end=Point(cx + r, cy),
            ),
        ]

        # Extract styling
        fill, stroke, opacity = self._extract_styling(element)

        # Get hyperlink from current context if any
        getattr(self, '_current_hyperlink', None)

        return Path(
            segments=segments,
            fill=fill,
            stroke=stroke,
            opacity=opacity,
        )

    def _convert_ellipse_to_ir(self, element: ET.Element):
        """Convert SVG ellipse to IR Path"""
        from ..ir import BezierSegment, Path, Point

        # Extract ellipse attributes
        cx = float(element.get('cx', 0))
        cy = float(element.get('cy', 0))
        rx = float(element.get('rx', 0))
        ry = float(element.get('ry', 0))

        if rx <= 0 or ry <= 0:
            return None

        # Create ellipse using 4 Bezier curves
        kx = 0.552284749831 * rx
        ky = 0.552284749831 * ry

        segments = [
            BezierSegment(
                start=Point(cx + rx, cy),
                control1=Point(cx + rx, cy - ky),
                control2=Point(cx + kx, cy - ry),
                end=Point(cx, cy - ry),
            ),
            BezierSegment(
                start=Point(cx, cy - ry),
                control1=Point(cx - kx, cy - ry),
                control2=Point(cx - rx, cy - ky),
                end=Point(cx - rx, cy),
            ),
            BezierSegment(
                start=Point(cx - rx, cy),
                control1=Point(cx - rx, cy + ky),
                control2=Point(cx - kx, cy + ry),
                end=Point(cx, cy + ry),
            ),
            BezierSegment(
                start=Point(cx, cy + ry),
                control1=Point(cx + kx, cy + ry),
                control2=Point(cx + rx, cy + ky),
                end=Point(cx + rx, cy),
            ),
        ]

        # Extract styling
        fill, stroke, opacity = self._extract_styling(element)

        # Get hyperlink from current context if any
        getattr(self, '_current_hyperlink', None)

        return Path(
            segments=segments,
            fill=fill,
            stroke=stroke,
            opacity=opacity,
        )

    def _convert_line_to_ir(self, element: ET.Element):
        """Convert SVG line to IR Path"""
        from ..ir import LineSegment, Path, Point

        # Extract line attributes
        x1 = float(element.get('x1', 0))
        y1 = float(element.get('y1', 0))
        x2 = float(element.get('x2', 0))
        y2 = float(element.get('y2', 0))

        segments = [LineSegment(start=Point(x1, y1), end=Point(x2, y2))]

        # Extract styling (lines typically only have stroke)
        fill, stroke, opacity = self._extract_styling(element)

        return Path(
            segments=segments,
            fill=None,  # Lines don't have fill
            stroke=stroke,
            opacity=opacity,
        )

    def _convert_path_to_ir(self, element: ET.Element):
        """Convert SVG path to IR Path by parsing d attribute"""
        from ..ir import Path

        d = element.get('d', '')
        if not d:
            return None

        # Use simplified path parsing for now - this could be enhanced
        # to use the existing path parsing from src/paths/parser.py
        segments = self._parse_path_data(d)

        if not segments:
            return None

        # Extract styling
        fill, stroke, opacity = self._extract_styling(element)

        # Get hyperlink from current context if any
        getattr(self, '_current_hyperlink', None)

        return Path(
            segments=segments,
            fill=fill,
            stroke=stroke,
            opacity=opacity,
        )

    def _convert_polygon_to_ir(self, element: ET.Element, closed: bool = True):
        """Convert SVG polygon/polyline to IR Path"""
        from ..ir import LineSegment, Path, Point

        points_str = element.get('points', '')
        if not points_str:
            return None

        # Parse points string - handle both "x1,y1 x2,y2" and "x1 y1 x2 y2" formats
        try:
            points = []
            # First normalize: replace all commas with spaces
            normalized = points_str.replace(',', ' ')
            # Split into individual coordinate values
            coords = [float(x) for x in normalized.split() if x.strip()]

            # Group coordinates into (x, y) pairs
            for i in range(0, len(coords) - 1, 2):
                points.append(Point(coords[i], coords[i + 1]))

            if len(points) < 2:
                return None

            # Create line segments between consecutive points
            segments = []
            for i in range(len(points) - 1):
                segments.append(LineSegment(start=points[i], end=points[i + 1]))

            # Close the polygon if needed
            if closed and len(points) > 2:
                segments.append(LineSegment(start=points[-1], end=points[0]))

            # Extract styling
            fill, stroke, opacity = self._extract_styling(element)

            return Path(
                segments=segments,
                fill=fill if closed else None,  # Only polygons have fill
                stroke=stroke,
                opacity=opacity,
            )
        except (ValueError, IndexError):
            # If parsing fails, return None
            return None

    def _convert_text_to_ir(self, element: ET.Element):
        """Convert SVG text to IR with enhanced tspan support"""
        from ..ir import Point, Rect, RichTextFrame, TextFrame

        # Extract text position
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        position = Point(x, y)

        # Extract text lines with full tspan structure
        lines = self._extract_text_lines(element)
        if not lines:
            return None

        # Check if we need RichTextFrame or can use simple TextFrame
        needs_rich_frame = (
            len(lines) > 1 or  # Multiple lines
            any(len(line.runs) > 1 for line in lines) or  # Multiple runs per line
            any(line.anchor != lines[0].anchor for line in lines[1:])  # Mixed anchors
        )

        if needs_rich_frame:
            # Use RichTextFrame for complex text
            # Estimate bounding box for all lines
            total_height = sum(line.primary_font_size * 1.2 for line in lines)
            max_width = max(
                sum(len(run.text) * run.font_size_pt * 0.6 for run in line.runs)
                for line in lines
            )

            bounds = Rect(x, y, max_width, total_height)

            return RichTextFrame(
                lines=lines,
                position=position,
                bounds=bounds,
                transform=element.get('transform'),
            )
        else:
            # Use simple TextFrame for backward compatibility
            line = lines[0]
            estimated_width = sum(len(run.text) * run.font_size_pt * 0.6 for run in line.runs)
            estimated_height = line.primary_font_size * 1.2

            # Get hyperlink from current context if any
            getattr(self, '_current_hyperlink', None)

            return TextFrame(
                origin=position,
                runs=line.runs,
                bbox=Rect(x, y, estimated_width, estimated_height),
                anchor=line.anchor,
            )

    def _convert_image_to_ir(self, element: ET.Element):
        """Convert SVG image to IR Image"""
        from ..ir import Image, Point, Rect

        # Extract image attributes
        x = float(element.get('x', 0))
        y = float(element.get('y', 0))
        width = float(element.get('width', 0))
        height = float(element.get('height', 0))

        if width <= 0 or height <= 0:
            return None

        # Extract href
        href = element.get('href') or element.get('{http://www.w3.org/1999/xlink}href')
        if not href:
            return None

        # For now, create placeholder with empty data
        # In a full implementation, we'd fetch and decode the image data
        data = b''
        format = 'png'  # Default format

        # Try to determine format from href
        if href.endswith('.jpg') or href.endswith('.jpeg'):
            format = 'jpg'
        elif href.endswith('.gif'):
            format = 'gif'
        elif href.endswith('.svg'):
            format = 'svg'

        # Get hyperlink from current context if any
        getattr(self, '_current_hyperlink', None)

        return Image(
            origin=Point(x, y),
            size=Rect(0, 0, width, height),
            data=data,
            format=format,
            href=href,
            opacity=float(element.get('opacity', 1.0)),
        )

    def _convert_group_to_ir(self, element: ET.Element):
        """Convert SVG group to IR Group"""
        from ..ir import Group

        # Process all children recursively
        child_nodes = []
        for ch in children(element):
            self._extract_recursive_to_ir(ch, child_nodes)

        if not child_nodes:
            return None

        # Get hyperlink from current context if any
        getattr(self, '_current_hyperlink', None)

        # Parse transform matrix if present
        transform_matrix = None
        transform_attr = element.get('transform')
        if transform_attr:
            try:
                from ..transforms.parser import TransformParser
                parser = TransformParser()
                tm = parser.parse_to_matrix(transform_attr)
                if hasattr(tm, 'to_numpy'):
                    tm = tm.to_numpy()
                transform_matrix = tm
            except Exception as e:
                self.logger.warning(f"Failed to parse group transform '{transform_attr}': {e}")

        return Group(
            children=child_nodes,
            opacity=float(element.get('opacity', 1.0)),
            transform=transform_matrix,
        )

    def _extract_styling(self, element: ET.Element):
        """Extract fill, stroke, and opacity from SVG element"""
        from ..ir import SolidPaint, Stroke, StrokeCap, StrokeJoin

        # Extract fill
        fill = None
        fill_attr = element.get('fill', '#000000')
        if fill_attr and fill_attr != 'none':
            if fill_attr.startswith('#'):
                fill = SolidPaint(rgb=fill_attr[1:])
            elif fill_attr.startswith('rgb('):
                # Parse rgb(r,g,b) format - simplified
                rgb_values = fill_attr[4:-1].split(',')
                if len(rgb_values) == 3:
                    r = int(rgb_values[0].strip())
                    g = int(rgb_values[1].strip())
                    b = int(rgb_values[2].strip())
                    rgb_hex = f"{r:02x}{g:02x}{b:02x}"
                    fill = SolidPaint(rgb=rgb_hex)
            else:
                # Named colors or other formats - use default
                fill = SolidPaint(rgb="000000")

        # Extract stroke
        stroke = None
        stroke_attr = element.get('stroke')
        if stroke_attr and stroke_attr != 'none':
            stroke_color = stroke_attr
            if stroke_color.startswith('#'):
                stroke_color = stroke_color[1:]
                # Expand 3-char hex to 6-char (e.g., "333" -> "333333")
                if len(stroke_color) == 3:
                    stroke_color = ''.join(c*2 for c in stroke_color)
            elif stroke_color.startswith('rgb('):
                # Parse rgb format
                rgb_values = stroke_color[4:-1].split(',')
                if len(rgb_values) == 3:
                    r = int(rgb_values[0].strip())
                    g = int(rgb_values[1].strip())
                    b = int(rgb_values[2].strip())
                    stroke_color = f"{r:02x}{g:02x}{b:02x}"
            else:
                stroke_color = "000000"

            stroke_width = float(element.get('stroke-width', 1.0))

            # Parse stroke properties
            stroke_join = StrokeJoin.MITER
            join_attr = element.get('stroke-linejoin', 'miter')
            if join_attr == 'round':
                stroke_join = StrokeJoin.ROUND
            elif join_attr == 'bevel':
                stroke_join = StrokeJoin.BEVEL

            stroke_cap = StrokeCap.BUTT
            cap_attr = element.get('stroke-linecap', 'butt')
            if cap_attr == 'round':
                stroke_cap = StrokeCap.ROUND
            elif cap_attr == 'square':
                stroke_cap = StrokeCap.SQUARE

            stroke = Stroke(
                paint=SolidPaint(rgb=stroke_color),
                width=stroke_width,
                join=stroke_join,
                cap=stroke_cap,
            )

        # Extract opacity
        opacity = float(element.get('opacity', 1.0))

        return fill, stroke, opacity

    def _extract_text_content(self, element: ET.Element) -> str:
        """Extract text content from text element and its children"""
        text_parts = []

        # Get direct text content
        if element.text:
            text_parts.append(element.text)

        # Process child elements (like tspan)
        for child in children(element):
            if self._get_local_tag(child.tag) == 'tspan':
                if child.text:
                    text_parts.append(child.text)
                # Handle tail text after tspan
                if child.tail:
                    text_parts.append(child.tail)
            elif child.text:
                text_parts.append(child.text)

        # Handle tail text
        if element.tail:
            text_parts.append(element.tail)

        return ''.join(text_parts).strip()

    def _extract_text_lines(self, element: ET.Element) -> list:
        """Extract text lines with tspan structure preserved

        Returns List[TextLine] with proper style inheritance and line breaks.
        Positioned tspans (with x/y attributes) create new lines.
        """
        from ..ir import TextAnchor, TextLine

        # Get base style from parent text element
        base_style = self._read_text_style(element)

        # Extract text anchor for the entire text element
        text_anchor_str = element.get('text-anchor', 'start')
        default_anchor = {
            'start': TextAnchor.START,
            'middle': TextAnchor.MIDDLE,
            'end': TextAnchor.END,
        }.get(text_anchor_str, TextAnchor.START)

        lines = []
        current_runs = []

        # Process direct text content first
        if element.text and element.text.strip():
            run = self._create_text_run(element.text.strip(), base_style)
            if run:
                current_runs.append(run)

        # Process child elements (tspan, etc.)
        for child in children(element):
            tag = self._get_local_tag(child.tag)

            if tag == 'tspan':
                # Check if this tspan starts a new line (positioned tspan)
                if child.get('x') is not None or child.get('y') is not None:
                    # Finish current line if it has content
                    if current_runs:
                        lines.append(TextLine(runs=current_runs, anchor=default_anchor))
                        current_runs = []

                # Get inherited style for this tspan
                tspan_style = self._merge_text_styles(base_style, self._read_text_style(child))

                # Extract tspan content
                if child.text and child.text.strip():
                    run = self._create_text_run(child.text.strip(), tspan_style)
                    if run:
                        current_runs.append(run)

                # Handle tail text after tspan
                if child.tail and child.tail.strip():
                    # Tail text uses parent style
                    run = self._create_text_run(child.tail.strip(), base_style)
                    if run:
                        current_runs.append(run)
            else:
                # Handle other child elements
                if child.text and child.text.strip():
                    run = self._create_text_run(child.text.strip(), base_style)
                    if run:
                        current_runs.append(run)

                if child.tail and child.tail.strip():
                    run = self._create_text_run(child.tail.strip(), base_style)
                    if run:
                        current_runs.append(run)

        # Add final line if it has content
        if current_runs:
            lines.append(TextLine(runs=current_runs, anchor=default_anchor))

        # If no lines were created but we have element text, create a basic line
        if not lines and element.text:
            run = self._create_text_run(element.text.strip(), base_style)
            if run:
                lines.append(TextLine(runs=[run], anchor=default_anchor))

        return lines

    def _read_text_style(self, element: ET.Element) -> dict:
        """Read text styling from element attributes and CSS styles

        Returns dict with normalized style properties for text rendering.
        """
        style = {
            'font_family': 'Arial',
            'font_size_pt': 12.0,
            'font_weight': 'normal',
            'font_style': 'normal',
            'text_decoration': 'none',
            'fill': '000000',  # Default black
        }

        # Extract from direct attributes
        if element.get('font-family'):
            style['font_family'] = element.get('font-family')

        if element.get('font-size'):
            style['font_size_pt'] = self._parse_font_size(element.get('font-size'))

        if element.get('font-weight'):
            style['font_weight'] = self._normalize_font_weight(element.get('font-weight'))

        if element.get('font-style'):
            style['font_style'] = element.get('font-style')

        if element.get('text-decoration'):
            style['text_decoration'] = element.get('text-decoration')

        # Extract fill color
        if element.get('fill'):
            style['fill'] = self._parse_color_value(element.get('fill'))

        # Parse style attribute if present
        if element.get('style'):
            css_styles = self._parse_css_style(element.get('style'))
            style.update(css_styles)

        return style

    def _merge_text_styles(self, parent_style: dict, child_style: dict) -> dict:
        """Merge parent and child styles with proper inheritance

        Child styles override parent where specified, following CSS inheritance rules.
        """
        merged = parent_style.copy()

        # Override with child styles where specified
        for key, value in child_style.items():
            if value is not None and value != '':
                merged[key] = value

        return merged

    def _create_text_run(self, text: str, style: dict):
        """Create a Run from text and style dictionary"""
        from ..ir import Run

        if not text or not text.strip():
            return None

        # Parse color value
        rgb = self._parse_color_value(style.get('fill', '000000'))

        # Handle font weight
        font_weight = style.get('font_weight', 'normal')
        is_bold = (
            font_weight == 'bold' or
            font_weight == 'bolder' or
            (font_weight.isdigit() and int(font_weight) >= FONT_WEIGHT_BOLD_THRESHOLD)
        )

        # Handle text decoration
        text_decoration = style.get('text_decoration', 'none')
        is_underline = 'underline' in text_decoration
        is_strike = 'line-through' in text_decoration

        try:
            return Run(
                text=text,
                font_family=style.get('font_family', 'Arial'),
                font_size_pt=style.get('font_size_pt', 12.0),
                bold=is_bold,
                italic=style.get('font_style') == 'italic',
                underline=is_underline,
                strike=is_strike,
                rgb=rgb,
            )
        except ValueError as e:
            # Log error but continue with fallback
            self.logger.warning(f"Error creating text run: {e}")
            return None

    def _normalize_font_weight(self, weight_str: str) -> str:
        """Normalize font weight values to standard form"""
        weight_str = weight_str.lower().strip()

        # Map numeric weights
        weight_map = {
            '100': 'lighter', '200': 'lighter', '300': 'light',
            '400': 'normal', '500': 'normal', '600': 'semibold',
            '700': 'bold', '800': 'bolder', '900': 'bolder',
        }

        return weight_map.get(weight_str, weight_str)

    def _parse_color_value(self, color_str: str) -> str:
        """Parse color value to RRGGBB format"""
        if not color_str or color_str == 'none':
            return '000000'

        color_str = color_str.strip()

        # Handle hex colors
        if color_str.startswith('#'):
            hex_color = color_str[1:]
            if len(hex_color) == 3:
                # Expand short hex (e.g., #f0a -> #ff00aa)
                hex_color = ''.join(c*2 for c in hex_color)
            if len(hex_color) == 6:
                return hex_color.upper()

        # Handle rgb() format
        if color_str.startswith('rgb(') and color_str.endswith(')'):
            rgb_values = color_str[4:-1].split(',')
            if len(rgb_values) == 3:
                try:
                    r = int(rgb_values[0].strip())
                    g = int(rgb_values[1].strip())
                    b = int(rgb_values[2].strip())
                    return f"{r:02X}{g:02X}{b:02X}"
                except ValueError:
                    pass

        # Handle named colors (basic set)
        named_colors = {
            'black': '000000', 'white': 'FFFFFF', 'red': 'FF0000',
            'green': '008000', 'blue': '0000FF', 'yellow': 'FFFF00',
            'cyan': '00FFFF', 'magenta': 'FF00FF', 'gray': '808080',
            'grey': '808080', 'silver': 'C0C0C0', 'maroon': '800000',
            'navy': '000080', 'lime': '00FF00', 'olive': '808000',
            'purple': '800080', 'teal': '008080', 'aqua': '00FFFF',
        }

        return named_colors.get(color_str.lower(), '000000')

    def _parse_css_style(self, style_str: str) -> dict:
        """Parse CSS style attribute into style dictionary"""
        styles = {}
        if not style_str:
            return styles

        # Split on semicolons and parse key:value pairs
        for declaration in style_str.split(';'):
            if ':' in declaration:
                key, value = declaration.split(':', 1)
                key = key.strip().replace('-', '_')  # Convert to underscore format
                value = value.strip()

                # Map CSS properties to our style keys
                css_map = {
                    'font_family': 'font_family',
                    'font_size': 'font_size_pt',
                    'font_weight': 'font_weight',
                    'font_style': 'font_style',
                    'text_decoration': 'text_decoration',
                    'fill': 'fill',
                }

                # Handle font-family with quotes
                if key == 'font_family':
                    value = value.strip('\'"')  # Remove quotes

                if key in css_map:
                    if key == 'font_size':
                        styles[css_map[key]] = self._parse_font_size(value)
                    elif key == 'fill':
                        styles[css_map[key]] = self._parse_color_value(value)
                    else:
                        styles[css_map[key]] = value

        return styles

    def _parse_font_size(self, font_size_str: str) -> float:
        """Parse font size from string to points"""
        if not font_size_str:
            return 12.0

        # Remove units and parse
        font_size_str = font_size_str.strip()
        if font_size_str.endswith('px'):
            return float(font_size_str[:-2]) * 0.75  # Convert px to pt
        elif font_size_str.endswith('pt'):
            return float(font_size_str[:-2])
        elif font_size_str.endswith('em'):
            return float(font_size_str[:-2]) * 12  # Assume 12pt base
        else:
            try:
                return float(font_size_str)
            except ValueError:
                return 12.0

    def _parse_path_data(self, d: str):
        """Basic path data parser - simplified version"""
        from ..ir import BezierSegment, LineSegment, Point

        segments = []

        # Very simplified path parsing - just handle basic commands
        # In a full implementation, this would use the existing path parser
        commands = re.findall(r'[MmLlHhVvCcSsQqTtAaZz][^MmLlHhVvCcSsQqTtAaZz]*', d)

        current_point = Point(0, 0)
        last_control = None  # Track last control point for T command

        for command in commands:
            cmd = command[0]
            params = command[1:].replace(',', ' ').split()
            coords = [float(p) for p in params if p]

            if cmd.upper() == 'M':  # Move to
                if len(coords) >= 2:
                    if cmd.isupper():
                        current_point = Point(coords[0], coords[1])
                    else:
                        current_point = Point(current_point.x + coords[0], current_point.y + coords[1])
                last_control = None

            elif cmd.upper() == 'L':  # Line to
                if len(coords) >= 2:
                    if cmd.isupper():
                        end_point = Point(coords[0], coords[1])
                    else:
                        end_point = Point(current_point.x + coords[0], current_point.y + coords[1])
                    segments.append(LineSegment(start=current_point, end=end_point))
                    current_point = end_point
                last_control = None

            elif cmd.upper() == 'H':  # Horizontal line
                if len(coords) >= 1:
                    if cmd.isupper():
                        end_point = Point(coords[0], current_point.y)
                    else:
                        end_point = Point(current_point.x + coords[0], current_point.y)
                    segments.append(LineSegment(start=current_point, end=end_point))
                    current_point = end_point
                last_control = None

            elif cmd.upper() == 'V':  # Vertical line
                if len(coords) >= 1:
                    if cmd.isupper():
                        end_point = Point(current_point.x, coords[0])
                    else:
                        end_point = Point(current_point.x, current_point.y + coords[0])
                    segments.append(LineSegment(start=current_point, end=end_point))
                    current_point = end_point
                last_control = None

            elif cmd.upper() == 'C':  # Cubic Bezier
                if len(coords) >= 6:
                    if cmd.isupper():
                        control1 = Point(coords[0], coords[1])
                        control2 = Point(coords[2], coords[3])
                        end_point = Point(coords[4], coords[5])
                    else:
                        control1 = Point(current_point.x + coords[0], current_point.y + coords[1])
                        control2 = Point(current_point.x + coords[2], current_point.y + coords[3])
                        end_point = Point(current_point.x + coords[4], current_point.y + coords[5])
                    segments.append(BezierSegment(start=current_point, control1=control1, control2=control2, end=end_point))
                    last_control = control2
                    current_point = end_point

            elif cmd.upper() == 'Q':  # Quadratic Bezier - convert to cubic
                if len(coords) >= 4:
                    # Get quadratic control point and end point
                    if cmd.isupper():
                        qcp = Point(coords[0], coords[1])
                        end_point = Point(coords[2], coords[3])
                    else:
                        qcp = Point(current_point.x + coords[0], current_point.y + coords[1])
                        end_point = Point(current_point.x + coords[2], current_point.y + coords[3])

                    # Convert Q to C using formula: CP1 = P0 + 2/3*(QCP - P0), CP2 = P2 + 2/3*(QCP - P2)
                    control1 = Point(
                        current_point.x + 2/3 * (qcp.x - current_point.x),
                        current_point.y + 2/3 * (qcp.y - current_point.y),
                    )
                    control2 = Point(
                        end_point.x + 2/3 * (qcp.x - end_point.x),
                        end_point.y + 2/3 * (qcp.y - end_point.y),
                    )

                    segments.append(BezierSegment(start=current_point, control1=control1, control2=control2, end=end_point))
                    last_control = qcp  # Store quadratic control for T command
                    current_point = end_point

            elif cmd.upper() == 'T':  # Smooth quadratic - convert to cubic
                if len(coords) >= 2:
                    # Calculate reflected control point
                    if last_control:
                        qcp = Point(
                            2 * current_point.x - last_control.x,
                            2 * current_point.y - last_control.y,
                        )
                    else:
                        qcp = current_point

                    # Get end point
                    if cmd.isupper():
                        end_point = Point(coords[0], coords[1])
                    else:
                        end_point = Point(current_point.x + coords[0], current_point.y + coords[1])

                    # Convert to cubic
                    control1 = Point(
                        current_point.x + 2/3 * (qcp.x - current_point.x),
                        current_point.y + 2/3 * (qcp.y - current_point.y),
                    )
                    control2 = Point(
                        end_point.x + 2/3 * (qcp.x - end_point.x),
                        end_point.y + 2/3 * (qcp.y - end_point.y),
                    )

                    segments.append(BezierSegment(start=current_point, control1=control1, control2=control2, end=end_point))
                    last_control = qcp
                    current_point = end_point

        return segments

    def _convert_foreignobject_to_ir(self, element: ET.Element):
        """
        Convert SVG foreignObject to appropriate IR element.

        This method implements the ForeignObject conversion strategy:
        1. Parse geometry (x, y, width, height) and transforms
        2. Detect payload content type (nested SVG, image, XHTML, etc.)
        3. Convert to appropriate IR element type based on content
        4. Apply bbox clipping for content that exceeds boundaries

        Returns:
            IR element (Group for nested SVG, Image for embedded content,
            Path for complex fallback content) or None if conversion fails
        """
        from ..ir import Rect

        try:
            # Extract geometry attributes (using same pattern as existing converters)
            x = float(element.get('x', 0))
            y = float(element.get('y', 0))
            width = float(element.get('width', 0))
            height = float(element.get('height', 0))

            # Validate dimensions
            if width <= 0 or height <= 0:
                self.logger.warning(f"ForeignObject has invalid dimensions: {width}x{height}")
                return None

            # Extract transform information (store as string like other converters)
            transform_attr = element.get('transform')

            # Create bounding rectangle for clipping
            bbox = Rect(x, y, width, height)

            # Detect payload content type
            payload_element = self._get_first_payload_child(element)
            if payload_element is None:
                self.logger.warning("ForeignObject has no content")
                return None

            payload_type = self._classify_payload_type(payload_element)

            # Calculate complexity score for routing decisions
            complexity_score = self._calculate_payload_complexity(payload_element, payload_type)
            self.logger.debug(f"ForeignObject payload type: {payload_type}, complexity: {complexity_score}")

            # Convert based on payload type
            if payload_type == "nested_svg":
                return self._convert_nested_svg_to_ir(payload_element, bbox, transform_attr)
            elif payload_type == "image":
                return self._convert_image_payload_to_ir(payload_element, bbox, transform_attr)
            elif payload_type == "xhtml":
                return self._convert_xhtml_to_ir(payload_element, bbox, transform_attr)
            else:
                # Fallback: create placeholder group for unknown content
                return self._create_foreignobject_placeholder(bbox, transform_attr, payload_type)

        except Exception as e:
            self.logger.error(f"Failed to convert foreignObject to IR: {e}")
            return None

    def _get_first_payload_child(self, foreignobject_element: ET.Element):
        """Get the first significant child element from foreignObject"""
        for child in children(foreignobject_element):
            if child.tag and not child.tag.startswith("{"):
                return child
            # Handle namespaced elements
            tag = child.tag.split('}')[-1] if '}' in str(child.tag) else str(child.tag)
            if tag and tag not in ['defs', 'metadata', 'title', 'desc']:
                return child
        return None

    def _classify_payload_type(self, payload_element: ET.Element) -> str:
        """
        Classify the payload content type for routing to appropriate converter.

        Analyzes the payload element and its namespace to determine the best
        conversion strategy. Supports nested SVG, images, XHTML, MathML, and
        provides fallback for unknown content.
        """
        if not payload_element.tag:
            return "unknown"

        # Extract tag and namespace
        tag_str = str(payload_element.tag)
        if '}' in tag_str:
            namespace, tag = tag_str.split('}', 1)
            namespace = namespace[1:]  # Remove leading {
        else:
            namespace = ""
            tag = tag_str

        # Priority 1: Nested SVG (highest fidelity)
        if tag == 'svg' and 'svg' in namespace.lower():
            return "nested_svg"

        # Priority 2: Image content (direct mapping)
        image_tags = ['img', 'image', 'object', 'picture']
        if tag in image_tags:
            # Verify it has image source
            if (payload_element.get('src') or
                payload_element.get('href') or
                payload_element.get('xlink:href') or
                payload_element.get('{http://www.w3.org/1999/xlink}href')):
                return "image"

        # Priority 3: XHTML content (moderate complexity)
        xhtml_tags = [
            'p', 'div', 'span', 'table', 'tbody', 'tr', 'td', 'th',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'dl', 'dt', 'dd',
            'a', 'em', 'strong', 'b', 'i', 'u',
            'br', 'hr', 'pre', 'code', 'blockquote',
        ]
        if tag in xhtml_tags or "xhtml" in namespace.lower() or "html" in namespace.lower():
            return "xhtml"

        # Priority 4: MathML content (high complexity)
        mathml_tags = ['math', 'mi', 'mo', 'mn', 'mrow', 'mfrac', 'msup', 'msub']
        if tag in mathml_tags or "mathml" in namespace.lower():
            return "mathml"

        # Priority 5: Check for container elements that might contain supported content
        container_tags = ['body', 'article', 'section', 'main', 'aside', 'header', 'footer']
        if tag in container_tags:
            # Look for supported content inside
            child_type = self._analyze_container_content(payload_element)
            if child_type != "unknown":
                return child_type

        # Fallback: unknown content (will use placeholder)
        return "unknown"

    def _analyze_container_content(self, container_element: ET.Element) -> str:
        """Analyze container element to detect primary content type"""
        from ..xml.safe_iter import children

        content_types = {"nested_svg": 0, "image": 0, "xhtml": 0, "mathml": 0}

        for child in children(container_element):
            child_type = self._classify_payload_type(child)
            if child_type in content_types:
                content_types[child_type] += 1

        # Return the most common type, or unknown if no clear winner
        max_count = max(content_types.values())
        if max_count > 0:
            for content_type, count in content_types.items():
                if count == max_count:
                    return content_type

        return "unknown"

    def _convert_nested_svg_to_ir(self, svg_element: ET.Element, bbox, transform_attr):
        """Convert nested SVG to IR Group with proper viewport handling"""
        from ..ir import Group

        # Create child IR elements by recursively parsing the nested SVG
        child_elements = []
        self._extract_recursive_to_ir(svg_element, child_elements)

        # Parse transform matrix if present
        transform_matrix = None
        if transform_attr:
            try:
                from ..transforms.parser import TransformParser
                parser = TransformParser()
                transform_matrix = parser.parse_to_matrix(transform_attr)
                if hasattr(transform_matrix, 'to_numpy'):
                    transform_matrix = transform_matrix.to_numpy()
            except Exception as e:
                self.logger.warning(f"Failed to parse transform '{transform_attr}': {e}")

        # Create group with transform
        return Group(
            children=child_elements,
            clip=None,  # TODO: Implement bbox clipping in future enhancement
            # PRIORITY: LOW - Edge case for oversized text
            # EFFORT: 2 hours - Bbox calculation and clipping logic
            # BLOCKER: None - Can be implemented when needed
            transform=transform_matrix,
        )

    def _convert_image_payload_to_ir(self, img_element: ET.Element, bbox, transform_attr):
        """Convert image payload to IR Image"""
        from ..ir import Image, Point

        # Extract image source
        href = (img_element.get('src') or
                img_element.get('href') or
                img_element.get('xlink:href') or
                img_element.get('{http://www.w3.org/1999/xlink}href'))

        if not href:
            self.logger.warning("Image element in foreignObject has no source")
            return None

        # Parse transform matrix if present
        transform_matrix = None
        if transform_attr:
            try:
                from ..transforms.parser import TransformParser
                parser = TransformParser()
                transform_matrix = parser.parse_to_matrix(transform_attr)
                if hasattr(transform_matrix, 'to_numpy'):
                    transform_matrix = transform_matrix.to_numpy()
            except Exception as e:
                self.logger.warning(f"Failed to parse transform '{transform_attr}': {e}")

        # Create image with transform (actual data loading would happen in processing pipeline)
        return Image(
            origin=Point(bbox.x, bbox.y),
            size=bbox,
            data=b'',  # Placeholder - actual loading happens later
            format="png",  # Default format
            href=href,
            clip=None,  # TODO: Implement bbox clipping if image exceeds dimensions
            # PRIORITY: LOW - Edge case for oversized images
            # EFFORT: 2 hours - Image bbox clipping
            # BLOCKER: None - Can be implemented when needed
            opacity=1.0,
            transform=transform_matrix,
        )

    def _convert_xhtml_to_ir(self, xhtml_element: ET.Element, bbox, transform_attr):
        """Convert XHTML content to IR TextFrame (simplified implementation)"""
        from ..ir import Point, Run, TextAnchor, TextFrame

        # Extract text content (very basic implementation)
        text_content = self._extract_xhtml_text_content(xhtml_element)
        if not text_content.strip():
            return None

        # Create basic text run
        run = Run(
            text=text_content,
            font_family="Arial",  # Default font
            font_size_pt=12.0,
            bold=False,
            italic=False,
        )

        return TextFrame(
            origin=Point(bbox.x, bbox.y),
            bbox=bbox,
            runs=[run],
            anchor=TextAnchor.START,
        )

    def _extract_xhtml_text_content(self, element: ET.Element) -> str:
        """Extract all text content from an XHTML element tree"""
        text_parts = []

        # Add element's direct text
        if element.text:
            text_parts.append(element.text.strip())

        # Recursively extract from children
        for child in children(element):
            child_text = self._extract_text_content(child)
            if child_text:
                text_parts.append(child_text)

            # Add tail text after child element
            if child.tail:
                text_parts.append(child.tail.strip())

        return ' '.join(text_parts)

    def _create_foreignobject_placeholder(self, bbox, transform_attr, payload_type: str):
        """Create placeholder group for unsupported foreignObject content"""
        from ..ir import Group, LineSegment, Path, Point, SolidPaint, Stroke

        # Create a simple rectangle as placeholder
        x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height

        # Rectangle path segments
        segments = [
            LineSegment(Point(x, y), Point(x + w, y)),         # Top
            LineSegment(Point(x + w, y), Point(x + w, y + h)), # Right
            LineSegment(Point(x + w, y + h), Point(x, y + h)), # Bottom
            LineSegment(Point(x, y + h), Point(x, y)),          # Left
        ]

        placeholder_path = Path(
            segments=segments,
            fill=SolidPaint(rgb="F0F0F0"),  # Light gray fill
            stroke=Stroke(paint=SolidPaint(rgb="999999"), width=1.0),  # Gray border
            opacity=0.5,
        )

        # Parse transform matrix if present
        transform_matrix = None
        if transform_attr:
            try:
                from ..transforms.parser import TransformParser
                parser = TransformParser()
                transform_matrix = parser.parse_to_matrix(transform_attr)
                if hasattr(transform_matrix, 'to_numpy'):
                    transform_matrix = transform_matrix.to_numpy()
            except Exception as e:
                self.logger.warning(f"Failed to parse transform '{transform_attr}': {e}")

        return Group(
            children=[placeholder_path],
            clip=None,
            transform=transform_matrix,
        )

    def _calculate_payload_complexity(self, payload_element: ET.Element, payload_type: str) -> int:
        """
        Calculate complexity score for payload content to aid routing decisions.

        Higher scores indicate more complex content that may require fallback strategies.

        Returns:
            Complexity score (0-100, where 0 = simple, 100 = extremely complex)
        """
        from ..xml.safe_iter import walk

        complexity = 0

        # Base complexity by type
        type_complexity = {
            "nested_svg": 20,    # SVG can be complex but we handle it well
            "image": 10,         # Images are straightforward
            "xhtml": 30,         # XHTML can be moderately complex
            "mathml": 50,        # MathML is complex
            "unknown": 60,        # Unknown content is risky
        }
        complexity += type_complexity.get(payload_type, 40)

        # Count descendant elements (DOM complexity)
        element_count = 0
        for element in walk(payload_element):
            element_count += 1

        # Penalize deep nesting
        if element_count > 10:
            complexity += min(20, element_count - 10)  # Cap at +20

        # Check for complex features
        complex_features = []

        for element in walk(payload_element):
            if not hasattr(element, 'tag'):
                continue

            tag = str(element.tag).split('}')[-1] if '}' in str(element.tag) else str(element.tag)

            # CSS and styling complexity
            if element.get('style'):
                complexity += 5
                complex_features.append("inline_css")

            # JavaScript or scripts (should be blocked for security)
            if tag in ['script', 'object', 'embed', 'iframe']:
                complexity += 25
                complex_features.append("active_content")

            # Complex layout elements
            if tag in ['table', 'form', 'canvas', 'video', 'audio']:
                complexity += 10
                complex_features.append("complex_layout")

            # Media elements
            if tag in ['img', 'image', 'picture', 'source']:
                complexity += 3
                complex_features.append("media")

        # Namespace complexity
        namespaces = set()
        for element in walk(payload_element):
            if hasattr(element, 'tag') and '}' in str(element.tag):
                namespace = str(element.tag).split('}')[0][1:]
                namespaces.add(namespace)

        if len(namespaces) > 2:
            complexity += 10
            complex_features.append("multi_namespace")

        # Cap complexity at 100
        complexity = min(100, complexity)

        if complex_features:
            self.logger.debug(f"Complex features detected: {complex_features}")

        return complexity

    def set_normalization_enabled(self, enabled: bool) -> None:
        """Enable or disable normalization during parsing"""
        self.enable_normalization = enabled
        if enabled and self.normalizer is None:
            self.normalizer = SVGNormalizer()


def create_parser(enable_normalization: bool = True) -> SVGParser:
    """Factory function to create SVGParser"""
    return SVGParser(enable_normalization)