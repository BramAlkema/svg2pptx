#!/usr/bin/env python3
"""
Unit Tests for PackageWriter Debug Tracing

Tests the debug instrumentation added to PackageWriter for E2E tracing capability.
"""

import pytest
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any

from core.io.package_writer import PackageWriter, PackageManifest, create_package_writer
from core.io.embedder import EmbedderResult


@pytest.fixture
def mock_embedder_result():
    """Create mock EmbedderResult for testing"""
    return EmbedderResult(
        slide_xml='<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree></p:spTree></p:cSld></p:sld>',
        relationship_data=[],
        media_files=[],
        elements_embedded=1,
        native_elements=1,
        emf_elements=0,
        processing_time_ms=1.0,
        total_size_bytes=100
    )


@pytest.fixture
def mock_embedder_results(mock_embedder_result):
    """Create list of mock embedder results"""
    return [mock_embedder_result, mock_embedder_result, mock_embedder_result]


class TestPackageWriterDebugParameter:
    """Test enable_debug parameter"""

    def test_init_with_debug_enabled(self):
        """Test initialization with debug enabled"""
        writer = PackageWriter(enable_debug=True)
        assert writer.enable_debug is True
        assert writer._debug_data is not None
        assert isinstance(writer._debug_data, dict)

    def test_init_with_debug_disabled(self):
        """Test initialization with debug disabled (default)"""
        writer = PackageWriter(enable_debug=False)
        assert writer.enable_debug is False
        assert writer._debug_data is None

    def test_init_default_debug_disabled(self):
        """Test default initialization has debug disabled"""
        writer = PackageWriter()
        assert writer.enable_debug is False
        assert writer._debug_data is None

    def test_factory_with_debug_enabled(self):
        """Test factory function with debug enabled"""
        writer = create_package_writer(enable_debug=True)
        assert writer.enable_debug is True

    def test_factory_default_debug_disabled(self):
        """Test factory function default"""
        writer = create_package_writer()
        assert writer.enable_debug is False


class TestPackageWriterDebugData:
    """Test debug data collection"""

    def test_debug_data_included_when_enabled(self, mock_embedder_results):
        """Test debug data is included in result when enabled"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)

            # Debug data should be present
            assert 'debug_data' in result
            assert isinstance(result['debug_data'], dict)

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_no_debug_data_when_disabled(self, mock_embedder_results):
        """Test debug data is NOT included when disabled"""
        writer = PackageWriter(enable_debug=False)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)

            # Debug data should NOT be present
            assert 'debug_data' not in result

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_debug_data_structure(self, mock_embedder_results):
        """Test debug data has correct structure"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)
            debug_data = result['debug_data']

            # Required fields
            assert 'package_creation_ms' in debug_data
            assert 'file_write_ms' in debug_data
            assert 'package_size_bytes' in debug_data
            assert 'compression_ratio' in debug_data
            assert 'total_time_ms' in debug_data
            assert 'zip_structure' in debug_data

        finally:
            Path(output_path).unlink(missing_ok=True)


