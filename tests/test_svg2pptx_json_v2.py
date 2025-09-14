#!/usr/bin/env python3

import pytest
import tempfile
import json
import base64
import zipfile
import io
from lxml import etree as ET
from pathlib import Path
from unittest.mock import patch, MagicMock
from svgelements import SVG, Color

from src.svg2pptx_json_v2 import (
    PptxJSON, emu_px, rgb_hex, stroke_cap, stroke_join,
    flatten_segment, to_lines, make_sp_from_lines, 
    slide_xml_from_shapes, update_presentation_size, convert,
    EMU_PER_PX, NS
)

class TestUtilityFunctions:
    """Test utility conversion functions."""
    
    def test_emu_px_conversion(self):
        """Test EMU to pixel conversion."""
        assert emu_px(0) == 0
        assert emu_px(1) == EMU_PER_PX
        assert emu_px(10.5) == int(round(10.5 * EMU_PER_PX))
        assert emu_px(-5) == int(round(-5 * EMU_PER_PX))
    
    def test_rgb_hex_valid_color(self):
        """Test RGB hex conversion for valid colors."""
        # Mock Color object
        color = MagicMock()
        color.value = True
        color.red = 1.0
        color.green = 0.5  
        color.blue = 0.0
        
        result = rgb_hex(color)
        assert result == "FF7F00"
    
    def test_rgb_hex_none_color(self):
        """Test RGB hex conversion for None color."""
        assert rgb_hex(None) is None
        
        # Test color with None value
        color = MagicMock()
        color.value = None
        assert rgb_hex(color) is None
    
    def test_stroke_cap_conversions(self):
        """Test stroke cap style conversions."""
        assert stroke_cap("butt") == "flat"
        assert stroke_cap("round") == "rnd" 
        assert stroke_cap("square") == "sq"
        assert stroke_cap("invalid") == "flat"
        assert stroke_cap(None) == "flat"
        assert stroke_cap("") == "flat"
    
    def test_stroke_join_conversions(self):
        """Test stroke join style conversions."""
        assert stroke_join("round") == "rnd"
        assert stroke_join("bevel") == "bevel"
        assert stroke_join("miter") == "miter"
        assert stroke_join("invalid") == "miter"
        assert stroke_join(None) == "miter"
        assert stroke_join("") == "miter"

class TestFlattenSegment:
    """Test segment flattening functionality."""
    
    def test_flatten_line_segment(self):
        """Test flattening of line segments."""
        # Mock Line segment
        line = MagicMock()
        line.__class__.__name__ = "Line"
        line.start = complex(0, 0)
        line.end = complex(10, 10)
        
        # Import Line to use isinstance check
        from svgelements import Line
        
        with patch('src.svg2pptx_json_v2.isinstance') as mock_isinstance:
            mock_isinstance.side_effect = lambda obj, cls: cls.__name__ == "Line"
            result = flatten_segment(line, 48)
            
        assert result == [(complex(0, 0), complex(10, 10))]
    
    def test_flatten_curve_segment(self):
        """Test flattening of curved segments."""
        # Mock curved segment
        curve = MagicMock()
        curve.__class__.__name__ = "CubicBezier"
        curve.point.side_effect = lambda t: complex(t*10, t*5)
        
        from svgelements import CubicBezier
        
        with patch('src.svg2pptx_json_v2.isinstance') as mock_isinstance:
            mock_isinstance.side_effect = lambda obj, cls: cls.__name__ == "CubicBezier"
            result = flatten_segment(curve, 4)
            
        assert len(result) == 4
        assert all(isinstance(seg, tuple) and len(seg) == 2 for seg in result)

