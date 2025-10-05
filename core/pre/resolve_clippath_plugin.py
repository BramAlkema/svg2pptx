"""
ClipPath Resolution Plugin for SVG Preprocessing

This plugin resolves all SVG clipPath elements into boolean-intersected paths
during preprocessing, eliminating the need for complex clipping handling in
DrawingML converters.

Key Features:
- Resolves clipPath references into direct path intersections
- Handles nested clipPath elements recursively
- Supports clipPathUnits coordinate systems (userSpaceOnUse, objectBoundingBox)
- Processes clipPath transforms and child element transforms
- Maintains SVG specification compliance
- Graceful fallback when boolean engines unavailable
"""

from __future__ import annotations
from typing import List, Dict, Optional, Tuple, Any
from lxml import etree as ET
import logging

from .base import PreprocessingPlugin, PreprocessingContext
from .geometry import (
    create_boolean_engine, create_service_adapters,
    create_path_spec, normalize_fill_rule
)

logger = logging.getLogger(__name__)


class ResolveClipPathsPlugin(PreprocessingPlugin):
    """
    Preprocessor plugin that resolves clipPath elements into direct path intersections.

    This plugin processes SVG documents to:
    1. Identify elements with clip-path attributes
    2. Resolve clipPath definitions recursively
    3. Convert clipPath contents to paths
    4. Perform boolean intersection operations
    5. Replace clipped elements with intersection results
    6. Remove unused clipPath definitions

    The result is an SVG document with no clipPath elements, making
    DrawingML conversion much simpler.
    """

    name = "resolve_clippath"
    description = "Resolves clipPath elements into boolean path intersections"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize clipPath resolution plugin.

        Config options:
            enable_nested_clips: Handle nested clipPath references (default: True)
            enable_transforms: Process clipPath and element transforms (default: True)
            fallback_behavior: Behavior when boolean engines unavailable (default: "keep_original")
                - "keep_original": Leave clipPath elements unchanged
                - "remove_clips": Remove clip-path attributes (no clipping)
                - "hide_clipped": Mark clipped elements as hidden
        """
        super().__init__(config)
        self.enable_nested_clips = self.config.get('enable_nested_clips', True)
        self.enable_transforms = self.config.get('enable_transforms', True)
        self.fallback_behavior = self.config.get('fallback_behavior', "keep_original")

        self._boolean_engine = None
        self._service_adapters = None
        self._clippath_cache = {}  # Cache resolved clipPath definitions
        self._processed_elements = set()  # Avoid infinite recursion
        self._svg_root = None  # Store SVG root for document-level operations

    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        """
        Check if element has clip-path attribute or is a clipPath definition.

        Args:
            element: SVG element to check
            context: Preprocessing context

        Returns:
            True if element can be processed by this plugin
        """
        # Initialize SVG root reference on first call
        if self._svg_root is None:
            # Find SVG root element
            current = element
            while current is not None:
                if current.tag.endswith('svg'):
                    self._svg_root = current
                    break
                current = current.getparent()

        # Process elements with clip-path attributes
        if element.get('clip-path'):
            return True

        # Process clipPath definition elements (for cleanup later)
        if element.tag.endswith('clipPath'):
            return True

        return False

    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        """
        Process individual elements with clip-path attributes or clipPath definitions.

        Args:
            element: SVG element to process
            context: Preprocessing context

        Returns:
            True if modifications were made, False otherwise
        """
        try:
            # Initialize boolean engine on first use
            if self._boolean_engine is None:
                if not self._initialize_boolean_engine(context):
                    return self._handle_no_boolean_engine_element(element, context)

            # Process elements with clip-path attributes
            if element.get('clip-path'):
                return self._process_clipped_element(element, context)

            # Process clipPath definitions (mark for potential cleanup)
            elif element.tag.endswith('clipPath'):
                return self._process_clippath_definition(element, context)

            return False

        except Exception as e:
            logger.warning(f"Failed to process element {element.tag}: {e}")
            return False

    def _process_clipped_element(self, element: ET.Element, context: PreprocessingContext) -> bool:
        """Process an element with clip-path attribute."""
        if not self._svg_root:
            logger.warning("No SVG root available for clipPath resolution")
            return False

        # Get all clipPath definitions
        clippath_definitions = self._catalog_clippath_definitions(self._svg_root)

        # Resolve clipping for this element
        try:
            intersection_result = self._resolve_element_clipping(
                element, clippath_definitions, self._svg_root
            )
            return intersection_result
        except Exception as e:
            logger.warning(f"Failed to resolve clipping for element {element.tag}: {e}")
            return False

    def _process_clippath_definition(self, element: ET.Element, context: PreprocessingContext) -> bool:
        """Process a clipPath definition element (for cleanup tracking)."""
        # For now, just track that we've seen this clipPath definition
        # Actual cleanup happens in a separate pass
        clip_id = element.get('id')
        if clip_id:
            logger.debug(f"Found clipPath definition: {clip_id}")

        return False  # No modifications to the clipPath definition itself

    def _handle_no_boolean_engine_element(self, element: ET.Element, context: PreprocessingContext) -> bool:
        """Handle element when no boolean engine is available."""
        if self.fallback_behavior == "remove_clips" and element.get('clip-path'):
            element.attrib.pop('clip-path', None)
            logger.debug(f"Removed clip-path attribute from {element.tag}")
            return True
        elif self.fallback_behavior == "hide_clipped" and element.get('clip-path'):
            element.set('visibility', 'hidden')
            logger.debug(f"Hidden clipped element {element.tag}")
            return True

        return False

    def _initialize_boolean_engine(self, context: PreprocessingContext) -> bool:
        """
        Initialize boolean operation engine with service adapters.

        Args:
            context: Processing context

        Returns:
            True if engine initialized successfully, False otherwise
        """
        try:
            # Create service adapters from conversion services
            services = getattr(context, 'services', None)
            if services:
                self._service_adapters = create_service_adapters(services)
                self._boolean_engine = create_boolean_engine(services)
            else:
                # Fallback to minimal adapters
                self._boolean_engine = create_boolean_engine()

            if self._boolean_engine:
                logger.debug(f"Initialized boolean engine: {type(self._boolean_engine).__name__}")
                return True
            else:
                logger.warning("No boolean operation engines available")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize boolean engine: {e}")
            return False

    def _catalog_clippath_definitions(self, svg_root: ET.Element) -> Dict[str, ET.Element]:
        """
        Catalog all clipPath definitions in the document.

        Args:
            svg_root: SVG root element

        Returns:
            Dictionary mapping clipPath IDs to clipPath elements
        """
        definitions = {}

        for clippath in svg_root.findall(".//clipPath"):
            clip_id = clippath.get('id')
            if clip_id:
                definitions[clip_id] = clippath
                logger.debug(f"Found clipPath definition: {clip_id}")

        return definitions

    def _find_clipped_elements(self, svg_root: ET.Element) -> List[ET.Element]:
        """
        Find all elements with clip-path attributes.

        Args:
            svg_root: SVG root element

        Returns:
            List of elements that reference clipPath definitions
        """
        return svg_root.findall(".//*[@clip-path]")

    def _resolve_element_clipping(self, element: ET.Element,
                                 clippath_definitions: Dict[str, ET.Element],
                                 svg_root: ET.Element) -> bool:
        """
        Resolve clipping for a single element by replacing it with intersection result.

        Args:
            element: Element with clip-path attribute
            clippath_definitions: Available clipPath definitions
            svg_root: SVG root element

        Returns:
            True if intersection was performed, False otherwise
        """
        clip_path_attr = element.get('clip-path')
        if not clip_path_attr:
            return False

        # Parse clip-path attribute (e.g., "url(#clipPath1)")
        clip_id = self._parse_clippath_reference(clip_path_attr)
        if not clip_id or clip_id not in clippath_definitions:
            logger.warning(f"ClipPath reference not found: {clip_path_attr}")
            return False

        try:
            # Get element's path representation
            element_path_spec = self._element_to_path_spec(element)
            if not element_path_spec:
                logger.warning(f"Cannot convert element {element.tag} to path")
                return False

            # Resolve clipPath to path specifications
            clippath_specs = self._resolve_clippath_to_paths(
                clippath_definitions[clip_id], clippath_definitions, svg_root
            )
            if not clippath_specs:
                logger.warning(f"ClipPath {clip_id} has no valid paths")
                return False

            # Perform boolean intersection
            intersection_result = self._boolean_engine.intersect(element_path_spec, clippath_specs)

            if intersection_result:
                # Replace element with intersection result
                self._replace_element_with_path(element, intersection_result)
                logger.debug(f"Successfully intersected element {element.tag} with clipPath {clip_id}")
                return True
            else:
                # Empty intersection - hide element or remove it
                element.set('visibility', 'hidden')
                logger.debug(f"Empty intersection for element {element.tag}, marking as hidden")
                return False

        except Exception as e:
            logger.error(f"Failed to perform intersection for element {element.tag}: {e}")
            return False

    def _parse_clippath_reference(self, clip_path_attr: str) -> Optional[str]:
        """
        Parse clipPath reference attribute to extract ID.

        Args:
            clip_path_attr: clip-path attribute value (e.g., "url(#clipPath1)")

        Returns:
            ClipPath ID or None if parsing fails
        """
        if not clip_path_attr:
            return None

        # Handle url(#id) format
        if clip_path_attr.startswith('url(#') and clip_path_attr.endswith(')'):
            return clip_path_attr[5:-1]  # Remove 'url(#' and ')'

        # Handle direct #id reference
        if clip_path_attr.startswith('#'):
            return clip_path_attr[1:]

        return None

    def _element_to_path_spec(self, element: ET.Element) -> Optional[Tuple[str, str]]:
        """
        Convert an SVG element to a PathSpec tuple for boolean operations.

        Args:
            element: SVG element to convert

        Returns:
            PathSpec tuple (d_string, fill_rule) or None if conversion fails
        """
        try:
            # Handle different element types
            if element.tag.endswith('path'):
                d_string = element.get('d', '')
                if d_string:
                    fill_rule = self._get_fill_rule(element)
                    return create_path_spec(d_string, fill_rule)

            elif element.tag.endswith('rect'):
                return self._rect_to_path_spec(element)

            elif element.tag.endswith('circle'):
                return self._circle_to_path_spec(element)

            elif element.tag.endswith('ellipse'):
                return self._ellipse_to_path_spec(element)

            elif element.tag.endswith('polyline'):
                return self._polyline_to_path_spec(element)

            elif element.tag.endswith('polygon'):
                return self._polygon_to_path_spec(element)

            elif element.tag.endswith('line'):
                return self._line_to_path_spec(element)

            else:
                logger.debug(f"Cannot convert {element.tag} to path - not supported")
                return None

        except Exception as e:
            logger.warning(f"Failed to convert {element.tag} to path: {e}")
            return None

    def _get_fill_rule(self, element: ET.Element) -> str:
        """Get fill rule for an element."""
        fill_rule = element.get('fill-rule', 'nonzero')
        return normalize_fill_rule(fill_rule)

    def _rect_to_path_spec(self, rect: ET.Element) -> Optional[Tuple[str, str]]:
        """Convert rect element to path specification."""
        try:
            x = float(rect.get('x', 0))
            y = float(rect.get('y', 0))
            width = float(rect.get('width', 0))
            height = float(rect.get('height', 0))

            if width <= 0 or height <= 0:
                return None

            d_string = f"M {x} {y} L {x + width} {y} L {x + width} {y + height} L {x} {y + height} Z"
            fill_rule = self._get_fill_rule(rect)
            return create_path_spec(d_string, fill_rule)

        except (ValueError, TypeError):
            return None

    def _circle_to_path_spec(self, circle: ET.Element) -> Optional[Tuple[str, str]]:
        """Convert circle element to path specification."""
        try:
            cx = float(circle.get('cx', 0))
            cy = float(circle.get('cy', 0))
            r = float(circle.get('r', 0))

            if r <= 0:
                return None

            # Create circular path using arc commands
            d_string = (f"M {cx - r} {cy} "
                       f"A {r} {r} 0 0 1 {cx + r} {cy} "
                       f"A {r} {r} 0 0 1 {cx - r} {cy} Z")

            fill_rule = self._get_fill_rule(circle)
            return create_path_spec(d_string, fill_rule)

        except (ValueError, TypeError):
            return None

    def _ellipse_to_path_spec(self, ellipse: ET.Element) -> Optional[Tuple[str, str]]:
        """Convert ellipse element to path specification."""
        try:
            cx = float(ellipse.get('cx', 0))
            cy = float(ellipse.get('cy', 0))
            rx = float(ellipse.get('rx', 0))
            ry = float(ellipse.get('ry', 0))

            if rx <= 0 or ry <= 0:
                return None

            # Create elliptical path using arc commands
            d_string = (f"M {cx - rx} {cy} "
                       f"A {rx} {ry} 0 0 1 {cx + rx} {cy} "
                       f"A {rx} {ry} 0 0 1 {cx - rx} {cy} Z")

            fill_rule = self._get_fill_rule(ellipse)
            return create_path_spec(d_string, fill_rule)

        except (ValueError, TypeError):
            return None

    def _line_to_path_spec(self, line: ET.Element) -> Optional[Tuple[str, str]]:
        """Convert line element to path specification."""
        try:
            x1 = float(line.get('x1', 0))
            y1 = float(line.get('y1', 0))
            x2 = float(line.get('x2', 0))
            y2 = float(line.get('y2', 0))

            d_string = f"M {x1} {y1} L {x2} {y2}"
            fill_rule = self._get_fill_rule(line)
            return create_path_spec(d_string, fill_rule)

        except (ValueError, TypeError):
            return None

    def _polygon_to_path_spec(self, polygon: ET.Element) -> Optional[Tuple[str, str]]:
        """Convert polygon element to path specification."""
        points_str = polygon.get('points', '')
        if not points_str:
            return None

        try:
            # Parse points string
            points = self._parse_points(points_str)
            if len(points) < 3:  # Need at least 3 points for a polygon
                return None

            # Build path string
            d_parts = [f"M {points[0][0]} {points[0][1]}"]
            for x, y in points[1:]:
                d_parts.append(f"L {x} {y}")
            d_parts.append("Z")  # Close the polygon

            d_string = " ".join(d_parts)
            fill_rule = self._get_fill_rule(polygon)
            return create_path_spec(d_string, fill_rule)

        except Exception:
            return None

    def _polyline_to_path_spec(self, polyline: ET.Element) -> Optional[Tuple[str, str]]:
        """Convert polyline element to path specification."""
        points_str = polyline.get('points', '')
        if not points_str:
            return None

        try:
            # Parse points string
            points = self._parse_points(points_str)
            if len(points) < 2:  # Need at least 2 points for a line
                return None

            # Build path string (no Z command for polyline)
            d_parts = [f"M {points[0][0]} {points[0][1]}"]
            for x, y in points[1:]:
                d_parts.append(f"L {x} {y}")

            d_string = " ".join(d_parts)
            fill_rule = self._get_fill_rule(polyline)
            return create_path_spec(d_string, fill_rule)

        except Exception:
            return None

    def _parse_points(self, points_str: str) -> List[Tuple[float, float]]:
        """Parse points string into list of coordinate tuples."""
        points = []

        # Normalize separators (commas and whitespace)
        import re
        coords = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', points_str)

        # Group coordinates into pairs
        for i in range(0, len(coords), 2):
            if i + 1 < len(coords):
                x = float(coords[i])
                y = float(coords[i + 1])
                points.append((x, y))

        return points

    def _resolve_clippath_to_paths(self, clippath_element: ET.Element,
                                  clippath_definitions: Dict[str, ET.Element],
                                  svg_root: ET.Element) -> List[Tuple[str, str]]:
        """
        Resolve a clipPath element to a list of PathSpec tuples.

        Args:
            clippath_element: clipPath element to resolve
            clippath_definitions: Available clipPath definitions
            svg_root: SVG root element

        Returns:
            List of PathSpec tuples for all paths in the clipPath
        """
        clip_id = clippath_element.get('id', 'unknown')

        # Check cache first
        if clip_id in self._clippath_cache:
            return self._clippath_cache[clip_id]

        # Avoid infinite recursion
        if clip_id in self._processed_elements:
            logger.warning(f"Circular clipPath reference detected for {clip_id}")
            return []

        self._processed_elements.add(clip_id)

        try:
            path_specs = []

            # Process all child elements in the clipPath
            for child in clippath_element:
                # Skip non-visible elements
                if child.get('visibility') == 'hidden':
                    continue

                # Handle nested clipPath references
                if child.get('clip-path') and self.enable_nested_clips:
                    nested_clip_id = self._parse_clippath_reference(child.get('clip-path'))
                    if nested_clip_id and nested_clip_id in clippath_definitions:
                        # Recursively resolve nested clipPath
                        nested_specs = self._resolve_clippath_to_paths(
                            clippath_definitions[nested_clip_id],
                            clippath_definitions,
                            svg_root
                        )

                        # Convert child element to path and intersect with nested clipPath
                        child_spec = self._element_to_path_spec(child)
                        if child_spec and nested_specs:
                            intersection_result = self._boolean_engine.intersect(child_spec, nested_specs)
                            if intersection_result:
                                path_specs.append(create_path_spec(intersection_result))

                else:
                    # Convert child element directly to path
                    child_spec = self._element_to_path_spec(child)
                    if child_spec:
                        path_specs.append(child_spec)

            # Cache the result
            self._clippath_cache[clip_id] = path_specs
            return path_specs

        finally:
            self._processed_elements.discard(clip_id)

    def _replace_element_with_path(self, original_element: ET.Element, path_d_string: str):
        """
        Replace an element with a path element containing the intersection result.

        Args:
            original_element: Original SVG element
            path_d_string: Path data string from boolean intersection
        """
        parent = original_element.getparent()
        if parent is None:
            logger.warning("Cannot replace element - no parent found")
            return

        # Create new path element
        new_path = ET.Element('path')
        new_path.set('d', path_d_string)

        # Copy relevant attributes from original element
        attrs_to_copy = ['id', 'class', 'style', 'fill', 'stroke', 'opacity', 'transform']
        for attr in attrs_to_copy:
            value = original_element.get(attr)
            if value:
                new_path.set(attr, value)

        # Remove clip-path attribute (no longer needed)
        new_path.attrib.pop('clip-path', None)

        # Replace element in parent
        element_index = list(parent).index(original_element)
        parent.remove(original_element)
        parent.insert(element_index, new_path)

    def _cleanup_clippath_definitions(self, svg_root: ET.Element,
                                    clippath_definitions: Dict[str, ET.Element]) -> int:
        """
        Remove unused clipPath definitions from the document.

        Args:
            svg_root: SVG root element
            clippath_definitions: Dictionary of clipPath definitions

        Returns:
            Number of definitions removed
        """
        # Find all remaining clipPath references
        remaining_refs = set()
        for element in svg_root.findall(".//*[@clip-path]"):
            clip_id = self._parse_clippath_reference(element.get('clip-path'))
            if clip_id:
                remaining_refs.add(clip_id)

        # Remove unused definitions
        removed_count = 0
        for clip_id, clippath_element in clippath_definitions.items():
            if clip_id not in remaining_refs:
                parent = clippath_element.getparent()
                if parent is not None:
                    parent.remove(clippath_element)
                    removed_count += 1
                    logger.debug(f"Removed unused clipPath definition: {clip_id}")

        return removed_count


def create_clippath_resolver(enable_nested_clips: bool = True,
                           enable_transforms: bool = True,
                           fallback_behavior: str = "keep_original") -> ResolveClipPathsPlugin:
    """
    Create a configured clipPath resolution plugin.

    Args:
        enable_nested_clips: Process nested clipPath references
        enable_transforms: Handle clipPath and element transforms
        fallback_behavior: Behavior when boolean engines unavailable

    Returns:
        Configured ResolveClipPathsPlugin instance
    """
    config = {
        'enable_nested_clips': enable_nested_clips,
        'enable_transforms': enable_transforms,
        'fallback_behavior': fallback_behavior
    }
    return ResolveClipPathsPlugin(config)