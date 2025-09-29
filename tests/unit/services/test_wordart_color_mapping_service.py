#!/usr/bin/env python3
"""
Tests for WordArt Color Mapping Service

Tests the lightweight service that integrates with existing gradient infrastructure.
"""

import pytest
from lxml import etree as ET
from unittest.mock import Mock

from core.services.wordart_color_mapping_service import (
    WordArtColorMappingService,
    create_wordart_color_mapping_service
)
from core.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext


class TestWordArtColorMappingService:
    """Test WordArt color mapping service functionality."""

    def setup_method(self):
        """Set up test service with mock services."""
        # Create mock services
        self.mock_services = Mock(spec=ConversionServices)
        self.mock_services.unit_converter = Mock()
        self.mock_services.viewport_handler = Mock()
        self.mock_services.font_service = Mock()
        self.mock_services.gradient_service = Mock()
        self.mock_services.pattern_service = Mock()
        self.mock_services.clip_service = Mock()

        self.service = WordArtColorMappingService(self.mock_services)

    def test_map_solid_fill_basic(self):
        """Test basic solid fill mapping."""
        fill = self.service.map_solid_fill("#FF0000")

        # Define namespace
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Check structure
        assert fill.tag == f"{a_ns}solidFill"
        srgb_clr = fill.find(f"{a_ns}srgbClr")
        assert srgb_clr is not None
        assert srgb_clr.get("val") == "FF0000"

        # Should not have alpha for fully opaque
        alpha = srgb_clr.find(f"{a_ns}alpha")
        assert alpha is None

    def test_map_solid_fill_with_opacity(self):
        """Test solid fill with opacity."""
        fill = self.service.map_solid_fill("#00FF00", opacity=0.5)

        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        srgb_clr = fill.find(f"{a_ns}srgbClr")
        assert srgb_clr.get("val") == "00FF00"

        # Check alpha value
        alpha = srgb_clr.find(f"{a_ns}alpha")
        assert alpha is not None
        assert alpha.get("val") == "50000"  # 50% = 50000

    def test_map_solid_fill_invalid_color(self):
        """Test solid fill with invalid color falls back to black."""
        fill = self.service.map_solid_fill("invalid-color")

        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        srgb_clr = fill.find(f"{a_ns}srgbClr")
        assert srgb_clr.get("val") == "000000"  # Black fallback

    def test_map_fill_reference_invalid_url(self):
        """Test mapping invalid fill reference."""
        svg_defs = ET.Element("defs")
        context = Mock(spec=ConversionContext)

        # Invalid URL format
        result = self.service.map_fill_reference("invalid-url", svg_defs, context)
        assert result is None

        # Missing gradient
        result = self.service.map_fill_reference("url(#missing)", svg_defs, context)
        assert result is None

    def test_simplify_for_wordart_within_limit(self):
        """Test gradient simplification when within stop limit."""
        # Create gradient with 5 stops (within 8 stop limit)
        gradient = ET.fromstring('''
            <linearGradient xmlns="http://www.w3.org/2000/svg" id="grad1">
                <stop offset="0%" stop-color="#FF0000"/>
                <stop offset="25%" stop-color="#FF8000"/>
                <stop offset="50%" stop-color="#FFFF00"/>
                <stop offset="75%" stop-color="#80FF00"/>
                <stop offset="100%" stop-color="#00FF00"/>
            </linearGradient>
        ''')

        simplified = self.service.simplify_for_wordart(gradient)

        # Should keep all stops since within limit
        stops = simplified.findall('.//{http://www.w3.org/2000/svg}stop')
        assert len(stops) == 5

    def test_simplify_for_wordart_over_limit(self):
        """Test gradient simplification when over stop limit."""
        # Create gradient with 12 stops (over 8 stop limit)
        gradient = ET.Element("linearGradient")
        gradient.set("id", "grad1")

        # Add 12 stops
        for i in range(12):
            stop = ET.SubElement(gradient, "{http://www.w3.org/2000/svg}stop")
            stop.set("offset", f"{i * 100 / 11:.1f}%")
            stop.set("stop-color", f"#{i*20:02X}{i*20:02X}{i*20:02X}")

        simplified = self.service.simplify_for_wordart(gradient)

        # Should reduce to max 8 stops
        stops = simplified.findall('.//{http://www.w3.org/2000/svg}stop')
        assert len(stops) <= 8
        assert len(stops) >= 2  # At least first and last

    def test_reduce_gradient_stops(self):
        """Test gradient stop reduction algorithm."""
        # Create 10 mock stops
        stops = []
        for i in range(10):
            stop = ET.Element("stop")
            stop.set("offset", f"{i * 10}%")
            stops.append(stop)

        # Reduce to 5 stops
        reduced = self.service._reduce_gradient_stops(stops, max_stops=5)

        assert len(reduced) == 5
        # First and last should be preserved
        assert reduced[0].get("offset") == "0%"
        assert reduced[-1].get("offset") == "90%"

    def test_reduce_gradient_stops_edge_cases(self):
        """Test gradient stop reduction edge cases."""
        # Single stop
        single_stop = [ET.Element("stop")]
        reduced = self.service._reduce_gradient_stops(single_stop, max_stops=3)
        assert len(reduced) == 1

        # Two stops
        two_stops = [ET.Element("stop") for _ in range(2)]
        reduced = self.service._reduce_gradient_stops(two_stops, max_stops=3)
        assert len(reduced) == 2

        # Empty list
        reduced = self.service._reduce_gradient_stops([], max_stops=3)
        assert len(reduced) == 0

    def test_factory_function(self):
        """Test factory function."""
        mock_services = Mock(spec=ConversionServices)
        service = create_wordart_color_mapping_service(mock_services)
        assert isinstance(service, WordArtColorMappingService)
        assert service.services is mock_services


