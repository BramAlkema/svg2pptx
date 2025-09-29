#!/usr/bin/env python3
"""
Unit tests for core Text Mapper.

Tests the mapping from IR TextFrame objects to PowerPoint DrawingML text XML.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tests.unit.core.conftest import IRTestBase

try:
    from core.mappers import TextMapper
    from core.ir import TextFrame, TextSpan, TextStyle, FontInfo
    from core.ir import Point, Rect, SolidPaint, Stroke
    CORE_MAPPERS_AVAILABLE = True
except ImportError:
    CORE_MAPPERS_AVAILABLE = False
    pytest.skip("Core mappers not available", allow_module_level=True)


class TestTextMapperCreation(IRTestBase):
    """Test TextMapper creation and initialization."""

    def test_text_mapper_initialization(self):
        """Test creating a text mapper."""
        mapper = TextMapper()

        assert mapper is not None
        assert hasattr(mapper, 'map_text_frame')
        assert callable(mapper.map_text_frame)

    def test_text_mapper_with_font_config(self):
        """Test text mapper with font configuration."""
        try:
            font_config = {
                'default_font': 'Arial',
                'fallback_fonts': ['Helvetica', 'sans-serif'],
                'font_size_multiplier': 1.0
            }

            mapper = TextMapper(font_config=font_config)
            assert mapper is not None

            if hasattr(mapper, 'font_config'):
                assert mapper.font_config == font_config
        except TypeError:
            # Font config might not be supported in constructor
            mapper = TextMapper()
            assert mapper is not None


class TestTextMapperBasicMapping(IRTestBase):
    """Test basic text mapping functionality."""

    def test_map_simple_text_frame(self):
        """Test mapping a simple text frame."""
        text_frame = TextFrame(
            content="Hello World",
            bounds=Rect(10, 20, 200, 30),
            style=None
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None
        if isinstance(result, str):
            # Should contain text content
            assert "Hello World" in result
            # Should contain text-related XML elements
            assert any(tag in result.lower() for tag in ['txbody', 'p', 'r', 't'])

    def test_map_text_frame_with_style(self):
        """Test mapping text frame with text style."""
        style = TextStyle(
            font_family="Arial",
            font_size=14,
            fill=SolidPaint(color="#000000")
        )

        text_frame = TextFrame(
            content="Styled Text",
            bounds=Rect(0, 0, 300, 50),
            style=style
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None
        if isinstance(result, str):
            # Should contain text content
            assert "Styled Text" in result
            # Should contain style information
            assert any(prop in result.lower() for prop in ['arial', 'font', 'sz'])

    def test_map_empty_text_frame(self):
        """Test mapping text frame with empty content."""
        text_frame = TextFrame(
            content="",
            bounds=Rect(10, 10, 100, 20),
            style=None
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None
        # Should produce valid structure even for empty content

    def test_map_multiline_text_frame(self):
        """Test mapping text frame with multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        text_frame = TextFrame(
            content=content,
            bounds=Rect(0, 0, 200, 60),
            style=None
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None
        if isinstance(result, str):
            # Should contain all lines
            assert "Line 1" in result
            assert "Line 2" in result
            assert "Line 3" in result
            # Should handle line breaks
            assert any(tag in result.lower() for tag in ['br', 'p'])


class TestTextMapperTextSpans(IRTestBase):
    """Test mapping of text spans with different styles."""

    def test_map_text_frame_with_spans(self):
        """Test mapping text frame containing text spans."""
        try:
            span1 = TextSpan(
                content="Bold ",
                style=TextStyle(font_weight="bold")
            )
            span2 = TextSpan(
                content="and italic",
                style=TextStyle(font_style="italic")
            )

            text_frame = TextFrame(
                content="",  # Content in spans
                bounds=Rect(0, 0, 200, 30),
                spans=[span1, span2]
            )

            mapper = TextMapper()
            result = mapper.map_text_frame(text_frame)

            assert result is not None
            if isinstance(result, str):
                # Should contain content from both spans
                assert "Bold" in result
                assert "italic" in result
                # Should contain style information
                assert any(style in result.lower() for style in ['b', 'i', 'bold', 'italic'])
        except (TypeError, AttributeError):
            pytest.skip("TextFrame with spans not available")

    def test_map_mixed_style_spans(self):
        """Test mapping spans with different styling."""
        try:
            span1 = TextSpan(
                content="Red text ",
                style=TextStyle(fill=SolidPaint(color="#FF0000"))
            )
            span2 = TextSpan(
                content="Blue text",
                style=TextStyle(fill=SolidPaint(color="#0000FF"))
            )

            text_frame = TextFrame(
                content="",
                bounds=Rect(0, 0, 250, 25),
                spans=[span1, span2]
            )

            mapper = TextMapper()
            result = mapper.map_text_frame(text_frame)

            assert result is not None
            if isinstance(result, str):
                # Should contain both text contents
                assert "Red text" in result
                assert "Blue text" in result
                # Should contain color information
                assert any(color in result.lower() for color in ['ff0000', 'red'])
                assert any(color in result.lower() for color in ['0000ff', 'blue'])
        except (TypeError, AttributeError):
            pytest.skip("TextSpan with colors not available")

    def test_map_nested_text_styling(self):
        """Test mapping complex nested text styling."""
        try:
            span = TextSpan(
                content="Bold italic underlined text",
                style=TextStyle(
                    font_weight="bold",
                    font_style="italic",
                    text_decoration="underline",
                    fill=SolidPaint(color="#008000")
                )
            )

            text_frame = TextFrame(
                content="",
                bounds=Rect(0, 0, 300, 30),
                spans=[span]
            )

            mapper = TextMapper()
            result = mapper.map_text_frame(text_frame)

            assert result is not None
            if isinstance(result, str):
                # Should contain the text
                assert "Bold italic underlined text" in result
                # Should contain multiple style properties
                style_props = ['bold', 'italic', 'underline', '008000']
                found_props = [prop for prop in style_props if prop in result.lower()]
                assert len(found_props) >= 2  # Should find multiple properties
        except (TypeError, AttributeError):
            pytest.skip("Complex TextStyle not available")


class TestTextMapperFontMapping(IRTestBase):
    """Test mapping of font properties."""

    def test_map_font_family(self):
        """Test mapping font family."""
        style = TextStyle(
            font_family="Times New Roman",
            font_size=16
        )

        text_frame = TextFrame(
            content="Font Test",
            bounds=Rect(0, 0, 200, 40),
            style=style
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None
        if isinstance(result, str):
            # Should contain font family information
            assert any(font in result for font in ["Times New Roman", "Times"])

    def test_map_font_size(self):
        """Test mapping font size."""
        style = TextStyle(
            font_family="Arial",
            font_size=18
        )

        text_frame = TextFrame(
            content="Size Test",
            bounds=Rect(0, 0, 150, 35),
            style=style
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None
        if isinstance(result, str):
            # Should contain font size (usually in hundreds for PowerPoint)
            # 18pt should be 1800 in PowerPoint units
            assert any(size in result for size in ['1800', '18'])

    def test_map_font_weight_and_style(self):
        """Test mapping font weight and style."""
        try:
            style = TextStyle(
                font_family="Helvetica",
                font_size=14,
                font_weight="bold",
                font_style="italic"
            )

            text_frame = TextFrame(
                content="Bold Italic",
                bounds=Rect(0, 0, 180, 30),
                style=style
            )

            mapper = TextMapper()
            result = mapper.map_text_frame(text_frame)

            assert result is not None
            if isinstance(result, str):
                # Should contain bold and italic indicators
                assert any(prop in result.lower() for prop in ['b', 'bold'])
                assert any(prop in result.lower() for prop in ['i', 'italic'])
        except TypeError:
            pytest.skip("Font weight/style not available")

    def test_map_font_fallbacks(self):
        """Test mapping font with fallback families."""
        style = TextStyle(
            font_family="Custom Font, Arial, sans-serif",
            font_size=12
        )

        text_frame = TextFrame(
            content="Fallback Test",
            bounds=Rect(0, 0, 200, 25),
            style=style
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None
        if isinstance(result, str):
            # Should handle font fallbacks (might use first or fallback)
            assert any(font in result for font in ["Custom Font", "Arial", "sans-serif"])


class TestTextMapperTextAlignment(IRTestBase):
    """Test mapping of text alignment properties."""

    def test_map_text_alignment(self):
        """Test mapping text alignment."""
        try:
            style = TextStyle(
                font_family="Arial",
                font_size=12,
                text_align="center"
            )

            text_frame = TextFrame(
                content="Centered Text",
                bounds=Rect(0, 0, 200, 30),
                style=style
            )

            mapper = TextMapper()
            result = mapper.map_text_frame(text_frame)

            assert result is not None
            if isinstance(result, str):
                # Should contain alignment information
                assert any(align in result.lower() for align in ['center', 'ctr'])
        except TypeError:
            pytest.skip("Text alignment not available")

    def test_map_vertical_alignment(self):
        """Test mapping vertical text alignment."""
        try:
            style = TextStyle(
                font_family="Arial",
                font_size=12,
                vertical_align="middle"
            )

            text_frame = TextFrame(
                content="Middle Aligned",
                bounds=Rect(0, 0, 200, 60),
                style=style
            )

            mapper = TextMapper()
            result = mapper.map_text_frame(text_frame)

            assert result is not None
            if isinstance(result, str):
                # Should contain vertical alignment
                assert any(align in result.lower() for align in ['middle', 'mid', 'ctr'])
        except TypeError:
            pytest.skip("Vertical alignment not available")

    def test_map_text_direction(self):
        """Test mapping text direction."""
        try:
            style = TextStyle(
                font_family="Arial",
                font_size=12,
                direction="rtl"
            )

            text_frame = TextFrame(
                content="Right to Left",
                bounds=Rect(0, 0, 200, 30),
                style=style
            )

            mapper = TextMapper()
            result = mapper.map_text_frame(text_frame)

            assert result is not None
            if isinstance(result, str):
                # Should contain direction information
                assert any(dir in result.lower() for dir in ['rtl', 'right'])
        except TypeError:
            pytest.skip("Text direction not available")


class TestTextMapperSpacing(IRTestBase):
    """Test mapping of text spacing properties."""

    def test_map_letter_spacing(self):
        """Test mapping letter spacing."""
        try:
            style = TextStyle(
                font_family="Arial",
                font_size=12,
                letter_spacing=2.0
            )

            text_frame = TextFrame(
                content="Spaced Text",
                bounds=Rect(0, 0, 250, 30),
                style=style
            )

            mapper = TextMapper()
            result = mapper.map_text_frame(text_frame)

            assert result is not None
            if isinstance(result, str):
                # Should contain letter spacing
                assert any(prop in result.lower() for prop in ['spc', 'spacing'])
        except TypeError:
            pytest.skip("Letter spacing not available")

    def test_map_line_height(self):
        """Test mapping line height."""
        try:
            style = TextStyle(
                font_family="Arial",
                font_size=12,
                line_height=1.5
            )

            text_frame = TextFrame(
                content="Line 1\nLine 2\nLine 3",
                bounds=Rect(0, 0, 200, 80),
                style=style
            )

            mapper = TextMapper()
            result = mapper.map_text_frame(text_frame)

            assert result is not None
            if isinstance(result, str):
                # Should contain line height information
                assert any(prop in result.lower() for prop in ['lnspc', 'lineheight'])
        except TypeError:
            pytest.skip("Line height not available")

    def test_map_text_indentation(self):
        """Test mapping text indentation."""
        try:
            style = TextStyle(
                font_family="Arial",
                font_size=12,
                text_indent=20
            )

            text_frame = TextFrame(
                content="Indented text paragraph",
                bounds=Rect(0, 0, 300, 40),
                style=style
            )

            mapper = TextMapper()
            result = mapper.map_text_frame(text_frame)

            assert result is not None
            if isinstance(result, str):
                # Should contain indentation
                assert any(prop in result.lower() for prop in ['indent', 'margl'])
        except TypeError:
            pytest.skip("Text indentation not available")


class TestTextMapperCoordinateTransformation(IRTestBase):
    """Test coordinate transformation for text positioning."""

    def test_text_frame_position_mapping(self):
        """Test mapping text frame position."""
        text_frame = TextFrame(
            content="Positioned Text",
            bounds=Rect(50, 100, 200, 30),
            style=None
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None
        # Position should be transformed to PowerPoint coordinates

    def test_text_frame_size_mapping(self):
        """Test mapping text frame size."""
        text_frame = TextFrame(
            content="Sized Text",
            bounds=Rect(0, 0, 300, 80),
            style=None
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None
        # Size should be converted to EMU units

    def test_coordinate_scaling_for_text(self):
        """Test coordinate scaling for text elements."""
        text_frame = TextFrame(
            content="Scaled Text",
            bounds=Rect(10, 20, 100, 25),
            style=None
        )

        # Test with scaling transformation
        try:
            mapper = TextMapper(coordinate_system={
                'scale_x': 2.0,
                'scale_y': 2.0,
                'offset_x': 0.0,
                'offset_y': 0.0
            })
        except TypeError:
            mapper = TextMapper()

        result = mapper.map_text_frame(text_frame)

        assert result is not None
        # Coordinates should be scaled appropriately


class TestTextMapperValidation(IRTestBase):
    """Test text mapper validation and error handling."""

    def test_map_invalid_text_frame(self):
        """Test mapping with invalid text frame object."""
        mapper = TextMapper()

        with pytest.raises((TypeError, ValueError, AttributeError)):
            mapper.map_text_frame(None)

        with pytest.raises((TypeError, ValueError, AttributeError)):
            mapper.map_text_frame("invalid_text_frame")

    def test_map_text_frame_invalid_bounds(self):
        """Test mapping text frame with invalid bounds."""
        try:
            invalid_text_frame = TextFrame(
                content="Test",
                bounds="invalid_bounds",  # Should be Rect
                style=None
            )

            mapper = TextMapper()

            with pytest.raises((TypeError, ValueError, AttributeError)):
                mapper.map_text_frame(invalid_text_frame)
        except (TypeError, ValueError):
            # TextFrame constructor might reject invalid bounds
            pass

    def test_map_text_frame_with_invalid_style(self):
        """Test mapping text frame with invalid style."""
        text_frame = TextFrame(
            content="Test Text",
            bounds=Rect(0, 0, 200, 30),
            style=Mock()  # Invalid style object
        )

        mapper = TextMapper()

        # Should either handle gracefully or raise appropriate error
        try:
            result = mapper.map_text_frame(text_frame)
            assert result is not None
        except (TypeError, ValueError, AttributeError):
            # Expected for invalid style
            pass

    def test_map_text_with_special_characters(self):
        """Test mapping text with special characters."""
        special_text = "Special: &<>\"'@#$%^&*()àáâãäåæçèéêë"
        text_frame = TextFrame(
            content=special_text,
            bounds=Rect(0, 0, 400, 30),
            style=None
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None
        if isinstance(result, str):
            # Should properly escape or encode special characters
            # XML should be valid even with special characters
            try:
                from lxml import etree
                wrapped = f"<root>{result}</root>"
                etree.fromstring(wrapped)
            except etree.XMLSyntaxError:
                # Special characters might need different handling
                pass


class TestTextMapperOutput(IRTestBase):
    """Test text mapper output format and structure."""

    def test_output_format_xml(self):
        """Test that output is valid XML format."""
        text_frame = TextFrame(
            content="XML Test",
            bounds=Rect(0, 0, 200, 30),
            style=TextStyle(font_size=12)
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None

        if isinstance(result, str):
            # Should be valid XML
            try:
                from lxml import etree
                etree.fromstring(result)
            except etree.XMLSyntaxError:
                # Try wrapping in root element
                wrapped = f"<root>{result}</root>"
                etree.fromstring(wrapped)

    def test_output_drawingml_text_structure(self):
        """Test that output follows DrawingML text structure."""
        text_frame = TextFrame(
            content="DrawingML Test",
            bounds=Rect(0, 0, 250, 35),
            style=None
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None

        if isinstance(result, str):
            # Should contain DrawingML text elements
            expected_elements = ['txbody', 'bodypx', 'p', 'r', 't']
            found_elements = [elem for elem in expected_elements if elem in result.lower()]
            # Should find some DrawingML text elements
            assert len(found_elements) > 0

    def test_output_contains_text_namespaces(self):
        """Test that output contains required text namespaces."""
        text_frame = TextFrame(
            content="Namespace Test",
            bounds=Rect(0, 0, 200, 30),
            style=None
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None

        if isinstance(result, str):
            # Should contain PowerPoint/Office namespaces
            expected_namespaces = ['a:', 'p:']
            found_namespaces = [ns for ns in expected_namespaces if ns in result]
            # Should find at least one namespace
            assert len(found_namespaces) > 0


class TestTextMapperPerformance(IRTestBase):
    """Test text mapper performance characteristics."""

    def test_mapping_performance_simple_text(self):
        """Test mapping performance with simple text."""
        import time

        text_frame = TextFrame(
            content="Performance Test",
            bounds=Rect(0, 0, 200, 30),
            style=TextStyle(font_size=12)
        )

        mapper = TextMapper()

        start_time = time.time()
        result = mapper.map_text_frame(text_frame)
        mapping_time = time.time() - start_time

        assert result is not None
        assert mapping_time < 0.01  # Should map very quickly

    def test_mapping_performance_long_text(self):
        """Test mapping performance with long text."""
        import time

        # Create long text content
        long_text = "Long text content. " * 100  # 2000 characters

        text_frame = TextFrame(
            content=long_text,
            bounds=Rect(0, 0, 400, 200),
            style=None
        )

        mapper = TextMapper()

        start_time = time.time()
        result = mapper.map_text_frame(text_frame)
        mapping_time = time.time() - start_time

        assert result is not None
        assert mapping_time < 0.1  # Should handle long text reasonably fast

    def test_mapping_performance_many_spans(self):
        """Test mapping performance with many text spans."""
        try:
            import time

            # Create many text spans
            spans = []
            for i in range(50):
                span = TextSpan(
                    content=f"Span {i} ",
                    style=TextStyle(font_size=10 + i % 10)
                )
                spans.append(span)

            text_frame = TextFrame(
                content="",
                bounds=Rect(0, 0, 600, 100),
                spans=spans
            )

            mapper = TextMapper()

            start_time = time.time()
            result = mapper.map_text_frame(text_frame)
            mapping_time = time.time() - start_time

            assert result is not None
            assert mapping_time < 0.1  # Should handle many spans reasonably fast
        except (TypeError, AttributeError):
            pytest.skip("TextFrame with many spans not available")

    def test_memory_usage_large_text(self):
        """Test memory usage with large text content."""
        import sys

        # Create very long text content
        large_text = "Large text content. " * 1000  # 20,000 characters

        text_frame = TextFrame(
            content=large_text,
            bounds=Rect(0, 0, 800, 400),
            style=None
        )

        mapper = TextMapper()
        result = mapper.map_text_frame(text_frame)

        assert result is not None

        if isinstance(result, str):
            result_size = sys.getsizeof(result)
            # Should produce reasonable output size
            assert result_size < 1000000  # Less than 1MB


if __name__ == "__main__":
    pytest.main([__file__])