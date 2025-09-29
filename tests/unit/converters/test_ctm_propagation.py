#!/usr/bin/env python3
"""
Unit tests for CTM propagation system
"""

import pytest
import numpy as np
from lxml import etree as ET
from unittest.mock import Mock

from src.converters.base import ConversionContext
from src.viewbox.ctm_utils import (
    create_root_context_with_viewport, walk_tree_with_ctm,
    apply_ctm_to_coordinates
)
from src.services.conversion_services import ConversionServices


class TestConversionContextCTM:
    """Test CTM integration in ConversionContext."""

    def test_context_with_ctm_fields(self):
        """Test ConversionContext initialization with CTM fields."""
        svg = '<g transform="translate(10, 20)"></g>'
        element = ET.fromstring(svg)

        parent_ctm = np.array([[1, 0, 5], [0, 1, 10], [0, 0, 1]], dtype=float)
        viewport_matrix = np.array([[9144, 0, 0], [0, 9144, 0], [0, 0, 1]], dtype=float)

        context = ConversionContext(
            svg_root=element,
            services=ConversionServices.create_default(),
            parent_ctm=parent_ctm,
            viewport_matrix=viewport_matrix
        )

        assert context.parent_ctm is parent_ctm
        assert context.viewport_matrix is viewport_matrix
        assert context.element_ctm is not None  # Should be calculated

    def test_context_backward_compatibility(self):
        """Test ConversionContext still works without CTM fields."""
        svg = '<rect x="10" y="20" width="30" height="40"></rect>'
        element = ET.fromstring(svg)

        # Create context without CTM fields (backward compatibility)
        context = ConversionContext(
            svg_root=element,
            services=ConversionServices.create_default()
        )

        assert context.parent_ctm is None
        assert context.viewport_matrix is None
        assert context.element_ctm is None

    def test_create_child_context(self):
        """Test child context creation with CTM propagation."""
        parent_svg = '<g transform="scale(2)"><rect transform="translate(5, 10)"/></g>'
        parent_element = ET.fromstring(parent_svg)
        child_element = parent_element[0]  # rect element

        viewport_matrix = np.array([[9144, 0, 0], [0, 9144, 0], [0, 0, 1]], dtype=float)

        parent_context = ConversionContext(
            svg_root=parent_element,
            services=ConversionServices.create_default(),
            viewport_matrix=viewport_matrix
        )

        child_context = parent_context.create_child_context(child_element)

        assert child_context.parent_ctm is not None
        assert child_context.viewport_matrix is viewport_matrix
        assert child_context.element_ctm is not None
        assert child_context.services is parent_context.services

    def test_transform_point(self):
        """Test point transformation using CTM."""
        svg = '<g transform="translate(10, 20)"></g>'
        element = ET.fromstring(svg)

        viewport_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)

        context = ConversionContext(
            svg_root=element,
            services=ConversionServices.create_default(),
            viewport_matrix=viewport_matrix
        )

        # Transform point (0, 0) - should be translated to (10, 20)
        x, y = context.transform_point(0, 0)
        assert abs(x - 10) < 1e-6
        assert abs(y - 20) < 1e-6

    def test_transform_length(self):
        """Test length transformation using CTM scale."""
        svg = '<g transform="scale(2, 3)"></g>'
        element = ET.fromstring(svg)

        viewport_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)

        context = ConversionContext(
            svg_root=element,
            services=ConversionServices.create_default(),
            viewport_matrix=viewport_matrix
        )

        # Transform lengths
        x_length = context.transform_length(10, 'x')
        y_length = context.transform_length(10, 'y')

        assert abs(x_length - 20) < 1e-6  # 10 * 2
        assert abs(y_length - 30) < 1e-6  # 10 * 3


class TestRootContextCreation:
    """Test root context creation with viewport matrix."""

    def test_create_root_context_simple(self):
        """Test root context creation with simple SVG."""
        svg = '<svg viewBox="0 0 100 100"></svg>'
        element = ET.fromstring(svg)

        context = create_root_context_with_viewport(
            element,
            ConversionServices.create_default(),
            9144000, 6858000
        )

        assert context.viewport_matrix is not None
        assert context.parent_ctm is None  # Root has no parent
        assert context.element_ctm is not None

    def test_create_root_context_with_normalization(self):
        """Test root context creation with content normalization."""
        # Create SVG that would trigger normalization (large coordinates)
        svg = '''<svg viewBox="0 0 100 100">
                   <g transform="translate(1000, 2000)">
                     <rect x="-900" y="-1900" width="50" height="50"/>
                   </g>
                 </svg>'''
        element = ET.fromstring(svg)

        context = create_root_context_with_viewport(
            element,
            ConversionServices.create_default()
        )

        assert context.viewport_matrix is not None
        # Context should be created successfully even with normalization


