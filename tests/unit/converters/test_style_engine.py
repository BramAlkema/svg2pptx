"""
Tests for StyleEngine - Modern Style Processing Engine

Tests the new StyleEngine implementation with focus on:
- Proper dependency injection
- Graceful fallback behavior
- Result types with error tracking
- Gradient resolution with fallbacks
"""

import pytest
from lxml import etree as ET
from unittest.mock import Mock, MagicMock
from src.converters.style_engine import StyleEngine
from src.converters.result_types import ConversionStatus
from src.converters.base import ConversionContext


class TestStyleEngine:
    """Test suite for StyleEngine functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create mock services for dependency injection
        self.mock_services = Mock()
        self.mock_services.unit_converter = Mock()
        self.mock_services.viewport_handler = Mock()
        self.mock_services.font_service = Mock()
        self.mock_services.gradient_service = Mock()
        self.mock_services.pattern_service = Mock()
        self.mock_services.clip_service = Mock()
        self.mock_services.color_parser = Mock()

        self.engine = StyleEngine(services=self.mock_services)
        self.context = Mock(spec=ConversionContext)

    def test_initialization(self):
        """Test engine initialization"""
        assert hasattr(self.engine, '_gradient_service')
        assert hasattr(self.engine, '_color_parser')
        assert hasattr(self.engine, '_services')
        assert self.engine._services == self.mock_services

    def test_process_element_styles_empty(self):
        """Test processing element with no styles"""
        element = ET.Element("rect")
        result = self.engine.process_element_styles(element, self.context)

        assert result.status == ConversionStatus.SUCCESS
        assert result.properties == {}
        assert not result.has_errors
        assert not result.has_warnings
        assert not result.has_fallbacks

    def test_process_element_styles_with_fill(self):
        """Test processing element with fill color"""
        element = ET.Element("rect")
        element.set("fill", "red")

        # Mock color parser to return hex color
        self.mock_services.color_parser.parse_color = Mock(return_value="FF0000")

        result = self.engine.process_element_styles(element, self.context)

        assert result.status == ConversionStatus.SUCCESS
        assert 'fill' in result.properties
        assert 'FF0000' in result.properties['fill']
        assert not result.has_errors

    def test_process_element_styles_with_stroke(self):
        """Test processing element with stroke color"""
        element = ET.Element("rect")
        element.set("stroke", "blue")

        # Mock color parser to return hex color
        self.mock_services.color_parser.parse_color = Mock(return_value="0000FF")

        result = self.engine.process_element_styles(element, self.context)

        assert result.status == ConversionStatus.SUCCESS
        assert 'stroke' in result.properties
        assert '0000FF' in result.properties['stroke']

    def test_process_element_styles_with_opacity(self):
        """Test processing element with opacity"""
        element = ET.Element("rect")
        element.set("opacity", "0.5")
        element.set("fill-opacity", "0.8")
        element.set("stroke-opacity", "0.3")

        result = self.engine.process_element_styles(element, self.context)

        assert result.status == ConversionStatus.SUCCESS
        assert result.properties['opacity'] == "0.5"
        assert result.properties['fill-opacity'] == "0.8"
        assert result.properties['stroke-opacity'] == "0.3"

    def test_process_element_styles_with_style_attribute(self):
        """Test processing element with CSS style attribute"""
        element = ET.Element("rect")
        element.set("style", "fill: red; stroke: blue; stroke-width: 2px")

        result = self.engine.process_element_styles(element, self.context)

        assert result.status == ConversionStatus.SUCCESS
        assert 'fill' in result.properties
        assert 'stroke' in result.properties
        assert 'stroke-width' in result.properties

    def test_resolve_gradient_fill_valid(self):
        """Test resolving valid gradient URL"""
        # Mock gradient service to return gradient content
        self.mock_services.gradient_service.get_gradient_content = Mock(
            return_value="<a:gradFill>...</a:gradFill>"
        )

        result = self.engine.resolve_gradient_fill("url(#gradient1)", self.context)

        assert result.has_content
        assert not result.is_fallback
        assert result.gradient_id == "gradient1"

    def test_resolve_gradient_fill_invalid_format(self):
        """Test resolving invalid gradient URL format"""
        result = self.engine.resolve_gradient_fill("invalid-url", self.context)

        assert result.has_content
        assert result.is_fallback
        assert "Invalid gradient URL format" in result.fallback_reason
        assert "808080" in result.content  # Gray fallback color

    def test_resolve_gradient_fill_missing_gradient(self):
        """Test resolving missing gradient"""
        # Mock gradient service to return None (gradient not found)
        self.mock_services.gradient_service.get_gradient_content = Mock(return_value=None)

        result = self.engine.resolve_gradient_fill("url(#missing)", self.context)

        assert result.has_content
        assert result.is_fallback
        assert "not found" in result.fallback_reason

    def test_process_fill_none(self):
        """Test processing fill='none'"""
        element = ET.Element("rect")
        element.set("fill", "none")

        result = self.engine.process_element_styles(element, self.context)

        assert result.status == ConversionStatus.SUCCESS
        assert 'fill' in result.properties
        assert '<a:noFill/>' in result.properties['fill']

    def test_process_stroke_none(self):
        """Test processing stroke='none'"""
        element = ET.Element("rect")
        element.set("stroke", "none")

        result = self.engine.process_element_styles(element, self.context)

        assert result.status == ConversionStatus.SUCCESS
        # stroke='none' results in empty string (no stroke)
        assert result.properties.get('stroke', '') == ''

    def test_process_fill_with_fallback(self):
        """Test fill processing with color parsing failure"""
        element = ET.Element("rect")
        element.set("fill", "invalid-color")

        # Mock color parser to return None (parsing failed)
        self.mock_services.color_parser.parse_color = Mock(return_value=None)

        result = self.engine.process_element_styles(element, self.context)

        assert result.status == ConversionStatus.SUCCESS_WITH_FALLBACK
        assert 'fill' in result.properties
        assert '000000' in result.properties['fill']  # Black fallback
        assert result.has_fallbacks
        assert 'fill_fallback' in result.fallbacks_used[0]

    def test_process_stroke_with_fallback(self):
        """Test stroke processing with color parsing failure"""
        element = ET.Element("rect")
        element.set("stroke", "invalid-color")

        # Mock color parser to return None (parsing failed)
        self.mock_services.color_parser.parse_color = Mock(return_value=None)

        result = self.engine.process_element_styles(element, self.context)

        assert result.status == ConversionStatus.SUCCESS_WITH_FALLBACK
        assert 'stroke' in result.properties
        assert '000000' in result.properties['stroke']  # Black fallback
        assert result.has_fallbacks

    def test_process_element_exception_handling(self):
        """Test exception handling in element processing"""
        element = ET.Element("rect")
        element.set("fill", "red")

        # Mock color parser to raise exception
        self.mock_services.color_parser.parse_color = Mock(side_effect=Exception("Test error"))

        result = self.engine.process_element_styles(element, self.context)

        # Engine handles exceptions gracefully with fallback
        assert result.status == ConversionStatus.SUCCESS_WITH_FALLBACK
        assert result.has_fallbacks
        assert "Color processing error" in result.fallbacks_used[0]

    def test_gradient_url_with_exception(self):
        """Test gradient resolution with exception"""
        # Mock gradient service to raise exception
        self.mock_services.gradient_service.get_gradient_content = Mock(
            side_effect=Exception("Gradient error")
        )

        result = self.engine.resolve_gradient_fill("url(#gradient1)", self.context)

        assert result.has_content
        assert result.is_fallback
        assert "Error resolving gradient" in result.fallback_reason

    def test_combined_fill_and_stroke_with_opacity(self):
        """Test combined fill, stroke, and opacity processing"""
        element = ET.Element("rect")
        element.set("fill", "red")
        element.set("stroke", "blue")
        element.set("opacity", "0.7")
        element.set("stroke-width", "2")

        # Mock color parser
        def parse_color(color):
            return "FF0000" if color == "red" else "0000FF"

        self.mock_services.color_parser.parse_color = Mock(side_effect=parse_color)

        result = self.engine.process_element_styles(element, self.context)

        assert result.status == ConversionStatus.SUCCESS
        assert 'fill' in result.properties
        assert 'stroke' in result.properties
        assert result.properties['opacity'] == "0.7"
        assert result.properties['stroke-width'] == "2"
        assert 'FF0000' in result.properties['fill']
        assert '0000FF' in result.properties['stroke']