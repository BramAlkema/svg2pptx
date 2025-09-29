"""
Tests for TextPathEngine - Modern Text-to-Path Conversion Engine

Tests the new TextPathEngine implementation with focus on:
- Coordinate system dependency injection
- Graceful fallback for missing dependencies
- Configuration management
- Cache functionality
"""

import pytest
from lxml import etree as ET
from unittest.mock import Mock, MagicMock
from src.converters.text_path_engine import TextPathEngine
from src.converters.result_types import TextConversionConfig
from src.converters.base import ConversionContext


class TestTextPathEngine:
    """Test suite for TextPathEngine functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create mock services
        self.mock_services = Mock()
        self.mock_services.coordinate_system = Mock()
        self.mock_services.font_service = Mock()
        self.mock_services.unit_converter = Mock()

        # Default configuration
        self.config = TextConversionConfig()

        self.engine = TextPathEngine(services=self.mock_services, config=self.config)
        self.context = Mock(spec=ConversionContext)

    def test_initialization(self):
        """Test engine initialization"""
        assert self.engine._services == self.mock_services
        assert self.engine._config == self.config
        assert self.engine._coordinate_system == self.mock_services.coordinate_system
        assert self.engine._font_service == self.mock_services.font_service
        assert self.engine._unit_converter == self.mock_services.unit_converter
        assert self.engine._path_cache is not None  # Cache enabled by default

    def test_initialization_without_config(self):
        """Test initialization with default config"""
        engine = TextPathEngine(services=self.mock_services)
        assert isinstance(engine._config, TextConversionConfig)
        assert engine._config.font_fallback_enabled is True

    def test_initialization_with_cache_disabled(self):
        """Test initialization with cache disabled"""
        config = TextConversionConfig(max_cache_size=0)
        engine = TextPathEngine(services=self.mock_services, config=config)
        assert engine._path_cache is None

    def test_convert_empty_text_element(self):
        """Test converting empty text element"""
        element = ET.Element("text")
        result = self.engine.convert_text_element(element, self.context)

        assert result.success is True
        assert "Empty text element" in result.content
        assert not result.has_errors

    def test_convert_text_with_content(self):
        """Test converting text element with content"""
        element = ET.Element("text")
        element.text = "Hello World"

        # Mock unit converter
        self.mock_services.unit_converter.to_emu = Mock(return_value=100000)

        result = self.engine.convert_text_element(element, self.context)

        assert result.success is True
        assert "Hello World" in result.content
        assert "<p:sp>" in result.content
        assert not result.has_errors

    def test_convert_text_with_tspan(self):
        """Test converting text with tspan children"""
        element = ET.Element("text")
        element.text = "Hello "

        tspan = ET.SubElement(element, "tspan")
        tspan.text = "World"

        # Mock unit converter
        self.mock_services.unit_converter.to_emu = Mock(return_value=100000)

        result = self.engine.convert_text_element(element, self.context)

        assert result.success is True
        # Text extraction joins with spaces, so we get extra space
        assert "Hello" in result.content and "World" in result.content

    def test_convert_text_missing_coordinate_system(self):
        """Test conversion with missing coordinate system"""
        # Remove coordinate system
        self.engine._coordinate_system = None

        element = ET.Element("text")
        element.text = "Test"

        result = self.engine.convert_text_element(element, self.context)

        assert result.success is False
        assert "Coordinate system not available" in result.errors[0].message
        assert result.has_content  # Should have fallback content
        assert "No Coordinate System" in result.content

    def test_text_attributes_extraction(self):
        """Test extraction of text attributes"""
        element = ET.Element("text")
        element.set("font-family", "Arial")
        element.set("font-size", "16")
        element.set("font-weight", "bold")
        element.set("x", "10")
        element.set("y", "20")

        attributes = self.engine._extract_text_attributes(element)

        assert attributes['font-family'] == "Arial"
        assert attributes['font-size'] == "16"
        assert attributes['font-weight'] == "bold"
        assert attributes['x'] == "10"
        assert attributes['y'] == "20"

    def test_text_attributes_with_defaults(self):
        """Test attribute extraction with defaults"""
        element = ET.Element("text")

        attributes = self.engine._extract_text_attributes(element)

        assert attributes['font-family'] == self.config.fallback_font_family
        assert attributes['font-size'] == "12"
        assert attributes['font-weight'] == "normal"
        assert attributes['x'] == "0"
        assert attributes['y'] == "0"

    def test_cache_functionality(self):
        """Test cache functionality"""
        element = ET.Element("text")
        element.text = "Cached Text"
        element.set("font-family", "Arial")

        # Mock unit converter
        self.mock_services.unit_converter.to_emu = Mock(return_value=100000)

        # First call
        result1 = self.engine.convert_text_element(element, self.context)
        assert result1.success is True

        # Second call should use cache
        result2 = self.engine.convert_text_element(element, self.context)
        assert result2.success is True
        assert result2.metadata.get("cache_hit") is True

    def test_cache_clear(self):
        """Test cache clearing"""
        element = ET.Element("text")
        element.text = "Text"

        # Mock unit converter
        self.mock_services.unit_converter.to_emu = Mock(return_value=100000)

        # Add to cache
        self.engine.convert_text_element(element, self.context)
        stats_before = self.engine.get_cache_stats()
        assert stats_before['cache_size'] > 0

        # Clear cache
        self.engine.clear_cache()
        stats_after = self.engine.get_cache_stats()
        assert stats_after['cache_size'] == 0

    def test_cache_stats(self):
        """Test cache statistics"""
        stats = self.engine.get_cache_stats()

        assert stats['cache_enabled'] is True
        assert stats['cache_size'] == 0
        assert stats['max_cache_size'] == self.config.max_cache_size

    def test_cache_disabled_stats(self):
        """Test cache stats when disabled"""
        config = TextConversionConfig(max_cache_size=0)
        engine = TextPathEngine(services=self.mock_services, config=config)

        stats = engine.get_cache_stats()
        assert stats['cache_enabled'] is False

    def test_convert_to_emu_with_unit_converter(self):
        """Test EMU conversion with unit converter"""
        result = self.engine._convert_to_emu("10px", self.context)

        # Should call unit converter
        self.mock_services.unit_converter.to_emu.assert_called_once()

    def test_convert_to_emu_fallback(self):
        """Test EMU conversion fallback"""
        # Remove unit converter
        self.engine._unit_converter = None

        result = self.engine._convert_to_emu("10", self.context)
        assert result == 127000  # 10 * 12700

    def test_convert_to_emu_invalid_value(self):
        """Test EMU conversion with invalid value"""
        # Remove unit converter
        self.engine._unit_converter = None

        result = self.engine._convert_to_emu("invalid", self.context)
        assert result == 0  # Default for invalid

    def test_text_with_transform(self):
        """Test text with transform attribute"""
        element = ET.Element("text")
        element.text = "Transformed"
        element.set("transform", "rotate(45)")

        attributes = self.engine._extract_text_attributes(element)
        assert attributes['transform'] == "rotate(45)"

    def test_text_with_decoration(self):
        """Test text decoration preservation"""
        element = ET.Element("text")
        element.text = "Decorated"
        element.set("text-decoration", "underline")

        attributes = self.engine._extract_text_attributes(element)
        assert attributes['text-decoration'] == "underline"

    def test_text_decoration_disabled(self):
        """Test text decoration when disabled"""
        config = TextConversionConfig(preserve_decorations=False)
        engine = TextPathEngine(services=self.mock_services, config=config)

        element = ET.Element("text")
        element.set("text-decoration", "underline")

        attributes = engine._extract_text_attributes(element)
        assert 'text-decoration' not in attributes

    def test_exception_handling(self):
        """Test exception handling during conversion"""
        element = ET.Element("text")
        element.text = "Error Test"

        # Mock unit converter to raise exception
        self.mock_services.unit_converter.to_emu = Mock(side_effect=Exception("Test error"))

        result = self.engine.convert_text_element(element, self.context)

        assert result.success is False
        assert "failed" in result.errors[0].message.lower()
        assert result.has_content  # Should have fallback

    def test_complex_text_element(self):
        """Test complex text element with multiple attributes"""
        element = ET.Element("text")
        element.text = "Complex "
        element.set("x", "100")
        element.set("y", "200")
        element.set("font-family", "Times New Roman, serif")
        element.set("font-size", "24")
        element.set("font-weight", "bold")
        element.set("font-style", "italic")
        element.set("text-anchor", "middle")

        tspan1 = ET.SubElement(element, "tspan")
        tspan1.text = "Text"

        # Mock unit converter
        self.mock_services.unit_converter.to_emu = Mock(return_value=200000)

        result = self.engine.convert_text_element(element, self.context)

        assert result.success is True
        # Text extraction joins with spaces
        assert "Complex" in result.content and "Text" in result.content
        assert "Times New Roman" in result.content
        assert result.metadata['font_family'] == "Times New Roman, serif"