class TestToLines:
    """Test shape to lines conversion."""
    
    @patch('src.svg2pptx_json_v2.flatten_segment')
    def test_to_lines_svg_path(self, mock_flatten):
        """Test conversion of SVG path to lines."""
        from svgelements import Path as SVGPath
        
        # Mock SVGPath
        path = MagicMock(spec=SVGPath)
        segment1 = MagicMock()
        segment2 = MagicMock()
        path.segments.return_value = [segment1, segment2]
        
        mock_flatten.side_effect = [[(0, 1)], [(2, 3)]]
        
        with patch('src.svg2pptx_json_v2.isinstance') as mock_isinstance:
            mock_isinstance.side_effect = lambda obj, cls: cls == SVGPath
            result = to_lines(path)
        
        assert result == [(0, 1), (2, 3)]
        assert mock_flatten.call_count == 2
    
    @patch('src.svg2pptx_json_v2.flatten_segment')
    @patch('src.svg2pptx_json_v2.SVGPath')
    def test_to_lines_other_shape(self, mock_svg_path_cls, mock_flatten):
        """Test conversion of other shapes to lines."""
        from svgelements import Shape
        
        # Mock shape
        shape = MagicMock(spec=Shape)
        
        # Mock SVGPath instance
        mock_path = MagicMock()
        segment1 = MagicMock()
        mock_path.segments.return_value = [segment1]
        mock_svg_path_cls.return_value = mock_path
        
        mock_flatten.return_value = [(0, 1)]
        
        with patch('src.svg2pptx_json_v2.isinstance') as mock_isinstance:
            mock_isinstance.return_value = False  # Not SVGPath
            result = to_lines(shape)
        
        assert result == [(0, 1)]
        mock_svg_path_cls.assert_called_once_with(shape)

