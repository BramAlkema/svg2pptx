#!/usr/bin/env python3
"""
Unit tests for mpath reference resolution.

Tests the proper resolution of mpath references to defined path elements,
ensuring that the actual path data is extracted and used for motion animations.
"""

import pytest
from unittest.mock import Mock
from lxml import etree

from src.converters.animation_converter import AnimationConverter
from src.converters.base import ConversionContext
from src.services.conversion_services import ConversionServices


class TestMPathResolution:
    """Test mpath reference resolution functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_services = Mock()
        self.converter = AnimationConverter(self.mock_services)

    def test_resolve_simple_mpath_reference(self):
        """Test resolution of simple mpath reference."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <defs>
                    <path id="simplePath" d="M 50,100 L 250,100"/>
                </defs>
                <circle id="path-follower" r="8">
                    <animateMotion dur="2s">
                        <mpath href="#simplePath"/>
                    </animateMotion>
                </circle>
            </svg>
        ''')

        # Test the resolution method directly
        path_data = self.converter._resolve_mpath_reference("#simplePath", svg_element)
        assert path_data == "M 50,100 L 250,100"

    def test_resolve_complex_mpath_reference(self):
        """Test resolution of complex path with curves."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <defs>
                    <path id="complexPath" d="M 50,100 Q 150,50 250,100 Q 150,150 50,100 Z"/>
                </defs>
                <rect id="path-follower" width="10" height="10">
                    <animateMotion dur="4s">
                        <mpath href="#complexPath"/>
                    </animateMotion>
                </rect>
            </svg>
        ''')

        path_data = self.converter._resolve_mpath_reference("#complexPath", svg_element)
        assert path_data == "M 50,100 Q 150,50 250,100 Q 150,150 50,100 Z"

    def test_resolve_mpath_reference_not_found(self):
        """Test resolution when referenced path doesn't exist."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <circle id="path-follower" r="8">
                    <animateMotion dur="2s">
                        <mpath href="#nonExistentPath"/>
                    </animateMotion>
                </circle>
            </svg>
        ''')

        path_data = self.converter._resolve_mpath_reference("#nonExistentPath", svg_element)
        assert path_data is None

    def test_resolve_mpath_reference_invalid_href(self):
        """Test resolution with invalid href format."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <defs>
                    <path id="testPath" d="M 0,0 L 100,100"/>
                </defs>
            </svg>
        ''')

        # Test without # prefix
        path_data = self.converter._resolve_mpath_reference("testPath", svg_element)
        assert path_data is None

        # Test empty href
        path_data = self.converter._resolve_mpath_reference("", svg_element)
        assert path_data is None

    def test_resolve_mpath_reference_non_path_element(self):
        """Test resolution when reference points to non-path element."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <defs>
                    <circle id="notAPath" cx="50" cy="50" r="25"/>
                </defs>
                <rect id="path-follower" width="10" height="10">
                    <animateMotion dur="2s">
                        <mpath href="#notAPath"/>
                    </animateMotion>
                </rect>
            </svg>
        ''')

        path_data = self.converter._resolve_mpath_reference("#notAPath", svg_element)
        assert path_data is None

    def test_mpath_integration_with_animation_conversion(self):
        """Test mpath resolution integrated with full animation conversion."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <defs>
                    <path id="testMotionPath" d="M 20,100 Q 150,50 280,100"/>
                </defs>
                <circle id="moving-circle" r="10">
                    <animateMotion dur="3s" repeatCount="indefinite">
                        <mpath href="#testMotionPath"/>
                    </animateMotion>
                </circle>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')

        result = self.converter.convert(animate_elem, context)

        assert result != ""
        assert "<a:animMotion>" in result
        assert 'dur="3000"' in result
        assert 'repeatCount="indefinite"' in result
        # Should contain the resolved path data
        assert "M 20,100 Q 150,50 280,100" in result

    def test_mpath_with_path_in_main_document(self):
        """Test mpath reference to path element in main document (not in defs)."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <!-- Visible path for motion -->
                <path id="visiblePath" d="M 30,50 L 270,50 L 270,150 L 30,150 Z"
                      fill="none" stroke="#ccc" stroke-dasharray="5,5"/>

                <rect id="moving-rect" width="15" height="15" fill="red">
                    <animateMotion dur="6s" repeatCount="indefinite">
                        <mpath href="#visiblePath"/>
                    </animateMotion>
                </rect>
            </svg>
        ''')

        path_data = self.converter._resolve_mpath_reference("#visiblePath", svg_element)
        assert path_data == "M 30,50 L 270,50 L 270,150 L 30,150 Z"

    def test_mpath_with_path_empty_d_attribute(self):
        """Test mpath reference to path with empty d attribute."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <defs>
                    <path id="emptyPath" d=""/>
                </defs>
                <circle id="path-follower" r="8">
                    <animateMotion dur="2s">
                        <mpath href="#emptyPath"/>
                    </animateMotion>
                </circle>
            </svg>
        ''')

        path_data = self.converter._resolve_mpath_reference("#emptyPath", svg_element)
        assert path_data == ""

    def test_mpath_with_path_no_d_attribute(self):
        """Test mpath reference to path element without d attribute."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
                <defs>
                    <path id="pathWithoutD" stroke="red"/>
                </defs>
                <circle id="path-follower" r="8">
                    <animateMotion dur="2s">
                        <mpath href="#pathWithoutD"/>
                    </animateMotion>
                </circle>
            </svg>
        ''')

        path_data = self.converter._resolve_mpath_reference("#pathWithoutD", svg_element)
        assert path_data == ""


class TestMPathIntegrationWithComplexSVG:
    """Test mpath resolution with the complex motion path SVG from test data."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_services = Mock()
        self.converter = AnimationConverter(self.mock_services)

    def test_complex_motion_path_svg_processing(self):
        """Test processing of the complex motion path SVG file."""
        # Load and test the actual complex motion path SVG
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">
          <defs>
            <path id="complexPath" d="M 50,100 Q 150,50 250,100 Q 150,150 50,100 Z"/>
          </defs>

          <use href="#complexPath" fill="none" stroke="#bdc3c7" stroke-width="2" stroke-dasharray="5,5"/>

          <circle id="moving-circle" r="8" fill="#e74c3c">
            <animateMotion dur="5s" repeatCount="indefinite">
              <mpath href="#complexPath"/>
            </animateMotion>
            <animate attributeName="r" values="8;12;8" dur="1s" repeatCount="indefinite"/>
          </circle>

          <rect id="moving-rect" width="12" height="12" fill="#3498db">
            <animateMotion path="M 20,20 L 280,20 L 280,180 L 20,180 Z" dur="8s" repeatCount="indefinite"/>
            <animateTransform attributeName="transform" type="rotate" values="0;360" dur="2s" repeatCount="indefinite"/>
          </rect>

          <text id="moving-text" font-family="Arial" font-size="14" fill="#2c3e50" text-anchor="middle">
            Hello!
            <animateMotion path="M 50,50 Q 100,30 150,50 Q 200,70 250,50" dur="4s" repeatCount="indefinite"/>
          </text>
        </svg>'''

        svg_element = etree.fromstring(svg_content)
        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        # Test the circle with mpath reference
        circle_motion = svg_element.find('.//{http://www.w3.org/2000/svg}circle/{http://www.w3.org/2000/svg}animateMotion')
        assert circle_motion is not None, "Could not find circle with animateMotion"
        circle_result = self.converter.convert(circle_motion, context)

        assert circle_result != ""
        assert "<a:animMotion>" in circle_result
        assert 'dur="5000"' in circle_result
        assert 'repeatCount="indefinite"' in circle_result
        # Should contain resolved path from mpath reference
        assert "M 50,100 Q 150,50 250,100 Q 150,150 50,100 Z" in circle_result

        # Test the rect with direct path
        rect_motion = svg_element.find('.//{http://www.w3.org/2000/svg}rect/{http://www.w3.org/2000/svg}animateMotion')
        rect_result = self.converter.convert(rect_motion, context)

        assert rect_result != ""
        assert "<a:animMotion>" in rect_result
        assert 'dur="8000"' in rect_result
        assert "M 20,20 L 280,20 L 280,180 L 20,180 Z" in rect_result

        # Test the text with direct path
        text_motion = svg_element.find('.//{http://www.w3.org/2000/svg}text/{http://www.w3.org/2000/svg}animateMotion')
        text_result = self.converter.convert(text_motion, context)

        assert text_result != ""
        assert "<a:animMotion>" in text_result
        assert 'dur="4000"' in text_result
        assert "M 50,50 Q 100,30 150,50 Q 200,70 250,50" in text_result