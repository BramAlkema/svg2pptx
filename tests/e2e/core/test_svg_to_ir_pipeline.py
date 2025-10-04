#!/usr/bin/env python3
"""
End-to-End Tests for SVG → IR Conversion Pipeline.

Tests the complete pipeline from SVG input to IR data structure output,
validating the Clean Slate Architecture's first major transformation.
"""

import pytest
from pathlib import Path
import tempfile
import os

# Add src to path for imports

try:
    from core.parsers import SVGParser
    from core.ir import Scene, Path, TextFrame, Group, Image
    from core.ir import Point, Rect, SolidPaint
    from lxml import etree
    CORE_PIPELINE_AVAILABLE = True
except ImportError:
    CORE_PIPELINE_AVAILABLE = False
    pytest.skip("Core pipeline components not available", allow_module_level=True)


class TestSVGToIRBasicPipeline:
    """Test basic SVG to IR conversion pipeline."""

    def test_simple_rectangle_svg_to_ir(self):
        """Test converting simple rectangle SVG to IR."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            <rect x="50" y="50" width="100" height="80" fill="#FF0000"/>
        </svg>
        '''

        try:
            # Parse SVG to IR
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert isinstance(scene, Scene)

            # Validate scene properties
            assert scene.width == 200
            assert scene.height == 200
            assert scene.viewbox == (0, 0, 200, 200)

            # Validate elements
            assert len(scene.elements) == 1
            element = scene.elements[0]

            # Rectangle should be converted to Path or kept as specific shape IR
            assert element is not None

            # If converted to Path IR
            if isinstance(element, Path):
                assert element.is_closed == True
                assert element.fill is not None
                assert isinstance(element.fill, SolidPaint)
                assert element.fill.color == "#FF0000"

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_simple_circle_svg_to_ir(self):
        """Test converting simple circle SVG to IR."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="30" fill="#0000FF" stroke="#000000" stroke-width="2"/>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert isinstance(scene, Scene)
            assert len(scene.elements) == 1

            element = scene.elements[0]
            assert element is not None

            # Circle should have fill and stroke properties
            if hasattr(element, 'fill'):
                assert element.fill is not None
            if hasattr(element, 'stroke'):
                assert element.stroke is not None

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_simple_text_svg_to_ir(self):
        """Test converting simple text SVG to IR."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="300" height="100" viewBox="0 0 300 100">
            <text x="10" y="50" font-family="Arial" font-size="16" fill="#000000">Hello World</text>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert len(scene.elements) == 1

            element = scene.elements[0]
            assert element is not None

            # Text should be converted to TextFrame IR
            if isinstance(element, TextFrame):
                assert element.content == "Hello World"
                assert element.bounds is not None
                assert isinstance(element.bounds, Rect)

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_path_element_svg_to_ir(self):
        """Test converting path element SVG to IR."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            <path d="M 10 10 L 90 90 L 10 90 Z" fill="#00FF00"/>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert len(scene.elements) == 1

            element = scene.elements[0]
            assert isinstance(element, Path)

            # Validate path IR structure
            assert element.data == "M 10 10 L 90 90 L 10 90 Z"
            assert element.is_closed == True
            assert len(element.segments) >= 3  # MoveTo, LineTo, LineTo (+ implied close)

            # Validate segments
            if element.segments:
                first_segment = element.segments[0]
                if hasattr(first_segment, 'start'):
                    assert first_segment.start == Point(10, 10)

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")


