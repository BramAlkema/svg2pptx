#!/usr/bin/env python3
"""
End-to-End Tests for Mesh Gradient Conversion Pipeline

Tests the complete mesh gradient workflow from SVG input through conversion
to PowerPoint DrawingML output, validating real-world usage scenarios.

This covers: SVG with mesh gradients → parsing → conversion → DrawingML → PPTX generation
"""

import pytest
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import Mock, patch
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import mesh gradient system components
MESH_GRADIENT_AVAILABLE = True
try:
    from src.converters.gradients.converter import GradientConverter
    from src.converters.gradients.mesh_engine import MeshGradientEngine
    from src.converters.base import ConversionContext
    from src.services.conversion_services import ConversionServices
    from src.pptx_minimal import MinimalPPTXGenerator
except ImportError as e:
    MESH_GRADIENT_AVAILABLE = False
    print(f"Mesh gradient imports not available: {e}")


@pytest.mark.skipif(not MESH_GRADIENT_AVAILABLE, reason="Mesh gradient system not available")
class TestMeshGradientE2E:
    """
    End-to-end tests for mesh gradient conversion pipeline.

    Tests complete workflow from SVG with mesh gradients to PowerPoint output.
    """

    @pytest.fixture
    def services(self):
        """Provide conversion services for tests"""
        return ConversionServices.create_default()

    @pytest.fixture
    def simple_mesh_svg(self):
        """Provide simple mesh gradient SVG for testing"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
    <defs>
        <meshgradient id="simpleMesh">
            <meshrow>
                <meshpatch>
                    <stop offset="0" stop-color="#FF0000" stop-opacity="1.0"/>
                    <stop offset="0" stop-color="#00FF00" stop-opacity="1.0"/>
                    <stop offset="1" stop-color="#0000FF" stop-opacity="1.0"/>
                    <stop offset="1" stop-color="#FFFF00" stop-opacity="1.0"/>
                </meshpatch>
            </meshrow>
        </meshgradient>
    </defs>
    <rect x="20" y="20" width="160" height="160" fill="url(#simpleMesh)"/>
</svg>'''

    @pytest.fixture
    def complex_mesh_svg(self):
        """Provide complex mesh gradient SVG for testing"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">
    <defs>
        <meshgradient id="complexMesh">
            <meshrow>
                <meshpatch>
                    <stop offset="0" stop-color="#FF0000" stop-opacity="1.0"/>
                    <stop offset="0" stop-color="#00FF00" stop-opacity="0.8"/>
                    <stop offset="1" stop-color="#0000FF" stop-opacity="0.6"/>
                    <stop offset="1" stop-color="#FFFF00" stop-opacity="0.4"/>
                </meshpatch>
                <meshpatch>
                    <stop offset="0" stop-color="#800000" stop-opacity="1.0"/>
                    <stop offset="0" stop-color="#008000" stop-opacity="0.9"/>
                    <stop offset="1" stop-color="#000080" stop-opacity="0.7"/>
                    <stop offset="1" stop-color="#808000" stop-opacity="0.5"/>
                </meshpatch>
            </meshrow>
            <meshrow>
                <meshpatch>
                    <stop offset="0" stop-color="#FF00FF" stop-opacity="0.8"/>
                    <stop offset="0" stop-color="#00FFFF" stop-opacity="0.6"/>
                    <stop offset="1" stop-color="#FF8000" stop-opacity="0.4"/>
                    <stop offset="1" stop-color="#8000FF" stop-opacity="0.2"/>
                </meshpatch>
                <meshpatch>
                    <stop offset="0" stop-color="#404040" stop-opacity="1.0"/>
                    <stop offset="0" stop-color="#808080" stop-opacity="0.8"/>
                    <stop offset="1" stop-color="#C0C0C0" stop-opacity="0.6"/>
                    <stop offset="1" stop-color="#E0E0E0" stop-opacity="0.4"/>
                </meshpatch>
            </meshrow>
        </meshgradient>
    </defs>
    <ellipse cx="150" cy="150" rx="120" ry="120" fill="url(#complexMesh)"/>
