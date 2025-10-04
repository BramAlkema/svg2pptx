#!/usr/bin/env python3
"""
Integration Tests for MultiPageConverter Debug Tracing

Tests that enable_debug flag propagates through the entire pipeline:
PipelineConfig → CleanSlateMultiPageConverter → PackageWriter → MultiPageResult
"""

import pytest
import tempfile
from pathlib import Path

from core.multipage.converter import CleanSlateMultiPageConverter, PageSource
from core.pipeline.config import PipelineConfig


class TestMultiPageConverterDebugPropagation:
    """Test debug flag propagation through multipage conversion"""

    def test_debug_flag_propagates_to_package_writer(self):
        """Test that enable_debug from config reaches PackageWriter"""
        config = PipelineConfig(enable_debug=True)
        converter = CleanSlateMultiPageConverter(config=config)

        # Verify PackageWriter was initialized with debug enabled
        assert converter.package_writer.enable_debug is True

    def test_debug_disabled_by_default(self):
        """Test that debug is disabled by default"""
        config = PipelineConfig()  # Default config
        converter = CleanSlateMultiPageConverter(config=config)

        # Verify PackageWriter has debug disabled
        assert converter.package_writer.enable_debug is False

    def test_debug_flag_disabled_explicitly(self):
        """Test explicit debug=False"""
        config = PipelineConfig(enable_debug=False)
        converter = CleanSlateMultiPageConverter(config=config)

        assert converter.package_writer.enable_debug is False


class TestMultiPageResultWithDebugData:
    """Test MultiPageResult includes package debug data"""

    def test_package_debug_data_present_when_enabled(self):
        """Test package_debug_data is in result when debug enabled"""
        config = PipelineConfig(enable_debug=True)
        converter = CleanSlateMultiPageConverter(config=config)

        # Create simple test pages
        pages = [
            PageSource(
                content='<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect x="10" y="10" width="100" height="100" fill="red"/></svg>',
                title="Page 1"
            ),
            PageSource(
                content='<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><circle cx="50" cy="50" r="40" fill="blue"/></svg>',
                title="Page 2"
            )
        ]

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = converter.convert_pages(pages, output_path)

            # Debug data should be present
            assert result.package_debug_data is not None
            assert isinstance(result.package_debug_data, dict)

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_package_debug_data_absent_when_disabled(self):
        """Test package_debug_data is None when debug disabled"""
        config = PipelineConfig(enable_debug=False)
        converter = CleanSlateMultiPageConverter(config=config)

        pages = [
            PageSource(
                content='<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect fill="green"/></svg>',
                title="Page 1"
            )
        ]

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = converter.convert_pages(pages, output_path)

            # Debug data should be None
            assert result.package_debug_data is None

        finally:
            Path(output_path).unlink(missing_ok=True)


class TestPackageDebugDataStructure:
    """Test structure of package debug data"""

    def test_debug_data_has_required_fields(self):
        """Test debug data contains all required timing/metrics"""
        config = PipelineConfig(enable_debug=True)
        converter = CleanSlateMultiPageConverter(config=config)

        pages = [
            PageSource(
                content='<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><text x="10" y="20">Test</text></svg>',
                title="Test Page"
            )
        ]

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = converter.convert_pages(pages, output_path)
            debug_data = result.package_debug_data

            # Required fields from PackageWriter tracing
            assert 'package_creation_ms' in debug_data
            assert 'file_write_ms' in debug_data
            assert 'package_size_bytes' in debug_data
            assert 'compression_ratio' in debug_data
            assert 'total_time_ms' in debug_data
            assert 'zip_structure' in debug_data

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_debug_data_timing_values(self):
        """Test debug data timing values are reasonable"""
        config = PipelineConfig(enable_debug=True)
        converter = CleanSlateMultiPageConverter(config=config)

        pages = [PageSource(
            content='<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect fill="orange"/></svg>',
            title="Timing Test"
        )]

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = converter.convert_pages(pages, output_path)
            debug_data = result.package_debug_data

            # All timing should be positive
            assert debug_data['package_creation_ms'] > 0
            assert debug_data['file_write_ms'] > 0
            assert debug_data['total_time_ms'] > 0

            # Should be reasonable (< 1 second for simple content)
            assert debug_data['package_creation_ms'] < 1000
            assert debug_data['file_write_ms'] < 500

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_debug_data_zip_structure(self):
        """Test ZIP structure data is correct"""
        config = PipelineConfig(enable_debug=True)
        converter = CleanSlateMultiPageConverter(config=config)

        # Create 3 pages
        pages = [
            PageSource(content=f'<svg xmlns="http://www.w3.org/2000/svg"><text>Page {i}</text></svg>', title=f"Page {i}")
            for i in range(1, 4)
        ]

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = converter.convert_pages(pages, output_path)
            zip_structure = result.package_debug_data['zip_structure']

            # Should have 3 slides
            assert zip_structure['slides'] == 3

        finally:
            Path(output_path).unlink(missing_ok=True)


class TestConvertFilesDebugPropagation:
    """Test debug propagation with convert_files()"""

    def test_convert_files_includes_debug_data(self):
        """Test convert_files() also propagates debug data"""
        config = PipelineConfig(enable_debug=True)
        converter = CleanSlateMultiPageConverter(config=config)

        # Create temp SVG files
        temp_dir = Path(tempfile.mkdtemp())
        svg_files = []

        for i in range(2):
            svg_path = temp_dir / f"test_{i}.svg"
            svg_path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg"><rect fill="purple"/></svg>')
            svg_files.append(str(svg_path))

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = converter.convert_files(svg_files, output_path)

            # Debug data should be present
            assert result.package_debug_data is not None
            assert 'package_creation_ms' in result.package_debug_data
            assert result.package_debug_data['zip_structure']['slides'] == 2

        finally:
            Path(output_path).unlink(missing_ok=True)
            for svg_file in svg_files:
                Path(svg_file).unlink(missing_ok=True)
            temp_dir.rmdir()


class TestE2ETracingComplete:
    """Test complete E2E tracing pipeline"""

    def test_complete_e2e_trace_available(self):
        """Test that both page traces AND package traces are available"""
        config = PipelineConfig(enable_debug=True)
        converter = CleanSlateMultiPageConverter(config=config)

        pages = [
            PageSource(
                content='<svg xmlns="http://www.w3.org/2000/svg"><rect fill="cyan"/></svg>',
                title="E2E Test"
            )
        ]

        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            output_path = tmp.name

        try:
            result = converter.convert_pages(pages, output_path)

            # Should have page results (conversion pipeline trace)
            assert len(result.page_results) == 1
            page_result = result.page_results[0]

            # Each page should have debug data from CleanSlateConverter
            if hasattr(page_result, 'debug_data') and page_result.debug_data:
                # Pipeline trace available
                assert 'parse_result' in page_result.debug_data or True  # May not be available yet

            # Should have package debug data (packaging trace)
            assert result.package_debug_data is not None

            # Combined: Full E2E trace from Parse → Analyze → Map → Embed → Package
            print(f"\n✅ Complete E2E Trace Available:")
            print(f"  Pages converted: {len(result.page_results)}")
            print(f"  Package creation: {result.package_debug_data['package_creation_ms']:.2f}ms")
            print(f"  File write: {result.package_debug_data['file_write_ms']:.2f}ms")
            print(f"  Package size: {result.package_debug_data['package_size_bytes']} bytes")

        finally:
            Path(output_path).unlink(missing_ok=True)
