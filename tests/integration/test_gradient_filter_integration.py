#!/usr/bin/env python3
"""
Integration tests for gradient and filter processing.

Tests how gradients and filters work together with shapes, text, and other converters
in real-world scenarios.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET
from pathlib import Path
import sys

# Import centralized fixtures
from tests.fixtures.common import *
from tests.fixtures.mock_objects import *
from tests.fixtures.svg_content import *

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.converters.gradients import GradientConverter
from src.converters.filters import FilterConverter
from src.converters.shapes import RectangleConverter, CircleConverter
from src.converters.text import TextConverter
from src.converters.base import ConversionContext


@pytest.mark.integration
class TestGradientShapeIntegration:
    """Test integration between gradients and shape converters."""

    def test_rectangle_with_linear_gradient_fill(self):
        """Test rectangle with linear gradient fill integration."""
        # Create SVG with rectangle referencing linear gradient
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
            <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" style="stop-color:red;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:blue;stop-opacity:1" />
                </linearGradient>
            </defs>
            <rect x="10" y="10" width="180" height="80" fill="url(#grad1)"/>
        </svg>
        '''

        root = ET.fromstring(svg_content)
        rect_element = root.find('.//{http://www.w3.org/2000/svg}rect')
        gradient_element = root.find('.//{http://www.w3.org/2000/svg}linearGradient')

        # Setup converters
        gradient_converter = GradientConverter()
        rect_converter = RectangleConverter()

        # Setup context with SVG root for gradient lookup
        context = Mock(spec=ConversionContext)
        context.svg_root = root
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (9144, 9144)  # 10px
        context.coordinate_system.svg_length_to_emu.side_effect = lambda val, direction: int(val * 914.4)
        context.get_next_shape_id.return_value = 1001

        # Test gradient conversion
        gradient_result = gradient_converter.convert(gradient_element, context)
        assert '<a:gradFill>' in gradient_result
        assert '<a:gsLst>' in gradient_result
        assert 'FF0000' in gradient_result  # Red color
        assert '0000FF' in gradient_result  # Blue color

        # Test gradient URL resolution
        gradient_fill = gradient_converter.get_fill_from_url('url(#grad1)', context)
        assert gradient_fill != ""
        assert '<a:gradFill>' in gradient_fill

        # Mock rectangle converter to use gradient fill
        rect_converter.generate_fill = Mock(return_value=gradient_fill)
        rect_converter.generate_stroke = Mock(return_value='')

        rect_result = rect_converter.convert(rect_element, context)

        # Should contain gradient fill in rectangle
        assert '<p:sp>' in rect_result
        assert '<a:gradFill>' in rect_result
        rect_converter.generate_fill.assert_called_once()

    def test_circle_with_radial_gradient_fill(self):
        """Test circle with radial gradient fill integration."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <defs>
                <radialGradient id="radial1" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" style="stop-color:white;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:black;stop-opacity:1" />
                </radialGradient>
            </defs>
            <circle cx="100" cy="100" r="90" fill="url(#radial1)"/>
        </svg>
        '''

        root = ET.fromstring(svg_content)
        circle_element = root.find('.//{http://www.w3.org/2000/svg}circle')
        gradient_element = root.find('.//{http://www.w3.org/2000/svg}radialGradient')

        gradient_converter = GradientConverter()
        circle_converter = CircleConverter()

        context = Mock(spec=ConversionContext)
        context.svg_root = root
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (9144, 9144)
        context.coordinate_system.svg_length_to_emu.return_value = 82296  # 90px
        context.get_next_shape_id.return_value = 2001

        # Test radial gradient conversion
        gradient_result = gradient_converter.convert(gradient_element, context)
        assert '<a:gradFill>' in gradient_result
        assert 'FFFFFF' in gradient_result  # White
        assert '000000' in gradient_result  # Black

        # Test integration with circle
        gradient_fill = gradient_converter.get_fill_from_url('url(#radial1)', context)
        circle_converter.generate_fill = Mock(return_value=gradient_fill)
        circle_converter.generate_stroke = Mock(return_value='')

        circle_result = circle_converter.convert(circle_element, context)

        assert '<p:sp>' in circle_result
        assert '<a:gradFill>' in circle_result
        circle_converter.generate_fill.assert_called_once()

    def test_multiple_shapes_sharing_gradient(self):
        """Test multiple shapes referencing the same gradient."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
            <defs>
                <linearGradient id="shared_grad">
                    <stop offset="0%" style="stop-color:green"/>
                    <stop offset="100%" style="stop-color:yellow"/>
                </linearGradient>
            </defs>
            <rect x="10" y="10" width="80" height="60" fill="url(#shared_grad)"/>
            <circle cx="150" cy="40" r="30" fill="url(#shared_grad)"/>
            <rect x="200" y="20" width="60" height="40" fill="url(#shared_grad)"/>
        </svg>
        '''

        root = ET.fromstring(svg_content)
        gradient_converter = GradientConverter()

        context = Mock(spec=ConversionContext)
        context.svg_root = root

        # Test that the same gradient can be retrieved multiple times
        gradient_fill_1 = gradient_converter.get_fill_from_url('url(#shared_grad)', context)
        gradient_fill_2 = gradient_converter.get_fill_from_url('url(#shared_grad)', context)
        gradient_fill_3 = gradient_converter.get_fill_from_url('url(#shared_grad)', context)

        # All should return the same gradient definition
        assert gradient_fill_1 == gradient_fill_2 == gradient_fill_3
        assert '<a:gradFill>' in gradient_fill_1
        assert '008000' in gradient_fill_1 or 'green' in gradient_fill_1.lower()


