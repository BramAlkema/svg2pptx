#!/usr/bin/env python3
"""
Unit Tests for GradientConverter Mesh Integration

Tests the integration of mesh gradient engine with the main GradientConverter class.
Covers mesh gradient detection, conversion, URL reference resolution, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from src.converters.gradients.converter import GradientConverter
    from src.converters.gradients.mesh_engine import MeshGradientEngine
    from src.converters.base import ConversionContext
    from src.services.conversion_services import ConversionServices
    GRADIENT_IMPORTS_AVAILABLE = True
except ImportError:
    GRADIENT_IMPORTS_AVAILABLE = False


@pytest.mark.skipif(not GRADIENT_IMPORTS_AVAILABLE, reason="Gradient system not available")
class TestGradientConverterMeshIntegration:
    """Test GradientConverter integration with mesh gradient engine"""

    def setup_method(self):
        """Set up test fixtures"""
        self.services = ConversionServices.create_default()
        self.converter = GradientConverter(self.services)

    def test_converter_has_mesh_engine(self):
        """Test that GradientConverter has mesh engine initialized"""
        assert hasattr(self.converter, 'mesh_engine')
        assert isinstance(self.converter.mesh_engine, MeshGradientEngine)

    def test_can_convert_mesh_gradient(self):
        """Test that converter can detect mesh gradient elements"""
        mesh_svg = '''<meshgradient xmlns="http://www.w3.org/2000/svg" id="mesh1">
            <meshrow>
                <meshpatch>
                    <stop stop-color="#FF0000"/>
                    <stop stop-color="#00FF00"/>
                    <stop stop-color="#0000FF"/>
                    <stop stop-color="#FFFF00"/>
                </meshpatch>
            </meshrow>
        </meshgradient>'''

        element = ET.fromstring(mesh_svg)

        # Create context
        svg_root = ET.Element('svg')
        svg_root.append(element)
        context = ConversionContext(services=self.services, svg_root=svg_root)

        # Test detection
        can_convert = self.converter.can_convert(element, context)
        assert can_convert is True

    def test_can_convert_non_mesh_gradient(self):
        """Test that converter properly rejects non-mesh elements"""
        rect_svg = '<rect x="10" y="10" width="50" height="50" fill="#FF0000"/>'
        element = ET.fromstring(rect_svg)

        svg_root = ET.Element('svg')
        context = ConversionContext(services=self.services, svg_root=svg_root)

        can_convert = self.converter.can_convert(element, context)
        assert can_convert is False

    def test_convert_mesh_gradient_direct(self):
        """Test direct mesh gradient conversion"""
        mesh_svg = '''<meshgradient xmlns="http://www.w3.org/2000/svg" id="mesh1">
            <meshrow>
                <meshpatch>
                    <stop offset="0" stop-color="#FF0000" stop-opacity="1.0"/>
                    <stop offset="0" stop-color="#00FF00" stop-opacity="1.0"/>
                    <stop offset="1" stop-color="#0000FF" stop-opacity="1.0"/>
                    <stop offset="1" stop-color="#FFFF00" stop-opacity="1.0"/>
                </meshpatch>
            </meshrow>
        </meshgradient>'''

        element = ET.fromstring(mesh_svg)

        # Create context
        svg_root = ET.Element('svg')
        svg_root.append(element)
        context = ConversionContext(services=self.services, svg_root=svg_root)

        # Test conversion
        result = self.converter.convert(element, context)

        assert isinstance(result, str)
        assert len(result) > 0
        assert 'gradFill' in result or 'solidFill' in result

    def test_convert_mesh_gradient_url_reference(self):
        """Test mesh gradient conversion via URL reference"""
        # Create SVG with mesh gradient definition
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <defs>
                <meshgradient id="mesh1">
                    <meshrow>
                        <meshpatch>
                            <stop offset="0" stop-color="#FF0000"/>
                            <stop offset="0" stop-color="#00FF00"/>
                            <stop offset="1" stop-color="#0000FF"/>
                            <stop offset="1" stop-color="#FFFF00"/>
                        </meshpatch>
                    </meshrow>
                </meshgradient>
            </defs>
            <rect x="10" y="10" width="80" height="80" fill="url(#mesh1)"/>
        </svg>'''

        svg_root = ET.fromstring(svg_content)
        context = ConversionContext(services=self.services, svg_root=svg_root)

        # Test URL reference resolution
        result = self.converter.get_fill_from_url('url(#mesh1)', context)

        assert isinstance(result, str)
        assert len(result) > 0
        assert 'gradFill' in result or 'solidFill' in result

    def test_get_fill_from_url_invalid_format(self):
        """Test URL reference with invalid format"""
        svg_root = ET.Element('svg')
        context = ConversionContext(services=self.services, svg_root=svg_root)

        # Test various invalid formats
        invalid_urls = [
            'invalid-url',
            'url(#',
            'url()',
            'url(#)',
            '',
            None
        ]

        for invalid_url in invalid_urls:
            if invalid_url is not None:
                result = self.converter.get_fill_from_url(invalid_url, context)
                assert result == ""

    def test_get_fill_from_url_missing_element(self):
        """Test URL reference to non-existent mesh gradient"""
        svg_root = ET.Element('svg')
        context = ConversionContext(services=self.services, svg_root=svg_root)

        result = self.converter.get_fill_from_url('url(#nonexistent)', context)

        # Should return fallback gradient
        assert isinstance(result, str)
        assert 'gradFill' in result or 'solidFill' in result

    def test_get_fill_from_url_no_svg_root(self):
        """Test URL reference with no SVG root in context"""
        context = ConversionContext(services=self.services, svg_root=None)

        result = self.converter.get_fill_from_url('url(#mesh1)', context)
        assert result == ""

    def test_convert_mesh_gradient_with_error_handling(self):
        """Test mesh gradient conversion with error conditions"""
        # Create malformed mesh gradient
        mesh_svg = '<meshgradient xmlns="http://www.w3.org/2000/svg" id="mesh1"/>'
        element = ET.fromstring(mesh_svg)

        svg_root = ET.Element('svg')
        svg_root.append(element)
        context = ConversionContext(services=self.services, svg_root=svg_root)

        # Should not raise exception
        result = self.converter.convert(element, context)

        assert isinstance(result, str)
        assert len(result) > 0
        # Should fallback to solid fill or basic gradient
        assert 'solidFill' in result or 'gradFill' in result

    @patch('src.converters.gradients.converter.GradientEngine')
    def test_mesh_gradient_with_engine_fallback(self, mock_gradient_engine):
        """Test mesh gradient conversion when high-performance engine fails"""
        # Mock the gradient engine to raise an exception
        mock_gradient_engine.return_value.process_single_gradient.side_effect = Exception("Engine failed")

        mesh_svg = '''<meshgradient xmlns="http://www.w3.org/2000/svg" id="mesh1">
            <meshrow>
                <meshpatch>
                    <stop stop-color="#FF0000"/>
                    <stop stop-color="#00FF00"/>
                    <stop stop-color="#0000FF"/>
                    <stop stop-color="#FFFF00"/>
                </meshpatch>
            </meshrow>
        </meshgradient>'''

        element = ET.fromstring(mesh_svg)

        svg_root = ET.Element('svg')
        svg_root.append(element)
        context = ConversionContext(services=self.services, svg_root=svg_root)

        # Should fallback to mesh engine
        result = self.converter.convert(element, context)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_mesh_gradient_supported_elements(self):
        """Test that mesh gradient is in supported elements list"""
        supported = self.converter.supported_elements
        assert 'meshgradient' in supported

    def test_mesh_gradient_cache_integration(self):
        """Test that mesh gradients work with gradient caching"""
        mesh_svg = '''<meshgradient xmlns="http://www.w3.org/2000/svg" id="mesh1">
            <meshrow>
                <meshpatch>
                    <stop stop-color="#FF0000"/>
                    <stop stop-color="#00FF00"/>
                    <stop stop-color="#0000FF"/>
                    <stop stop-color="#FFFF00"/>
                </meshpatch>
            </meshrow>
        </meshgradient>'''

        element = ET.fromstring(mesh_svg)

        svg_root = ET.Element('svg')
        svg_root.append(element)
        context = ConversionContext(services=self.services, svg_root=svg_root)

        # Convert twice - second should use cache if implemented
        result1 = self.converter.convert(element, context)
        result2 = self.converter.convert(element, context)

        assert result1 == result2
        assert isinstance(result1, str)
        assert len(result1) > 0

    def test_mesh_gradient_with_complex_svg_structure(self):
        """Test mesh gradient in complex SVG with multiple defs"""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <defs>
                <linearGradient id="linear1">
                    <stop offset="0%" stop-color="#FF0000"/>
                    <stop offset="100%" stop-color="#0000FF"/>
                </linearGradient>
                <meshgradient id="mesh1">
                    <meshrow>
                        <meshpatch>
                            <stop stop-color="#FF0000"/>
                            <stop stop-color="#00FF00"/>
                            <stop stop-color="#0000FF"/>
                            <stop stop-color="#FFFF00"/>
                        </meshpatch>
                    </meshrow>
                </meshgradient>
                <radialGradient id="radial1">
                    <stop offset="0%" stop-color="#FFFFFF"/>
                    <stop offset="100%" stop-color="#000000"/>
                </radialGradient>
            </defs>
            <rect x="10" y="10" width="60" height="60" fill="url(#mesh1)"/>
            <rect x="80" y="10" width="60" height="60" fill="url(#linear1)"/>
        </svg>'''

        svg_root = ET.fromstring(svg_content)
        context = ConversionContext(services=self.services, svg_root=svg_root)

        # Test mesh gradient resolution in complex structure
        result = self.converter.get_fill_from_url('url(#mesh1)', context)

        assert isinstance(result, str)
        assert len(result) > 0
        assert 'gradFill' in result or 'solidFill' in result

    def test_mesh_gradient_with_namespace_variations(self):
        """Test mesh gradient handling with different namespace scenarios"""
        # Test with explicit namespace
        mesh_with_ns = '''<meshgradient xmlns="http://www.w3.org/2000/svg" id="mesh1">
            <meshrow>
                <meshpatch>
                    <stop stop-color="#FF0000"/>
                    <stop stop-color="#00FF00"/>
                    <stop stop-color="#0000FF"/>
                    <stop stop-color="#FFFF00"/>
                </meshpatch>
            </meshrow>
        </meshgradient>'''

        # Test without explicit namespace
        mesh_no_ns = '''<meshgradient id="mesh1">
            <meshrow>
                <meshpatch>
                    <stop stop-color="#FF0000"/>
                    <stop stop-color="#00FF00"/>
                    <stop stop-color="#0000FF"/>
                    <stop stop-color="#FFFF00"/>
                </meshpatch>
            </meshrow>
        </meshgradient>'''

        for mesh_svg in [mesh_with_ns, mesh_no_ns]:
            element = ET.fromstring(mesh_svg)

            svg_root = ET.Element('svg')
            svg_root.append(element)
            context = ConversionContext(services=self.services, svg_root=svg_root)

            # Both should work
            result = self.converter.convert(element, context)
            assert isinstance(result, str)
            assert len(result) > 0


@pytest.mark.skipif(not GRADIENT_IMPORTS_AVAILABLE, reason="Gradient system not available")
class TestGradientConverterMeshErrorHandling:
    """Test error handling in mesh gradient conversion"""

    def setup_method(self):
        """Set up test fixtures"""
        self.services = ConversionServices.create_default()
        self.converter = GradientConverter(self.services)

    def test_mesh_gradient_with_corrupted_xml(self):
        """Test mesh gradient handling with corrupted XML structure"""
        # This should not crash the converter
        try:
            mesh_svg = '<meshgradient><invalid></meshgradient>'
            element = ET.fromstring(mesh_svg)

            svg_root = ET.Element('svg')
            context = ConversionContext(services=self.services, svg_root=svg_root)

            result = self.converter.convert(element, context)
            assert isinstance(result, str)

        except ET.XMLSyntaxError:
            # If XML is truly malformed, that's expected
            pass

    def test_mesh_gradient_with_missing_stops(self):
        """Test mesh gradient with insufficient stop elements"""
        mesh_svg = '''<meshgradient xmlns="http://www.w3.org/2000/svg" id="mesh1">
            <meshrow>
                <meshpatch>
                    <stop stop-color="#FF0000"/>
                    <!-- Missing 3 stops -->
                </meshpatch>
            </meshrow>
        </meshgradient>'''

        element = ET.fromstring(mesh_svg)

        svg_root = ET.Element('svg')
        svg_root.append(element)
        context = ConversionContext(services=self.services, svg_root=svg_root)

        # Should not crash, should provide fallback
        result = self.converter.convert(element, context)
        assert isinstance(result, str)
        assert len(result) > 0

    @patch('src.converters.gradients.mesh_engine.MeshGradientEngine.convert_mesh_gradient')
    def test_mesh_engine_exception_handling(self, mock_convert):
        """Test handling when mesh engine raises exception"""
        mock_convert.side_effect = Exception("Mesh engine error")

        mesh_svg = '''<meshgradient xmlns="http://www.w3.org/2000/svg" id="mesh1">
            <meshrow>
                <meshpatch>
                    <stop stop-color="#FF0000"/>
                    <stop stop-color="#00FF00"/>
                    <stop stop-color="#0000FF"/>
                    <stop stop-color="#FFFF00"/>
                </meshpatch>
            </meshrow>
        </meshgradient>'''

        element = ET.fromstring(mesh_svg)

        svg_root = ET.Element('svg')
        svg_root.append(element)
        context = ConversionContext(services=self.services, svg_root=svg_root)

        # Should not crash, should provide fallback
        result = self.converter.convert(element, context)
        assert isinstance(result, str)
        assert len(result) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])