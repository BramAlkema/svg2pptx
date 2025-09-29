#!/usr/bin/env python3
"""
Unit tests for motion path animation conversion.

Tests the conversion of SVG motion paths to PowerPoint custom motion paths,
including SVG path data parsing, coordinate system conversion, and mpath reference handling.
"""

import pytest
from unittest.mock import Mock
from lxml import etree

from src.converters.animation_converter import AnimationConverter
from src.converters.base import ConversionContext
from src.services.conversion_services import ConversionServices


class TestMotionPathConverter:
    """Test motion path animation conversion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_services = Mock()
        self.converter = AnimationConverter(self.mock_services)

    def test_simple_linear_motion_path(self):
        """Test simple linear motion path conversion."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
                <circle id="moving-circle" r="5">
                    <animateMotion path="M 10,10 L 90,90" dur="2s"/>
                </circle>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')

        result = self.converter.convert(animate_elem, context)

        assert result != ""
        assert "<a:animMotion>" in result
        assert 'dur="2000"' in result
        assert "<a:path" in result
        # Should contain the path data
        assert "M 10,10 L 90,90" in result

    def test_quadratic_curve_motion_path(self):
        """Test quadratic curve motion path conversion."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
                <rect id="moving-rect" width="10" height="10">
                    <animateMotion path="M 50,50 Q 100,25 150,50" dur="3s"/>
                </rect>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')

        result = self.converter.convert(animate_elem, context)

        assert result != ""
        assert "<a:animMotion>" in result
        assert 'dur="3000"' in result
        # Should handle quadratic curve
        assert "Q 100,25 150,50" in result

    def test_complex_path_with_closepath(self):
        """Test complex path with closepath command."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <circle id="orbiting-circle" r="8">
                    <animateMotion path="M 50,100 Q 150,50 250,100 Q 150,150 50,100 Z" dur="5s"/>
                </circle>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')

        result = self.converter.convert(animate_elem, context)

        assert result != ""
        assert "<a:animMotion>" in result
        assert 'dur="5000"' in result
        # Should handle closepath
        assert "Z" in result

    def test_mpath_reference_handling(self):
        """Test mpath reference to defined path."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <defs>
                    <path id="complexPath" d="M 50,100 Q 150,50 250,100"/>
                </defs>
                <circle id="path-follower" r="8">
                    <animateMotion dur="4s">
                        <mpath href="#complexPath"/>
                    </animateMotion>
                </circle>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')

        result = self.converter.convert(animate_elem, context)

        assert result != ""
        assert "<a:animMotion>" in result
        assert 'dur="4000"' in result
        # Should resolve mpath reference
        # For now, check that some path is included
        assert "<a:path" in result

    def test_rectangular_motion_path(self):
        """Test rectangular motion path."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <rect id="rect-mover" width="12" height="12">
                    <animateMotion path="M 20,20 L 280,20 L 280,180 L 20,180 Z" dur="8s"/>
                </rect>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')

        result = self.converter.convert(animate_elem, context)

        assert result != ""
        assert "<a:animMotion>" in result
        assert 'dur="8000"' in result
        # Should include rectangular path
        assert "L 280,20 L 280,180 L 20,180" in result

    def test_motion_path_with_repeat(self):
        """Test motion path with repeat count."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
                <circle id="repeating-circle" r="6">
                    <animateMotion path="M 25,50 L 175,50" dur="2s" repeatCount="indefinite"/>
                </circle>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')

        result = self.converter.convert(animate_elem, context)

        assert result != ""
        assert "<a:animMotion>" in result
        assert 'dur="2000"' in result
        assert 'repeatCount="indefinite"' in result

    def test_motion_path_no_path_data(self):
        """Test motion path with no path data - should use default."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
                <circle id="static-circle" r="5">
                    <animateMotion dur="1s"/>
                </circle>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')

        result = self.converter.convert(animate_elem, context)

        assert result != ""
        assert "<a:animMotion>" in result
        # Should use default path
        assert "M 0,0" in result


class TestMotionPathCoordinateConversion:
    """Test motion path coordinate system conversion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_services = Mock()
        self.converter = AnimationConverter(self.mock_services)

    def test_path_data_parsing(self):
        """Test parsing of complex path data."""
        # Test parsing method directly if exposed
        path_data = "M 50,100 Q 150,50 250,100 Q 150,150 50,100 Z"

        # For now, just verify the path data is preserved in output
        svg_element = etree.fromstring(f'''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <circle id="test-circle" r="8">
                    <animateMotion path="{path_data}" dur="2s"/>
                </circle>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')

        result = self.converter.convert(animate_elem, context)

        assert result != ""
        assert path_data in result

    def test_coordinate_precision(self):
        """Test coordinate precision handling."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
                <circle id="precise-circle" r="3">
                    <animateMotion path="M 12.345,67.890 L 87.654,32.109" dur="1.5s"/>
                </circle>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')

        result = self.converter.convert(animate_elem, context)

        assert result != ""
        # Should preserve decimal precision
        assert "12.345,67.890" in result or "12.345" in result

    def test_relative_path_commands(self):
        """Test relative path commands."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
                <rect id="relative-rect" width="8" height="8">
                    <animateMotion path="M 20,50 l 50,0 l 0,30 l -50,0 z" dur="3s"/>
                </rect>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')

        result = self.converter.convert(animate_elem, context)

        assert result != ""
        assert "<a:animMotion>" in result
        # Should preserve relative commands (even if not converted)
        assert "l 50,0" in result or "L " in result  # Might be converted to absolute


class TestMotionPathIntegration:
    """Test motion path integration with other animation features."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_services = Mock()
        self.converter = AnimationConverter(self.mock_services)

    def test_motion_path_with_transform_animation(self):
        """Test motion path combined with transform animation."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
                <rect id="rotating-mover" width="12" height="12">
                    <animateMotion path="M 20,50 L 180,50" dur="4s"/>
                    <animateTransform attributeName="transform" type="rotate"
                                      values="0;360" dur="2s" repeatCount="indefinite"/>
                </rect>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        # Test motion animation
        motion_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')
        motion_result = self.converter.convert(motion_elem, context)

        # Test transform animation
        transform_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateTransform')
        transform_result = self.converter.convert(transform_elem, context)

        assert motion_result != ""
        assert transform_result != ""
        assert "<a:animMotion>" in motion_result
        assert "<a:animRot>" in transform_result

    def test_motion_path_with_opacity_animation(self):
        """Test motion path combined with opacity animation."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 250 100">
                <circle id="fading-mover" r="10">
                    <animateMotion path="M 25,50 Q 125,25 225,50" dur="3s"/>
                    <animate attributeName="opacity" values="1;0;1" dur="1.5s" repeatCount="indefinite"/>
                </circle>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        # Test motion animation
        motion_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')
        motion_result = self.converter.convert(motion_elem, context)

        # Test opacity animation
        opacity_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animate')
        opacity_result = self.converter.convert(opacity_elem, context)

        assert motion_result != ""
        assert opacity_result != ""
        assert "<a:animMotion>" in motion_result
        assert "<a:animEffect>" in opacity_result or "opacity" in opacity_result