#!/usr/bin/env python3
"""
Tests for WordArt Transform Builder

Validates DrawingML transform generation from SVG transforms.
"""

import pytest
import numpy as np
from lxml import etree as ET

from src.converters.wordart_builder import (
    WordArtTransformBuilder, WordArtShapeConfig, create_wordart_builder
)
from src.utils.ooxml_transform_utils import OOXMLTransformUtils, OOXMLTransform


class TestOOXMLTransformUtils:
    """Test OOXML transform utilities."""

    def setup_method(self):
        """Set up test utilities."""
        self.utils = OOXMLTransformUtils()

    def test_degrees_to_angle_units(self):
        """Test degree to angle unit conversion."""
        # Test common angles
        assert self.utils.degrees_to_angle_units(0) == 0
        assert self.utils.degrees_to_angle_units(90) == 90 * 60000
        assert self.utils.degrees_to_angle_units(180) == 180 * 60000
        assert self.utils.degrees_to_angle_units(360) == 360 * 60000

        # Test fractional angles
        assert self.utils.degrees_to_angle_units(45.5) == 45.5 * 60000

    def test_angle_units_to_degrees(self):
        """Test angle unit to degree conversion."""
        # Test round-trip conversion
        original_degrees = 37.5
        angle_units = self.utils.degrees_to_angle_units(original_degrees)
        converted_back = self.utils.angle_units_to_degrees(angle_units)
        assert abs(converted_back - original_degrees) < 0.001

    def test_pixels_to_emu(self):
        """Test pixel to EMU conversion."""
        # Standard web DPI: 96 pixels per inch, 914400 EMU per inch
        # So 1 pixel = 914400 / 96 = 9525 EMU
        assert self.utils.pixels_to_emu(1) == 9525
        assert self.utils.pixels_to_emu(96) == 914400  # 1 inch
        assert self.utils.pixels_to_emu(10) == 95250

    def test_points_to_emu(self):
        """Test point to EMU conversion."""
        # 1 point = 1/72 inch = 12700 EMU
        assert self.utils.points_to_emu(1) == 12700
        assert self.utils.points_to_emu(72) == 914400  # 1 inch

    def test_create_ooxml_transform_pixels(self):
        """Test OOXML transform creation from pixels."""
        transform = self.utils.create_ooxml_transform(
            translate_x=10.0,
            translate_y=20.0,
            width=100.0,
            height=50.0,
            rotation_deg=45.0,
            flip_h=True,
            input_unit="px"
        )

        assert transform.x == 10 * 9525  # 10 pixels to EMU
        assert transform.y == 20 * 9525  # 20 pixels to EMU
        assert transform.width == 100 * 9525
        assert transform.height == 50 * 9525
        assert transform.rotation == 45 * 60000
        assert transform.flip_h is True
        assert transform.flip_v is False

    def test_create_ooxml_transform_points(self):
        """Test OOXML transform creation from points."""
        transform = self.utils.create_ooxml_transform(
            translate_x=10.0,
            translate_y=20.0,
            width=72.0,  # 1 inch
            height=36.0,  # 0.5 inch
            rotation_deg=90.0,
            input_unit="pt"
        )

        assert transform.x == 10 * 12700
        assert transform.y == 20 * 12700
        assert transform.width == 72 * 12700  # 1 inch in EMU
        assert transform.height == 36 * 12700
        assert transform.rotation == 90 * 60000

    def test_generate_xfrm_xml(self):
        """Test XML generation for transforms."""
        transform = OOXMLTransform(
            x=95250,  # 10 pixels
            y=190500,  # 20 pixels
            width=952500,  # 100 pixels
            height=476250,  # 50 pixels
            rotation=2700000,  # 45 degrees
            flip_h=True,
            flip_v=False
        )

        xml = self.utils.generate_xfrm_xml(transform)

        # Define namespace for testing
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Check root element
        assert xml.tag == f"{a_ns}xfrm"
        assert xml.get("flipH") == "1"
        assert xml.get("flipV") is None  # Not set for False
        assert xml.get("rot") == "2700000"

        # Check offset
        off = xml.find(f"{a_ns}off")
        assert off is not None
        assert off.get("x") == "95250"
        assert off.get("y") == "190500"

        # Check extent
        ext = xml.find(f"{a_ns}ext")
        assert ext is not None
        assert ext.get("cx") == "952500"
        assert ext.get("cy") == "476250"

    def test_validate_transform_limits(self):
        """Test transform validation."""
        # Valid transform
        valid_transform = OOXMLTransform(
            x=100000, y=200000, width=300000, height=400000, rotation=1800000
        )
        result = self.utils.validate_transform_limits(valid_transform)
        assert result['valid'] is True
        assert len(result['errors']) == 0

        # Invalid transform (negative dimensions)
        invalid_transform = OOXMLTransform(
            x=100000, y=200000, width=-300000, height=400000
        )
        result = self.utils.validate_transform_limits(invalid_transform)
        assert result['valid'] is False
        assert len(result['errors']) > 0

        # Transform with warnings (very large)
        large_transform = OOXMLTransform(
            x=100000, y=200000,
            width=200 * 914400,  # 200 inches (very large)
            height=400000
        )
        result = self.utils.validate_transform_limits(large_transform)
        assert result['valid'] is True
        assert len(result['warnings']) > 0

    def test_optimize_transform(self):
        """Test transform optimization."""
        # Transform with rotation close to 90 degrees
        transform = OOXMLTransform(
            x=100000, y=200000, width=300000, height=400000,
            rotation=89 * 60000 + 30000  # 89.5 degrees (close to 90)
        )

        optimized = self.utils.optimize_transform(transform)

        # Should snap to exact 90 degrees
        assert optimized.rotation == 90 * 60000

        # Other properties should be unchanged
        assert optimized.x == transform.x
        assert optimized.y == transform.y
        assert optimized.width == transform.width
        assert optimized.height == transform.height


