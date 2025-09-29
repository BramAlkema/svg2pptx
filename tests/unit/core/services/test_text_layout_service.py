#!/usr/bin/env python3
"""
Test Text Layout Service

Comprehensive tests for precise text layout calculations, coordinate conversions,
and SVG baseline to PowerPoint top-left positioning.
"""

import pytest
import math
from unittest.mock import Mock, patch
from core.services.text_layout_engine import (
    create_text_layout_engine,
    TextMeasurements,
    TextLayoutResult
)
from core.ir.font_metadata import create_font_metadata
from core.ir.text import Run, TextAnchor


class TestTextLayoutService:
    """Test text layout calculation functionality."""

    @pytest.fixture
    def layout_engine(self):
        """Create text layout engine."""
        return create_text_layout_engine()

    def test_layout_engine_initialization(self, layout_engine):
        """Test layout engine initialization."""
        assert layout_engine is not None

        capabilities = layout_engine.get_capabilities()
        assert capabilities['precise_measurements'] is True
        assert capabilities['coordinate_conversion'] is True
        assert capabilities['baseline_conversion'] is True

    def test_basic_text_measurement(self, layout_engine):
        """Test basic text measurement functionality."""
        font_metadata = create_font_metadata("Arial", size_pt=12.0)
        text = "Hello World"

        measurements = layout_engine.measure_text_only(text, font_metadata)

        assert isinstance(measurements, TextMeasurements)
        assert measurements.width_pt > 0
        assert measurements.height_pt > 0
        assert measurements.font_size == 12.0
        assert measurements.character_count == len(text)

    def test_font_metrics_calculation(self, layout_engine):
        """Test font metrics calculation."""
        font_metadata = create_font_metadata("Arial", size_pt=24.0)

        measurements = layout_engine.measure_text_only("Test", font_metadata)

        # Font metrics should be proportional to font size
        assert measurements.ascent_pt == 24.0 * 0.8  # 19.2pt
        assert measurements.descent_pt == 24.0 * 0.2  # 4.8pt
        assert measurements.line_height_pt == 24.0 * 1.2  # 28.8pt

    def test_character_width_estimation(self, layout_engine):
        """Test character width estimation accuracy."""
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        # Test different character types
        test_cases = [
            ("i", 0.3),  # Narrow character
            ("m", 1.0),  # Wide character
            ("W", 1.2),  # Very wide character
            (" ", 0.25)  # Space
        ]

        for char, expected_ratio in test_cases:
            measurements = layout_engine.measure_text_only(char, font_metadata)
            expected_width = font_metadata.size_pt * expected_ratio

            # Allow 20% tolerance for character width estimation
            assert abs(measurements.width_pt - expected_width) < expected_width * 0.2

    def test_svg_baseline_to_powerpoint_conversion(self, layout_engine):
        """Test SVG baseline to PowerPoint top-left conversion."""
        font_metadata = create_font_metadata("Arial", size_pt=12.0)
        text = "Baseline Test"

        # SVG coordinates (x, y at baseline)
        svg_x, svg_y = 100.0, 200.0
        text_anchor = TextAnchor.START

        layout_result = layout_engine.calculate_text_layout(
            svg_x=svg_x,
            svg_y=svg_y,
            text=text,
            font_metadata=font_metadata,
            anchor=text_anchor
        )

        assert isinstance(layout_result, TextLayoutResult)

        # PowerPoint coordinates should be adjusted for top-left positioning
        # Y coordinate should be moved up by ascent amount
        expected_ppt_y = svg_y - layout_result.measurements.ascent_pt
        assert abs(layout_result.ppt_top_left_x - svg_x) < 0.1
        assert abs(layout_result.ppt_top_left_y - expected_ppt_y) < 0.1

    def test_text_anchor_positioning(self, layout_engine):
        """Test different text anchor positioning."""
        font_metadata = create_font_metadata("Arial", size_pt=12.0)
        text = "Anchor Test"
        svg_x, svg_y = 100.0, 200.0

        # Test all anchor types
        anchor_tests = [
            (TextAnchor.START, 0.0),  # No x adjustment
            (TextAnchor.MIDDLE, -0.5),  # Move left by half width
            (TextAnchor.END, -1.0)  # Move left by full width
        ]

        for anchor, x_ratio in anchor_tests:
            layout_result = layout_engine.calculate_text_layout(
                text=text,
                font_metadata=font_metadata,
                svg_x=svg_x,
                svg_y=svg_y,
                text_anchor=anchor
            )

            expected_x = svg_x + (x_ratio * layout_result.measurements.width_pt)
            assert abs(layout_result.ppt_top_left_x - expected_x) < 1.0

    def test_multi_line_text_layout(self, layout_engine):
        """Test multi-line text layout calculations."""
        font_metadata = create_font_metadata("Arial", size_pt=12.0)
        text = "Line 1\nLine 2\nLine 3"
        svg_x, svg_y = 50.0, 100.0

        layout_result = layout_engine.calculate_text_layout(
            text=text,
            font_metadata=font_metadata,
            svg_x=svg_x,
            svg_y=svg_y,
            text_anchor=TextAnchor.START
        )

        # Multi-line text should have increased height
        expected_height = layout_result.measurements.line_height_pt * 3
        assert abs(layout_result.measurements.height_pt - expected_height) < 1.0

        # Width should be the width of the longest line
        lines = text.split('\n')
        max_line_length = max(len(line) for line in lines)
        assert layout_result.measurements.width_pt > 0

    def test_emu_coordinate_conversion(self, layout_engine):
        """Test EMU coordinate conversion."""
        font_metadata = create_font_metadata("Arial", size_pt=12.0)
        text = "EMU Test"

        layout_result = layout_engine.calculate_text_layout(
            text=text,
            font_metadata=font_metadata,
            svg_x=72.0,  # 1 inch in points
            svg_y=72.0,
            text_anchor=TextAnchor.START
        )

        # 1 inch = 914400 EMU
        expected_emu_per_pt = 914400.0 / 72.0

        assert layout_result.ppt_top_left_x_emu is not None
        assert layout_result.ppt_top_left_y_emu is not None

        # Check EMU conversion accuracy
        expected_x_emu = layout_result.ppt_top_left_x * expected_emu_per_pt
        expected_y_emu = layout_result.ppt_top_left_y * expected_emu_per_pt

        assert abs(layout_result.ppt_top_left_x_emu - expected_x_emu) < 100  # Allow small rounding
        assert abs(layout_result.ppt_top_left_y_emu - expected_y_emu) < 100

    def test_font_size_scaling(self, layout_engine):
        """Test layout scaling with different font sizes."""
        text = "Scale Test"
        svg_x, svg_y = 100.0, 100.0

        sizes = [8.0, 12.0, 18.0, 24.0, 36.0]
        results = []

        for size in sizes:
            font_metadata = create_font_metadata("Arial", size_pt=size)
            layout_result = layout_engine.calculate_text_layout(
                text=text,
                font_metadata=font_metadata,
                svg_x=svg_x,
                svg_y=svg_y,
                text_anchor=TextAnchor.START
            )
            results.append(layout_result)

        # Larger fonts should have proportionally larger measurements
        for i in range(1, len(results)):
            current_result = results[i]
            previous_result = results[i-1]
            size_ratio = sizes[i] / sizes[i-1]

            width_ratio = current_result.measurements.width_pt / previous_result.measurements.width_pt
            height_ratio = current_result.measurements.height_pt / previous_result.measurements.height_pt

            # Ratios should be close to size ratio (within 10% tolerance)
            assert abs(width_ratio - size_ratio) < size_ratio * 0.1
            assert abs(height_ratio - size_ratio) < size_ratio * 0.1

    def test_text_box_bounds_calculation(self, layout_engine):
        """Test text box bounds calculation for PowerPoint."""
        font_metadata = create_font_metadata("Arial", size_pt=16.0)
        text = "Bounds Test"

        layout_result = layout_engine.calculate_text_layout(
            text=text,
            font_metadata=font_metadata,
            svg_x=50.0,
            svg_y=75.0,
            text_anchor=TextAnchor.MIDDLE
        )

        # Text box should encompass the entire text
        assert layout_result.text_box_width_pt > 0
        assert layout_result.text_box_height_pt > 0

        # Box dimensions should match or exceed measurements
        assert layout_result.text_box_width_pt >= layout_result.measurements.width_pt
        assert layout_result.text_box_height_pt >= layout_result.measurements.height_pt

    def test_performance_requirements(self, layout_engine):
        """Test performance requirements (10ms per text element)."""
        import time

        font_metadata = create_font_metadata("Arial", size_pt=12.0)
        text = "Performance test with longer text content to ensure calculations remain fast"

        start_time = time.perf_counter()

        layout_result = layout_engine.calculate_text_layout(
            text=text,
            font_metadata=font_metadata,
            svg_x=100.0,
            svg_y=100.0,
            text_anchor=TextAnchor.START
        )

        processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        # Should complete within 10ms requirement
        assert processing_time < 10.0
        assert layout_result is not None

    def test_unicode_text_layout(self, layout_engine):
        """Test layout with unicode characters."""
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        unicode_tests = [
            "English",
            "你好世界",  # Chinese
            "🌟⭐✨",  # Emoji
            "Mixed: Hello 你好"
        ]

        for text in unicode_tests:
            layout_result = layout_engine.calculate_text_layout(
                text=text,
                font_metadata=font_metadata,
                svg_x=0.0,
                svg_y=0.0,
                text_anchor=TextAnchor.START
            )

            assert layout_result is not None
            assert layout_result.measurements.width_pt > 0
            assert layout_result.measurements.height_pt > 0

    def test_error_handling(self, layout_engine):
        """Test error handling for edge cases."""
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        # Empty text
        layout_result = layout_engine.calculate_text_layout(
            text="",
            font_metadata=font_metadata,
            svg_x=0.0,
            svg_y=0.0,
            text_anchor=TextAnchor.START
        )
        assert layout_result is not None

        # Zero font size
        zero_font = create_font_metadata("Arial", size_pt=0.0)
        layout_result = layout_engine.calculate_text_layout(
            text="Test",
            font_metadata=zero_font,
            svg_x=0.0,
            svg_y=0.0,
            text_anchor=TextAnchor.START
        )
        assert layout_result is not None

    def test_coordinate_system_accuracy(self, layout_engine):
        """Test coordinate system conversion accuracy."""
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        # Test known coordinate conversions
        test_cases = [
            (0.0, 0.0),      # Origin
            (72.0, 72.0),    # 1 inch
            (144.0, 144.0),  # 2 inches
            (-36.0, -36.0)   # Negative coordinates
        ]

        for svg_x, svg_y in test_cases:
            layout_result = layout_engine.calculate_text_layout(
                text="Test",
                font_metadata=font_metadata,
                svg_x=svg_x,
                svg_y=svg_y,
                text_anchor=TextAnchor.START
            )

            # Verify coordinate conversion maintains precision
            assert layout_result.ppt_top_left_x is not None
            assert layout_result.ppt_top_left_y is not None

            # X should be close to SVG X (adjusted for anchor)
            assert abs(layout_result.ppt_top_left_x - svg_x) < 1.0


class TestTextLayoutEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_layout_engine_without_font_system(self):
        """Test layout engine without font system."""
        engine = create_text_layout_engine()
        assert engine is not None

        font_metadata = create_font_metadata("Arial", size_pt=12.0)
        layout_result = engine.calculate_text_layout(
            text="Fallback Test",
            font_metadata=font_metadata,
            svg_x=0.0,
            svg_y=0.0,
            text_anchor=TextAnchor.START
        )

        # Should work with fallback implementations
        assert layout_result is not None
        assert layout_result.measurements.width_pt > 0

    def test_extreme_font_sizes(self):
        """Test with extreme font sizes."""
        engine = create_text_layout_engine()

        extreme_sizes = [0.1, 0.5, 1.0, 144.0, 288.0]

        for size in extreme_sizes:
            font_metadata = create_font_metadata("Arial", size_pt=size)
            layout_result = engine.calculate_text_layout(
                text="Size Test",
                font_metadata=font_metadata,
                svg_x=0.0,
                svg_y=0.0,
                text_anchor=TextAnchor.START
            )

            assert layout_result is not None
            # Measurements should scale proportionally
            if size > 0:
                assert layout_result.measurements.width_pt > 0
                assert layout_result.measurements.height_pt > 0

    def test_very_long_text(self):
        """Test with very long text strings."""
        engine = create_text_layout_engine()
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        # 1000 character string
        long_text = "A" * 1000

        layout_result = engine.calculate_text_layout(
            text=long_text,
            font_metadata=font_metadata,
            svg_x=0.0,
            svg_y=0.0,
            text_anchor=TextAnchor.START
        )

        assert layout_result is not None
        assert layout_result.measurements.character_count == 1000
        assert layout_result.measurements.width_pt > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])