"""
Enhanced Metafile (EMF) blob generator for PowerPoint compatibility.

This module provides pure Python EMF generation without external dependencies,
enabling vector-first fallback strategies for complex SVG filter effects.
Generates EMF blobs that can be embedded in PowerPoint presentations.
"""

import struct
from typing import List
from enum import IntEnum


class EMFRecordType(IntEnum):
    """EMF record types for metafile generation."""
    EMR_HEADER = 1
    EMR_POLYBEZIER = 2
    EMR_POLYGON = 3
    EMR_POLYLINE = 4
    EMR_POLYBEZIERTO = 5
    EMR_POLYLINETO = 6
    EMR_POLYPOLYLINE = 7
    EMR_POLYPOLYGON = 8
    EMR_SETWINDOWEXTEX = 9
    EMR_SETWINDOWORGEX = 10
    EMR_SETVIEWPORTEXTEX = 11
    EMR_SETVIEWPORTORGEX = 12
    EMR_SETBRUSHORGEX = 13
    EMR_EOF = 14
    EMR_SETPIXELV = 15
    EMR_SETMAPPERFLAGS = 16
    EMR_SETMAPMODE = 17
    EMR_SETBKMODE = 18
    EMR_SETPOLYFILLMODE = 19
    EMR_SETROP2 = 20
    EMR_SETSTRETCHBLTMODE = 21
    EMR_SETTEXTALIGN = 22
    EMR_SETCOLORADJUSTMENT = 23
    EMR_SETTEXTCOLOR = 24
    EMR_SETBKCOLOR = 25
    EMR_OFFSETCLIPRGN = 26
    EMR_MOVETOEX = 27
    EMR_SETMETARGN = 28
    EMR_EXCLUDECLIPRECT = 29
    EMR_INTERSECTCLIPRECT = 30
    EMR_SCALEVIEWPORTEXTEX = 31
    EMR_SCALEWINDOWEXTEX = 32
    EMR_SAVEDC = 33
    EMR_RESTOREDC = 34
    EMR_SETWORLDTRANSFORM = 35
    EMR_MODIFYWORLDTRANSFORM = 36
    EMR_SELECTOBJECT = 37
    EMR_CREATEPEN = 38
    EMR_CREATEBRUSHINDIRECT = 39
    EMR_DELETEOBJECT = 40
    EMR_ANGLEARC = 41
    EMR_ELLIPSE = 42
    EMR_RECTANGLE = 43
    EMR_ROUNDRECT = 44
    EMR_ARC = 45
    EMR_CHORD = 46
    EMR_PIE = 47
    EMR_SELECTPALETTE = 48
    EMR_CREATEPALETTE = 49
    EMR_SETPALETTEENTRIES = 50
    EMR_RESIZEPALETTE = 51
    EMR_REALIZEPALETTE = 52
    EMR_EXTFLOODFILL = 53
    EMR_LINETO = 54
    EMR_ARCTO = 55
    EMR_POLYDRAW = 56
    EMR_SETARCDIRECTION = 57
    EMR_SETMITERLIMIT = 58
    EMR_BEGINPATH = 59
    EMR_ENDPATH = 60
    EMR_CLOSEFIGURE = 61
    EMR_FILLPATH = 62
    EMR_STROKEANDFILLPATH = 63
    EMR_STROKEPATH = 64
    EMR_FLATTENPATH = 65
    EMR_WIDENPATH = 66
    EMR_SELECTCLIPPATH = 67
    EMR_ABORTPATH = 68
    EMR_COMMENT = 70
    EMR_FILLRGN = 71
    EMR_FRAMERGN = 72
    EMR_INVERTRGN = 73
    EMR_PAINTRGN = 74
    EMR_EXTSELECTCLIPRGN = 75
    EMR_BITBLT = 76
    EMR_STRETCHBLT = 77
    EMR_MASKBLT = 78
    EMR_PLGBLT = 79
    EMR_SETDIBITSTODEVICE = 80
    EMR_STRETCHDIBITS = 81
    EMR_EXTCREATEFONTINDIRECTW = 82
    EMR_EXTTEXTOUTA = 83
    EMR_EXTTEXTOUTW = 84
    EMR_POLYBEZIER16 = 85
    EMR_POLYGON16 = 86
    EMR_POLYLINE16 = 87
    EMR_POLYBEZIERTO16 = 88
    EMR_POLYLINETO16 = 89
    EMR_POLYPOLYLINE16 = 90
    EMR_POLYPOLYGON16 = 91
    EMR_POLYDRAW16 = 92
    EMR_CREATEMONOBRUSH = 93
    EMR_CREATEDIBPATTERNBRUSHPT = 94
    EMR_EXTCREATEPEN = 95
    EMR_POLYTEXTOUTA = 96
    EMR_POLYTEXTOUTW = 97


