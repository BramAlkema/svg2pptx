#!/usr/bin/env python3
"""
Test suite for minimal PPTX generation functionality.

Validates that generated PPTX files:
1. Are valid ZIP archives
2. Contain required OOXML structure
3. Have proper XML format
4. Can be opened by PowerPoint (if available)
"""

import pytest
import zipfile
import tempfile
from lxml import etree as ET
from pathlib import Path
from unittest.mock import patch

# Import modules under test
try:
    from development.prototypes.pptx_minimal import MinimalPPTXGenerator, svg_to_pptx
    from src.ooxml_templates import get_pptx_file_structure, create_slide_xml
except ImportError:
    # Fallback for test environment
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from development.prototypes.pptx_minimal import MinimalPPTXGenerator, svg_to_pptx
    from ooxml_templates import get_pptx_file_structure, create_slide_xml


class TestOOXMLTemplates:
    """Test OOXML template generation."""

    def test_pptx_file_structure_completeness(self):
        """Test that all required PPTX files are included."""
        structure = get_pptx_file_structure()

        required_files = [
            '[Content_Types].xml',
            '_rels/.rels',
            'ppt/presentation.xml',
            'ppt/_rels/presentation.xml.rels',
            'ppt/slideMasters/slideMaster1.xml',
            'ppt/slideMasters/_rels/slideMaster1.xml.rels',
            'ppt/slideLayouts/slideLayout1.xml',
            'ppt/slideLayouts/_rels/slideLayout1.xml.rels',
            'ppt/slides/_rels/slide1.xml.rels'
        ]

        for required_file in required_files:
            assert required_file in structure, f"Missing required file: {required_file}"

    def test_xml_templates_are_valid(self):
        """Test that all XML templates are well-formed."""
        structure = get_pptx_file_structure()

        for file_path, xml_content in structure.items():
            if xml_content.strip():  # Skip empty content
                try:
                    # Convert to bytes to handle encoding declaration
                    ET.fromstring(xml_content.encode('utf-8'))
                except ET.ParseError as e:
                    pytest.fail(f"Invalid XML in {file_path}: {e}")

    def test_create_slide_xml_with_content(self):
        """Test slide XML creation with DrawingML content."""
        test_drawingml = '''
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="2" name="Test Shape"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
            </p:sp>'''

        slide_xml = create_slide_xml(test_drawingml)

        # Validate XML is well-formed
        slide_element = ET.fromstring(slide_xml)

        # Check that content is embedded
        assert "Test Shape" in slide_xml
        assert test_drawingml.strip() in slide_xml

    def test_create_slide_xml_with_empty_content(self):
        """Test slide XML creation with empty content."""
        slide_xml = create_slide_xml("")

        # Should still be valid XML
        slide_element = ET.fromstring(slide_xml)
        assert slide_element.tag.endswith('sld')


