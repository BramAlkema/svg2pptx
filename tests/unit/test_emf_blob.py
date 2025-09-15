"""
Test suite for EMF blob generation.
Tests EMF pattern creation, PowerPoint compatibility, and pattern tiles.
"""

import pytest
import struct
from unittest.mock import patch, Mock

from src.emf_blob import (
    EMFBlob, EMFRecordType, EMFBrushStyle, EMFHatchStyle,
    create_pattern_tile, get_starter_pack
)


@pytest.fixture
def emf_blob():
    """Create an EMFBlob instance for testing."""
    return EMFBlob(width=200, height=150)


class TestEMFBlob:
    """Test suite for EMF blob generation functionality."""

    def test_initialization(self, emf_blob):
        """Test EMF blob initialization."""
        assert emf_blob.width == 200
        assert emf_blob.height == 150
        assert len(emf_blob.records) == 1  # Header record
        assert emf_blob.next_handle == 1
        assert emf_blob.object_handles == []

    def test_header_structure(self, emf_blob):
        """Test EMF header record structure."""
        header = emf_blob.records[0]

        # Check header starts with correct record type
        record_type = struct.unpack('<I', header[:4])[0]
        assert record_type == EMFRecordType.EMR_HEADER

        # Check header size
        record_size = struct.unpack('<I', header[4:8])[0]
        assert record_size == 108

        # Check bounds rectangle
        bounds = struct.unpack('<4l', header[8:24])
        assert bounds == (0, 0, 200, 150)

    def test_handle_allocation(self, emf_blob):
        """Test object handle allocation."""
        handle1 = emf_blob._allocate_handle()
        handle2 = emf_blob._allocate_handle()

        assert handle1 == 1
        assert handle2 == 2
        assert emf_blob.object_handles == [1, 2]
        assert emf_blob.next_handle == 3

    def test_add_hatch_horizontal(self, emf_blob):
        """Test adding horizontal hatch pattern."""
        handle = emf_blob.add_hatch("horizontal", color=0xFF0000, background=0xFFFFFF)

        assert handle == 1
        assert len(emf_blob.records) == 2  # Header + brush creation

        # Verify brush creation record
        brush_record = emf_blob.records[1]
        record_type = struct.unpack('<I', brush_record[:4])[0]
        assert record_type == EMFRecordType.EMR_CREATEBRUSHINDIRECT

    def test_add_hatch_vertical(self, emf_blob):
        """Test adding vertical hatch pattern."""
        handle = emf_blob.add_hatch("vertical", color=0x00FF00)

        assert handle == 1
        assert len(emf_blob.records) == 2

    def test_add_hatch_diagonal(self, emf_blob):
        """Test adding diagonal hatch pattern."""
        handle = emf_blob.add_hatch("diagonal", color=0x0000FF)

        assert handle == 1
        assert len(emf_blob.records) == 2

    def test_add_hatch_cross(self, emf_blob):
        """Test adding cross hatch pattern."""
        handle = emf_blob.add_hatch("cross", color=0x000000)

        assert handle == 1
        assert len(emf_blob.records) == 2

    def test_add_hatch_invalid_pattern(self, emf_blob):
        """Test adding hatch with invalid pattern defaults to horizontal."""
        handle = emf_blob.add_hatch("invalid_pattern", color=0x000000)

        assert handle == 1
        assert len(emf_blob.records) == 2

    def test_add_crosshatch(self, emf_blob):
        """Test adding crosshatch pattern."""
        handle = emf_blob.add_crosshatch(spacing=15, color=0x800080)

        assert handle == 1
        assert len(emf_blob.records) == 2

    def test_add_hex_dots(self, emf_blob):
        """Test adding hexagonal dot pattern."""
        handle = emf_blob.add_hex_dots(radius=8, spacing=20, color=0xFF8000)

        assert handle == 1
        assert len(emf_blob.records) == 2

    def test_add_grid(self, emf_blob):
        """Test adding grid pattern."""
        handle = emf_blob.add_grid(
            cell_width=25, cell_height=25,
            line_width=2, color=0x404040
        )

        assert handle == 1
        assert len(emf_blob.records) == 2

    def test_add_brick(self, emf_blob):
        """Test adding brick pattern."""
        handle = emf_blob.add_brick(
            brick_width=40, brick_height=20,
            mortar_width=3, color=0x8B4513, mortar_color=0xD3D3D3
        )

        assert handle == 1
        assert len(emf_blob.records) == 2

    def test_add_raster_32bpp(self, emf_blob):
        """Test adding 32-bit raster pattern."""
        pixel_data = b'\xFF\x00\x00\xFF' * (10 * 10)  # 10x10 red pixels
        handle = emf_blob.add_raster_32bpp(10, 10, pixel_data)

        assert handle == 1
        assert len(emf_blob.records) == 2

    def test_fill_rectangle(self, emf_blob):
        """Test filling rectangle with brush."""
        brush_handle = emf_blob.add_hatch("horizontal")
        emf_blob.fill_rectangle(10, 20, 100, 80, brush_handle)

        # Should have header, brush creation, select object, and rectangle records
        assert len(emf_blob.records) == 4

        # Check select object record
        select_record = emf_blob.records[2]
        record_type = struct.unpack('<I', select_record[:4])[0]
        assert record_type == EMFRecordType.EMR_SELECTOBJECT

        # Check rectangle record
        rect_record = emf_blob.records[3]
        record_type = struct.unpack('<I', rect_record[:4])[0]
        assert record_type == EMFRecordType.EMR_RECTANGLE

    def test_multiple_patterns(self, emf_blob):
        """Test creating multiple patterns in same EMF."""
        handle1 = emf_blob.add_hatch("horizontal", color=0xFF0000)
        handle2 = emf_blob.add_grid(cell_width=20, cell_height=20)
        handle3 = emf_blob.add_hex_dots(radius=5, spacing=15)

        assert handle1 == 1
        assert handle2 == 2
        assert handle3 == 3
        assert len(emf_blob.object_handles) == 3
        assert len(emf_blob.records) == 4  # Header + 3 brush creations

    def test_finalize_basic(self, emf_blob):
        """Test basic EMF finalization."""
        brush_handle = emf_blob.add_hatch("horizontal")
        emf_blob.fill_rectangle(0, 0, 100, 100, brush_handle)

        blob = emf_blob.finalize()

        assert isinstance(blob, bytes)
        assert len(blob) > 0

        # Check that EOF record was added
        # Should have header, brush, select, rectangle, EOF = 5 records
        assert len(emf_blob.records) == 5

    def test_finalize_updates_header(self, emf_blob):
        """Test that finalize updates header with correct values."""
        brush_handle = emf_blob.add_hatch("horizontal")
        emf_blob.fill_rectangle(0, 0, 100, 100, brush_handle)

        blob = emf_blob.finalize()

        # Check that header was updated with total size and record count
        header = emf_blob.records[0]
        total_size = struct.unpack('<I', header[44:48])[0]
        num_records = struct.unpack('<I', header[48:52])[0]
        num_handles = struct.unpack('<H', header[52:54])[0]

        assert total_size == len(blob)
        assert num_records == 5  # header, brush, select, rectangle, EOF
        assert num_handles == 1

    def test_xml_tile_fill(self, emf_blob):
        """Test PowerPoint XML generation for tiled fill."""
        brush_handle = emf_blob.add_hatch("horizontal")
        xml = emf_blob.xml_tile_fill(brush_handle)

        assert '<a:blipFill>' in xml
        assert '<a:tile' in xml
        assert f'r:embed="emf_{brush_handle}"' in xml
        assert 'algn="tl"' in xml

    def test_xml_stretch_fill(self, emf_blob):
        """Test PowerPoint XML generation for stretched fill."""
        brush_handle = emf_blob.add_grid(cell_width=30, cell_height=30)
        xml = emf_blob.xml_stretch_fill(brush_handle)

        assert '<a:blipFill>' in xml
        assert '<a:stretch>' in xml
        assert f'r:embed="emf_{brush_handle}"' in xml
        assert '<a:fillRect/>' in xml

    def test_xml_contains_base64_data(self, emf_blob):
        """Test that XML methods include base64 EMF data."""
        brush_handle = emf_blob.add_hatch("horizontal")

        with patch('base64.b64encode') as mock_b64:
            mock_b64.return_value.decode.return_value = "mock_base64_data"
            xml = emf_blob.xml_tile_fill(brush_handle)

            mock_b64.assert_called_once()
            # The actual embedding would be handled by PowerPoint packaging

    def test_empty_emf_finalization(self):
        """Test finalizing EMF with no patterns."""
        emf = EMFBlob(100, 100)
        blob = emf.finalize()

        assert isinstance(blob, bytes)
        assert len(blob) > 0
        # Should have header and EOF only
        assert len(emf.records) == 2


