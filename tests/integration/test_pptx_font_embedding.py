#!/usr/bin/env python3
"""
Integration Test for PPTX Font Embedding

Tests integration between FontEmbeddingEngine and PPTXPackageBuilder
for creating PPTX packages with embedded fonts.
"""

import pytest
from pathlib import Path
import sys
import tempfile
import os
import zipfile
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, mock_open

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.pptx.package_builder import PPTXPackageBuilder, create_pptx_with_embedded_fonts
from core.services.font_embedding_engine import FontEmbeddingEngine
from src.data.embedded_font import EmbeddedFont, FontSubsetRequest, EmbeddingPermission


class TestPPTXFontEmbeddingIntegration:
    """
    Integration tests for PPTX font embedding system.

    Tests the complete workflow from font embedding to PPTX package creation.
    """

    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_embedded_fonts(self):
        """Create sample embedded fonts for testing."""
        fonts = []

        # Create sample font 1
        font1 = EmbeddedFont(
            font_name="Arial",
            font_data=b"mock arial font data for testing" * 20,
            subset_characters={'H', 'e', 'l', 'o', ' ', 'W', 'r', 'd'},
            original_size=10000,
            embedded_size=3000,
            embedding_allowed=True,
            embedding_permission=EmbeddingPermission.INSTALLABLE,
            font_family="Arial",
            font_weight="normal",
            font_style="normal",
            file_format="ttf"
        )
        fonts.append(font1)

        # Create sample font 2
        font2 = EmbeddedFont(
            font_name="Times-New-Roman",
            font_data=b"mock times new roman font data for testing" * 15,
            subset_characters={'T', 'i', 'm', 'e', 's', ' ', 'R', 'o', 'a', 'n'},
            original_size=8000,
            embedded_size=2500,
            embedding_allowed=True,
            embedding_permission=EmbeddingPermission.INSTALLABLE,
            font_family="Times New Roman",
            font_weight="normal",
            font_style="normal",
            file_format="ttf"
        )
        fonts.append(font2)

        return fonts

    @pytest.fixture
    def sample_svg_content(self):
        """Create sample SVG content for testing (without embedded fonts)."""
        return '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
    <rect x="50" y="50" width="300" height="200" fill="#4472C4" stroke="#2F5597" stroke-width="3"/>
    <text x="200" y="150" text-anchor="middle" font-family="Arial" font-size="24" fill="white">
        Hello World
    </text>
    <text x="200" y="280" text-anchor="middle" font-family="Times New Roman" font-size="16" fill="#333">
        Sample text with embedded fonts
    </text>
</svg>'''

    @pytest.fixture
    def sample_svg_with_embedded_fonts(self):
        """Create sample SVG content with embedded fonts for testing."""
        return '''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
    <defs>
        <style>
            @font-face {
                font-family: 'Arial';
                src: url(data:application/font-woff2;charset=utf-8;base64,UklGRlQGAABXRUJQVlA4IEgGAADwFwCdASqQAH4APpE+m0olpCMiIagCABoJQWdu4XcAYwBhAGEAYQBh...) format('woff2');
                font-weight: normal;
                font-style: normal;
            }
            @font-face {
                font-family: 'Times New Roman';
                src: url(data:application/font-truetype;charset=utf-8;base64,AAEAAAAQAQAABAAAR0RFRgAjAA8AAAGQAAAAJkdQT1MAAAXkAAAAVkdTVUIAAAY8AAAAQGhlYWTk...) format('truetype');
                font-weight: normal;
                font-style: normal;
            }
        </style>
    </defs>
    <rect x="50" y="50" width="300" height="200" fill="#4472C4" stroke="#2F5597" stroke-width="3"/>
    <text x="200" y="150" text-anchor="middle" font-family="Arial" font-size="24" fill="white">
        Hello World
    </text>
    <text x="200" y="280" text-anchor="middle" font-family="Times New Roman" font-size="16" fill="#333">
        Sample text with embedded fonts
    </text>