class TestPptxJSON:
    """Test PPTX JSON handling class."""
    
    def test_init(self):
        """Test PptxJSON initialization."""
        entries = [{"path": "test.xml", "text": "content"}]
        pj = PptxJSON(entries)
        
        assert pj.entries == entries
        assert pj._index == {"test.xml": 0}
    
    def test_looks_like_xml(self):
        """Test XML content detection."""
        assert PptxJSON._looks_like_xml("<?xml version='1.0'?>")
        assert PptxJSON._looks_like_xml("<p:sld>content</p:sld>")
        assert PptxJSON._looks_like_xml("  <a:test>")
        assert not PptxJSON._looks_like_xml("not xml content")
        assert not PptxJSON._looks_like_xml("base64content==")
    
    def test_b64_or_utf8_xml_content(self):
        """Test base64 or UTF8 detection for XML content."""
        xml_content = "<?xml version='1.0'?><root/>"
        result = PptxJSON._b64_or_utf8(xml_content)
        assert result == {"text": xml_content}
    
    def test_b64_or_utf8_base64_content(self):
        """Test base64 or UTF8 detection for base64 content."""
        b64_content = base64.b64encode(b"test content").decode('ascii')
        result = PptxJSON._b64_or_utf8(b64_content)
        assert result == {"b64": b64_content}
    
    def test_b64_or_utf8_text_content(self):
        """Test base64 or UTF8 detection for plain text."""
        text_content = "plain text content"
        result = PptxJSON._b64_or_utf8(text_content)
        assert result == {"text": text_content}
    
    def test_from_obj_list(self):
        """Test creation from list object."""
        entries = [{"path": "test.xml", "text": "content"}]
        pj = PptxJSON._from_obj(entries)
        
        assert pj.entries == entries
        assert pj._index == {"test.xml": 0}
    
    def test_from_obj_dict_files_wrapper(self):
        """Test creation from dict with files wrapper."""
        obj = {"files": [{"path": "test.xml", "text": "content"}]}
        pj = PptxJSON._from_obj(obj)
        
        assert len(pj.entries) == 1
        assert pj.entries[0]["path"] == "test.xml"
    
    def test_from_obj_dict_mapping(self):
        """Test creation from dict mapping format."""
        obj = {
            "ppt/slide1.xml": "<?xml version='1.0'?><root/>",
            "ppt/media/image1.png": base64.b64encode(b"image data").decode('ascii')
        }
        pj = PptxJSON._from_obj(obj)
        
        assert len(pj.entries) == 2
        paths = [e["path"] for e in pj.entries]
        assert "ppt/slide1.xml" in paths
        assert "ppt/media/image1.png" in paths
    
    def test_from_obj_invalid(self):
        """Test creation from invalid object."""
        with pytest.raises(ValueError, match="Unsupported JSON root"):
            PptxJSON._from_obj("invalid")
    
    def test_get_text_from_text_field(self):
        """Test getting text from text field."""
        entries = [{"path": "test.xml", "text": "content"}]
        pj = PptxJSON(entries)
        
        assert pj.get_text("test.xml") == "content"
    
    def test_get_text_from_b64_field(self):
        """Test getting text from base64 field."""
        content = "test content"
        b64_content = base64.b64encode(content.encode('utf-8')).decode('ascii')
        entries = [{"path": "test.xml", "b64": b64_content}]
        pj = PptxJSON(entries)
        
        assert pj.get_text("test.xml") == content
    
    def test_get_text_from_data_field(self):
        """Test getting text from data field."""
        content = "test content"
        b64_content = base64.b64encode(content.encode('utf-8')).decode('ascii')
        entries = [{"path": "test.xml", "data": b64_content}]
        pj = PptxJSON(entries)
        
        assert pj.get_text("test.xml") == content
    
    def test_get_text_from_content_field_base64(self):
        """Test getting text from content field with base64 encoding."""
        content = "test content"
        b64_content = base64.b64encode(content.encode('utf-8')).decode('ascii')
        entries = [{"path": "test.xml", "content": b64_content, "encoding": "base64"}]
        pj = PptxJSON(entries)
        
        assert pj.get_text("test.xml") == content
    
    def test_get_text_from_content_field_utf8(self):
        """Test getting text from content field with utf8 encoding."""
        content = "test content"
        entries = [{"path": "test.xml", "content": content, "encoding": "utf8"}]
        pj = PptxJSON(entries)
        
        assert pj.get_text("test.xml") == content
    
    def test_get_text_missing_payload(self):
        """Test getting text with missing payload."""
        entries = [{"path": "test.xml"}]
        pj = PptxJSON(entries)
        
        with pytest.raises(ValueError, match="no textual payload"):
            pj.get_text("test.xml")
    
    def test_upsert_text_new_entry(self):
        """Test upserting text for new entry."""
        pj = PptxJSON([])
        pj.upsert_text("new.xml", "new content")
        
        assert len(pj.entries) == 1
        assert pj.entries[0] == {"path": "new.xml", "text": "new content"}
        assert pj._index["new.xml"] == 0
    
    def test_upsert_text_existing_entry(self):
        """Test upserting text for existing entry."""
        entries = [{"path": "test.xml", "text": "old content"}]
        pj = PptxJSON(entries)
        pj.upsert_text("test.xml", "new content")
        
        assert len(pj.entries) == 1
        assert pj.entries[0] == {"path": "test.xml", "text": "new content"}
    
    def test_to_pptx_bytes_text(self):
        """Test converting to PPTX bytes with text content."""
        entries = [{"path": "test.xml", "text": "content"}]
        pj = PptxJSON(entries)
        
        pptx_bytes = pj.to_pptx_bytes()
        
        # Verify it's a valid ZIP
        with zipfile.ZipFile(io.BytesIO(pptx_bytes), 'r') as zf:
            assert "test.xml" in zf.namelist()
            assert zf.read("test.xml") == b"content"
    
    def test_to_pptx_bytes_b64(self):
        """Test converting to PPTX bytes with base64 content."""
        content = b"test content"
        b64_content = base64.b64encode(content).decode('ascii')
        entries = [{"path": "test.bin", "b64": b64_content}]
        pj = PptxJSON(entries)
        
        pptx_bytes = pj.to_pptx_bytes()
        
        with zipfile.ZipFile(io.BytesIO(pptx_bytes), 'r') as zf:
            assert zf.read("test.bin") == content
    
    @patch('builtins.open')
    @patch('base64.b64decode')
    @patch('zipfile.ZipFile')
    def test_from_minimalpptx_txt(self, mock_zipfile, mock_b64decode, mock_open):
        """Test loading from minimalpptx.txt file."""
        # Mock file content
        mock_file = MagicMock()
        mock_file.read.return_value = "base64content"
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Mock base64 decode
        mock_b64decode.return_value = b"zip_content"
        
        # Mock zipfile
        mock_zf = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zf
        mock_zf.namelist.return_value = ["fileObj.txt", "other.json"]
        mock_zf.read.return_value = b'[{"path": "test.xml", "text": "content"}]'
        
        result = PptxJSON.from_minimalpptx_txt("test.txt")
        
        assert len(result.entries) == 1
        assert result.entries[0]["path"] == "test.xml"
    
    @patch('builtins.open')
    @patch('base64.b64decode')
    @patch('zipfile.ZipFile')
    def test_from_minimalpptx_txt_fallback_file(self, mock_zipfile, mock_b64decode, mock_open):
        """Test loading from minimalpptx.txt with fallback file selection."""
        # Mock file content
        mock_file = MagicMock()
        mock_file.read.return_value = "base64content"
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Mock base64 decode
        mock_b64decode.return_value = b"zip_content"
        
        # Mock zipfile without fileObj.txt/fileObj.json
        mock_zf = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zf
        mock_zf.namelist.return_value = ["data.xml", "info.txt"]  # No fileObj files
        mock_zf.read.return_value = b'[{"path": "test.xml", "text": "content"}]'
        
        result = PptxJSON.from_minimalpptx_txt("test.txt")
        
        # Should use fallback .txt file (info.txt)
        mock_zf.read.assert_called_once_with("info.txt")
        
    def test_from_obj_dict_metadata_skip(self):
        """Test creation from dict skipping metadata entries."""
        obj = {
            "_metadata": {"version": "1.0"},
            "_config": {"debug": True},
            "ppt/slide1.xml": "<?xml version='1.0'?><root/>"
        }
        pj = PptxJSON._from_obj(obj)
        
        # Should only have one entry (metadata keys skipped)
        assert len(pj.entries) == 1
        assert pj.entries[0]["path"] == "ppt/slide1.xml"
    
    def test_from_obj_dict_recognized_keys(self):
        """Test creation from dict with recognized keys in values."""
        obj = {
            "file1.xml": {"text": "content1", "encoding": "utf8"},
            "file2.bin": {"b64": base64.b64encode(b"binary").decode('ascii')},
            "file3.data": {"data": base64.b64encode(b"data").decode('ascii')},
            "file4.content": {"content": "content4", "encoding": "utf8"}
        }
        pj = PptxJSON._from_obj(obj)
        
        assert len(pj.entries) == 4
        paths = [e["path"] for e in pj.entries]
        assert all(f"file{i}" in str(paths) for i in range(1, 5))
    
    def test_from_obj_dict_unrecognized_dict_value(self):
        """Test creation from dict with unrecognized dict values."""
        obj = {
            "config.json": {"setting1": "value1", "setting2": "value2"}
        }
        pj = PptxJSON._from_obj(obj)
        
        assert len(pj.entries) == 1
        assert pj.entries[0]["path"] == "config.json"
        assert "text" in pj.entries[0]
        # Should be JSON serialized
        import json
        parsed = json.loads(pj.entries[0]["text"])
        assert parsed["setting1"] == "value1"
    
    def test_from_obj_dict_bytes_value(self):
        """Test creation from dict with bytes/bytearray values."""
        binary_data = b"binary content"
        obj = {
            "file1.bin": binary_data,
            "file2.bin": bytearray(binary_data)
        }
        pj = PptxJSON._from_obj(obj)
        
        assert len(pj.entries) == 2
        for entry in pj.entries:
            assert "b64" in entry
            decoded = base64.b64decode(entry["b64"])
            assert decoded == binary_data
    
    def test_from_obj_dict_other_value_types(self):
        """Test creation from dict with other value types."""
        obj = {
            "number.json": 42,
            "list.json": [1, 2, 3],
            "bool.json": True
        }
        pj = PptxJSON._from_obj(obj)
        
        assert len(pj.entries) == 3
        for entry in pj.entries:
            assert "text" in entry
            # All should be JSON serialized
    
    def test_to_pptx_bytes_data_field(self):
        """Test converting to PPTX bytes with data field."""
        content = b"test data content"
        data_content = base64.b64encode(content).decode('ascii')
        entries = [{"path": "test.bin", "data": data_content}]
        pj = PptxJSON(entries)
        
        pptx_bytes = pj.to_pptx_bytes()
        
        with zipfile.ZipFile(io.BytesIO(pptx_bytes), 'r') as zf:
            assert zf.read("test.bin") == content
    
    def test_to_pptx_bytes_content_field_base64(self):
        """Test converting to PPTX bytes with content field base64."""
        content = b"test content"
        b64_content = base64.b64encode(content).decode('ascii')
        entries = [{"path": "test.bin", "content": b64_content, "encoding": "base64"}]
        pj = PptxJSON(entries)
        
        pptx_bytes = pj.to_pptx_bytes()
        
        with zipfile.ZipFile(io.BytesIO(pptx_bytes), 'r') as zf:
            assert zf.read("test.bin") == content
    
    def test_to_pptx_bytes_content_field_utf8(self):
        """Test converting to PPTX bytes with content field utf8."""
        content = "test content"
        entries = [{"path": "test.txt", "content": content, "encoding": "utf8"}]
        pj = PptxJSON(entries)
        
        pptx_bytes = pj.to_pptx_bytes()
        
        with zipfile.ZipFile(io.BytesIO(pptx_bytes), 'r') as zf:
            assert zf.read("test.txt") == content.encode('utf-8')
    
    def test_to_pptx_bytes_missing_payload(self):
        """Test converting to PPTX bytes with missing payload."""
        entries = [{"path": "test.xml"}]  # No payload fields
        pj = PptxJSON(entries)
        
        with pytest.raises(ValueError, match="Entry missing payload"):
            pj.to_pptx_bytes()

