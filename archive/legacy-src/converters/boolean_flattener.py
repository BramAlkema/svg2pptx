#!/usr/bin/env python3
"""
Boolean ClipPath Flattener

This module handles boolean operations for flattening nested clipPaths into
single composite paths. Moved from preprocessing to preserve information
until conversion time.

Key Features:
- Nested clipPath chain resolution
- Boolean intersection operations
- Element-to-path conversion
- Path specification caching
"""

from __future__ import annotations
from typing import List, Dict, Set, Optional, Tuple, Any
from lxml import etree as ET
import logging

from .clippath_types import ClipPathDefinition
from ..preprocessing.geometry import (
    create_path_spec, normalize_fill_rule, create_boolean_engine
)

logger = logging.getLogger(__name__)


class BooleanFlattener:
    """
    Flattens nested clipPaths using boolean operations.

    This class handles the conversion of complex nested clipPath structures
    into single composite paths that can be used with custGeom or EMF.
    """

    def __init__(self, services=None):
        """
        Initialize BooleanFlattener.

        Args:
            services: ConversionServices for boolean engine creation
        """
        self.services = services
        self._boolean_engine = None
        self._clippath_cache: Dict[str, List[Tuple[str, str]]] = {}
        self._processed_elements: Set[str] = set()

    def flatten_nested_clipaths(self, clip_chain: List[ClipPathDefinition]) -> Optional[str]:
        """
        Flatten a chain of nested clipPaths into a single path.

        Args:
            clip_chain: List of ClipPathDefinition objects to flatten

        Returns:
            Single path data string or None if flattening fails
        """
        if not clip_chain:
            return None

        try:
            # Initialize boolean engine if needed
            if not self._initialize_boolean_engine():
                logger.warning("No boolean engine available for flattening")
                return None

            # Convert all clipPaths to path specifications
            all_path_specs = []
            for clip_def in clip_chain:
                path_specs = self._clippath_definition_to_paths(clip_def)
                all_path_specs.extend(path_specs)

            if not all_path_specs:
                logger.warning("No valid paths found in clipPath chain")
                return None

            # Perform boolean intersection of all paths
            result_path = self._boolean_intersect_all(all_path_specs)
            return result_path

        except Exception as e:
            logger.error(f"Failed to flatten clipPath chain: {e}")
            return None

    def resolve_clippath_chain(self, clip_def: ClipPathDefinition,
                              clippath_definitions: Dict[str, ClipPathDefinition]) -> List[ClipPathDefinition]:
        """
        Resolve nested clipPath references into a chain.

        Args:
            clip_def: Starting clipPath definition
            clippath_definitions: Available clipPath definitions

        Returns:
            List of ClipPathDefinition objects in resolution order
        """
        return self._resolve_clippath_chain_recursive(clip_def, clippath_definitions, set())

    def boolean_intersect_paths(self, path_specs: List[Tuple[str, str]]) -> Optional[str]:
        """
        Perform boolean intersection on multiple path specifications.

        Args:
            path_specs: List of (path_data, fill_rule) tuples

        Returns:
            Intersection result path data or None if operation fails
        """
        if not path_specs:
            return None

        try:
            if not self._initialize_boolean_engine():
                return None

            return self._boolean_intersect_all(path_specs)

        except Exception as e:
            logger.error(f"Boolean intersection failed: {e}")
            return None

    def element_to_path_spec(self, element: ET.Element) -> Optional[Tuple[str, str]]:
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

    def _initialize_boolean_engine(self) -> bool:
        """Initialize boolean operation engine."""
        if self._boolean_engine is not None:
            return True

        try:
            if self.services:
                self._boolean_engine = create_boolean_engine(self.services)
            else:
                self._boolean_engine = create_boolean_engine()

            return self._boolean_engine is not None

        except Exception as e:
            logger.error(f"Failed to initialize boolean engine: {e}")
            return False

    def _resolve_clippath_chain_recursive(self, clip_def: ClipPathDefinition,
                                        clippath_definitions: Dict[str, ClipPathDefinition],
                                        visited: Set[str]) -> List[ClipPathDefinition]:
        """Recursively resolve clipPath chain."""
        if clip_def.id in visited:
            logger.warning(f"Circular clipPath reference detected: {clip_def.id}")
            return []

        visited.add(clip_def.id)
        chain = [clip_def]

        # Check for nested clipPath references in shapes
        if clip_def.shapes:
            for shape in clip_def.shapes:
                nested_ref = shape.get('clip-path')
                if nested_ref:
                    nested_id = self._parse_clippath_reference(nested_ref)
                    if nested_id and nested_id in clippath_definitions:
                        nested_chain = self._resolve_clippath_chain_recursive(
                            clippath_definitions[nested_id], clippath_definitions, visited.copy()
                        )
                        chain.extend(nested_chain)

        visited.discard(clip_def.id)
        return chain

    def _clippath_definition_to_paths(self, clip_def: ClipPathDefinition) -> List[Tuple[str, str]]:
        """Convert ClipPathDefinition to list of path specifications."""
        path_specs = []

        # Handle direct path data
        if clip_def.path_data:
            fill_rule = normalize_fill_rule(clip_def.clip_rule)
            path_specs.append(create_path_spec(clip_def.path_data, fill_rule))

        # Handle shape elements
        if clip_def.shapes:
            for shape in clip_def.shapes:
                # Skip non-visible elements
                if shape.get('visibility') == 'hidden':
                    continue

                shape_spec = self.element_to_path_spec(shape)
                if shape_spec:
                    path_specs.append(shape_spec)

        return path_specs

    def _boolean_intersect_all(self, path_specs: List[Tuple[str, str]]) -> Optional[str]:
        """Perform boolean intersection on all path specifications."""
        if not path_specs:
            return None

        if len(path_specs) == 1:
            return path_specs[0][0]  # Return the path data

        try:
            # Start with first path
            result = path_specs[0]

            # Intersect with each subsequent path
            for path_spec in path_specs[1:]:
                result = self._boolean_engine.intersect(result, [path_spec])
                if not result:
                    logger.debug("Empty intersection result")
                    return None

            # Extract path data from result
            if isinstance(result, tuple):
                return result[0]
            elif isinstance(result, str):
                return result
            else:
                logger.warning(f"Unexpected boolean result type: {type(result)}")
                return None

        except Exception as e:
            logger.error(f"Boolean intersection operation failed: {e}")
            return None

    def _parse_clippath_reference(self, clip_ref: str) -> Optional[str]:
        """Parse clipPath reference to extract ID."""
        if not clip_ref:
            return None

        # Handle url(#id) format
        if clip_ref.startswith('url(#') and clip_ref.endswith(')'):
            return clip_ref[5:-1]

        # Handle direct #id reference
        if clip_ref.startswith('#'):
            return clip_ref[1:]

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

    def clear_cache(self) -> None:
        """Clear path specification cache."""
        self._clippath_cache.clear()
        self._processed_elements.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'cache_size': len(self._clippath_cache),
            'processed_count': len(self._processed_elements)
        }