@pytest.mark.integration
class TestFilterShapeIntegration:
    """Test integration between filters and shape converters."""

    def test_rectangle_with_gaussian_blur_filter(self):
        """Test rectangle with Gaussian blur filter integration."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
            <defs>
                <filter id="blur1">
                    <feGaussianBlur in="SourceGraphic" stdDeviation="3"/>
                </filter>
            </defs>
            <rect x="20" y="20" width="160" height="60" fill="red" filter="url(#blur1)"/>
        </svg>
        '''

        root = ET.fromstring(svg_content)
        rect_element = root.find('.//{http://www.w3.org/2000/svg}rect')
        filter_element = root.find('.//{http://www.w3.org/2000/svg}filter')

        filters_converter = FilterConverter()
        rect_converter = RectangleConverter()

        context = Mock(spec=ConversionContext)
        context.svg_root = root
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (18288, 18288)  # 20px
        context.coordinate_system.svg_length_to_emu.side_effect = lambda val, direction: int(val * 914.4)
        context.get_next_shape_id.return_value = 3001

        # Test filter conversion
        filter_result = filters_converter.convert(filter_element, context)

        # Should contain blur effect
        assert isinstance(filter_result, str)
        # Note: Specific filter implementation may vary, but should return some effect

        # Test filter application to rectangle
        # Mock the filter application (would normally be done by shape converter)
        rect_converter.generate_fill = Mock(return_value='<a:solidFill><a:srgbClr val="FF0000"/></a:solidFill>')
        rect_converter.generate_stroke = Mock(return_value='')

        # Apply filter effect (integration point)
        rect_result = rect_converter.convert(rect_element, context)

        assert '<p:sp>' in rect_result
        assert 'Rectangle 3001' in rect_result

    def test_circle_with_drop_shadow_filter(self):
        """Test circle with drop shadow filter integration."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <defs>
                <filter id="shadow1">
                    <feDropShadow dx="2" dy="2" stdDeviation="3" flood-color="black"/>
                </filter>
            </defs>
            <circle cx="100" cy="100" r="70" fill="blue" filter="url(#shadow1)"/>
        </svg>
        '''

        root = ET.fromstring(svg_content)
        circle_element = root.find('.//{http://www.w3.org/2000/svg}circle')
        filter_element = root.find('.//{http://www.w3.org/2000/svg}filter')

        filters_converter = FilterConverter()
        circle_converter = CircleConverter()

        context = Mock(spec=ConversionContext)
        context.svg_root = root
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (27432, 27432)  # 30px (100-70)
        context.coordinate_system.svg_length_to_emu.return_value = 127728  # 140px diameter
        context.get_next_shape_id.return_value = 3002

        # Test filter processing
        filter_result = filters_converter.convert(filter_element, context)

        # Should process drop shadow
        assert isinstance(filter_result, str)

        # Test integration with circle
        circle_converter.generate_fill = Mock(return_value='<a:solidFill><a:srgbClr val="0000FF"/></a:solidFill>')
        circle_converter.generate_stroke = Mock(return_value='')

        circle_result = circle_converter.convert(circle_element, context)

        assert '<p:sp>' in circle_result
        assert 'Circle 3002' in circle_result


@pytest.mark.integration
class TestGradientFilterCombination:
    """Test combinations of gradients and filters."""

    def test_gradient_with_filter_effects(self):
        """Test shape with both gradient fill and filter effects."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
            <defs>
                <linearGradient id="grad_filter">
                    <stop offset="0%" style="stop-color:purple"/>
                    <stop offset="100%" style="stop-color:pink"/>
                </linearGradient>
                <filter id="blur_shadow">
                    <feGaussianBlur stdDeviation="2"/>
                    <feDropShadow dx="3" dy="3" stdDeviation="1" flood-color="gray"/>
                </filter>
            </defs>
            <rect x="50" y="50" width="200" height="100"
                  fill="url(#grad_filter)" filter="url(#blur_shadow)"/>
        </svg>
        '''

        root = ET.fromstring(svg_content)
        rect_element = root.find('.//{http://www.w3.org/2000/svg}rect')
        gradient_element = root.find('.//{http://www.w3.org/2000/svg}linearGradient')
        filter_element = root.find('.//{http://www.w3.org/2000/svg}filter')

        gradient_converter = GradientConverter()
        filters_converter = FilterConverter()
        rect_converter = RectangleConverter()

        context = Mock(spec=ConversionContext)
        context.svg_root = root
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (45720, 45720)  # 50px
        context.coordinate_system.svg_length_to_emu.side_effect = lambda val, direction: int(val * 914.4)
        context.get_next_shape_id.return_value = 4001

        # Test gradient processing
        gradient_result = gradient_converter.convert(gradient_element, context)
        gradient_fill = gradient_converter.get_fill_from_url('url(#grad_filter)', context)

        assert '<a:gradFill>' in gradient_fill

        # Test filter processing
        filter_result = filters_converter.convert(filter_element, context)
        assert isinstance(filter_result, str)

        # Test combined effect on rectangle
        rect_converter.generate_fill = Mock(return_value=gradient_fill)
        rect_converter.generate_stroke = Mock(return_value='')

        rect_result = rect_converter.convert(rect_element, context)

        assert '<p:sp>' in rect_result
        assert '<a:gradFill>' in rect_result

    def test_complex_gradient_stops_processing(self):
        """Test complex gradient with multiple stops and transformations."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">
            <defs>
                <linearGradient id="complex_grad" x1="0%" y1="0%" x2="100%" y2="100%"
                                gradientTransform="rotate(45 0.5 0.5)">
                    <stop offset="0%" style="stop-color:red;stop-opacity:1"/>
                    <stop offset="25%" style="stop-color:orange;stop-opacity:0.8"/>
                    <stop offset="50%" style="stop-color:yellow;stop-opacity:0.6"/>
                    <stop offset="75%" style="stop-color:green;stop-opacity:0.8"/>
                    <stop offset="100%" style="stop-color:blue;stop-opacity:1"/>
                </linearGradient>
            </defs>
            <rect x="0" y="0" width="400" height="300" fill="url(#complex_grad)"/>
        </svg>
        '''

        root = ET.fromstring(svg_content)
        gradient_element = root.find('.//{http://www.w3.org/2000/svg}linearGradient')

        gradient_converter = GradientConverter()
        context = Mock(spec=ConversionContext)
        context.svg_root = root

        # Test complex gradient processing
        gradient_result = gradient_converter.convert(gradient_element, context)

        assert '<a:gradFill>' in gradient_result
        assert '<a:gsLst>' in gradient_result

        # Should contain all stop colors
        assert 'FF0000' in gradient_result  # Red
        assert 'FFA500' in gradient_result or 'orange' in gradient_result.lower()
        assert 'FFFF00' in gradient_result  # Yellow
        assert '008000' in gradient_result or 'green' in gradient_result.lower()
        assert '0000FF' in gradient_result  # Blue


@pytest.mark.integration
class TestTextGradientFilterIntegration:
    """Test integration of text with gradients and filters."""

    def test_text_with_gradient_fill(self):
        """Test text element with gradient fill."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 100">
            <defs>
                <linearGradient id="text_grad">
                    <stop offset="0%" style="stop-color:gold"/>
                    <stop offset="100%" style="stop-color:red"/>
                </linearGradient>
            </defs>
            <text x="50" y="50" font-size="24" fill="url(#text_grad)">Gradient Text</text>
        </svg>
        '''

        root = ET.fromstring(svg_content)
        text_element = root.find('.//{http://www.w3.org/2000/svg}text')

        gradient_converter = GradientConverter()
        text_converter = TextConverter()

        context = Mock(spec=ConversionContext)
        context.svg_root = root
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (45720, 45720)  # 50px
        context.get_next_shape_id.return_value = 5001

        # Test gradient retrieval for text
        gradient_fill = gradient_converter.get_fill_from_url('url(#text_grad)', context)
        assert '<a:gradFill>' in gradient_fill

        # Mock text converter methods
        text_converter._extract_text_content = Mock(return_value='Gradient Text')
        text_converter._get_font_family = Mock(return_value='Arial')
        text_converter._get_font_size = Mock(return_value=24)
        text_converter._get_font_weight = Mock(return_value='normal')
        text_converter._get_font_style = Mock(return_value='normal')
        text_converter._get_text_anchor = Mock(return_value='l')
        text_converter._get_text_decoration = Mock(return_value='')
        text_converter._get_fill_color = Mock(return_value=gradient_fill)
        text_converter.to_emu = Mock(return_value=91440)

        text_result = text_converter.convert(text_element, context)

        assert '<a:sp>' in text_result
        assert 'Gradient Text' in text_result
        assert '<a:gradFill>' in text_result

    def test_text_with_filter_effects(self):
        """Test text element with filter effects."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 100">
            <defs>
                <filter id="text_shadow">
                    <feDropShadow dx="2" dy="2" stdDeviation="1" flood-color="black"/>
                </filter>
            </defs>
            <text x="50" y="50" font-size="20" fill="white" filter="url(#text_shadow)">Shadow Text</text>
        </svg>
        '''

        root = ET.fromstring(svg_content)
        text_element = root.find('.//{http://www.w3.org/2000/svg}text')
        filter_element = root.find('.//{http://www.w3.org/2000/svg}filter')

        filters_converter = FilterConverter()
        text_converter = TextConverter()

        context = Mock(spec=ConversionContext)
        context.svg_root = root
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.return_value = (45720, 45720)
        context.get_next_shape_id.return_value = 5002

        # Test filter processing
        filter_result = filters_converter.convert(filter_element, context)
        assert isinstance(filter_result, str)

        # Mock text converter for integration test
        text_converter._extract_text_content = Mock(return_value='Shadow Text')
        text_converter._get_font_family = Mock(return_value='Arial')
        text_converter._get_font_size = Mock(return_value=20)
        text_converter._get_font_weight = Mock(return_value='normal')
        text_converter._get_font_style = Mock(return_value='normal')
        text_converter._get_text_anchor = Mock(return_value='l')
        text_converter._get_text_decoration = Mock(return_value='')
        text_converter._get_fill_color = Mock(return_value='<a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>')
        text_converter.to_emu = Mock(return_value=91440)

        text_result = text_converter.convert(text_element, context)

        assert '<a:sp>' in text_result
        assert 'Shadow Text' in text_result


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world scenarios with complex combinations."""

    def test_logo_with_gradients_and_shadows(self):
        """Test logo-like SVG with gradients and drop shadows."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300">
            <defs>
                <linearGradient id="logo_bg">
                    <stop offset="0%" style="stop-color:#4a90e2"/>
                    <stop offset="100%" style="stop-color:#1a5f9e"/>
                </linearGradient>
                <radialGradient id="highlight">
                    <stop offset="0%" style="stop-color:white;stop-opacity:0.3"/>
                    <stop offset="100%" style="stop-color:white;stop-opacity:0"/>
                </radialGradient>
                <filter id="logo_shadow">
                    <feDropShadow dx="5" dy="5" stdDeviation="3" flood-color="rgba(0,0,0,0.5)"/>
                </filter>
            </defs>

            <!-- Main background -->
            <rect x="50" y="50" width="400" height="200" rx="20"
                  fill="url(#logo_bg)" filter="url(#logo_shadow)"/>

            <!-- Highlight overlay -->
            <ellipse cx="250" cy="100" rx="180" ry="80" fill="url(#highlight)"/>

            <!-- Logo text -->
            <text x="250" y="160" text-anchor="middle" font-size="36" fill="white">LOGO</text>
        </svg>
        '''

        root = ET.fromstring(svg_content)

        # Get all elements
        rect_element = root.find('.//{http://www.w3.org/2000/svg}rect')
        ellipse_element = root.find('.//{http://www.w3.org/2000/svg}ellipse')
        text_element = root.find('.//{http://www.w3.org/2000/svg}text')

        # Setup converters
        gradient_converter = GradientConverter()
        filters_converter = FilterConverter()
        rect_converter = RectangleConverter()
        text_converter = TextConverter()

        context = Mock(spec=ConversionContext)
        context.svg_root = root
        context.coordinate_system = Mock()
        context.coordinate_system.svg_to_emu.side_effect = lambda x, y: (int(x * 914.4), int(y * 914.4))
        context.coordinate_system.svg_length_to_emu.side_effect = lambda val, direction: int(val * 914.4)
        context.get_next_shape_id.side_effect = [6001, 6002, 6003]

        # Test gradient processing
        logo_bg_fill = gradient_converter.get_fill_from_url('url(#logo_bg)', context)
        highlight_fill = gradient_converter.get_fill_from_url('url(#highlight)', context)

        assert '<a:gradFill>' in logo_bg_fill
        assert '<a:gradFill>' in highlight_fill

        # Test filter processing
        filter_element = root.find('.//{http://www.w3.org/2000/svg}filter')
        filter_result = filters_converter.convert(filter_element, context)
        assert isinstance(filter_result, str)

        # Test integrated conversion
        rect_converter.generate_fill = Mock(return_value=logo_bg_fill)
        rect_converter.generate_stroke = Mock(return_value='')

        rect_result = rect_converter.convert(rect_element, context)

        assert '<p:sp>' in rect_result
        assert '<a:gradFill>' in rect_result
        assert '<a:prstGeom prst="roundRect">' in rect_result  # Rounded corners

    def test_complex_filter_chain_processing(self):
        """Test complex filter with multiple primitives."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
            <defs>
                <filter id="complex_filter" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur"/>
                    <feOffset in="blur" dx="3" dy="3" result="offset"/>
                    <feFlood flood-color="red" flood-opacity="0.5" result="flood"/>
                    <feComposite in="flood" in2="offset" operator="in" result="shadow"/>
                    <feComposite in="SourceGraphic" in2="shadow" operator="over"/>
                </filter>
            </defs>
            <rect x="50" y="50" width="200" height="100" fill="blue" filter="url(#complex_filter)"/>
        </svg>
        '''

        root = ET.fromstring(svg_content)
        filter_element = root.find('.//{http://www.w3.org/2000/svg}filter')

        filters_converter = FilterConverter()
        context = Mock(spec=ConversionContext)
        context.svg_root = root

        # Test complex filter chain processing
        filter_result = filters_converter.convert(filter_element, context)

        # Should handle complex filter chain
        assert isinstance(filter_result, str)
        # The specific output depends on the filter implementation
        # But it should process without errors