class TestWordArtColorIntegration:
    """Test integration with existing gradient infrastructure."""

    def setup_method(self):
        """Set up test with mock services."""
        self.mock_services = Mock(spec=ConversionServices)
        self.mock_services.unit_converter = Mock()
        self.mock_services.viewport_handler = Mock()
        self.mock_services.font_service = Mock()
        self.mock_services.gradient_service = Mock()
        self.mock_services.pattern_service = Mock()
        self.mock_services.clip_service = Mock()

        self.service = WordArtColorMappingService(self.mock_services)

    def test_gradient_converter_integration(self):
        """Test that service correctly initializes gradient converter."""
        # Service should have gradient converter
        assert hasattr(self.service, 'gradient_converter')
        assert hasattr(self.service, 'gradient_engine')

        # Gradient converter should use the same services
        assert self.service.gradient_converter.services is self.mock_services

    def test_map_gradient_fill_failure_handling(self):
        """Test graceful handling of gradient conversion failures."""
        # Create invalid gradient element
        invalid_gradient = ET.Element("invalidGradient")
        context = Mock(spec=ConversionContext)

        # Should return None for unsupported gradient
        result = self.service.map_gradient_fill(invalid_gradient, context)
        assert result is None

    def test_find_gradient_by_id(self):
        """Test gradient lookup by ID."""
        # Create SVG defs with gradient
        svg_defs = ET.fromstring('''
            <defs xmlns="http://www.w3.org/2000/svg">
                <linearGradient id="grad1">
                    <stop offset="0%" stop-color="#FF0000"/>
                    <stop offset="100%" stop-color="#0000FF"/>
                </linearGradient>
            </defs>
        ''')

        # Should find gradient by ID
        gradient = self.service._find_gradient("grad1", svg_defs)
        assert gradient is not None
        assert gradient.get("id") == "grad1"

        # Should return None for missing gradient
        missing = self.service._find_gradient("missing", svg_defs)
        assert missing is None