class TestWordArtTransformBuilder:
    """Test WordArt transform builder functionality."""

    def setup_method(self):
        """Set up test builder."""
        self.builder = WordArtTransformBuilder()

    def test_build_basic_wordart_shape(self):
        """Test building basic WordArt shape without transform."""
        config = WordArtShapeConfig(
            text="Hello World",
            font_family="Arial",
            font_size=24.0,
            width=200.0,
            height=50.0,
            x=10.0,
            y=20.0,
            fill_color="#FF0000"
        )

        shape = self.builder.build_wordart_shape(config)

        # Define namespaces
        p_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Check shape structure
        assert shape.tag == f"{p_ns}sp"

        # Check non-visual properties
        nvpr = shape.find(f"{p_ns}nvSpPr")
        assert nvpr is not None

        cnvpr = nvpr.find(f"{p_ns}cNvPr")
        assert cnvpr is not None
        assert cnvpr.get("name").startswith("WordArt")

        cnvsppr = nvpr.find(f"{p_ns}cNvSpPr")
        assert cnvsppr is not None
        assert cnvsppr.get("txBox") == "1"  # Marked as text shape

        # Check shape properties
        sppr = shape.find(f"{p_ns}spPr")
        assert sppr is not None

        # Check transform
        xfrm = sppr.find(f"{a_ns}xfrm")
        assert xfrm is not None

        off = xfrm.find(f"{a_ns}off")
        assert off is not None
        assert off.get("x") == str(10 * 9525)  # 10 pixels in EMU
        assert off.get("y") == str(20 * 9525)  # 20 pixels in EMU

        ext = xfrm.find(f"{a_ns}ext")
        assert ext is not None
        assert ext.get("cx") == str(200 * 9525)  # 200 pixels in EMU
        assert ext.get("cy") == str(50 * 9525)   # 50 pixels in EMU

        # Check fill color
        solidfill = sppr.find(f"{a_ns}solidFill")
        assert solidfill is not None
        srgbclr = solidfill.find(f"{a_ns}srgbClr")
        assert srgbclr is not None
        assert srgbclr.get("val") == "FF0000"

        # Check text body
        txbody = shape.find(f"{p_ns}txBody")
        assert txbody is not None

        p = txbody.find(f"{a_ns}p")
        assert p is not None

        r = p.find(f"{a_ns}r")
        assert r is not None

        t = r.find(f"{a_ns}t")
        assert t is not None
        assert t.text == "Hello World"

        # Check font properties
        rpr = r.find(f"{a_ns}rPr")
        assert rpr is not None
        assert rpr.get("sz") == "2400"  # 24 * 100

        latin = rpr.find(f"{a_ns}latin")
        assert latin is not None
        assert latin.get("typeface") == "Arial"

    def test_build_wordart_with_transform(self):
        """Test building WordArt shape with SVG transform."""
        config = WordArtShapeConfig(
            text="Rotated Text",
            width=150.0,
            height=40.0,
            x=0.0,
            y=0.0,
            transform="translate(50, 100) rotate(45) scale(1.5, 2.0)"
        )

        shape = self.builder.build_wordart_shape(config)

        # Define namespaces
        p_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Check that transform was applied
        sppr = shape.find(f"{p_ns}spPr")
        xfrm = sppr.find(f"{a_ns}xfrm")

        # Should have rotation
        assert xfrm.get("rot") is not None
        rotation = int(xfrm.get("rot"))
        # Allow larger tolerance for decomposed transforms as they may not be exactly 45°
        assert abs(rotation - 45 * 60000) < 600000  # Allow 10 degree tolerance

        # Check position includes translation
        off = xfrm.find(f"{a_ns}off")
        x_emu = int(off.get("x"))
        y_emu = int(off.get("y"))

        # Should include base position + translation
        assert x_emu > 50 * 9525 * 0.8  # Approximately 50 pixels translated
        assert y_emu > 100 * 9525 * 0.8  # Approximately 100 pixels translated

        # Check dimensions include scaling
        ext = xfrm.find(f"{a_ns}ext")
        width_emu = int(ext.get("cx"))
        height_emu = int(ext.get("cy"))

        # Should be scaled
        assert width_emu > 150 * 9525  # Scaled up from original width
        assert height_emu > 40 * 9525   # Scaled up from original height

    def test_build_wordart_with_flip(self):
        """Test building WordArt shape with flip transform."""
        config = WordArtShapeConfig(
            text="Flipped",
            width=100.0,
            height=30.0,
            transform="scale(-1, 1)"  # Horizontal flip
        )

        shape = self.builder.build_wordart_shape(config)

        # Define namespaces
        p_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        sppr = shape.find(f"{p_ns}spPr")
        xfrm = sppr.find(f"{a_ns}xfrm")

        # Should have flip attribute
        assert xfrm.get("flipH") == "1"
        assert xfrm.get("flipV") is None

    def test_build_wordart_with_complex_effects(self):
        """Test WordArt with complex transforms that trigger effects."""
        config = WordArtShapeConfig(
            text="Skewed Text",
            width=120.0,
            height=35.0,
            transform="skewX(25) scale(3, 1)"  # High skew and scale ratio
        )

        shape = self.builder.build_wordart_shape(config)

        # Define namespaces
        p_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Check that effects were added for complex transform
        txbody = shape.find(f"{p_ns}txBody")
        p = txbody.find(f"{a_ns}p")
        r = p.find(f"{a_ns}r")
        rpr = r.find(f"{a_ns}rPr")

        # Should have text outline for complex transforms
        ln = rpr.find(f"{a_ns}ln")
        assert ln is not None

    def test_validate_wordart_compatibility(self):
        """Test WordArt compatibility validation."""
        # Valid configuration
        valid_config = WordArtShapeConfig(
            text="Valid Text",
            width=100.0,
            height=50.0
        )

        result = self.builder.validate_wordart_compatibility(valid_config)
        assert result['compatible'] is True
        assert len(result['errors']) == 0

        # Invalid configuration (no text)
        invalid_config = WordArtShapeConfig(
            text="",
            width=100.0,
            height=50.0
        )

        result = self.builder.validate_wordart_compatibility(invalid_config)
        assert result['compatible'] is False
        assert len(result['errors']) > 0

        # Configuration with warnings (very large font)
        warning_config = WordArtShapeConfig(
            text="Large Font",
            font_size=2000.0,  # Very large
            width=100.0,
            height=50.0
        )

        result = self.builder.validate_wordart_compatibility(warning_config)
        assert result['compatible'] is True
        assert len(result['warnings']) > 0

    def test_matrix_transform_handling(self):
        """Test handling of matrix transforms."""
        # Create numpy matrix transform
        matrix = np.array([[1.5, 0.2, 30], [0.3, 2.0, 40]], dtype=float)

        config = WordArtShapeConfig(
            text="Matrix Transform",
            width=100.0,
            height=50.0,
            transform=matrix
        )

        shape = self.builder.build_wordart_shape(config)

        # Define namespaces
        p_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # Should successfully generate shape
        assert shape.tag == f"{p_ns}sp"

        # Should have transform applied
        sppr = shape.find(f"{p_ns}spPr")
        xfrm = sppr.find(f"{a_ns}xfrm")
        assert xfrm is not None

        # Should have position and dimensions
        off = xfrm.find(f"{a_ns}off")
        ext = xfrm.find(f"{a_ns}ext")
        assert off is not None
        assert ext is not None

    def test_stroke_properties(self):
        """Test stroke property generation."""
        config = WordArtShapeConfig(
            text="Stroked Text",
            width=100.0,
            height=50.0,
            stroke_color="#00FF00",
            stroke_width=2.0
        )

        shape = self.builder.build_wordart_shape(config)

        # Define namespaces
        p_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        sppr = shape.find(f"{p_ns}spPr")

        # Should have stroke
        ln = sppr.find(f"{a_ns}ln")
        assert ln is not None
        assert ln.get("w") == str(2 * 9525)  # 2 pixels in EMU

        solidfill = ln.find(f"{a_ns}solidFill")
        assert solidfill is not None
        srgbclr = solidfill.find(f"{a_ns}srgbClr")
        assert srgbclr is not None
        assert srgbclr.get("val") == "00FF00"

    def test_factory_function(self):
        """Test factory function."""
        builder = create_wordart_builder()
        assert isinstance(builder, WordArtTransformBuilder)


