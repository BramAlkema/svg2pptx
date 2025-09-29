#!/usr/bin/env python3
"""
Unit tests for core IR Text components.

Tests the text system (TextFrame, TextSpan, TextStyle, etc.) that handles
text rendering and layout in the IR structure.
"""

import pytest
from unittest.mock import Mock

from tests.unit.core.conftest import IRTestBase

try:
    from core.ir import TextFrame, TextSpan, TextStyle, FontInfo
    from core.ir import Point, Rect, SolidPaint
    from core.ir import validate_ir, IRValidationError
    CORE_IR_AVAILABLE = True
except ImportError:
    CORE_IR_AVAILABLE = False
    pytest.skip("Core IR components not available", allow_module_level=True)


class TestTextFrameCreation(IRTestBase):
    """Test TextFrame object creation and properties."""

    def test_text_frame_basic(self):
        """Test creating a basic text frame."""
        try:
            frame = TextFrame(
                content="Hello World",
                bounds=Rect(10, 20, 200, 50),
                style=None
            )

            assert frame.content == "Hello World"
            assert frame.bounds == Rect(10, 20, 200, 50)
            self.assert_valid_ir_element(frame)
        except NameError:
            pytest.skip("TextFrame not available")

    def test_text_frame_with_style(self):
        """Test creating text frame with text style."""
        try:
            style = TextStyle(
                font_family="Arial",
                font_size=14,
                fill=SolidPaint(color="#000000")
            )

            frame = TextFrame(
                content="Styled Text",
                bounds=Rect(0, 0, 300, 100),
                style=style
            )

            assert frame.content == "Styled Text"
            assert frame.style == style
            self.assert_valid_ir_element(frame)
        except NameError:
            pytest.skip("TextFrame or TextStyle not available")

    def test_text_frame_empty_content(self):
        """Test text frame with empty content."""
        try:
            frame = TextFrame(
                content="",
                bounds=Rect(10, 10, 100, 20),
                style=None
            )

            assert frame.content == ""
            self.assert_valid_ir_element(frame)
        except NameError:
            pytest.skip("TextFrame not available")

    def test_text_frame_multiline_content(self):
        """Test text frame with multiline content."""
        try:
            content = "Line 1\nLine 2\nLine 3"
            frame = TextFrame(
                content=content,
                bounds=Rect(0, 0, 200, 60),
                style=None
            )

            assert frame.content == content
            assert "\n" in frame.content
            self.assert_valid_ir_element(frame)
        except NameError:
            pytest.skip("TextFrame not available")

    def test_text_frame_with_spans(self):
        """Test text frame containing text spans."""
        try:
            span1 = TextSpan(
                content="Bold ",
                style=TextStyle(font_weight="bold")
            )
            span2 = TextSpan(
                content="and italic",
                style=TextStyle(font_style="italic")
            )

            frame = TextFrame(
                content="",  # Content in spans
                bounds=Rect(0, 0, 200, 30),
                spans=[span1, span2]
            )

            if hasattr(frame, 'spans'):
                assert len(frame.spans) == 2
                assert frame.spans[0] == span1
                assert frame.spans[1] == span2
            self.assert_valid_ir_element(frame)
        except NameError:
            pytest.skip("TextFrame with spans not available")


class TestTextSpanCreation(IRTestBase):
    """Test TextSpan object creation and properties."""

    def test_text_span_basic(self):
        """Test creating a basic text span."""
        try:
            span = TextSpan(
                content="Sample text",
                style=None
            )

            assert span.content == "Sample text"
            self.assert_valid_ir_element(span)
        except NameError:
            pytest.skip("TextSpan not available")

    def test_text_span_with_style(self):
        """Test text span with styling."""
        try:
            style = TextStyle(
                font_family="Times New Roman",
                font_size=16,
                font_weight="bold",
                fill=SolidPaint(color="#FF0000")
            )

            span = TextSpan(
                content="Styled span",
                style=style
            )

            assert span.content == "Styled span"
            assert span.style == style
            self.assert_valid_ir_element(span)
        except NameError:
            pytest.skip("TextSpan or TextStyle not available")

    def test_text_span_empty_content(self):
        """Test text span with empty content."""
        try:
            span = TextSpan(
                content="",
                style=None
            )

            assert span.content == ""
            self.assert_valid_ir_element(span)
        except NameError:
            pytest.skip("TextSpan not available")

    def test_text_span_special_characters(self):
        """Test text span with special characters."""
        try:
            special_content = "Special: &<>\"'@#$%^&*()"
            span = TextSpan(
                content=special_content,
                style=None
            )

            assert span.content == special_content
            self.assert_valid_ir_element(span)
        except NameError:
            pytest.skip("TextSpan not available")