class TestDrawingMLGeneration:
    """Test DrawingML XML generation."""
    
    def test_make_sp_from_lines_basic(self):
        """Test creating shape from lines."""
        lines = [(complex(0, 0), complex(10, 10)), (complex(10, 10), complex(20, 0))]
        stroke_hex = "FF0000"
        stroke_w_px = 2.0
        cap = "round"
        join = "miter"
        fill_hex = "00FF00"
        offx, offy = 0, 0
        shape_id = 2
        
        result = make_sp_from_lines(lines, stroke_hex, stroke_w_px, cap, join, fill_hex, offx, offy, shape_id)
        
        # Verify it's an XML element
        assert result.tag.endswith("}sp")
        
        # Check shape ID
        cNvPr = result.find(f".//{{{NS['p']}}}cNvPr")
        assert cNvPr.get("id") == "2"
        assert cNvPr.get("name") == "shape2"
        
        # Check stroke properties
        ln = result.find(f".//{{{NS['a']}}}ln")
        assert ln is not None
        assert ln.get("cap") == "rnd"  # stroke_cap("round") == "rnd"
        
        # Check fill - find solidFill that's a direct child of spPr (not inside ln)
        spPr = result.find(f".//{{{NS['p']}}}spPr")
        solidFill = spPr.find(f"{{{NS['a']}}}solidFill")  # Direct child only
        assert solidFill is not None
        srgbClr = solidFill.find(f"{{{NS['a']}}}srgbClr")
        assert srgbClr.get("val") == "00FF00"
    
    def test_make_sp_from_lines_no_stroke(self):
        """Test creating shape with no stroke."""
        lines = [(complex(0, 0), complex(10, 10))]
        
        result = make_sp_from_lines(lines, None, 0, None, None, None, 0, 0, 1)
        
        # Should have zero-width line
        ln = result.find(f".//{{{NS['a']}}}ln")
        assert ln.get("w") == "0"
    
    def test_make_sp_from_lines_closed_path(self):
        """Test creating shape with closed path."""
        # Create a closed path (start == end)
        lines = [(complex(0, 0), complex(10, 0)), (complex(10, 0), complex(10, 10)), (complex(10, 10), complex(0, 0))]
        
        result = make_sp_from_lines(lines, None, 0, None, None, None, 0, 0, 1)
        
        # Should have close element
        apath = result.find(f".//{{{NS['a']}}}path")
        close = apath.find(f"{{{NS['a']}}}close")
        assert close is not None
    
    def test_slide_xml_from_shapes(self):
        """Test creating slide XML from shapes."""
        # Create mock shape elements
        shape1 = ET.Element(f"{{{NS['p']}}}sp")
        shape2 = ET.Element(f"{{{NS['p']}}}sp")
        shapes = [shape1, shape2]
        
        result = slide_xml_from_shapes(shapes)
        
        # Parse the result
        root = ET.fromstring(result)
        assert root.tag.endswith("}sld")
        
        # Should contain both shapes
        spTree = root.find(f".//{{{NS['p']}}}spTree")
        shapes_found = spTree.findall(f"{{{NS['p']}}}sp")
        assert len(shapes_found) == 2
    
    def test_update_presentation_size(self):
        """Test updating presentation size."""
        presentation_xml = f"""<?xml version="1.0"?>
        <p:presentation xmlns:p="{NS['p']}">
            <p:sldSz cx="9144000" cy="6858000"/>
        </p:presentation>"""
        
        result = update_presentation_size(presentation_xml, 12345, 67890)
        
        # Parse and check
        root = ET.fromstring(result)
        sldSz = root.find(f".//{{{NS['p']}}}sldSz")
        assert sldSz.get("cx") == "12345"
        assert sldSz.get("cy") == "67890"
    
    def test_update_presentation_size_no_sldSz(self):
        """Test updating presentation size when sldSz element missing."""
        presentation_xml = f"""<?xml version="1.0"?>
        <p:presentation xmlns:p="{NS['p']}">
        </p:presentation>"""
        
        # Should not crash, just return unchanged
        result = update_presentation_size(presentation_xml, 12345, 67890)
        assert "12345" not in result

