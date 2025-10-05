#!/usr/bin/env python3
"""
CTM (Current Transformation Matrix) Utilities for Viewport System

Provides tree walking and CTM propagation utilities for proper
coordinate transformation through SVG element hierarchies.
"""

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np
from lxml import etree as ET

if TYPE_CHECKING:
    from ..converters.base import ConversionContext, ConverterRegistry
    from ..services.conversion_services import ConversionServices

logger = logging.getLogger(__name__)


def create_root_context_with_viewport(svg_root: ET.Element, services: 'ConversionServices',
                                    slide_w_emu: int = 9144000, slide_h_emu: int = 6858000) -> 'ConversionContext':
    """
    Create root conversion context with proper viewport matrix.

    Args:
        svg_root: SVG root element
        services: ConversionServices instance
        slide_w_emu: Target slide width in EMU (default: 10 inches)
        slide_h_emu: Target slide height in EMU (default: 7.5 inches)

    Returns:
        ConversionContext with viewport matrix for root element
    """
    try:
        from ..converters.base import ConversionContext
        from ..transforms.matrix_composer import (
            needs_normalise,
            normalise_content_matrix,
            viewport_matrix,
        )

        # Create viewport transformation matrix
        viewport_matrix_transform = viewport_matrix(svg_root, slide_w_emu, slide_h_emu)

        # Apply content normalization if needed
        if needs_normalise(svg_root):
            from .content_bounds import calculate_raw_content_bounds
            min_x, min_y, max_x, max_y = calculate_raw_content_bounds(svg_root)
            normalization_matrix = normalise_content_matrix(min_x, min_y)
            # Prepend normalization to viewport matrix
            viewport_matrix_transform = viewport_matrix_transform @ normalization_matrix

        # Create root context with viewport matrix
        context = ConversionContext(
            svg_root=svg_root,
            services=services,
            parent_ctm=None,  # Root has no parent
            viewport_matrix=viewport_matrix_transform,
        )

        return context

    except ImportError as e:
        logger.warning(f"Transform system not available, using fallback context: {e}")
        # Fallback to basic context without CTM
        from ..converters.base import ConversionContext
        return ConversionContext(svg_root=svg_root, services=services)


def create_child_context_with_ctm(parent_context: 'ConversionContext', child_element: ET.Element) -> 'ConversionContext':
    """
    Create a child context with proper CTM propagation.

    Args:
        parent_context: Parent ConversionContext
        child_element: Child SVG element

    Returns:
        New ConversionContext with proper CTM chain
    """
    try:
        from ..converters.base import ConversionContext
        from ..transforms.matrix_composer import element_ctm

        # Calculate CTM for child element using parent element's CTM
        child_ctm = element_ctm(child_element, parent_context.element_ctm, parent_context.viewport_matrix)

        # Create child context with propagated CTM
        child_context = ConversionContext(
            svg_root=child_element,
            services=parent_context.services,
            parent_ctm=parent_context.element_ctm,
            viewport_matrix=parent_context.viewport_matrix,
        )
        child_context.element_ctm = child_ctm

        return child_context

    except ImportError:
        # Fallback to basic context creation without CTM
        from ..converters.base import ConversionContext
        return ConversionContext(svg_root=child_element, services=parent_context.services)


def walk_tree_with_ctm(element: ET.Element, context: 'ConversionContext',
                      converter_registry: 'ConverterRegistry',
                      visit_func: callable) -> None:
    """
    Walk SVG element tree with proper CTM propagation.

    Args:
        element: Current SVG element
        context: ConversionContext for current element
        converter_registry: Registry to get converters
        visit_func: Function to call for each element: visit_func(element, context, converter)
    """
    # Get converter for current element
    converter = converter_registry.get_converter(element)

    # Visit current element
    if converter is not None:
        visit_func(element, context, converter)

    # Process children with CTM propagation
    for child in element:
        # Create child context with proper CTM chain
        child_context = create_child_context_with_ctm(context, child)

        # Recursively walk child tree
        walk_tree_with_ctm(child, child_context, converter_registry, visit_func)


def apply_ctm_to_coordinates(ctm: np.ndarray | None, points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """
    Apply CTM transformation to a list of coordinate points.

    Args:
        ctm: 3x3 transformation matrix
        points: List of (x, y) coordinate tuples

    Returns:
        List of transformed (x, y) coordinate tuples
    """
    try:
        if ctm is None or len(points) == 0:
            return points

        # Convert points to homogeneous coordinates
        homogeneous = np.array([[x, y, 1] for x, y in points]).T

        # Apply transformation
        transformed = ctm @ homogeneous

        # Convert back to (x, y) tuples
        return [(float(transformed[0, i]), float(transformed[1, i])) for i in range(transformed.shape[1])]

    except Exception as e:
        logger.warning(f"CTM coordinate transformation failed: {e}")
        return points  # Return original points on error


def transform_point_with_ctm(ctm: np.ndarray | None, x: float, y: float) -> tuple[float, float]:
    """
    Transform a single point using CTM.

    Args:
        ctm: 3x3 transformation matrix
        x, y: Point coordinates

    Returns:
        Transformed (x, y) coordinates
    """
    if ctm is None:
        return x, y

    try:
        point = np.array([x, y, 1])
        transformed = ctm @ point
        return float(transformed[0]), float(transformed[1])
    except Exception as e:
        logger.warning(f"CTM point transformation failed: {e}")
        return x, y


def extract_scale_from_ctm(ctm: np.ndarray | None, direction: str = 'x') -> float:
    """
    Extract scale factor from CTM matrix.

    Args:
        ctm: 3x3 transformation matrix
        direction: 'x' or 'y' for directional scaling

    Returns:
        Scale factor for specified direction
    """
    if ctm is None:
        return 1.0

    try:
        if direction == 'x':
            return float(ctm[0, 0])
        else:
            return float(ctm[1, 1])
    except Exception as e:
        logger.warning(f"CTM scale extraction failed: {e}")
        return 1.0