class TestCreatePatternTile:
    """Test suite for pattern tile factory function."""

    def test_create_hatch_tile(self):
        """Test creating hatch pattern tile."""
        emf = create_pattern_tile('hatch', direction='vertical', color=0xFF0000)

        assert isinstance(emf, EMFBlob)
        assert emf.width == 100  # Default width
        assert emf.height == 100  # Default height
        assert len(emf.object_handles) == 1

    def test_create_crosshatch_tile(self):
        """Test creating crosshatch pattern tile."""
        emf = create_pattern_tile('crosshatch', spacing=20, color=0x00FF00)

        assert isinstance(emf, EMFBlob)
        assert len(emf.object_handles) == 1

    def test_create_dots_tile(self):
        """Test creating dots pattern tile."""
        emf = create_pattern_tile('dots', radius=10, spacing=25, color=0x0000FF)

        assert isinstance(emf, EMFBlob)
        assert len(emf.object_handles) == 1

    def test_create_grid_tile(self):
        """Test creating grid pattern tile."""
        emf = create_pattern_tile('grid', cell_width=15, cell_height=15, color=0x808080)

        assert isinstance(emf, EMFBlob)
        assert len(emf.object_handles) == 1

    def test_create_brick_tile(self):
        """Test creating brick pattern tile."""
        emf = create_pattern_tile('brick', brick_width=25, brick_height=12)

        assert isinstance(emf, EMFBlob)
        assert len(emf.object_handles) == 1

    def test_create_tile_custom_dimensions(self):
        """Test creating pattern tile with custom dimensions."""
        emf = create_pattern_tile('hatch', width=200, height=150)

        assert emf.width == 200
        assert emf.height == 150

    def test_create_tile_invalid_pattern(self):
        """Test creating tile with invalid pattern type."""
        with pytest.raises(ValueError, match="Unknown pattern type"):
            create_pattern_tile('invalid_pattern')

    def test_create_tile_with_defaults(self):
        """Test creating tile uses appropriate defaults."""
        emf = create_pattern_tile('hatch')

        # Should use default parameters
        assert emf.width == 100
        assert emf.height == 100
        assert len(emf.object_handles) == 1


