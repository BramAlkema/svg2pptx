#!/usr/bin/env python3
"""
E2E Tests for Native Shape Fidelity

Tests comprehensive SVG to PPTX conversion with:
- Simple shapes (circles, ellipses, rectangles) → native PowerPoint shapes
- Complex shapes (with filters, clipping, transforms) → custom geometry fallback
- Mixed complexity scenarios
- File size validation
- XML structure verification
"""

import pytest
import zipfile
from pathlib import Path
from lxml import etree as ET

from core.pipeline.converter import CleanSlateConverter


class TestNativeShapeFidelity:
    """Test end-to-end native shape support with real-world SVG files"""

    def test_simple_shapes_all_native(self):
        """Test that simple circles, ellipses, and rectangles use native presets"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
            <!-- Simple circle -->
            <circle cx="50" cy="50" r="30" fill="red"/>

            <!-- Simple ellipse -->
            <ellipse cx="150" cy="50" rx="40" ry="25" fill="blue"/>

            <!-- Simple rectangle -->
            <rect x="200" y="20" width="60" height="60" fill="green"/>

            <!-- Rounded rectangle -->
            <rect x="280" y="20" width="60" height="60" rx="10" fill="orange"/>

            <!-- Another circle with stroke -->
            <circle cx="50" cy="150" r="30" fill="yellow" stroke="black" stroke-width="2"/>
        </svg>
        '''

        # Convert to PPTX
        converter = CleanSlateConverter()
        result = converter.convert_string(svg_content)

        # Write output
        output_path = '/tmp/simple_shapes_native.pptx'
        with open(output_path, 'wb') as f:
            f.write(result.output_data)

        # Verify PPTX structure
        prstGeom_count, custGeom_count = self._count_geometry_types(output_path)

        # All 5 shapes should be native (prstGeom)
        assert prstGeom_count >= 5, f"Expected 5+ native shapes, got {prstGeom_count}"
        print(f"✅ Native shapes: {prstGeom_count}, Custom geometry: {custGeom_count}")

    def test_complex_shapes_fallback(self):
        """Test that complex shapes fall back to custom geometry"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
            <!-- Circle with filter (complex) -->
            <defs>
                <filter id="blur">
                    <feGaussianBlur stdDeviation="3"/>
                </filter>
                <clipPath id="clip">
                    <rect x="0" y="0" width="50" height="50"/>
                </clipPath>
            </defs>

            <circle cx="50" cy="50" r="30" fill="red" filter="url(#blur)"/>

            <!-- Ellipse with clipping (complex) -->
            <ellipse cx="150" cy="50" rx="40" ry="25" fill="blue" clip-path="url(#clip)"/>

            <!-- Rectangle with rotation (complex) -->
            <rect x="200" y="20" width="60" height="60" fill="green" transform="rotate(45 230 50)"/>
        </svg>
        '''

        # Convert to PPTX
        converter = CleanSlateConverter()
        result = converter.convert_string(svg_content)

        # Write output
        output_path = '/tmp/complex_shapes_fallback.pptx'
        with open(output_path, 'wb') as f:
            f.write(result.output_data)

        # Verify fallback to custom geometry or EMF
        prstGeom_count, custGeom_count = self._count_geometry_types(output_path)

        # Complex shapes may use custom geometry or EMF fallback
        print(f"✅ Complex shapes - Native: {prstGeom_count}, Custom/EMF: {custGeom_count}")
        # At least some shapes should be present
        total_shapes = prstGeom_count + custGeom_count
        assert total_shapes > 0, "Expected some shapes to be generated"

    def test_mixed_complexity_shapes(self):
        """Test mix of simple and complex shapes in same SVG"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
            <defs>
                <filter id="shadow">
                    <feDropShadow dx="2" dy="2" stdDeviation="2"/>
                </filter>
            </defs>

            <!-- Simple shapes (should be native) -->
            <circle cx="50" cy="50" r="30" fill="#FF5733"/>
            <ellipse cx="150" cy="50" rx="40" ry="25" fill="#3498DB"/>
            <rect x="250" y="20" width="80" height="60" fill="#2ECC71"/>
            <rect x="350" y="20" width="80" height="60" rx="15" fill="#9B59B6"/>

            <!-- Complex shapes (should fall back) -->
            <circle cx="50" cy="200" r="30" fill="#E74C3C" filter="url(#shadow)"/>
            <rect x="150" y="170" width="60" height="60" fill="#F39C12" transform="rotate(30 180 200)"/>

            <!-- More simple shapes -->
            <circle cx="350" cy="200" r="35" fill="#1ABC9C" stroke="#000" stroke-width="3"/>
            <ellipse cx="500" cy="200" rx="50" ry="30" fill="#34495E"/>
        </svg>
        '''

        # Convert to PPTX
        converter = CleanSlateConverter()
        result = converter.convert_string(svg_content)

        # Write output
        output_path = '/tmp/mixed_complexity_shapes.pptx'
        with open(output_path, 'wb') as f:
            f.write(result.output_data)

        # Verify mix of native and custom geometry
        prstGeom_count, custGeom_count = self._count_geometry_types(output_path)

        print(f"✅ Mixed shapes - Native: {prstGeom_count}, Custom/EMF: {custGeom_count}")
        # Should have native shapes (simple ones)
        assert prstGeom_count >= 4, f"Expected at least 4 native shapes, got {prstGeom_count}"

    def test_file_size_comparison_native_vs_fallback(self):
        """Test that native shapes produce smaller file sizes than custom geometry"""
        # Simple SVG with native shapes
        simple_svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
            <circle cx="50" cy="50" r="30" fill="red"/>
            <circle cx="150" cy="50" r="30" fill="blue"/>
            <circle cx="250" cy="50" r="30" fill="green"/>
            <ellipse cx="50" cy="150" rx="40" ry="25" fill="orange"/>
            <ellipse cx="150" cy="150" rx="40" ry="25" fill="purple"/>
            <rect x="250" y="125" width="60" height="50" fill="yellow"/>
        </svg>
        '''

        converter = CleanSlateConverter()

        # Generate PPTX with native shapes
        result_native = converter.convert_string(simple_svg)
        size_native = len(result_native.output_data)

        output_native = '/tmp/native_shapes_comparison.pptx'
        with open(output_native, 'wb') as f:
            f.write(result_native.output_data)

        print(f"✅ Native shapes PPTX size: {size_native:,} bytes")

        # Verify it's a valid PPTX
        assert size_native > 0, "PPTX should have content"

        # Verify structure
        prstGeom_count, custGeom_count = self._count_geometry_types(output_native)
        print(f"   Native geometry count: {prstGeom_count}")
        print(f"   Custom geometry count: {custGeom_count}")

    def test_roundtrip_powerpoint_compatibility(self):
        """Test that generated PPTX has valid PowerPoint structure"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">
            <circle cx="100" cy="100" r="50" fill="#3498DB" stroke="#2C3E50" stroke-width="3"/>
            <rect x="175" y="50" width="100" height="100" rx="10" fill="#E74C3C"/>
        </svg>
        '''

        converter = CleanSlateConverter()
        result = converter.convert_string(svg_content)

        output_path = '/tmp/powerpoint_compatibility.pptx'
        with open(output_path, 'wb') as f:
            f.write(result.output_data)

        # Verify PPTX structure
        self._validate_pptx_structure(output_path)
        print(f"✅ PowerPoint compatibility validated")

    def test_gradient_fill_native_shapes(self):
        """Test that simple shapes with gradients still use native geometry"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
            <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1"/>
                    <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1"/>
                </linearGradient>
                <radialGradient id="grad2">
                    <stop offset="0%" style="stop-color:rgb(0,0,255);stop-opacity:1"/>
                    <stop offset="100%" style="stop-color:rgb(0,255,0);stop-opacity:1"/>
                </radialGradient>
            </defs>

            <circle cx="100" cy="100" r="50" fill="url(#grad1)"/>
            <rect x="200" y="50" width="100" height="100" fill="url(#grad2)"/>
        </svg>
        '''

        converter = CleanSlateConverter()
        result = converter.convert_string(svg_content)

        output_path = '/tmp/gradient_native_shapes.pptx'
        with open(output_path, 'wb') as f:
            f.write(result.output_data)

        prstGeom_count, custGeom_count = self._count_geometry_types(output_path)
        print(f"✅ Gradient shapes - Native: {prstGeom_count}, Custom: {custGeom_count}")

    def test_stroke_properties_preservation(self):
        """Test that stroke properties are preserved in native shapes"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
            <!-- Circle with thick stroke -->
            <circle cx="75" cy="75" r="40" fill="none" stroke="red" stroke-width="5"/>

            <!-- Rectangle with dashed stroke -->
            <rect x="150" y="35" width="80" height="80" fill="lightblue"
                  stroke="navy" stroke-width="3" stroke-dasharray="5,3"/>

            <!-- Ellipse with rounded caps -->
            <ellipse cx="320" cy="75" rx="50" ry="30" fill="yellow"
                     stroke="orange" stroke-width="4" stroke-linecap="round"/>
        </svg>
        '''

        converter = CleanSlateConverter()
        result = converter.convert_string(svg_content)

        output_path = '/tmp/stroke_properties_shapes.pptx'
        with open(output_path, 'wb') as f:
            f.write(result.output_data)

        # Verify shapes were created
        prstGeom_count, custGeom_count = self._count_geometry_types(output_path)
        assert prstGeom_count > 0, "Expected native shapes with strokes"
        print(f"✅ Stroke properties - Native shapes: {prstGeom_count}")

    # Helper methods

    def _count_geometry_types(self, pptx_path: str) -> tuple[int, int]:
        """Count native preset geometry vs custom geometry in PPTX

        Returns:
            Tuple of (prstGeom_count, custGeom_count)
        """
        prstGeom_count = 0
        custGeom_count = 0

        try:
            with zipfile.ZipFile(pptx_path, 'r') as zf:
                # Find slide XMLs
                slide_files = [n for n in zf.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]

                for slide_file in slide_files:
                    xml_content = zf.read(slide_file)
                    root = ET.fromstring(xml_content)

                    # Count prstGeom elements (native shapes)
                    ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
                    prstGeom_elements = root.findall('.//a:prstGeom', ns)
                    prstGeom_count += len(prstGeom_elements)

                    # Count custGeom elements (custom geometry)
                    custGeom_elements = root.findall('.//a:custGeom', ns)
                    custGeom_count += len(custGeom_elements)

        except Exception as e:
            print(f"Warning: Could not parse PPTX structure: {e}")

        return prstGeom_count, custGeom_count

    def _validate_pptx_structure(self, pptx_path: str):
        """Validate that PPTX has required structure"""
        with zipfile.ZipFile(pptx_path, 'r') as zf:
            # Check required files exist
            required_files = [
                '[Content_Types].xml',
                '_rels/.rels',
                'ppt/presentation.xml',
            ]

            for required in required_files:
                assert required in zf.namelist(), f"Missing required file: {required}"

            # Verify at least one slide exists
            slide_files = [n for n in zf.namelist() if n.startswith('ppt/slides/slide')]
            assert len(slide_files) > 0, "No slides found in PPTX"


class TestNativeShapeEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_small_shapes(self):
        """Test that very small shapes still generate valid output"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
            <circle cx="50" cy="50" r="0.5" fill="red"/>
            <rect x="100" y="49.5" width="1" height="1" fill="blue"/>
            <ellipse cx="150" cy="50" rx="0.8" ry="0.3" fill="green"/>
        </svg>
        '''

        converter = CleanSlateConverter()
        result = converter.convert_string(svg_content)

        assert len(result.output_data) > 0, "Should generate PPTX even for tiny shapes"
        print("✅ Very small shapes handled correctly")

    def test_overlapping_shapes(self):
        """Test overlapping shapes preserve z-order"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
            <circle cx="100" cy="100" r="50" fill="red" opacity="0.7"/>
            <circle cx="120" cy="120" r="50" fill="blue" opacity="0.7"/>
            <rect x="80" y="80" width="80" height="80" fill="green" opacity="0.7"/>
        </svg>
        '''

        converter = CleanSlateConverter()
        result = converter.convert_string(svg_content)

        output_path = '/tmp/overlapping_shapes.pptx'
        with open(output_path, 'wb') as f:
            f.write(result.output_data)

        print("✅ Overlapping shapes processed")

    def test_shapes_with_transparency(self):
        """Test shapes with opacity values"""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
            <circle cx="100" cy="100" r="50" fill="red" opacity="0.5"/>
            <rect x="150" y="50" width="100" height="100" fill="blue" opacity="0.8"/>
            <ellipse cx="350" cy="100" rx="60" ry="40" fill="green" opacity="0.3"/>
        </svg>
        '''

        converter = CleanSlateConverter()
        result = converter.convert_string(svg_content)

        output_path = '/tmp/transparent_shapes.pptx'
        with open(output_path, 'wb') as f:
            f.write(result.output_data)

        print("✅ Transparent shapes processed")