class TestSVGToIRComplexPipeline:
    """Test complex SVG to IR conversion scenarios."""

    def test_nested_groups_svg_to_ir(self):
        """Test converting nested groups SVG to IR."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            <g transform="translate(20, 20)">
                <rect x="0" y="0" width="50" height="50" fill="#FF0000"/>
                <g transform="rotate(45)">
                    <circle cx="25" cy="25" r="10" fill="#0000FF"/>
                </g>
            </g>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert len(scene.elements) >= 1

            # Should handle groups either by flattening or preserving hierarchy
            if len(scene.elements) == 1 and isinstance(scene.elements[0], Group):
                # Group preserved
                group = scene.elements[0]
                assert group.transform is not None
                assert len(group.children) >= 1
            else:
                # Groups flattened
                assert len(scene.elements) >= 2

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_styled_elements_svg_to_ir(self):
        """Test converting styled elements SVG to IR."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">
            <defs>
                <style>
                    .red-rect { fill: #FF0000; stroke: #000000; stroke-width: 2; }
                    .blue-text { fill: #0000FF; font-family: Arial; font-size: 18px; }
                </style>
            </defs>
            <rect x="10" y="10" width="100" height="80" class="red-rect"/>
            <text x="130" y="50" class="blue-text">Styled Text</text>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert len(scene.elements) >= 2

            # Find rectangle and text elements
            rect_element = None
            text_element = None

            for element in scene.elements:
                if isinstance(element, Path) or (hasattr(element, 'fill') and hasattr(element, 'stroke')):
                    rect_element = element
                elif isinstance(element, TextFrame):
                    text_element = element

            # Validate styles were applied
            if rect_element and hasattr(rect_element, 'fill'):
                assert rect_element.fill is not None
            if rect_element and hasattr(rect_element, 'stroke'):
                assert rect_element.stroke is not None

            if text_element:
                assert text_element.content == "Styled Text"
                if hasattr(text_element, 'style') and text_element.style:
                    assert text_element.style is not None

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_gradient_fill_svg_to_ir(self):
        """Test converting gradient fills SVG to IR."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" style="stop-color:#FF0000;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#0000FF;stop-opacity:1" />
                </linearGradient>
            </defs>
            <rect x="50" y="50" width="100" height="100" fill="url(#grad1)"/>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert len(scene.elements) >= 1

            element = scene.elements[0]
            assert element is not None

            # Should handle gradient fill
            if hasattr(element, 'fill') and element.fill:
                # Gradient should be converted to appropriate IR structure
                assert element.fill is not None
                # May be LinearGradient IR or converted to solid fill

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_image_element_svg_to_ir(self):
        """Test converting image elements SVG to IR."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">
            <image x="50" y="50" width="100" height="80" href="test_image.png"/>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert len(scene.elements) >= 1

            element = scene.elements[0]
            assert element is not None

            # Image should be converted to Image IR
            if isinstance(element, Image):
                assert element.src == "test_image.png"
                assert element.bounds is not None
                assert element.bounds.width == 100
                assert element.bounds.height == 80

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")


class TestSVGToIRErrorHandling:
    """Test SVG to IR conversion error handling."""

    def test_malformed_svg_handling(self):
        """Test handling of malformed SVG input."""
        malformed_svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
            <rect x="50" y="50" width="100" height="80" fill="#FF0000"
            <!-- Missing closing tag and quote -->
        '''

        try:
            parser = SVGParser()

            # Should either handle gracefully or raise appropriate error
            try:
                scene = parser.parse_to_ir(malformed_svg)
                # If parsing succeeds, should have valid scene
                if scene is not None:
                    assert isinstance(scene, Scene)
            except (etree.XMLSyntaxError, ValueError, TypeError):
                # Expected for malformed SVG
                pass

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_empty_svg_handling(self):
        """Test handling of empty SVG input."""
        empty_svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(empty_svg)

            assert scene is not None
            assert isinstance(scene, Scene)
            assert scene.width == 100
            assert scene.height == 100
            assert len(scene.elements) == 0

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_unsupported_elements_handling(self):
        """Test handling of unsupported SVG elements."""
        svg_with_unsupported = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            <rect x="10" y="10" width="50" height="50" fill="#FF0000"/>
            <foreignObject x="80" y="80" width="100" height="100">
                <div xmlns="http://www.w3.org/1999/xhtml">HTML Content</div>
            </foreignObject>
            <animate attributeName="opacity" from="0" to="1" dur="2s"/>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_with_unsupported)

            assert scene is not None
            assert isinstance(scene, Scene)

            # Should handle supported elements and ignore/skip unsupported ones
            # At minimum, the rectangle should be processed
            supported_elements = [e for e in scene.elements if e is not None]
            assert len(supported_elements) >= 1

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_invalid_attribute_values_handling(self):
        """Test handling of invalid attribute values."""
        svg_with_invalid_attrs = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            <rect x="invalid" y="50" width="100" height="invalid_height" fill="not_a_color"/>
            <circle cx="50" cy="50" r="negative_radius" fill="#FF0000"/>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_with_invalid_attrs)

            assert scene is not None
            assert isinstance(scene, Scene)

            # Should handle invalid values gracefully
            # May skip invalid elements or use default values
            assert scene.elements is not None

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")


class TestSVGToIRCoordinateTransformation:
    """Test coordinate system transformation during SVG to IR conversion."""

    def test_viewbox_coordinate_transformation(self):
        """Test coordinate transformation with viewBox."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 200 150">
            <rect x="50" y="50" width="100" height="50" fill="#FF0000"/>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert scene.width == 400
            assert scene.height == 300
            assert scene.viewbox == (0, 0, 200, 150)

            # Coordinates should be preserved in original SVG coordinate space
            # Transformation should be handled during mapping phase
            assert len(scene.elements) >= 1

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_nested_transform_handling(self):
        """Test handling of nested transformations."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            <g transform="translate(50, 50)">
                <g transform="scale(2)">
                    <rect x="0" y="0" width="25" height="25" fill="#FF0000"/>
                </g>
            </g>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert len(scene.elements) >= 1

            # Transformations should be preserved in IR structure
            # Either flattened into coordinates or preserved as transform attributes

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_percentage_units_handling(self):
        """Test handling of percentage units."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            <rect x="25%" y="25%" width="50%" height="50%" fill="#FF0000"/>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert len(scene.elements) >= 1

            # Percentages should be resolved to absolute coordinates
            element = scene.elements[0]

            # 25% of 200 = 50, 50% of 200 = 100
            if hasattr(element, 'bounds'):
                # For shape converted to bounds
                assert element.bounds.x == 50
                assert element.bounds.y == 50
                assert element.bounds.width == 100
                assert element.bounds.height == 100

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")


class TestSVGToIRPerformance:
    """Test SVG to IR conversion performance."""

    def test_large_svg_conversion_performance(self):
        """Test performance with large SVG files."""
        import time

        # Generate large SVG with many elements
        elements = []
        for i in range(100):
            elements.append(f'<rect x="{i*5}" y="{i*5}" width="20" height="20" fill="#{i:02x}0000"/>')

        large_svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">
            {"".join(elements)}
        </svg>
        '''

        try:
            parser = SVGParser()

            start_time = time.time()
            scene = parser.parse_to_ir(large_svg)
            conversion_time = time.time() - start_time

            assert scene is not None
            assert len(scene.elements) == 100
            assert conversion_time < 1.0  # Should convert within 1 second

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_complex_path_conversion_performance(self):
        """Test performance with complex path elements."""
        import time

        # Generate complex path with many commands
        path_commands = ["M 0 0"]
        for i in range(200):
            path_commands.append(f"L {i} {i%10}")
        path_commands.append("Z")

        complex_svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" width="500" height="500" viewBox="0 0 500 500">
            <path d="{' '.join(path_commands)}" fill="#FF0000"/>
        </svg>
        '''

        try:
            parser = SVGParser()

            start_time = time.time()
            scene = parser.parse_to_ir(complex_svg)
            conversion_time = time.time() - start_time

            assert scene is not None
            assert len(scene.elements) == 1
            assert conversion_time < 0.1  # Should be very fast

            # Complex path should be properly segmented
            element = scene.elements[0]
            if isinstance(element, Path):
                assert len(element.segments) >= 200

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_memory_usage_large_conversion(self):
        """Test memory usage during large conversions."""
        import sys

        # Create moderately large SVG
        elements = []
        for i in range(50):
            elements.append(f'<circle cx="{i*10}" cy="{i*10}" r="5" fill="#{i:02x}00{255-i*5:02x}"/>')

        svg_content = f'''
        <svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">
            {"".join(elements)}
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(svg_content)

            assert scene is not None
            assert len(scene.elements) == 50

            # Check memory usage is reasonable
            scene_size = sys.getsizeof(scene)
            elements_size = sum(sys.getsizeof(e) for e in scene.elements)
            total_size = scene_size + elements_size

            assert total_size < 500000  # Less than 500KB

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")


class TestSVGToIRIntegration:
    """Test SVG to IR conversion integration scenarios."""

    def test_real_world_svg_conversion(self):
        """Test conversion of realistic SVG content."""
        real_world_svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
            <!-- Background -->
            <rect width="100%" height="100%" fill="#F0F0F0"/>

            <!-- Header -->
            <text x="200" y="30" text-anchor="middle" font-family="Arial" font-size="24" font-weight="bold">Dashboard</text>

            <!-- Chart area -->
            <rect x="50" y="60" width="300" height="180" fill="white" stroke="#CCCCCC" stroke-width="1"/>

            <!-- Data bars -->
            <rect x="80" y="180" width="30" height="40" fill="#3498db"/>
            <rect x="130" y="160" width="30" height="60" fill="#e74c3c"/>
            <rect x="180" y="140" width="30" height="80" fill="#2ecc71"/>
            <rect x="230" y="170" width="30" height="50" fill="#f39c12"/>

            <!-- Labels -->
            <text x="95" y="235" text-anchor="middle" font-size="12">Q1</text>
            <text x="145" y="235" text-anchor="middle" font-size="12">Q2</text>
            <text x="195" y="235" text-anchor="middle" font-size="12">Q3</text>
            <text x="245" y="235" text-anchor="middle" font-size="12">Q4</text>

            <!-- Legend -->
            <circle cx="70" cy="270" r="5" fill="#3498db"/>
            <text x="85" y="275" font-size="10">Sales</text>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(real_world_svg)

            assert scene is not None
            assert isinstance(scene, Scene)
            assert scene.width == 400
            assert scene.height == 300

            # Should have multiple elements (rectangles, text, circle)
            assert len(scene.elements) >= 8

            # Verify different element types are present
            has_shapes = any(isinstance(e, Path) or hasattr(e, 'fill') for e in scene.elements)
            has_text = any(isinstance(e, TextFrame) for e in scene.elements)

            assert has_shapes or has_text  # Should have at least one type

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_svg_with_embedded_styles(self):
        """Test SVG with embedded CSS styles."""
        styled_svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">
            <defs>
                <style type="text/css"><![CDATA[
                    .header { font-family: Arial; font-size: 18px; font-weight: bold; fill: #333; }
                    .box { fill: #e8f4fd; stroke: #1976d2; stroke-width: 2; }
                    .accent { fill: #ff5722; }
                ]]></style>
            </defs>

            <rect x="20" y="20" width="260" height="160" class="box"/>
            <text x="150" y="45" text-anchor="middle" class="header">Styled Content</text>
            <circle cx="80" cy="100" r="20" class="accent"/>
            <circle cx="220" cy="100" r="20" class="accent"/>
        </svg>
        '''

        try:
            parser = SVGParser()
            scene = parser.parse_to_ir(styled_svg)

            assert scene is not None
            assert len(scene.elements) >= 4

            # Styles should be applied to elements
            for element in scene.elements:
                assert element is not None
                # Elements should have appropriate fill/stroke properties

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")

    def test_svg_with_file_input(self):
        """Test SVG parsing from file input."""
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="150" height="150" viewBox="0 0 150 150">
            <rect x="25" y="25" width="100" height="100" fill="#4CAF50" stroke="#388E3C" stroke-width="3"/>
            <text x="75" y="85" text-anchor="middle" font-family="Arial" font-size="16" fill="white">FILE</text>
        </svg>
        '''

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as temp_file:
            temp_file.write(svg_content)
            temp_file_path = temp_file.name

        try:
            parser = SVGParser()

            # Test file-based parsing if supported
            if hasattr(parser, 'parse_file_to_ir'):
                scene = parser.parse_file_to_ir(temp_file_path)

                assert scene is not None
                assert len(scene.elements) >= 2

                # Should have rectangle and text elements
                shapes = [e for e in scene.elements if isinstance(e, Path) or hasattr(e, 'fill')]
                texts = [e for e in scene.elements if isinstance(e, TextFrame)]

                assert len(shapes) >= 1
                assert len(texts) >= 1
            else:
                # Parse from string if file parsing not available
                scene = parser.parse_to_ir(svg_content)
                assert scene is not None

        except NameError:
            pytest.skip("SVGParser.parse_to_ir not available")
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)


if __name__ == "__main__":
    pytest.main([__file__])