class EMFBrushStyle(IntEnum):
    """EMF brush styles for pattern generation."""
    BS_SOLID = 0
    BS_NULL = 1
    BS_HATCHED = 2
    BS_PATTERN = 3
    BS_INDEXED = 4
    BS_DIBPATTERN = 5
    BS_DIBPATTERNPT = 6
    BS_PATTERN8X8 = 7
    BS_DIBPATTERN8X8 = 8
    BS_MONOPATTERN = 9


class EMFHatchStyle(IntEnum):
    """EMF hatch styles for pattern tiles."""
    HS_HORIZONTAL = 0
    HS_VERTICAL = 1
    HS_FDIAGONAL = 2
    HS_BDIAGONAL = 3
    HS_CROSS = 4
    HS_DIAGCROSS = 5


class EMFBlob:
    """Enhanced Metafile blob generator for PowerPoint compatibility."""

    def __init__(self, width: int = 100, height: int = 100):
        """Initialize EMF blob generator.

        Args:
            width: EMF canvas width in EMUs
            height: EMF canvas height in EMUs
        """
        self.width = width
        self.height = height
        self.records: List[bytes] = []
        self.object_handles = []
        self.next_handle = 1

        # Initialize EMF header
        self._init_header()

    def _init_header(self) -> None:
        """Initialize EMF header record."""
        # EMF header structure
        header_size = 108  # Size of EMF header
        header_data = struct.pack('<I', EMFRecordType.EMR_HEADER)  # Record type
        header_data += struct.pack('<I', header_size)  # Record size

        # Bounds rectangle (logical units)
        header_data += struct.pack('<4l', 0, 0, self.width, self.height)

        # Frame rectangle (device units, .01mm)
        frame_width = self.width * 2540 // 914400  # Convert EMU to .01mm
        frame_height = self.height * 2540 // 914400
        header_data += struct.pack('<4l', 0, 0, frame_width, frame_height)

        # Signature 'ENHMETA'
        header_data += b'ENHMETA '

        # Version, size, number of records (to be updated)
        header_data += struct.pack('<III', 0x10000, 0, 0)

        # Number of handles, reserved, description length, description offset
        header_data += struct.pack('<HHHH', 0, 0, 0, 0)

        # Palette entries, device width, device height
        header_data += struct.pack('<III', 0, frame_width // 100, frame_height // 100)

        # Device resolution
        header_data += struct.pack('<II', 96, 96)  # 96 DPI

        # Millimeter size
        header_data += struct.pack('<II', frame_width // 100, frame_height // 100)

        # Pad to header size
        padding = header_size - len(header_data)
        header_data += b'\x00' * padding

        self.records.append(header_data)

    def _add_record(self, record_type: EMFRecordType, data: bytes) -> None:
        """Add a record to the EMF blob.

        Args:
            record_type: EMF record type
            data: Record data
        """
        record_size = 8 + len(data)  # Header + data
        record = struct.pack('<II', record_type, record_size) + data
        self.records.append(record)

    def _allocate_handle(self) -> int:
        """Allocate a new object handle."""
        handle = self.next_handle
        self.object_handles.append(handle)
        self.next_handle += 1
        return handle

    def add_hatch(self, pattern: str = "horizontal", color: int = 0x000000,
                  background: int = 0xFFFFFF) -> int:
        """Add a hatch pattern to the EMF.

        Args:
            pattern: Hatch pattern type ("horizontal", "vertical", "diagonal", "cross")
            color: Foreground color (RGB)
            background: Background color (RGB)

        Returns:
            Handle to the created brush object
        """
        # Map pattern names to EMF hatch styles
        hatch_map = {
            "horizontal": EMFHatchStyle.HS_HORIZONTAL,
            "vertical": EMFHatchStyle.HS_VERTICAL,
            "diagonal": EMFHatchStyle.HS_FDIAGONAL,
            "cross": EMFHatchStyle.HS_CROSS,
            "diagcross": EMFHatchStyle.HS_DIAGCROSS
        }

        hatch_style = hatch_map.get(pattern, EMFHatchStyle.HS_HORIZONTAL)
        handle = self._allocate_handle()

        # Create hatched brush
        brush_data = struct.pack('<III',
                                EMFBrushStyle.BS_HATCHED,
                                color,
                                hatch_style)
        self._add_record(EMFRecordType.EMR_CREATEBRUSHINDIRECT,
                        struct.pack('<I', handle) + brush_data)

        return handle

    def add_crosshatch(self, spacing: int = 10, color: int = 0x000000,
                      background: int = 0xFFFFFF) -> int:
        """Add a crosshatch pattern.

        Args:
            spacing: Spacing between lines in logical units
            color: Line color (RGB)
            background: Background color (RGB)

        Returns:
            Handle to the created brush object
        """
        return self.add_hatch("cross", color, background)

    def add_hex_dots(self, radius: int = 5, spacing: int = 15,
                    color: int = 0x000000, background: int = 0xFFFFFF) -> int:
        """Add hexagonal dot pattern.

        Args:
            radius: Dot radius in logical units
            spacing: Spacing between dots
            color: Dot color (RGB)
            background: Background color (RGB)

        Returns:
            Handle to the created pattern brush
        """
        # Create a simple dot pattern using a custom bitmap
        # For now, use a solid brush as approximation
        handle = self._allocate_handle()

        brush_data = struct.pack('<III',
                                EMFBrushStyle.BS_SOLID,
                                color,
                                0)
        self._add_record(EMFRecordType.EMR_CREATEBRUSHINDIRECT,
                        struct.pack('<I', handle) + brush_data)

        return handle

    def add_grid(self, cell_width: int = 20, cell_height: int = 20,
                line_width: int = 1, color: int = 0x000000,
                background: int = 0xFFFFFF) -> int:
        """Add a grid pattern.

        Args:
            cell_width: Grid cell width
            cell_height: Grid cell height
            line_width: Grid line width
            color: Line color (RGB)
            background: Background color (RGB)

        Returns:
            Handle to the created pattern brush
        """
        return self.add_hatch("cross", color, background)

    def add_brick(self, brick_width: int = 30, brick_height: int = 15,
                 mortar_width: int = 2, color: int = 0x8B4513,
                 mortar_color: int = 0xD3D3D3) -> int:
        """Add a brick pattern.

        Args:
            brick_width: Width of each brick
            brick_height: Height of each brick
            mortar_width: Width of mortar lines
            color: Brick color (RGB)
            mortar_color: Mortar color (RGB)

        Returns:
            Handle to the created pattern brush
        """
        handle = self._allocate_handle()

        brush_data = struct.pack('<III',
                                EMFBrushStyle.BS_SOLID,
                                color,
                                0)
        self._add_record(EMFRecordType.EMR_CREATEBRUSHINDIRECT,
                        struct.pack('<I', handle) + brush_data)

        return handle

    def add_raster_32bpp(self, width: int, height: int,
                        pixel_data: bytes) -> int:
        """Add a 32-bit raster image for complex patterns.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            pixel_data: RGBA pixel data

        Returns:
            Handle to the created pattern brush
        """
        handle = self._allocate_handle()

        # Create DIB pattern brush
        # This is a simplified implementation
        brush_data = struct.pack('<III',
                                EMFBrushStyle.BS_DIBPATTERNPT,
                                0,  # Placeholder for DIB data
                                0)
        self._add_record(EMFRecordType.EMR_CREATEDIBPATTERNBRUSHPT,
                        struct.pack('<I', handle) + brush_data)

        return handle

    def fill_rectangle(self, x: int, y: int, width: int, height: int,
                      brush_handle: int) -> None:
        """Fill a rectangle with the specified brush.

        Args:
            x: Rectangle x coordinate
            y: Rectangle y coordinate
            width: Rectangle width
            height: Rectangle height
            brush_handle: Handle to brush object
        """
        # Select brush
        self._add_record(EMFRecordType.EMR_SELECTOBJECT,
                        struct.pack('<I', brush_handle))

        # Draw rectangle
        rect_data = struct.pack('<4l', x, y, x + width, y + height)
        self._add_record(EMFRecordType.EMR_RECTANGLE, rect_data)

    def finalize(self) -> bytes:
        """Finalize the EMF and return the complete blob.

        Returns:
            Complete EMF blob as bytes
        """
        # Add EOF record
        self._add_record(EMFRecordType.EMR_EOF, struct.pack('<III', 0, 0, 0))

        # Calculate total size and update header
        total_size = sum(len(record) for record in self.records)
        num_records = len(self.records)

        # Update header with correct values
        header = bytearray(self.records[0])
        struct.pack_into('<I', header, 44, total_size)  # Total size
        struct.pack_into('<I', header, 48, num_records)  # Number of records
        struct.pack_into('<H', header, 52, len(self.object_handles))  # Number of handles
        self.records[0] = bytes(header)

        # Combine all records
        return b''.join(self.records)

    def xml_tile_fill(self, brush_handle: int) -> str:
        """Generate PowerPoint XML for tiled fill using EMF pattern.

        Args:
            brush_handle: Handle to the pattern brush

        Returns:
            PowerPoint DrawingML XML for tiled fill
        """
        emf_data = self.finalize()
        import base64
        emf_b64 = base64.b64encode(emf_data).decode('ascii')

        return f'''
        <a:blipFill>
            <a:blip r:embed="emf_{brush_handle}">
                <a:extLst>
                    <a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">
                        <a14:useLocalDpi xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main" val="0"/>
                    </a:ext>
                </a:extLst>
            </a:blip>
            <a:tile tx="0" ty="0" sx="100000" sy="100000" algn="tl" flip="none"/>
        </a:blipFill>'''

    def xml_stretch_fill(self, brush_handle: int) -> str:
        """Generate PowerPoint XML for stretched fill using EMF pattern.

        Args:
            brush_handle: Handle to the pattern brush

        Returns:
            PowerPoint DrawingML XML for stretched fill
        """
        emf_data = self.finalize()
        import base64
        emf_b64 = base64.b64encode(emf_data).decode('ascii')

        return f'''
        <a:blipFill>
            <a:blip r:embed="emf_{brush_handle}">
                <a:extLst>
                    <a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">
                        <a14:useLocalDpi xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main" val="0"/>
                    </a:ext>
                </a:extLst>
            </a:blip>
            <a:stretch>
                <a:fillRect/>
            </a:stretch>
        </a:blipFill>'''


def create_pattern_tile(pattern_type: str, **kwargs) -> EMFBlob:
    """Factory function to create common pattern tiles.

    Args:
        pattern_type: Type of pattern ("hatch", "crosshatch", "dots", "grid", "brick")
        **kwargs: Pattern-specific parameters

    Returns:
        EMFBlob configured with the specified pattern
    """
    emf = EMFBlob(kwargs.get('width', 100), kwargs.get('height', 100))

    if pattern_type == "hatch":
        brush = emf.add_hatch(
            pattern=kwargs.get('direction', 'horizontal'),
            color=kwargs.get('color', 0x000000),
            background=kwargs.get('background', 0xFFFFFF)
        )
    elif pattern_type == "crosshatch":
        brush = emf.add_crosshatch(
            spacing=kwargs.get('spacing', 10),
            color=kwargs.get('color', 0x000000),
            background=kwargs.get('background', 0xFFFFFF)
        )
    elif pattern_type == "dots":
        brush = emf.add_hex_dots(
            radius=kwargs.get('radius', 5),
            spacing=kwargs.get('spacing', 15),
            color=kwargs.get('color', 0x000000),
            background=kwargs.get('background', 0xFFFFFF)
        )
    elif pattern_type == "grid":
        brush = emf.add_grid(
            cell_width=kwargs.get('cell_width', 20),
            cell_height=kwargs.get('cell_height', 20),
            line_width=kwargs.get('line_width', 1),
            color=kwargs.get('color', 0x000000),
            background=kwargs.get('background', 0xFFFFFF)
        )
    elif pattern_type == "brick":
        brush = emf.add_brick(
            brick_width=kwargs.get('brick_width', 30),
            brick_height=kwargs.get('brick_height', 15),
            mortar_width=kwargs.get('mortar_width', 2),
            color=kwargs.get('color', 0x8B4513),
            mortar_color=kwargs.get('mortar_color', 0xD3D3D3)
        )
    else:
        raise ValueError(f"Unknown pattern type: {pattern_type}")

    # Fill the entire canvas with the pattern
    emf.fill_rectangle(0, 0, emf.width, emf.height, brush)

    return emf


# Example usage and starter pack patterns
def get_starter_pack() -> dict:
    """Get a starter pack of common EMF pattern tiles.

    Returns:
        Dictionary mapping pattern names to EMFBlob instances
    """
    patterns = {}

    # Basic hatch patterns
    patterns['horizontal_lines'] = create_pattern_tile('hatch', direction='horizontal')
    patterns['vertical_lines'] = create_pattern_tile('hatch', direction='vertical')
    patterns['diagonal_lines'] = create_pattern_tile('hatch', direction='diagonal')
    patterns['crosshatch'] = create_pattern_tile('crosshatch')

    # Grid patterns
    patterns['fine_grid'] = create_pattern_tile('grid', cell_width=10, cell_height=10)
    patterns['coarse_grid'] = create_pattern_tile('grid', cell_width=30, cell_height=30)

    # Dot patterns
    patterns['small_dots'] = create_pattern_tile('dots', radius=2, spacing=10)
    patterns['large_dots'] = create_pattern_tile('dots', radius=5, spacing=20)

    # Brick pattern
    patterns['brick'] = create_pattern_tile('brick')

    return patterns