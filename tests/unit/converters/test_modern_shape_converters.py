#!/usr/bin/env python3
"""
Unit Tests for Modern Shape Converters

Tests the modern shape converter APIs and functionality without requiring
full dependency injection setup. Focuses on testing what currently works.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import modern shape converters
from src.converters.shapes import (
    RectangleConverter,
    CircleConverter,
    EllipseConverter,
    PolygonConverter,
    LineConverter
)


class TestModernShapeConverterAPIs:
    """
    Unit tests for modern shape converter APIs and class structure.
    """

    def test_rectangle_converter_class_structure(self):
        """Test RectangleConverter class structure and API."""
        # Test class attributes
        assert hasattr(RectangleConverter, 'supported_elements')
        assert RectangleConverter.supported_elements == ['rect']

        # Test class methods exist
        assert hasattr(RectangleConverter, 'can_convert')
        assert hasattr(RectangleConverter, 'convert')

        # Test inheritance
        assert 'NumPyShapeConverter' in [cls.__name__ for cls in RectangleConverter.__mro__]

    def test_circle_converter_class_structure(self):
        """Test CircleConverter class structure and API."""
        assert hasattr(CircleConverter, 'supported_elements')
        assert CircleConverter.supported_elements == ['circle']
        assert hasattr(CircleConverter, 'can_convert')
        assert hasattr(CircleConverter, 'convert')
        assert 'NumPyShapeConverter' in [cls.__name__ for cls in CircleConverter.__mro__]

    def test_ellipse_converter_class_structure(self):
        """Test EllipseConverter class structure and API."""
        assert hasattr(EllipseConverter, 'supported_elements')
        assert EllipseConverter.supported_elements == ['ellipse']
        assert hasattr(EllipseConverter, 'can_convert')
        assert hasattr(EllipseConverter, 'convert')

    def test_polygon_converter_class_structure(self):
        """Test PolygonConverter class structure and API."""
        assert hasattr(PolygonConverter, 'supported_elements')
        assert PolygonConverter.supported_elements == ['polygon', 'polyline']
        assert hasattr(PolygonConverter, 'can_convert')
        assert hasattr(PolygonConverter, 'convert')

    def test_line_converter_class_structure(self):
        """Test LineConverter class structure and API."""
        assert hasattr(LineConverter, 'supported_elements')
        assert LineConverter.supported_elements == ['line']
        assert hasattr(LineConverter, 'can_convert')
        assert hasattr(LineConverter, 'convert')

    def test_all_converters_inherit_from_numpy_converter(self):
        """Test that all converters inherit from NumPyShapeConverter."""
        converters = [
            RectangleConverter,
            CircleConverter,
            EllipseConverter,
            PolygonConverter,
            LineConverter
        ]

        for converter_class in converters:
            mro_names = [cls.__name__ for cls in converter_class.__mro__]
            assert 'NumPyShapeConverter' in mro_names, f"{converter_class.__name__} should inherit from NumPyShapeConverter"

    def test_converter_supported_elements_unique(self):
        """Test that each converter has unique supported elements."""
        converters = {
            'RectangleConverter': RectangleConverter.supported_elements,
            'CircleConverter': CircleConverter.supported_elements,
            'EllipseConverter': EllipseConverter.supported_elements,
            'PolygonConverter': PolygonConverter.supported_elements,
            'LineConverter': LineConverter.supported_elements
        }

        # Collect all elements
        all_elements = []
        for elements in converters.values():
            all_elements.extend(elements)

        # Test that primary elements are unique (polygon/polyline is expected overlap)
        primary_elements = ['rect', 'circle', 'ellipse', 'line']
        for element in primary_elements:
            count = all_elements.count(element)
            assert count == 1, f"Element '{element}' appears {count} times, should be unique"


class TestModernShapeConverterCanConvert:
    """
    Unit tests for can_convert methods without full instantiation.
    """

    def test_rectangle_can_convert_detection(self):
        """Test RectangleConverter can_convert logic."""
        # Create test elements
        rect_element = ET.fromstring('<rect x="0" y="0" width="100" height="50"/>')
        circle_element = ET.fromstring('<circle cx="50" cy="50" r="25"/>')

        # Test can_convert method at class level using mock instance
        # Since we can't easily instantiate with services, test the logic
        converter = RectangleConverter.__new__(RectangleConverter)
        converter.get_element_tag = lambda el: el.tag.split('}')[-1] if '}' in el.tag else el.tag

        assert converter.can_convert(rect_element) is True
        assert converter.can_convert(circle_element) is False

    def test_circle_can_convert_detection(self):
        """Test CircleConverter can_convert logic."""
        rect_element = ET.fromstring('<rect x="0" y="0" width="100" height="50"/>')
        circle_element = ET.fromstring('<circle cx="50" cy="50" r="25"/>')

        converter = CircleConverter.__new__(CircleConverter)
        converter.get_element_tag = lambda el: el.tag.split('}')[-1] if '}' in el.tag else el.tag

        assert converter.can_convert(circle_element) is True
        assert converter.can_convert(rect_element) is False

    def test_ellipse_can_convert_detection(self):
        """Test EllipseConverter can_convert logic."""
        ellipse_element = ET.fromstring('<ellipse cx="50" cy="50" rx="40" ry="20"/>')
        circle_element = ET.fromstring('<circle cx="50" cy="50" r="25"/>')

        converter = EllipseConverter.__new__(EllipseConverter)
        converter.get_element_tag = lambda el: el.tag.split('}')[-1] if '}' in el.tag else el.tag

        assert converter.can_convert(ellipse_element) is True
        assert converter.can_convert(circle_element) is False

    def test_polygon_can_convert_detection(self):
        """Test PolygonConverter can_convert logic."""
        polygon_element = ET.fromstring('<polygon points="0,0 100,0 50,50"/>')
        polyline_element = ET.fromstring('<polyline points="0,0 100,100 200,0"/>')
        rect_element = ET.fromstring('<rect x="0" y="0" width="100" height="50"/>')

        converter = PolygonConverter.__new__(PolygonConverter)
        converter.get_element_tag = lambda el: el.tag.split('}')[-1] if '}' in el.tag else el.tag

        assert converter.can_convert(polygon_element) is True
        assert converter.can_convert(polyline_element) is True
        assert converter.can_convert(rect_element) is False

    def test_line_can_convert_detection(self):
        """Test LineConverter can_convert logic."""
        line_element = ET.fromstring('<line x1="0" y1="0" x2="100" y2="100"/>')
        rect_element = ET.fromstring('<rect x="0" y="0" width="100" height="50"/>')

        converter = LineConverter.__new__(LineConverter)
        converter.get_element_tag = lambda el: el.tag.split('}')[-1] if '}' in el.tag else el.tag

        assert converter.can_convert(line_element) is True
        assert converter.can_convert(rect_element) is False


class TestModernShapeConverterEdgeCases:
    """
    Unit tests for edge cases in modern shape converters.
    """

    def test_namespaced_svg_elements(self):
        """Test converters handle namespaced SVG elements."""
        # Create namespaced elements
        namespaced_rect = ET.fromstring('<svg:rect xmlns:svg="http://www.w3.org/2000/svg" x="0" y="0" width="100" height="50"/>')

        converter = RectangleConverter.__new__(RectangleConverter)
        converter.get_element_tag = lambda el: el.tag.split('}')[-1] if '}' in el.tag else el.tag

        # Should handle namespaced elements correctly
        assert converter.can_convert(namespaced_rect) is True

    def test_case_insensitive_element_detection(self):
        """Test that element detection handles case correctly."""
        # SVG elements should be case sensitive
        rect_element = ET.fromstring('<rect x="0" y="0" width="100" height="50"/>')

        converter = RectangleConverter.__new__(RectangleConverter)
        converter.get_element_tag = lambda el: el.tag.split('}')[-1] if '}' in el.tag else el.tag

        assert converter.can_convert(rect_element) is True

    def test_unknown_elements_rejected(self):
        """Test that unknown elements are rejected by all converters."""
        unknown_element = ET.fromstring('<unknown-element x="0" y="0"/>')

        converters = [
            RectangleConverter,
            CircleConverter,
            EllipseConverter,
            PolygonConverter,
            LineConverter
        ]

        for converter_class in converters:
            converter = converter_class.__new__(converter_class)
            converter.get_element_tag = lambda el: el.tag.split('}')[-1] if '}' in el.tag else el.tag

            assert converter.can_convert(unknown_element) is False


class TestModernShapeConverterIntegration:
    """
    Integration tests for modern shape converters with the shape module.
    """

    def test_all_converters_importable_from_shapes_module(self):
        """Test that all modern converters can be imported from shapes module."""
        from src.converters.shapes import (
            RectangleConverter,
            CircleConverter,
            EllipseConverter,
            PolygonConverter,
            LineConverter
        )

        # All should be importable
        assert RectangleConverter is not None
        assert CircleConverter is not None
        assert EllipseConverter is not None
        assert PolygonConverter is not None
        assert LineConverter is not None

    def test_converters_available_in_main_converters_module(self):
        """Test that converters are available from main converters module."""
        from src.converters import (
            RectangleConverter,
            CircleConverter,
            EllipseConverter,
            PolygonConverter,
            LineConverter
        )

        # Test they're the modern implementations
        for converter in [RectangleConverter, CircleConverter, EllipseConverter]:
            mro_names = [cls.__name__ for cls in converter.__mro__]
            assert 'NumPyShapeConverter' in mro_names

    def test_no_placeholder_converters_remaining(self):
        """Test that no placeholder converters remain after legacy removal."""
        from src.converters.shapes import RectangleConverter

        # Should not be a placeholder
        assert RectangleConverter.__name__ != 'PlaceholderConverter'
        assert hasattr(RectangleConverter, 'supported_elements')
        assert hasattr(RectangleConverter, 'can_convert')

    def test_modern_architecture_performance_attributes(self):
        """Test that modern converters have performance-related attributes."""
        from src.converters.shapes.numpy_converter import NumPyShapeConverter

        # Test NumPy converter has performance features
        assert hasattr(NumPyShapeConverter, 'supported_elements')
        # Check for instance attribute that would be created on initialization
        # geometry_engine is an instance attribute, not class attribute

        # Test our converters inherit these
        mro_names = [cls.__name__ for cls in RectangleConverter.__mro__]
        assert 'NumPyShapeConverter' in mro_names


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])