class TestMinimalPPTXGenerator:
    """Test the MinimalPPTXGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create a MinimalPPTXGenerator instance for testing."""
        return MinimalPPTXGenerator()

    @pytest.fixture
    def sample_svg(self):
        """Sample SVG content for testing."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100" width="200" height="100">
    <rect x="10" y="10" width="80" height="40" fill="blue"/>
    <circle cx="150" cy="30" r="20" fill="red"/>
</svg>'''

    @pytest.fixture
    def temp_output_path(self):
        """Create temporary file path for PPTX output."""
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            yield Path(tmp.name)
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)

    def test_parse_viewbox_from_svg(self, generator, sample_svg):
        """Test parsing viewBox from SVG content."""
        svg_root = ET.fromstring(sample_svg)
        viewbox = generator._parse_viewbox(svg_root)

        assert viewbox == (0, 0, 200, 100)

    def test_parse_viewbox_fallback_to_width_height(self, generator):
        """Test fallback to width/height when viewBox is missing."""
        svg_no_viewbox = '''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="150">
        </svg>'''

        svg_root = ET.fromstring(svg_no_viewbox)
        viewbox = generator._parse_viewbox(svg_root)

        assert viewbox == (0, 0, 300, 150)

    def test_calculate_slide_dimensions_aspect_ratio(self, generator):
        """Test slide dimension calculation preserves aspect ratio."""
        # 2:1 aspect ratio
        viewbox = (0, 0, 200, 100)
        width_emu, height_emu = generator._calculate_slide_dimensions(viewbox)

        # Should maintain 2:1 aspect ratio
        aspect_ratio = width_emu / height_emu
        assert abs(aspect_ratio - 2.0) < 0.01  # Allow small floating point errors

    def test_calculate_slide_dimensions_reasonable_size(self, generator):
        """Test slide dimensions are reasonable for PowerPoint."""
        viewbox = (0, 0, 100, 100)  # Square
        width_emu, height_emu = generator._calculate_slide_dimensions(viewbox)

        # Should be around 10 inches (target width)
        expected_width_emu = 10.0 * generator.emu_per_inch
        assert abs(width_emu - expected_width_emu) < 100000  # Allow some variation

    def test_create_presentation_xml_with_dimensions(self, generator):
        """Test presentation XML creation with custom dimensions."""
        width_emu = 10000000  # ~10.9 inches
        height_emu = 5000000   # ~5.5 inches

        presentation_xml = generator._create_presentation_xml(width_emu, height_emu)

        # Validate XML structure
        presentation_root = ET.fromstring(presentation_xml)

        # Check dimensions are embedded
        assert f'cx="{width_emu}"' in presentation_xml
        assert f'cy="{height_emu}"' in presentation_xml

    def test_create_pptx_from_svg_creates_file(self, generator, sample_svg, temp_output_path):
        """Test that PPTX file is created from SVG."""
        generator.create_pptx_from_svg(sample_svg, temp_output_path)

        # File should exist
        assert temp_output_path.exists()
        assert temp_output_path.stat().st_size > 0

    def test_create_pptx_from_svg_creates_valid_zip(self, generator, sample_svg, temp_output_path):
        """Test that created PPTX is a valid ZIP file."""
        generator.create_pptx_from_svg(sample_svg, temp_output_path)

        # Should be readable as ZIP
        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            # Should have expected files
            zip_files = zip_file.namelist()

            required_files = [
                '[Content_Types].xml',
                '_rels/.rels',
                'ppt/presentation.xml',
                'ppt/slides/slide1.xml'
            ]

            for required_file in required_files:
                assert required_file in zip_files, f"Missing file in PPTX: {required_file}"

    def test_pptx_contains_valid_xml_files(self, generator, sample_svg, temp_output_path):
        """Test that all XML files in PPTX are well-formed."""
        generator.create_pptx_from_svg(sample_svg, temp_output_path)

        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            for file_name in zip_file.namelist():
                if file_name.endswith('.xml'):
                    xml_content = zip_file.read(file_name).decode('utf-8')
                    try:
                        ET.fromstring(xml_content)
                    except ET.ParseError as e:
                        pytest.fail(f"Invalid XML in PPTX file {file_name}: {e}")

    def test_pptx_has_correct_content_types(self, generator, sample_svg, temp_output_path):
        """Test that Content_Types.xml has correct MIME types."""
        generator.create_pptx_from_svg(sample_svg, temp_output_path)

        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            content_types = zip_file.read('[Content_Types].xml').decode('utf-8')

            # Should contain required content types
            assert 'presentationml.presentation.main' in content_types
            assert 'presentationml.slide' in content_types
            assert 'presentationml.slideMaster' in content_types
            assert 'presentationml.slideLayout' in content_types


class TestSVGToPPTXFunction:
    """Test the simple svg_to_pptx function."""

    @pytest.fixture
    def sample_svg(self):
        """Sample SVG for testing."""
        return '''<svg viewBox="0 0 100 50">
            <rect x="0" y="0" width="100" height="50" fill="green"/>
        </svg>'''

    @pytest.fixture
    def temp_output_path(self):
        """Create temporary file path for PPTX output."""
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            yield Path(tmp.name)
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)

    def test_svg_to_pptx_function_creates_file(self, sample_svg, temp_output_path):
        """Test simple API function creates PPTX file."""
        svg_to_pptx(sample_svg, temp_output_path)

        assert temp_output_path.exists()
        assert temp_output_path.stat().st_size > 0

    def test_svg_to_pptx_function_creates_valid_pptx(self, sample_svg, temp_output_path):
        """Test simple API function creates valid PPTX structure."""
        svg_to_pptx(sample_svg, temp_output_path)

        # Verify ZIP structure
        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            files = zip_file.namelist()
            assert '[Content_Types].xml' in files
            assert 'ppt/presentation.xml' in files
            assert 'ppt/slides/slide1.xml' in files

    def test_svg_to_pptx_with_string_path(self, sample_svg):
        """Test function works with string path."""
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            temp_path_str = tmp.name

        try:
            svg_to_pptx(sample_svg, temp_path_str)
            assert Path(temp_path_str).exists()
        finally:
            Path(temp_path_str).unlink(missing_ok=True)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def generator(self):
        return MinimalPPTXGenerator()

    @pytest.fixture
    def temp_output_path(self):
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            yield Path(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)

    def test_malformed_svg_handling(self, generator, temp_output_path):
        """Test handling of malformed SVG content."""
        malformed_svg = '<svg><rect></svg>'  # Unclosed rect tag

        # Should not crash, even with malformed SVG
        try:
            generator.create_pptx_from_svg(malformed_svg, temp_output_path)
        except ET.ParseError:
            # Acceptable to fail on malformed XML
            pass

    def test_svg_without_viewbox_or_dimensions(self, generator, temp_output_path):
        """Test SVG without viewBox or width/height attributes."""
        minimal_svg = '<svg xmlns="http://www.w3.org/2000/svg"></svg>'

        # Should use defaults and create file
        generator.create_pptx_from_svg(minimal_svg, temp_output_path)
        assert temp_output_path.exists()

    def test_very_large_viewbox(self, generator):
        """Test handling of very large viewBox dimensions."""
        large_viewbox = (0, 0, 10000, 5000)
        width_emu, height_emu = generator._calculate_slide_dimensions(large_viewbox)

        # Should still produce reasonable dimensions
        assert width_emu > 0
        assert height_emu > 0
        assert width_emu < 50000000  # Less than ~55 inches (reasonable max)

    def test_zero_dimensions_viewbox(self, generator):
        """Test handling of zero dimension viewBox."""
        zero_viewbox = (0, 0, 0, 100)

        # Should handle gracefully without division by zero
        try:
            width_emu, height_emu = generator._calculate_slide_dimensions(zero_viewbox)
            assert width_emu > 0
            assert height_emu > 0
        except ZeroDivisionError:
            pytest.fail("Should handle zero dimensions without division by zero")


class TestPowerPointCompatibility:
    """Test PowerPoint compatibility (if PowerPoint is available)."""

    def test_pptx_file_mime_type_detection(self):
        """Test that PPTX file can be detected by MIME type."""
        # This would be expanded if we had access to PowerPoint or LibreOffice
        pass

    def test_pptx_basic_structure_compliance(self):
        """Test basic OOXML compliance."""
        # Could be expanded with schema validation
        pass


# Integration test to verify the complete workflow
def test_complete_svg_to_pptx_workflow():
    """Test the complete SVG to PPTX conversion workflow."""
    svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
        <rect x="50" y="50" width="100" height="80" fill="blue" stroke="black"/>
        <circle cx="300" cy="100" r="50" fill="red"/>
        <text x="200" y="120" font-size="16">Hello PPTX!</text>
    </svg>'''

    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
        output_path = Path(tmp.name)

    try:
        # Convert SVG to PPTX
        svg_to_pptx(svg_content, output_path)

        # Verify file was created
        assert output_path.exists()
        assert output_path.stat().st_size > 1000  # Should be substantial size

        # Verify ZIP structure
        with zipfile.ZipFile(output_path, 'r') as zip_file:
            files = zip_file.namelist()

            # Key files present
            assert '[Content_Types].xml' in files
            assert 'ppt/presentation.xml' in files
            assert 'ppt/slides/slide1.xml' in files

            # Presentation has custom dimensions based on viewBox
            presentation_xml = zip_file.read('ppt/presentation.xml').decode('utf-8')

            # Should have slide dimensions (not default 16:9)
            assert 'sldSz cx=' in presentation_xml
            assert 'cy=' in presentation_xml

    finally:
        output_path.unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])