</svg>'''

    @pytest.fixture
    def mixed_gradients_svg(self):
        """Provide SVG with mixed gradient types including mesh"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300">
    <defs>
        <linearGradient id="linearGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#FF0000"/>
            <stop offset="100%" stop-color="#0000FF"/>
        </linearGradient>
        <radialGradient id="radialGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#FFFFFF"/>
            <stop offset="100%" stop-color="#000000"/>
        </radialGradient>
        <meshgradient id="meshGrad">
            <meshrow>
                <meshpatch>
                    <stop stop-color="#FF0000"/>
                    <stop stop-color="#00FF00"/>
                    <stop stop-color="#0000FF"/>
                    <stop stop-color="#FFFF00"/>
                </meshpatch>
            </meshrow>
        </meshgradient>
    </defs>
    <rect x="10" y="10" width="120" height="80" fill="url(#linearGrad)"/>
    <rect x="140" y="10" width="120" height="80" fill="url(#radialGrad)"/>
    <rect x="270" y="10" width="120" height="80" fill="url(#meshGrad)"/>
    <circle cx="200" cy="200" r="80" fill="url(#meshGrad)"/>
</svg>'''

    def test_simple_mesh_gradient_parsing_e2e(self, services, simple_mesh_svg):
        """Test end-to-end parsing of simple mesh gradient"""
        # Parse SVG
        svg_root = ET.fromstring(simple_mesh_svg.encode('utf-8'))
        context = ConversionContext(services=services, svg_root=svg_root)

        # Create converter
        converter = GradientConverter(services)

        # Find mesh gradient element
        mesh_element = svg_root.find('.//*[@id="simpleMesh"]')
        assert mesh_element is not None
        assert mesh_element.tag.endswith('meshgradient')

        # Test conversion
        result = converter.convert(mesh_element, context)

        # Validate result
        assert isinstance(result, str)
        assert len(result) > 50  # Should be substantial XML
        assert ('gradFill' in result or 'solidFill' in result)

        # Validate XML structure
        try:
            # Wrap in root element for parsing
            xml_test = f'<root xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">{result}</root>'
            parsed = ET.fromstring(xml_test)
            assert parsed is not None
        except ET.XMLSyntaxError as e:
            pytest.fail(f"Generated XML is invalid: {e}")

    def test_complex_mesh_gradient_parsing_e2e(self, services, complex_mesh_svg):
        """Test end-to-end parsing of complex mesh gradient with multiple patches"""
        # Parse SVG
        svg_root = ET.fromstring(complex_mesh_svg.encode('utf-8'))
        context = ConversionContext(services=services, svg_root=svg_root)

        # Create converter
        converter = GradientConverter(services)

        # Find mesh gradient element
        mesh_element = svg_root.find('.//*[@id="complexMesh"]')
        assert mesh_element is not None

        # Test conversion
        result = converter.convert(mesh_element, context)

        # Validate result
        assert isinstance(result, str)
        assert len(result) > 50
        assert ('gradFill' in result or 'solidFill' in result)

        # Should handle complex mesh appropriately
        if 'gradFill' in result:
            # If gradient, should have proper structure
            assert '<a:gsLst>' in result
            assert '<a:gs pos=' in result

    def test_mesh_gradient_url_resolution_e2e(self, services, simple_mesh_svg):
        """Test end-to-end URL reference resolution for mesh gradients"""
        # Parse SVG
        svg_root = ET.fromstring(simple_mesh_svg.encode('utf-8'))
        context = ConversionContext(services=services, svg_root=svg_root)

        # Create converter
        converter = GradientConverter(services)

        # Test URL resolution
        result = converter.get_fill_from_url('url(#simpleMesh)', context)

        # Validate result
        assert isinstance(result, str)
        assert len(result) > 0
        assert ('gradFill' in result or 'solidFill' in result)

        # Test that direct conversion and URL resolution give same result
        mesh_element = svg_root.find('.//*[@id="simpleMesh"]')
        direct_result = converter.convert(mesh_element, context)
        assert result == direct_result

    def test_mixed_gradients_conversion_e2e(self, services, mixed_gradients_svg):
        """Test end-to-end conversion of SVG with mixed gradient types"""
        # Parse SVG
        svg_root = ET.fromstring(mixed_gradients_svg.encode('utf-8'))
        context = ConversionContext(services=services, svg_root=svg_root)

        # Create converter
        converter = GradientConverter(services)

        # Test each gradient type
        gradient_ids = ['linearGrad', 'radialGrad', 'meshGrad']
        results = {}

        for grad_id in gradient_ids:
            url = f'url(#{grad_id})'
            result = converter.get_fill_from_url(url, context)
            results[grad_id] = result

            # Each should produce valid output
            assert isinstance(result, str)
            assert len(result) > 0
            assert ('gradFill' in result or 'solidFill' in result)

        # Results should be different (different gradient types)
        assert len(set(results.values())) >= 2  # At least 2 different results

    def test_mesh_gradient_to_pptx_e2e(self, services, simple_mesh_svg):
        """Test complete pipeline from mesh gradient SVG to PPTX file"""
        # Create temporary file for PPTX output
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_file:
            output_path = tmp_file.name

        try:
            # Create PPTX generator
            generator = MinimalPPTXGenerator()

            # Convert SVG to PPTX
            generator.create_pptx_from_svg(simple_mesh_svg, output_path)

            # Verify PPTX file was created
            pptx_path = Path(output_path)
            assert pptx_path.exists()
            assert pptx_path.stat().st_size > 1000  # Should be substantial file

            # Verify PPTX structure by opening as ZIP
            import zipfile
            with zipfile.ZipFile(output_path, 'r') as pptx_zip:
                files = pptx_zip.namelist()

                # Check for required PPTX structure
                assert '[Content_Types].xml' in files
                assert 'ppt/presentation.xml' in files
                assert 'ppt/slides/slide1.xml' in files

                # Read slide content and check for DrawingML
                slide_content = pptx_zip.read('ppt/slides/slide1.xml').decode('utf-8')
                assert 'drawingml' in slide_content or 'a:' in slide_content

        finally:
            # Cleanup
            if Path(output_path).exists():
                Path(output_path).unlink()

    def test_mesh_gradient_performance_e2e(self, services, complex_mesh_svg):
        """Test mesh gradient conversion performance"""
        # Parse SVG
        svg_root = ET.fromstring(complex_mesh_svg.encode('utf-8'))
        context = ConversionContext(services=services, svg_root=svg_root)

        # Create converter
        converter = GradientConverter(services)

        # Time the conversion
        start_time = time.time()

        # Convert multiple times to get average
        num_iterations = 10
        for _ in range(num_iterations):
            result = converter.get_fill_from_url('url(#complexMesh)', context)
            assert len(result) > 0

        end_time = time.time()
        avg_time = (end_time - start_time) / num_iterations

        # Should be reasonably fast (< 50ms per conversion)
        assert avg_time < 0.05, f"Mesh gradient conversion too slow: {avg_time:.3f}s"

    def test_mesh_gradient_error_recovery_e2e(self, services):
        """Test end-to-end error recovery with malformed mesh gradients"""
        malformed_svgs = [
            # Empty mesh gradient
            '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
                <defs><meshgradient id="empty"/></defs>
                <rect fill="url(#empty)" width="100" height="100"/>
            </svg>''',

            # Mesh with insufficient stops
            '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
                <defs>
                    <meshgradient id="insufficient">
                        <meshrow>
                            <meshpatch>
                                <stop stop-color="#FF0000"/>
                                <!-- Missing 3 stops -->
                            </meshpatch>
                        </meshrow>
                    </meshgradient>
                </defs>
                <rect fill="url(#insufficient)" width="100" height="100"/>
            </svg>''',

            # Mesh with no rows
            '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
                <defs>
                    <meshgradient id="norows">
                        <!-- No meshrow elements -->
                    </meshgradient>
                </defs>
                <rect fill="url(#norows)" width="100" height="100"/>
            </svg>'''
        ]

        converter = GradientConverter(services)

        for i, malformed_svg in enumerate(malformed_svgs):
            svg_root = ET.fromstring(malformed_svg.encode('utf-8'))
            context = ConversionContext(services=services, svg_root=svg_root)

            # Should not crash, should provide fallback
            gradient_ids = ['empty', 'insufficient', 'norows']
            result = converter.get_fill_from_url(f'url(#{gradient_ids[i]})', context)

            assert isinstance(result, str)
            assert len(result) > 0
            # Should fallback to solid fill or basic gradient
            assert ('solidFill' in result or 'gradFill' in result)

    def test_mesh_gradient_namespace_handling_e2e(self, services):
        """Test end-to-end mesh gradient handling with different namespace scenarios"""
        namespace_variants = [
            # With explicit SVG namespace
            '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
                <defs>
                    <meshgradient id="withNS">
                        <meshrow>
                            <meshpatch>
                                <stop stop-color="#FF0000"/>
                                <stop stop-color="#00FF00"/>
                                <stop stop-color="#0000FF"/>
                                <stop stop-color="#FFFF00"/>
                            </meshpatch>
                        </meshrow>
                    </meshgradient>
                </defs>
                <rect fill="url(#withNS)" width="100" height="100"/>
            </svg>''',

            # Without explicit namespace (relies on parent)
            '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
                <defs>
                    <meshgradient id="inheritNS">
                        <meshrow>
                            <meshpatch>
                                <stop stop-color="#FF0000"/>
                                <stop stop-color="#00FF00"/>
                                <stop stop-color="#0000FF"/>
                                <stop stop-color="#FFFF00"/>
                            </meshpatch>
                        </meshrow>
                    </meshgradient>
                </defs>
                <rect fill="url(#inheritNS)" width="100" height="100"/>
            </svg>'''
        ]

        converter = GradientConverter(services)

        for i, svg_content in enumerate(namespace_variants):
            svg_root = ET.fromstring(svg_content.encode('utf-8'))
            context = ConversionContext(services=services, svg_root=svg_root)

            gradient_ids = ['withNS', 'inheritNS']
            result = converter.get_fill_from_url(f'url(#{gradient_ids[i]})', context)

            # Both should work and produce valid gradients
            assert isinstance(result, str)
            assert len(result) > 0
            assert ('gradFill' in result or 'solidFill' in result)

    def test_mesh_gradient_memory_efficiency_e2e(self, services, complex_mesh_svg):
        """Test memory efficiency of mesh gradient conversion"""
        import gc
        import sys

        # Parse SVG
        svg_root = ET.fromstring(complex_mesh_svg.encode('utf-8'))
        context = ConversionContext(services=services, svg_root=svg_root)

        # Create converter
        converter = GradientConverter(services)

        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Perform multiple conversions
        for _ in range(50):
            result = converter.get_fill_from_url('url(#complexMesh)', context)
            assert len(result) > 0

        # Check memory usage after
        gc.collect()
        final_objects = len(gc.get_objects())

        # Memory usage shouldn't grow significantly
        object_growth = final_objects - initial_objects
        assert object_growth < 1000, f"Too many objects created: {object_growth}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])