class TestPackageWriterTiming:
    """Test timing measurements"""

    def test_package_creation_timing_positive(self, mock_embedder_results):
        """Test package creation time is measured and positive"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)
            debug_data = result['debug_data']

            # Package creation time should be positive
            assert debug_data['package_creation_ms'] > 0
            # Should be reasonable (< 1 second for 3 simple slides)
            assert debug_data['package_creation_ms'] < 1000

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_file_write_timing_positive(self, mock_embedder_results):
        """Test file write time is measured and positive"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)
            debug_data = result['debug_data']

            # File write time should be positive
            assert debug_data['file_write_ms'] > 0
            # Should be reasonable (< 500ms for small file)
            assert debug_data['file_write_ms'] < 500

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_total_time_equals_sum(self, mock_embedder_results):
        """Test total time approximately equals sum of stages"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)
            debug_data = result['debug_data']

            # Total should be approximately package creation + file write
            total = debug_data['total_time_ms']
            stages = debug_data['package_creation_ms'] + debug_data['file_write_ms']

            # Allow 10% tolerance for overhead
            assert abs(total - stages) / total < 0.1

        finally:
            Path(output_path).unlink(missing_ok=True)


class TestPackageWriterCompressionRatio:
    """Test compression ratio calculation"""

    def test_compression_ratio_calculated(self, mock_embedder_results):
        """Test compression ratio is calculated"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)
            debug_data = result['debug_data']

            # Compression ratio should be positive float
            assert isinstance(debug_data['compression_ratio'], float)
            assert debug_data['compression_ratio'] > 0

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_compression_ratio_reasonable(self, mock_embedder_results):
        """Test compression ratio is in reasonable range"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)
            debug_data = result['debug_data']

            # Compression ratio should be positive
            # Note: Can be > 1 for minimal content (ZIP overhead > content)
            # or < 1 for large content (actual compression)
            assert debug_data['compression_ratio'] > 0
            # Should not be impossibly large
            assert debug_data['compression_ratio'] < 100.0

        finally:
            Path(output_path).unlink(missing_ok=True)


class TestPackageWriterZIPStructure:
    """Test ZIP structure counting"""

    def test_zip_structure_present(self, mock_embedder_results):
        """Test ZIP structure data is present"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)
            debug_data = result['debug_data']

            # ZIP structure should be dict
            assert isinstance(debug_data['zip_structure'], dict)

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_zip_structure_counts(self, mock_embedder_results):
        """Test ZIP structure has correct counts"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)
            debug_data = result['debug_data']
            zip_structure = debug_data['zip_structure']

            # Should have expected counts
            assert zip_structure['slides'] == 3
            assert zip_structure['relationships'] == 0  # Mock has no relationships
            assert zip_structure['media_files'] == 0  # Mock has no media
            assert 'content_types' in zip_structure

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_zip_structure_with_media(self, mock_embedder_result):
        """Test ZIP structure counts media files correctly"""
        # Create embedder result with media
        result_with_media = EmbedderResult(
            slide_xml='<p:sld></p:sld>',
            relationship_data=[{'type': 'image', 'target': 'media/image1.png'}],
            media_files=[{'filename': 'image1.png', 'data': b'fake-png-data'}],
            elements_embedded=1,
            native_elements=1,
            emf_elements=0,
            processing_time_ms=1.0,
            total_size_bytes=100
        )

        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package([result_with_media], output_path)
            debug_data = result['debug_data']
            zip_structure = debug_data['zip_structure']

            # Should count media files
            assert zip_structure['media_files'] == 1
            assert zip_structure['relationships'] == 1

        finally:
            Path(output_path).unlink(missing_ok=True)


class TestPackageWriterPackageSize:
    """Test package size tracking"""

    def test_package_size_in_debug_data(self, mock_embedder_results):
        """Test package size is tracked in debug data"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)
            debug_data = result['debug_data']

            # Package size should be in debug data
            assert 'package_size_bytes' in debug_data
            assert debug_data['package_size_bytes'] > 0

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_package_size_matches_result(self, mock_embedder_results):
        """Test debug package size matches main result"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)
            debug_data = result['debug_data']

            # Debug size should match main result size
            assert debug_data['package_size_bytes'] == result['package_size_bytes']

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_package_size_matches_file(self, mock_embedder_results):
        """Test package size matches actual file size"""
        writer = PackageWriter(enable_debug=True)

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = writer.write_package(mock_embedder_results, output_path)
            debug_data = result['debug_data']

            # Debug size should match file on disk
            actual_file_size = Path(output_path).stat().st_size
            assert debug_data['package_size_bytes'] == actual_file_size

        finally:
            Path(output_path).unlink(missing_ok=True)


class TestPackageWriterBehaviorNoChange:
    """Test that debug mode doesn't change behavior"""

    def test_output_identical_with_and_without_debug(self, mock_embedder_results):
        """Test output file is identical with debug on/off"""
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp1:
            output_path_debug = tmp1.name

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp2:
            output_path_no_debug = tmp2.name

        try:
            # Write with debug
            writer_debug = PackageWriter(enable_debug=True)
            writer_debug.write_package(mock_embedder_results, output_path_debug)

            # Write without debug
            writer_no_debug = PackageWriter(enable_debug=False)
            writer_no_debug.write_package(mock_embedder_results, output_path_no_debug)

            # Files should be identical
            debug_content = Path(output_path_debug).read_bytes()
            no_debug_content = Path(output_path_no_debug).read_bytes()

            assert debug_content == no_debug_content

        finally:
            Path(output_path_debug).unlink(missing_ok=True)
            Path(output_path_no_debug).unlink(missing_ok=True)

    def test_result_structure_compatible(self, mock_embedder_results):
        """Test result structure is compatible with/without debug"""
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            writer_debug = PackageWriter(enable_debug=True)
            result_debug = writer_debug.write_package(mock_embedder_results, output_path)

            writer_no_debug = PackageWriter(enable_debug=False)
            result_no_debug = writer_no_debug.write_package(mock_embedder_results, output_path)

            # Base fields should be same
            for key in ['output_path', 'package_size_bytes', 'slide_count', 'media_files', 'relationships']:
                assert key in result_debug
                assert key in result_no_debug
                assert result_debug[key] == result_no_debug[key]

        finally:
            Path(output_path).unlink(missing_ok=True)