class TestTreeWalking:
    """Test tree walking with CTM propagation."""

    def test_walk_tree_simple(self):
        """Test tree walking with simple SVG structure."""
        svg = '''<svg viewBox="0 0 100 100">
                   <g transform="translate(10, 20)">
                     <rect x="5" y="10" width="30" height="40"/>
                     <circle cx="50" cy="60" r="15"/>
                   </g>
                 </svg>'''
        element = ET.fromstring(svg)

        visited_elements = []

        def visit_func(elem, context, converter):
            visited_elements.append({
                'tag': elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag,
                'has_ctm': context.element_ctm is not None,
                'converter': converter.__class__.__name__ if converter else None
            })

        # Create mock registry
        mock_registry = Mock()
        mock_registry.get_converter.return_value = Mock()

        context = create_root_context_with_viewport(
            element,
            ConversionServices.create_default()
        )

        walk_tree_with_ctm(element, context, mock_registry, visit_func)

        # Should visit svg, g, rect, circle
        assert len(visited_elements) == 4
        assert all(item['has_ctm'] for item in visited_elements)

    def test_apply_ctm_to_coordinates(self):
        """Test CTM application to coordinate lists."""
        # Create translation matrix
        ctm = np.array([[1, 0, 10], [0, 1, 20], [0, 0, 1]], dtype=float)

        points = [(0, 0), (5, 10), (15, 25)]
        transformed = apply_ctm_to_coordinates(ctm, points)

        expected = [(10, 20), (15, 30), (25, 45)]

        for actual, exp in zip(transformed, expected):
            assert abs(actual[0] - exp[0]) < 1e-6
            assert abs(actual[1] - exp[1]) < 1e-6

    def test_apply_ctm_with_scaling(self):
        """Test CTM application with scaling transformation."""
        # Create scale + translate matrix
        ctm = np.array([[2, 0, 5], [0, 3, 10], [0, 0, 1]], dtype=float)

        points = [(1, 2), (3, 4)]
        transformed = apply_ctm_to_coordinates(ctm, points)

        # (1,2) -> (1*2+5, 2*3+10) = (7, 16)
        # (3,4) -> (3*2+5, 4*3+10) = (11, 22)
        expected = [(7, 16), (11, 22)]

        for actual, exp in zip(transformed, expected):
            assert abs(actual[0] - exp[0]) < 1e-6
            assert abs(actual[1] - exp[1]) < 1e-6

    def test_apply_ctm_error_handling(self):
        """Test CTM coordinate transformation error handling."""
        # Test with None CTM
        points = [(1, 2), (3, 4)]
        result = apply_ctm_to_coordinates(None, points)
        assert result == points

        # Test with empty points
        ctm = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
        result = apply_ctm_to_coordinates(ctm, [])
        assert result == []


class TestDTDALogoCTMIntegration:
    """Test CTM system with DTDA logo pattern."""

    def test_dtda_group_transform_ctm(self):
        """Test CTM calculation for DTDA logo group transform."""
        # Simplified DTDA pattern
        svg = '''<svg viewBox="0 0 174.58 42.967">
                   <g transform="translate(509.85 466.99)">
                     <path d="m-493.81-466.99h-16.04v34.422"/>
                   </g>
                 </svg>'''
        element = ET.fromstring(svg)

        context = create_root_context_with_viewport(
            element,
            ConversionServices.create_default(),
            9144000, 6858000
        )

        # Get group element
        g_element = element[0]
        child_context = context.create_child_context(g_element)

        assert child_context.element_ctm is not None

        # Test transformation of a known point
        # Path starts at m-493.81-466.99, after group transform translate(509.85 466.99)
        # Effective coordinate should be approximately (16, 0)
        x, y = child_context.transform_point(-493.81, -466.99)

        # Should be transformed through viewport matrix to EMU
        assert x > 0  # Should be positive (on-slide)
        assert y >= 0  # Should be positive or zero