#!/usr/bin/env python3
"""
Test suite for Clean Slate Package Writer.

Tests PPTX package assembly from EmbedderResult inputs.
"""

import pytest
import zipfile
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch
from lxml import etree as ET
from io import BytesIO

from core.io.package_writer import PackageWriter, PackageManifest, PackageError
from core.io.embedder import EmbedderResult


class TestPackageWriter:
    """Test the PackageWriter class."""

    @pytest.fixture
    def package_writer(self):
        """Create a PackageWriter instance for testing."""
        return PackageWriter()

    @pytest.fixture
    def sample_embedder_result(self):
        """Create sample EmbedderResult for testing."""
        slide_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name="Slide"/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="9144000" cy="6858000"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="9144000" cy="6858000"/>
                </a:xfrm>
            </p:grpSpPr>
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="2" name="Test Rectangle"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="914400" y="685800"/>
                        <a:ext cx="1828800" cy="914400"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect"/>
                    <a:solidFill>
                        <a:srgbClr val="0000FF"/>
                    </a:solidFill>
                </p:spPr>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>'''

        return EmbedderResult(
            slide_xml=slide_xml,
            relationship_data=[
                {
                    'id': 'rId1',
                    'type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout',
                    'target': '../slideLayouts/slideLayout1.xml'
                }
            ],
            media_files=[
                {
                    'filename': 'image1.png',
                    'content_type': 'image/png',
                    'data': b'fake_png_data',
                    'relationship_id': 'rId2'
                }
            ],
            elements_embedded=1,
            native_elements=1,
            emf_elements=0,
            total_size_bytes=1024
        )

    @pytest.fixture
    def temp_output_path(self):
        """Create temporary file path for PPTX output."""
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            yield Path(tmp.name)
        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)

    def test_package_writer_initialization(self, package_writer):
        """Test PackageWriter initializes correctly."""
        assert package_writer is not None
        assert hasattr(package_writer, '_content_types')
        assert 'slide' in package_writer._content_types
        assert 'presentation' in package_writer._content_types

    def test_write_package_creates_file(self, package_writer, sample_embedder_result, temp_output_path):
        """Test that write_package creates a PPTX file."""
        result = package_writer.write_package([sample_embedder_result], str(temp_output_path))

        assert temp_output_path.exists()
        assert temp_output_path.stat().st_size > 0
        assert result['output_path'] == str(temp_output_path)
        assert result['slide_count'] == 1
        assert result['package_size_bytes'] > 0

    def test_write_package_creates_valid_zip(self, package_writer, sample_embedder_result, temp_output_path):
        """Test that created PPTX is a valid ZIP file with expected structure."""
        package_writer.write_package([sample_embedder_result], str(temp_output_path))

        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            files = zip_file.namelist()

            # Check required OOXML structure
            required_files = [
                '[Content_Types].xml',
                '_rels/.rels',
                'ppt/presentation.xml',
                'ppt/_rels/presentation.xml.rels',
                'ppt/slides/slide1.xml',
                'ppt/slides/_rels/slide1.xml.rels'
            ]

            for required_file in required_files:
                assert required_file in files, f"Missing required file: {required_file}"

    def test_package_contains_valid_xml_files(self, package_writer, sample_embedder_result, temp_output_path):
        """Test that all XML files in the package are well-formed."""
        package_writer.write_package([sample_embedder_result], str(temp_output_path))

        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            for file_name in zip_file.namelist():
                if file_name.endswith('.xml'):
                    xml_content = zip_file.read(file_name)
                    try:
                        ET.fromstring(xml_content)
                    except ET.XMLSyntaxError as e:
                        pytest.fail(f"Invalid XML in PPTX file {file_name}: {e}")

    def test_package_contains_slide_content(self, package_writer, sample_embedder_result, temp_output_path):
        """Test that the package contains the embedded slide content."""
        package_writer.write_package([sample_embedder_result], str(temp_output_path))

        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            slide_xml = zip_file.read('ppt/slides/slide1.xml').decode('utf-8')

            # Should contain our test shape
            assert 'Test Rectangle' in slide_xml
            assert 'prstGeom prst="rect"' in slide_xml
            assert 'srgbClr val="0000FF"' in slide_xml

    def test_package_contains_media_files(self, package_writer, sample_embedder_result, temp_output_path):
        """Test that media files are properly embedded."""
        package_writer.write_package([sample_embedder_result], str(temp_output_path))

        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            files = zip_file.namelist()

            # Media file should be present
            assert 'ppt/media/image1.png' in files

            # Check media content
            media_content = zip_file.read('ppt/media/image1.png')
            assert media_content == b'fake_png_data'

    def test_content_types_includes_media(self, package_writer, sample_embedder_result, temp_output_path):
        """Test that Content_Types.xml includes media file types."""
        package_writer.write_package([sample_embedder_result], str(temp_output_path))

        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            content_types = zip_file.read('[Content_Types].xml').decode('utf-8')

            # Should contain media content types
            assert 'image/png' in content_types
            # The package writer uses Default entries, not Override entries for media
            assert 'Default Extension="png"' in content_types

    def test_relationships_are_correct(self, package_writer, sample_embedder_result, temp_output_path):
        """Test that relationships are properly established."""
        package_writer.write_package([sample_embedder_result], str(temp_output_path))

        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            # Check slide relationships
            slide_rels = zip_file.read('ppt/slides/_rels/slide1.xml.rels').decode('utf-8')
            assert 'slideLayout1.xml' in slide_rels
            # The sample embedder result has a relationship to slideLayout, not media
            # Media relationships would be added by the actual mapping process
            assert 'rId1' in slide_rels

    def test_write_package_stream(self, package_writer, sample_embedder_result):
        """Test writing package to a stream."""
        stream = BytesIO()
        result = package_writer.write_package_stream([sample_embedder_result], stream)

        assert result['slide_count'] == 1
        assert result['package_size_bytes'] > 0

        # Stream should contain ZIP data
        stream.seek(0)
        with zipfile.ZipFile(stream, 'r') as zip_file:
            files = zip_file.namelist()
            assert '[Content_Types].xml' in files
            assert 'ppt/slides/slide1.xml' in files

    def test_multiple_slides_package(self, package_writer, sample_embedder_result, temp_output_path):
        """Test package creation with multiple slides."""
        # Create a second slide
        slide2 = EmbedderResult(
            slide_xml=sample_embedder_result.slide_xml.replace('Test Rectangle', 'Test Circle'),
            relationship_data=sample_embedder_result.relationship_data,
            media_files=[],
            elements_embedded=1,
            native_elements=1
        )

        result = package_writer.write_package([sample_embedder_result, slide2], str(temp_output_path))

        assert result['slide_count'] == 2

        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            files = zip_file.namelist()
            assert 'ppt/slides/slide1.xml' in files
            assert 'ppt/slides/slide2.xml' in files
            assert 'ppt/slides/_rels/slide1.xml.rels' in files
            assert 'ppt/slides/_rels/slide2.xml.rels' in files

    def test_custom_manifest(self, package_writer, sample_embedder_result, temp_output_path):
        """Test package creation with custom manifest."""
        manifest = PackageManifest(
            slides=['slide1.xml'],
            relationships=[],
            media_files=[],
            content_types=[],
            title='Test Presentation',
            author='Test Author'
        )

        result = package_writer.write_package([sample_embedder_result], str(temp_output_path), manifest)

        assert result['slide_count'] == 1
        assert temp_output_path.exists()

    def test_package_error_handling(self, package_writer):
        """Test error handling for invalid inputs."""
        with pytest.raises(PackageError):
            # Invalid output path
            package_writer.write_package([], '/invalid/path/test.pptx')

    def test_statistics_calculation(self, package_writer, sample_embedder_result, temp_output_path):
        """Test that package statistics are calculated correctly."""
        result = package_writer.write_package([sample_embedder_result], str(temp_output_path))

        assert 'processing_time_ms' in result
        assert 'compression_ratio' in result
        assert 'media_files' in result
        assert 'relationships' in result
        assert result['processing_time_ms'] >= 0
        assert result['media_files'] == 1  # One media file in sample
        assert result['slide_count'] == 1

    def test_empty_embedder_results(self, package_writer, temp_output_path):
        """Test handling of empty embedder results."""
        result = package_writer.write_package([], str(temp_output_path))

        assert result['slide_count'] == 0
        assert temp_output_path.exists()

        # Should still create valid PPTX structure
        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            files = zip_file.namelist()
            assert '[Content_Types].xml' in files
            assert 'ppt/presentation.xml' in files


class TestPackageManifest:
    """Test the PackageManifest class."""

    def test_manifest_creation(self):
        """Test PackageManifest creation."""
        manifest = PackageManifest(
            slides=['slide1.xml'],
            relationships=[{'id': 'rId1', 'type': 'layout', 'target': 'layout1.xml'}],
            media_files=[{'filename': 'image1.png', 'type': 'image/png'}],
            content_types=[{'extension': 'png', 'content_type': 'image/png'}],
            title='Test',
            author='Test Author'
        )

        assert manifest.title == 'Test'
        assert manifest.author == 'Test Author'
        assert len(manifest.slides) == 1
        assert len(manifest.relationships) == 1
        assert len(manifest.media_files) == 1


class TestPackageValidation:
    """Test package validation and compatibility."""

    @pytest.fixture
    def package_writer(self):
        return PackageWriter()

    @pytest.fixture
    def sample_embedder_result(self):
        """Minimal valid EmbedderResult."""
        return EmbedderResult(
            slide_xml='<?xml version="1.0"?><p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name="Slide"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr></p:grpSpPr></p:spTree></p:cSld></p:sld>',
            relationship_data=[],
            media_files=[]
        )

    def test_minimal_package_structure(self, package_writer, sample_embedder_result, temp_output_path):
        """Test that minimal package has correct OOXML structure."""
        package_writer.write_package([sample_embedder_result], str(temp_output_path))

        with zipfile.ZipFile(temp_output_path, 'r') as zip_file:
            # Check OOXML compliance
            assert '[Content_Types].xml' in zip_file.namelist()
            assert '_rels/.rels' in zip_file.namelist()

            # Check presentation structure
            presentation_xml = zip_file.read('ppt/presentation.xml').decode('utf-8')
            assert 'presentation' in presentation_xml
            assert 'sldIdLst' in presentation_xml

    @pytest.fixture
    def temp_output_path(self):
        """Create temporary file path for PPTX output."""
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            yield Path(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])