class TestGetStarterPack:
    """Test suite for starter pack pattern collection."""

    def test_starter_pack_creation(self):
        """Test creating starter pack of patterns."""
        patterns = get_starter_pack()

        assert isinstance(patterns, dict)
        assert len(patterns) > 0

    def test_starter_pack_pattern_types(self):
        """Test starter pack contains expected pattern types."""
        patterns = get_starter_pack()

        expected_patterns = [
            'horizontal_lines', 'vertical_lines', 'diagonal_lines', 'crosshatch',
            'fine_grid', 'coarse_grid', 'small_dots', 'large_dots', 'brick'
        ]

        for pattern_name in expected_patterns:
            assert pattern_name in patterns
            assert isinstance(patterns[pattern_name], EMFBlob)

    def test_starter_pack_pattern_uniqueness(self):
        """Test starter pack patterns are distinct."""
        patterns = get_starter_pack()

        # Each pattern should have different characteristics
        emf_blobs = list(patterns.values())
        assert len(emf_blobs) == len(set(id(emf) for emf in emf_blobs))

    def test_starter_pack_finalization(self):
        """Test starter pack patterns can be finalized."""
        patterns = get_starter_pack()

        for name, emf in patterns.items():
            blob = emf.finalize()
            assert isinstance(blob, bytes)
            assert len(blob) > 0, f"Pattern {name} produced empty blob"