class TestXMLStructure:
    """Test XML structure and schema compliance."""

    def setup_method(self):
        """Set up test builder."""
        self.builder = WordArtTransformBuilder()

    def test_xml_namespace_declarations(self):
        """Test that generated XML has proper namespace structure."""
        config = WordArtShapeConfig(
            text="Namespace Test",
            width=100.0,
            height=50.0
        )

        shape = self.builder.build_wordart_shape(config)

        # Check that all elements use proper prefixes
        self._validate_element_namespaces(shape)

    def _validate_element_namespaces(self, element):
        """Recursively validate element namespace URIs."""
        p_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        a_ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

        # PowerPoint shape elements should have presentation namespace
        if element.tag.startswith(p_ns):
            valid_tags = [f"{p_ns}sp", f"{p_ns}nvSpPr", f"{p_ns}cNvPr",
                         f"{p_ns}cNvSpPr", f"{p_ns}nvPr", f"{p_ns}spPr", f"{p_ns}txBody"]
            assert element.tag in valid_tags

        # DrawingML elements should have drawingml namespace
        elif element.tag.startswith(a_ns):
            valid_tags = [
                f"{a_ns}xfrm", f"{a_ns}off", f"{a_ns}ext", f"{a_ns}prstGeom", f"{a_ns}avLst",
                f"{a_ns}solidFill", f"{a_ns}srgbClr", f"{a_ns}ln", f"{a_ns}bodyPr", f"{a_ns}lstStyle",
                f"{a_ns}p", f"{a_ns}r", f"{a_ns}rPr", f"{a_ns}latin", f"{a_ns}t", f"{a_ns}endParaRPr",
                f"{a_ns}effectLst", f"{a_ns}outerShdw", f"{a_ns}alpha"
            ]
            assert element.tag in valid_tags

        # Recursively check children
        for child in element:
            self._validate_element_namespaces(child)

    def test_xml_serialization(self):
        """Test that XML can be properly serialized."""
        config = WordArtShapeConfig(
            text="Serialization Test",
            width=100.0,
            height=50.0
        )

        shape = self.builder.build_wordart_shape(config)

        # Should be able to serialize to string
        xml_string = ET.tostring(shape, encoding='unicode')
        assert "Serialization Test" in xml_string
        # Check for namespace URIs in serialized XML
        assert "http://schemas.openxmlformats.org/presentationml/2006/main" in xml_string
        assert "http://schemas.openxmlformats.org/drawingml/2006/main" in xml_string

        # Should be able to parse back
        reparsed = ET.fromstring(xml_string)
        p_ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        assert reparsed.tag == f"{p_ns}sp"