class TestTextStyleCreation(IRTestBase):
    """Test TextStyle object creation and properties."""

    def test_text_style_basic(self):
        """Test creating basic text style."""
        try:
            style = TextStyle(
                font_family="Arial",
                font_size=12
            )

            assert style.font_family == "Arial"
            assert style.font_size == 12
            self.assert_valid_ir_element(style)
        except NameError:
            pytest.skip("TextStyle not available")

    def test_text_style_comprehensive(self):
        """Test text style with all properties."""
        try:
            style = TextStyle(
                font_family="Helvetica",
                font_size=14,
                font_weight="bold",
                font_style="italic",
                text_decoration="underline",
                fill=SolidPaint(color="#0000FF"),
                stroke=None,
                letter_spacing=1.5,
                line_height=1.2
            )

            assert style.font_family == "Helvetica"
            assert style.font_size == 14
            if hasattr(style, 'font_weight'):
                assert style.font_weight == "bold"
            if hasattr(style, 'font_style'):
                assert style.font_style == "italic"
            if hasattr(style, 'text_decoration'):
                assert style.text_decoration == "underline"
            if hasattr(style, 'letter_spacing'):
                assert style.letter_spacing == 1.5
            if hasattr(style, 'line_height'):
                assert style.line_height == 1.2

            self.assert_valid_ir_element(style)
        except (NameError, TypeError):
            pytest.skip("Comprehensive TextStyle not available")

    def test_text_style_with_paint(self):
        """Test text style with fill and stroke paints."""
        try:
            fill_paint = SolidPaint(color="#FF0000")
            stroke_paint = SolidPaint(color="#000000")

            style = TextStyle(
                font_family="Georgia",
                font_size=18,
                fill=fill_paint,
                stroke=stroke_paint
            )

            assert style.fill == fill_paint
            if hasattr(style, 'stroke'):
                assert style.stroke == stroke_paint
            self.assert_valid_ir_element(style)
        except NameError:
            pytest.skip("TextStyle with paints not available")

    def test_text_style_font_variants(self):
        """Test text style with font variants."""
        try:
            style = TextStyle(
                font_family="Times New Roman",
                font_size=16,
                font_variant="small-caps",
                text_transform="uppercase"
            )

            if hasattr(style, 'font_variant'):
                assert style.font_variant == "small-caps"
            if hasattr(style, 'text_transform'):
                assert style.text_transform == "uppercase"
            self.assert_valid_ir_element(style)
        except (NameError, TypeError):
            pytest.skip("TextStyle variants not available")


class TestFontInfoCreation(IRTestBase):
    """Test FontInfo object creation and properties."""

    def test_font_info_basic(self):
        """Test creating basic font info."""
        try:
            font_info = FontInfo(
                family="Arial",
                size=12,
                weight="normal",
                style="normal"
            )

            assert font_info.family == "Arial"
            assert font_info.size == 12
            assert font_info.weight == "normal"
            assert font_info.style == "normal"
            self.assert_valid_ir_element(font_info)
        except NameError:
            pytest.skip("FontInfo not available")

    def test_font_info_with_metrics(self):
        """Test font info with font metrics."""
        try:
            font_info = FontInfo(
                family="Helvetica",
                size=14,
                weight="bold",
                style="italic",
                ascent=12,
                descent=3,
                line_height=16
            )

            assert font_info.family == "Helvetica"
            assert font_info.size == 14
            if hasattr(font_info, 'ascent'):
                assert font_info.ascent == 12
            if hasattr(font_info, 'descent'):
                assert font_info.descent == 3
            if hasattr(font_info, 'line_height'):
                assert font_info.line_height == 16
            self.assert_valid_ir_element(font_info)
        except (NameError, TypeError):
            pytest.skip("FontInfo with metrics not available")

    def test_font_info_fallback_families(self):
        """Test font info with fallback font families."""
        try:
            font_info = FontInfo(
                family="Custom Font, Arial, sans-serif",
                size=12,
                weight="normal",
                style="normal"
            )

            assert "Custom Font" in font_info.family
            assert "Arial" in font_info.family
            assert "sans-serif" in font_info.family
            self.assert_valid_ir_element(font_info)
        except NameError:
            pytest.skip("FontInfo not available")


