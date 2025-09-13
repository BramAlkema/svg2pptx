"""
Tests for BaseConverter fallback color handling and ColorParser integration.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

from src.converters.base import BaseConverter, ConversionContext


class TestConverter(BaseConverter):
    """Concrete test implementation of BaseConverter"""
    
    def can_convert(self, element, context=None):
        return True
    
    def convert(self, element, context):
        return "test"


class TestFallbackColors:
    """Test fallback color handling in BaseConverter"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.converter = TestConverter()
        self.context = ConversionContext()
        
    def test_generate_fill_fallback_gray_for_unfound_reference(self):
        """Test that generate_fill uses gray fallback when gradient/pattern reference not found"""
        # Test with a gradient reference that doesn't exist
        result = self.converter.generate_fill("url(#nonexistent)", "1", self.context)
        
        # Should contain fallback gray color (currently hardcoded as 808080)
        assert '<a:srgbClr val="808080"/>' in result
        assert '<a:solidFill>' in result
    
    def test_generate_gradient_fill_fallback_gray(self):
        """Test that generate_gradient_fill uses gray fallback (placeholder implementation)"""
        gradient = {"type": "linear", "stops": []}
        result = self.converter.generate_gradient_fill(gradient, "1")
        
        # Should contain fallback gray color (currently hardcoded as 808080)
        assert '<a:srgbClr val="808080"/>' in result
        assert '<a:solidFill>' in result
    
    def test_generate_pattern_fill_fallback_gray(self):
        """Test that generate_pattern_fill uses gray fallback (placeholder implementation)"""
        pattern = {"width": "10", "height": "10"}
        result = self.converter.generate_pattern_fill(pattern, "1")
        
        # Should contain fallback gray color (currently hardcoded as 808080)
        assert '<a:srgbClr val="808080"/>' in result
        assert '<a:solidFill>' in result
    
    def test_generate_fill_with_valid_color(self):
        """Test that generate_fill uses ColorParser when valid color provided"""
        result = self.converter.generate_fill("red", "1", self.context)
        
        # Should not contain hardcoded gray, should use ColorParser
        assert '<a:srgbClr val="808080"/>' not in result
        assert '<a:solidFill>' in result
    
    def test_generate_fill_with_opacity(self):
        """Test that generate_fill handles opacity correctly with ColorParser"""
        result = self.converter.generate_fill("blue", "0.5", self.context)
        
        # Should contain alpha element for opacity
        assert '<a:alpha val="50000"/>' in result
        assert '<a:solidFill>' in result
        assert '<a:srgbClr val="808080"/>' not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])