class TestConvertFunction:
    """Test the main convert function."""
    
    @patch('src.svg2pptx_json_v2.SVG')
    @patch('src.svg2pptx_json_v2.PptxJSON')
    @patch('builtins.open')
    def test_convert_basic(self, mock_open, mock_pptx_json_cls, mock_svg_cls):
        """Test basic conversion functionality."""
        # Mock SVG
        mock_svg = MagicMock()
        mock_svg.viewbox = MagicMock()
        mock_svg.viewbox.x = 0
        mock_svg.viewbox.y = 0
        mock_svg.viewbox.width = 100
        mock_svg.viewbox.height = 80
        mock_svg_cls.parse.return_value = mock_svg
        
        # Mock shape element
        mock_element = MagicMock()
        mock_element.__class__.__name__ = "Shape"
        mock_element.values = {}
        mock_svg.elements.return_value = [mock_element]
        
        # Mock PptxJSON
        mock_pj = MagicMock()
        mock_pj._index = {"ppt/slides/slide1.xml": 0, "ppt/presentation.xml": 1}
        mock_pj.get_text.return_value = "<presentation/>"
        mock_pj.to_pptx_bytes.return_value = b"pptx_content"
        mock_pptx_json_cls.from_minimalpptx_txt.return_value = mock_pj
        
        # Mock file write
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch('src.svg2pptx_json_v2.to_lines') as mock_to_lines:
            mock_to_lines.return_value = [(complex(0, 0), complex(10, 10))]
            
            with patch('src.svg2pptx_json_v2.isinstance') as mock_isinstance:
                mock_isinstance.side_effect = lambda obj, cls: hasattr(obj, '__class__') and obj.__class__.__name__ == "Shape"
                
                convert("test.svg", "minimal.txt", "output.pptx")
        
        # Verify calls
        mock_svg_cls.parse.assert_called_once_with("test.svg")
        mock_pptx_json_cls.from_minimalpptx_txt.assert_called_once_with("minimal.txt")
        mock_pj.upsert_text.assert_called()
        mock_file.write.assert_called_once_with(b"pptx_content")
    
    @patch('src.svg2pptx_json_v2.SVG')
    @patch('src.svg2pptx_json_v2.PptxJSON')
    @patch('builtins.open')
    def test_convert_no_viewbox(self, mock_open, mock_pptx_json_cls, mock_svg_cls):
        """Test conversion with SVG that has no viewbox."""
        # Mock SVG without viewbox
        mock_svg = MagicMock()
        mock_svg.viewbox = None
        mock_svg.width = 200
        mock_svg.height = 150
        mock_svg_cls.parse.return_value = mock_svg
        mock_svg.elements.return_value = []
        
        # Mock PptxJSON
        mock_pj = MagicMock()
        mock_pj._index = {"ppt/slides/slide1.xml": 0}
        mock_pj.to_pptx_bytes.return_value = b"pptx_content"
        mock_pptx_json_cls.from_minimalpptx_txt.return_value = mock_pj
        
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        convert("test.svg", "minimal.txt", "output.pptx")
        
        # Should handle dimensions from width/height
        mock_pj.upsert_text.assert_called()
    
    @patch('src.svg2pptx_json_v2.SVG')
    @patch('src.svg2pptx_json_v2.PptxJSON')
    def test_convert_no_slide1_xml(self, mock_pptx_json_cls, mock_svg_cls):
        """Test conversion when slide1.xml doesn't exist."""
        # Mock SVG
        mock_svg = MagicMock()
        mock_svg.viewbox = None
        mock_svg.width = 200
        mock_svg.height = 150
        mock_svg_cls.parse.return_value = mock_svg
        mock_svg.elements.return_value = []
        
        # Mock PptxJSON without slide1.xml but with slide2.xml
        mock_pj = MagicMock()
        mock_pj._index = {"ppt/slides/slide2.xml": 0}
        mock_pj.entries = [{"path": "ppt/slides/slide2.xml", "text": "content"}]
        mock_pj.to_pptx_bytes.return_value = b"pptx_content"
        mock_pptx_json_cls.from_minimalpptx_txt.return_value = mock_pj
        
        with patch('builtins.open') as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            convert("test.svg", "minimal.txt", "output.pptx")
        
        # Should use slide2.xml instead
        mock_pj.upsert_text.assert_called()
        calls = mock_pj.upsert_text.call_args_list
        assert any("ppt/slides/slide2.xml" in str(call) for call in calls)
    
    @patch('src.svg2pptx_json_v2.SVG')
    @patch('src.svg2pptx_json_v2.PptxJSON')
    def test_convert_no_slides_found(self, mock_pptx_json_cls, mock_svg_cls):
        """Test conversion when no slide XML is found."""
        # Mock SVG
        mock_svg = MagicMock()
        mock_svg.viewbox = None
        mock_svg_cls.parse.return_value = mock_svg
        
        # Mock PptxJSON without any slide XML files
        mock_pj = MagicMock()
        mock_pj._index = {"other.xml": 0}
        mock_pj.entries = [{"path": "other.xml", "text": "content"}]
        mock_pptx_json_cls.from_minimalpptx_txt.return_value = mock_pj
        
        with pytest.raises(FileNotFoundError, match="No slide XML found"):
            convert("test.svg", "minimal.txt", "output.pptx")

class TestConstants:
    """Test module constants."""
    
    def test_emu_per_px_constant(self):
        """Test EMU_PER_PX constant value."""
        assert EMU_PER_PX == 9525
    
    def test_namespaces(self):
        """Test namespace constants."""
        assert 'p' in NS
        assert 'a' in NS
        assert 'r' in NS
        assert 'pr' in NS
        
        assert NS['p'] == "http://schemas.openxmlformats.org/presentationml/2006/main"
        assert NS['a'] == "http://schemas.openxmlformats.org/drawingml/2006/main"

if __name__ == "__main__":
    pytest.main([__file__])