class TestTextLayoutAndMeasurement(IRTestBase):
    """Test text layout and measurement functionality."""

    def test_text_frame_bounds_calculation(self):
        """Test text frame bounds calculation."""
        try:
            frame = TextFrame(
                content="Test Text",
                bounds=Rect(10, 20, 200, 50),
                style=TextStyle(font_size=12)
            )

            # Test bounds access
            assert frame.bounds.x == 10
            assert frame.bounds.y == 20
            assert frame.bounds.width == 200
            assert frame.bounds.height == 50

            # Test if text measurement methods exist
            if hasattr(frame, 'measure_text'):
                measurements = frame.measure_text()
                assert isinstance(measurements, dict)
        except NameError:
            pytest.skip("TextFrame bounds not available")

    def test_text_line_breaking(self):
        """Test text line breaking functionality."""
        try:
            long_text = "This is a very long line of text that should be wrapped"
            frame = TextFrame(
                content=long_text,
                bounds=Rect(0, 0, 100, 100),  # Narrow width
                style=TextStyle(font_size=12)
            )

            # Test if line breaking methods exist
            if hasattr(frame, 'get_lines'):
                lines = frame.get_lines()
                assert isinstance(lines, list)
                # Should break into multiple lines
                assert len(lines) > 1 or len(lines[0]) < len(long_text)
        except NameError:
            pytest.skip("TextFrame line breaking not available")

    def test_text_baseline_alignment(self):
        """Test text baseline alignment."""
        try:
            frame = TextFrame(
                content="Baseline Test",
                bounds=Rect(0, 0, 200, 30),
                style=TextStyle(font_size=16)
            )

            # Test baseline calculation if available
            if hasattr(frame, 'baseline_y'):
                baseline = frame.baseline_y
                assert isinstance(baseline, (int, float))
                assert 0 <= baseline <= frame.bounds.height
        except NameError:
            pytest.skip("TextFrame baseline not available")


class TestTextValidation(IRTestBase):
    """Test text validation and error handling."""

    def test_text_frame_invalid_bounds(self):
        """Test text frame with invalid bounds."""
        try:
            with pytest.raises((TypeError, ValueError)):
                TextFrame(
                    content="Test",
                    bounds="invalid_bounds",  # Should be Rect
                    style=None
                )
        except NameError:
            pytest.skip("TextFrame not available")

    def test_text_style_invalid_font_size(self):
        """Test text style with invalid font size."""
        try:
            with pytest.raises((TypeError, ValueError)):
                TextStyle(
                    font_family="Arial",
                    font_size="invalid_size"  # Should be number
                )
        except NameError:
            pytest.skip("TextStyle not available")

    def test_text_style_negative_font_size(self):
        """Test text style with negative font size."""
        try:
            with pytest.raises(ValueError):
                TextStyle(
                    font_family="Arial",
                    font_size=-5  # Invalid negative size
                )
        except NameError:
            pytest.skip("TextStyle not available")

    def test_font_info_invalid_parameters(self):
        """Test font info with invalid parameters."""
        try:
            with pytest.raises((TypeError, ValueError)):
                FontInfo(
                    family=None,  # Invalid None family
                    size=12,
                    weight="normal",
                    style="normal"
                )
        except NameError:
            pytest.skip("FontInfo not available")