</svg>'''

    def test_pptx_package_builder_basic_functionality(self, temp_directory, sample_embedded_fonts, sample_svg_content):
        """Test basic PPTXPackageBuilder functionality with font embedding."""
        builder = PPTXPackageBuilder()

        # Add embedded fonts
        for font in sample_embedded_fonts:
            relationship_id = builder.add_embedded_font(font)
            assert relationship_id.startswith('rId')

            # Check the embedded font in the builder (not the original)
            embedded_font = builder.get_embedded_font_by_name(font.font_name)
            assert embedded_font.relationship_id == relationship_id

        # Verify fonts were added
        assert len(builder._embedded_fonts) == 2
        assert builder.get_embedded_font_by_name("Arial") is not None
        assert builder.get_embedded_font_by_name("Times-New-Roman") is not None

        # Create PPTX file
        output_path = temp_directory / "test_embedded_fonts.pptx"
        builder.create_pptx_from_svg(sample_svg_content, output_path)

        # Verify PPTX file was created
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_pptx_package_content_validation(self, temp_directory, sample_embedded_fonts, sample_svg_with_embedded_fonts):
        """Test that PPTX package contains correct embedded font content."""
        builder = PPTXPackageBuilder()

        # Add embedded fonts (to test manual font addition)
        for font in sample_embedded_fonts:
            builder.add_embedded_font(font)

        # Create PPTX file
        output_path = temp_directory / "test_validation.pptx"
        builder.create_pptx_from_svg(sample_svg_with_embedded_fonts, output_path)

        # Examine PPTX package content
        with zipfile.ZipFile(output_path, 'r') as pptx_zip:
            file_list = pptx_zip.namelist()

            # Verify font files are embedded
            assert 'ppt/fonts/Arial.ttf' in file_list
            assert 'ppt/fonts/Times-New-Roman.ttf' in file_list

            # Verify content types include font declarations
            content_types = pptx_zip.read('[Content_Types].xml').decode('utf-8')
            assert 'application/vnd.ms-fontobject' in content_types
            assert '/ppt/fonts/Arial.ttf' in content_types
            assert '/ppt/fonts/Times-New-Roman.ttf' in content_types

            # Verify presentation relationships include font relationships
            pres_rels = pptx_zip.read('ppt/_rels/presentation.xml.rels').decode('utf-8')
            assert 'fonts/Arial.ttf' in pres_rels
            assert 'fonts/Times-New-Roman.ttf' in pres_rels

            # Verify font data integrity
            arial_data = pptx_zip.read('ppt/fonts/Arial.ttf')
            times_data = pptx_zip.read('ppt/fonts/Times-New-Roman.ttf')

            assert arial_data == sample_embedded_fonts[0].font_data
            assert times_data == sample_embedded_fonts[1].font_data

    def test_pptx_relationship_management(self, temp_directory, sample_embedded_fonts, sample_svg_with_embedded_fonts):
        """Test PPTX relationship management for embedded fonts."""
        builder = PPTXPackageBuilder()

        # Add fonts and track relationship IDs
        relationship_ids = []
        for font in sample_embedded_fonts:
            rel_id = builder.add_embedded_font(font)
            relationship_ids.append(rel_id)

        # Verify relationship ID generation
        assert relationship_ids[0] == 'rId3'  # After rId1 (master) and rId2 (slide)
        assert relationship_ids[1] == 'rId4'

        # Verify relationship lookup
        assert builder.get_font_relationship_id("Arial") == 'rId3'
        assert builder.get_font_relationship_id("Times-New-Roman") == 'rId4'
        assert builder.get_font_relationship_id("NonExistent") is None

        # Create PPTX and verify relationships in XML
        output_path = temp_directory / "test_relationships.pptx"
        builder.create_pptx_from_svg(sample_svg_with_embedded_fonts, output_path)

        with zipfile.ZipFile(output_path, 'r') as pptx_zip:
            pres_rels_xml = pptx_zip.read('ppt/_rels/presentation.xml.rels').decode('utf-8')
            root = ET.fromstring(pres_rels_xml)

            # Find font relationships
            font_relationships = []
            for rel in root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                if 'font' in rel.get('Type', ''):
                    font_relationships.append({
                        'id': rel.get('Id'),
                        'target': rel.get('Target')
                    })

            assert len(font_relationships) == 2
            assert any(rel['id'] == 'rId3' and 'Arial.ttf' in rel['target'] for rel in font_relationships)
            assert any(rel['id'] == 'rId4' and 'Times-New-Roman.ttf' in rel['target'] for rel in font_relationships)

    def test_font_embedding_engine_pptx_integration(self, temp_directory, sample_svg_content):
        """Test FontEmbeddingEngine integration with PPTX creation."""
        engine = FontEmbeddingEngine()

        # Mock font loading and subsetting
        with patch.object(engine._font_service, 'load_font_from_path') as mock_load:
            mock_font = Mock()
            mock_font.__contains__ = Mock(return_value=True)
            mock_os2 = Mock()
            mock_os2.fsType = 0  # Installable
            mock_font.__getitem__ = Mock(return_value=mock_os2)
            mock_load.return_value = mock_font

            with patch.object(engine, '_perform_font_subsetting') as mock_subset:
                mock_subset.return_value = b'mock subset font data'

                with patch('os.path.getsize', return_value=5000):

                    # Create text-font mappings
                    text_font_mappings = [
                        {
                            'text': 'Hello World',
                            'font_path': '/mock/arial.ttf',
                            'font_name': 'Arial'
                        },
                        {
                            'text': 'Sample text',
                            'font_path': '/mock/times.ttf',
                            'font_name': 'Times New Roman'
                        }
                    ]

                    # Create PPTX with embedded fonts
                    output_path = str(temp_directory / "engine_integration.pptx")
                    result = engine.create_pptx_embedding_package(
                        text_font_mappings=text_font_mappings,
                        svg_content=sample_svg_content,
                        output_path=output_path,
                        optimization_level='basic'
                    )

        # Verify result
        assert result['success'] is True
        assert result['output_path'] == output_path
        assert 'package_statistics' in result
        assert 'embedding_statistics' in result
        assert len(result['embedded_fonts']) == 2

        # Verify PPTX file was created
        assert Path(output_path).exists()

    def test_pptx_compatibility_validation(self, sample_embedded_fonts):
        """Test PPTX compatibility validation for embedded fonts."""
        engine = FontEmbeddingEngine()

        # Test with compatible fonts
        validation_result = engine.validate_pptx_compatibility(sample_embedded_fonts)

        assert len(validation_result['compatible_fonts']) == 2
        assert len(validation_result['incompatible_fonts']) == 0
        assert validation_result['compatibility_score'] == 1.0
        assert validation_result['total_size_mb'] > 0

        # Test with incompatible font (too large)
        large_font = EmbeddedFont(
            font_name="LargeFont",
            font_data=b"x" * (60 * 1024 * 1024),  # 60MB font
            subset_characters={'A'},
            original_size=60 * 1024 * 1024,
            embedded_size=60 * 1024 * 1024,
            embedding_allowed=True,
            embedding_permission=EmbeddingPermission.INSTALLABLE
        )

        validation_result = engine.validate_pptx_compatibility([large_font])

        assert len(validation_result['compatible_fonts']) == 0
        assert len(validation_result['incompatible_fonts']) == 1
        assert validation_result['compatibility_score'] == 0.0
        assert 'exceeds recommended 50MB limit' in validation_result['incompatible_fonts'][0]['issues'][0]

    def test_package_statistics_reporting(self, temp_directory, sample_embedded_fonts, sample_svg_content):
        """Test package statistics reporting functionality."""
        builder = PPTXPackageBuilder()

        # Add embedded fonts
        for font in sample_embedded_fonts:
            builder.add_embedded_font(font)

        # Get statistics
        stats = builder.get_package_statistics()

        assert stats['embedded_fonts_count'] == 2
        assert stats['total_font_size_bytes'] > 0
        assert stats['total_font_size_mb'] > 0
        assert len(stats['font_names']) == 2
        assert 'Arial' in stats['font_names']
        assert 'Times-New-Roman' in stats['font_names']
        assert len(stats['font_relationships']) == 2
        assert stats['average_compression_ratio'] > 0

    def test_create_pptx_with_embedded_fonts_api(self, temp_directory, sample_embedded_fonts, sample_svg_content):
        """Test the convenience API function for creating PPTX with embedded fonts."""
        output_path = temp_directory / "api_test.pptx"

        builder = create_pptx_with_embedded_fonts(
            svg_content=sample_svg_content,
            output_path=output_path,
            embedded_fonts=sample_embedded_fonts
        )

        # Verify file was created
        assert output_path.exists()

        # Verify builder has fonts
        assert len(builder._embedded_fonts) == 2
        assert builder.get_embedded_font_by_name("Arial") is not None

        # Verify package statistics
        stats = builder.get_package_statistics()
        assert stats['embedded_fonts_count'] == 2

    def test_font_filename_sanitization(self, temp_directory, sample_svg_content):
        """Test font filename sanitization for ZIP entry names."""
        builder = PPTXPackageBuilder()

        # Create font with problematic name
        problematic_font = EmbeddedFont(
            font_name="Font With Spaces & Special@Characters!",
            font_data=b"mock font data",
            subset_characters={'A'},
            original_size=1000,
            embedded_size=500,
            embedding_allowed=True,
            embedding_permission=EmbeddingPermission.INSTALLABLE
        )

        builder.add_embedded_font(problematic_font)

        # Create PPTX
        output_path = temp_directory / "sanitization_test.pptx"
        builder.create_pptx_from_svg(sample_svg_content, output_path)

        # Verify sanitized filename in package
        with zipfile.ZipFile(output_path, 'r') as pptx_zip:
            file_list = pptx_zip.namelist()

            # Should have sanitized filename
            font_files = [f for f in file_list if f.startswith('ppt/fonts/')]
            assert len(font_files) == 1

            # Filename should be sanitized
            font_filename = font_files[0]
            assert 'ppt/fonts/Font_With_Spaces___Special_Characters_.ttf' == font_filename

    def test_error_handling_in_pptx_creation(self, temp_directory, sample_svg_content):
        """Test error handling during PPTX creation."""
        engine = FontEmbeddingEngine()

        # Test with empty font mappings
        result = engine.create_pptx_embedding_package(
            text_font_mappings=[],
            svg_content=sample_svg_content,
            output_path=str(temp_directory / "empty_test.pptx")
        )

        assert result['success'] is False
        assert 'No fonts could be embedded successfully' in result['error']

        # Test with invalid font paths
        invalid_mappings = [
            {
                'text': 'Test',
                'font_path': '/nonexistent/font.ttf',
                'font_name': 'NonExistent'
            }
        ]

        result = engine.create_pptx_embedding_package(
            text_font_mappings=invalid_mappings,
            svg_content=sample_svg_content,
            output_path=str(temp_directory / "invalid_test.pptx")
        )

        assert result['success'] is False
        assert result['embedded_fonts_count'] == 0

    def test_package_builder_clear_fonts(self, sample_embedded_fonts):
        """Test clearing embedded fonts from package builder."""
        builder = PPTXPackageBuilder()

        # Add fonts
        for font in sample_embedded_fonts:
            builder.add_embedded_font(font)

        assert len(builder._embedded_fonts) == 2
        assert len(builder._font_relationships) == 2

        # Clear fonts
        builder.clear_embedded_fonts()

        assert len(builder._embedded_fonts) == 0
        assert len(builder._font_relationships) == 0
        assert builder._relationship_counter == 3  # Reset to initial value


class TestPPTXPackageValidation:
    """
    Tests for PPTX package validation and PowerPoint compatibility.

    Verifies that generated packages are valid OOXML and can be opened by PowerPoint.
    """

    def test_ooxml_structure_validation(self, tmp_path):
        """Test that generated PPTX has valid OOXML structure."""
        builder = PPTXPackageBuilder()

        # Create simple PPTX
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="blue"/></svg>'
        output_path = tmp_path / "structure_test.pptx"

        builder.create_pptx_from_svg(svg_content, output_path)

        # Validate OOXML structure
        with zipfile.ZipFile(output_path, 'r') as pptx_zip:
            file_list = pptx_zip.namelist()

            # Required OOXML files
            required_files = [
                '[Content_Types].xml',
                '_rels/.rels',
                'ppt/presentation.xml',
                'ppt/_rels/presentation.xml.rels',
                'ppt/slides/slide1.xml',
                'ppt/slides/_rels/slide1.xml.rels',
                'ppt/slideMasters/slideMaster1.xml',
                'ppt/slideMasters/_rels/slideMaster1.xml.rels',
                'ppt/slideLayouts/slideLayout1.xml',
                'ppt/slideLayouts/_rels/slideLayout1.xml.rels'
            ]

            for required_file in required_files:
                assert required_file in file_list

            # Validate XML structure of key files
            content_types_xml = pptx_zip.read('[Content_Types].xml')
            ET.fromstring(content_types_xml)  # Should not raise exception

            presentation_xml = pptx_zip.read('ppt/presentation.xml')
            ET.fromstring(presentation_xml)  # Should not raise exception

    def test_content_type_registration(self, tmp_path):
        """Test that content types are properly registered for fonts."""
        builder = PPTXPackageBuilder()

        # Add mock font
        mock_font = EmbeddedFont(
            font_name="TestFont",
            font_data=b"mock font data",
            subset_characters={'T'},
            original_size=1000,
            embedded_size=500,
            embedding_allowed=True,
            embedding_permission=EmbeddingPermission.INSTALLABLE
        )

        builder.add_embedded_font(mock_font)

        # Create PPTX with SVG that contains embedded fonts
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <defs>
        <style>
            @font-face {
                font-family: 'TestFont';
                src: url(data:application/font-truetype;charset=utf-8;base64,AAEAAAAQAQAABAAAR0RFRg...) format('truetype');
            }
        </style>
    </defs>
    <text font-family="TestFont">Test</text>
</svg>'''
        output_path = tmp_path / "content_type_test.pptx"

        builder.create_pptx_from_svg(svg_content, output_path)

        # Verify content type registration
        with zipfile.ZipFile(output_path, 'r') as pptx_zip:
            content_types_xml = pptx_zip.read('[Content_Types].xml').decode('utf-8')

            # Should have font content type defaults
            assert 'Extension="ttf"' in content_types_xml
            assert 'application/vnd.ms-fontobject' in content_types_xml

            # Should have specific font override
            assert '/ppt/fonts/TestFont.ttf' in content_types_xml


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__])