class TestEMFRecordStructure:
    """Test suite for EMF record structure validation."""

    def test_record_header_format(self):
        """Test EMF record header format."""
        emf = EMFBlob(100, 100)
        emf.add_hatch("horizontal")

        # Check brush creation record format
        brush_record = emf.records[1]

        # First 4 bytes: record type
        record_type = struct.unpack('<I', brush_record[:4])[0]
        assert record_type == EMFRecordType.EMR_CREATEBRUSHINDIRECT

        # Next 4 bytes: record size
        record_size = struct.unpack('<I', brush_record[4:8])[0]
        assert record_size == len(brush_record)
        assert record_size >= 8  # Minimum record size

    def test_brush_data_structure(self):
        """Test brush data structure in records."""
        emf = EMFBlob(100, 100)
        handle = emf.add_hatch("horizontal", color=0xFF0000)

        brush_record = emf.records[1]

        # Skip record header (8 bytes) and handle (4 bytes)
        brush_data_start = 12

        # Check brush style
        brush_style = struct.unpack('<I', brush_record[brush_data_start:brush_data_start+4])[0]
        assert brush_style == EMFBrushStyle.BS_HATCHED

        # Check brush color
        brush_color = struct.unpack('<I', brush_record[brush_data_start+4:brush_data_start+8])[0]
        assert brush_color == 0xFF0000

    def test_record_alignment(self):
        """Test that records maintain proper alignment."""
        emf = EMFBlob(100, 100)
        emf.add_hatch("horizontal")
        emf.add_grid(cell_width=20, cell_height=20)

        for record in emf.records:
            # All records should be at least 8 bytes (type + size)
            assert len(record) >= 8

            # Record size should match actual size
            declared_size = struct.unpack('<I', record[4:8])[0]
            assert declared_size == len(record)


class TestEMFCompatibility:
    """Test suite for PowerPoint EMF compatibility."""

    def test_emf_signature(self, emf_blob):
        """Test EMF has correct signature."""
        header = emf_blob.records[0]

        # EMF signature should be at offset 40
        signature = header[40:48]
        assert signature == b'ENHMETA '

    def test_emf_version(self, emf_blob):
        """Test EMF version field."""
        header = emf_blob.records[0]

        # Version should be at offset 48
        version = struct.unpack('<I', header[48:52])[0]
        assert version == 0x10000  # EMF version 1.0

    def test_device_resolution(self, emf_blob):
        """Test EMF device resolution settings."""
        header = emf_blob.records[0]

        # Device resolution is at offsets 80 and 84
        h_res = struct.unpack('<I', header[80:84])[0]
        v_res = struct.unpack('<I', header[84:88])[0]

        assert h_res == 96  # 96 DPI
        assert v_res == 96  # 96 DPI

    def test_coordinate_mapping(self, emf_blob):
        """Test coordinate system mapping for PowerPoint."""
        # EMF should use logical coordinates that map to PowerPoint EMUs
        assert emf_blob.width > 0
        assert emf_blob.height > 0

        # Bounds should be set correctly in header
        header = emf_blob.records[0]
        bounds = struct.unpack('<4l', header[8:24])
        assert bounds == (0, 0, emf_blob.width, emf_blob.height)

    def test_frame_rectangle(self, emf_blob):
        """Test frame rectangle for device units."""
        header = emf_blob.records[0]

        # Frame rectangle at offset 24 (in .01mm units)
        frame = struct.unpack('<4l', header[24:40])
        expected_width = emf_blob.width * 2540 // 914400  # EMU to .01mm
        expected_height = emf_blob.height * 2540 // 914400

        assert frame == (0, 0, expected_width, expected_height)


class TestPerformanceOptimization:
    """Test suite for EMF generation performance."""

    def test_large_pattern_generation(self):
        """Test performance with large pattern dimensions."""
        emf = EMFBlob(width=1000, height=1000)

        # Should handle large dimensions efficiently
        handle = emf.add_hatch("crosshatch")
        emf.fill_rectangle(0, 0, 1000, 1000, handle)

        blob = emf.finalize()
        assert len(blob) > 0

    def test_multiple_pattern_efficiency(self):
        """Test efficiency with multiple patterns."""
        emf = EMFBlob(200, 200)

        # Create multiple patterns
        handles = []
        for i in range(10):
            handle = emf.add_hatch("horizontal", color=i * 0x111111)
            handles.append(handle)
            emf.fill_rectangle(i * 20, 0, 20, 200, handle)

        blob = emf.finalize()
        assert len(blob) > 0
        assert len(handles) == 10

    def test_memory_usage_pattern(self):
        """Test memory usage pattern for EMF generation."""
        emf = EMFBlob(500, 500)

        initial_records = len(emf.records)

        # Add pattern and fill
        handle = emf.add_grid(cell_width=50, cell_height=50)
        emf.fill_rectangle(0, 0, 500, 500, handle)

        # Should only add necessary records
        final_records = len(emf.records)
        assert final_records == initial_records + 3  # brush, select, rectangle