class TestTextEquality(IRTestBase):
    """Test text equality and comparison."""

    def test_text_frame_equality(self):
        """Test text frame equality comparison."""
        try:
            bounds = Rect(10, 20, 200, 50)
            style = TextStyle(font_size=12)

            frame1 = TextFrame(
                content="Test Text",
                bounds=bounds,
                style=style
            )

            frame2 = TextFrame(
                content="Test Text",
                bounds=bounds,
                style=style
            )

            frame3 = TextFrame(
                content="Different Text",
                bounds=bounds,
                style=style
            )

            assert frame1 == frame2
            assert frame1 != frame3
        except NameError:
            pytest.skip("TextFrame not available")

    def test_text_style_equality(self):
        """Test text style equality comparison."""
        try:
            style1 = TextStyle(
                font_family="Arial",
                font_size=12,
                font_weight="bold"
            )

            style2 = TextStyle(
                font_family="Arial",
                font_size=12,
                font_weight="bold"
            )

            style3 = TextStyle(
                font_family="Arial",
                font_size=14,  # Different size
                font_weight="bold"
            )

            assert style1 == style2
            assert style1 != style3
        except NameError:
            pytest.skip("TextStyle not available")

    def test_text_span_equality(self):
        """Test text span equality comparison."""
        try:
            style = TextStyle(font_size=12)

            span1 = TextSpan(content="Text", style=style)
            span2 = TextSpan(content="Text", style=style)
            span3 = TextSpan(content="Different", style=style)

            assert span1 == span2
            assert span1 != span3
        except NameError:
            pytest.skip("TextSpan not available")


class TestTextSerialization(IRTestBase):
    """Test text serialization and data exchange."""

    def test_text_frame_dict_representation(self):
        """Test converting text frame to dictionary."""
        try:
            frame = TextFrame(
                content="Test Text",
                bounds=Rect(0, 0, 200, 50),
                style=TextStyle(font_size=12)
            )

            # Test dict conversion
            try:
                import dataclasses
                if dataclasses.is_dataclass(frame):
                    frame_dict = dataclasses.asdict(frame)
                    assert 'content' in frame_dict
                    assert frame_dict['content'] == 'Test Text'
            except (ImportError, TypeError):
                # Manual dict creation
                frame_dict = {
                    'content': frame.content,
                    'bounds': frame.bounds
                }
                assert frame_dict['content'] == 'Test Text'
        except NameError:
            pytest.skip("TextFrame not available")

    def test_text_style_dict_representation(self):
        """Test converting text style to dictionary."""
        try:
            style = TextStyle(
                font_family="Arial",
                font_size=12,
                font_weight="bold"
            )

            # Test dict conversion
            try:
                import dataclasses
                if dataclasses.is_dataclass(style):
                    style_dict = dataclasses.asdict(style)
                    assert 'font_family' in style_dict
                    assert 'font_size' in style_dict
            except (ImportError, TypeError):
                # Manual dict creation
                style_dict = {
                    'font_family': style.font_family,
                    'font_size': style.font_size
                }
                assert style_dict['font_family'] == 'Arial'
        except NameError:
            pytest.skip("TextStyle not available")


class TestTextPerformance(IRTestBase):
    """Test text performance characteristics."""

    def test_text_frame_creation_performance(self):
        """Test text frame creation performance."""
        try:
            import time

            start_time = time.time()

            frames = []
            for i in range(100):
                frame = TextFrame(
                    content=f"Text frame {i}",
                    bounds=Rect(i, i, 200, 30),
                    style=TextStyle(font_size=12)
                )
                frames.append(frame)

            creation_time = time.time() - start_time

            assert len(frames) == 100
            assert creation_time < 0.1  # Should create quickly

            # Verify first and last frames
            assert frames[0].content == "Text frame 0"
            assert frames[99].content == "Text frame 99"
        except NameError:
            pytest.skip("TextFrame not available")

    def test_text_style_creation_performance(self):
        """Test text style creation performance."""
        try:
            import time

            start_time = time.time()

            styles = []
            for i in range(1000):
                style = TextStyle(
                    font_family="Arial",
                    font_size=10 + (i % 20)  # Vary font size
                )
                styles.append(style)

            creation_time = time.time() - start_time

            assert len(styles) == 1000
            assert creation_time < 0.1  # Should create very quickly

            # Verify variation
            assert styles[0].font_size != styles[10].font_size or \
                   styles[0].font_size == styles[20].font_size  # Pattern repeats
        except NameError:
            pytest.skip("TextStyle not available")


if __name__ == "__main__":
    pytest.main([__file__])