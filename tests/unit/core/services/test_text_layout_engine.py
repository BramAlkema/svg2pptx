#!/usr/bin/env python3
"""
Unit tests for TextLayoutEngine.

Tests precise SVG to PowerPoint text layout calculations,
font metrics integration, and text measurement functionality.
"""

import pytest
from unittest.mock import Mock

from core.services.text_layout_engine import (
    TextLayoutEngine, TextMeasurements, TextLayoutResult,
    create_text_layout_engine, svg_text_to_ppt_box_modern
)
from core.ir.font_metadata import FontMetadata, FontMetrics, create_font_metadata
from core.ir.text import TextAnchor
from core.ir.geometry import Point, Rect


class TestTextLayoutEngine:
    """Test TextLayoutEngine core functionality."""

    def test_layout_engine_initialization(self):
        """Test TextLayoutEngine initializes correctly."""
        layout_engine = TextLayoutEngine()
        assert layout_engine is not None
        assert layout_engine._measurement_cache == {}

    def test_layout_engine_with_services(self):
        """Test TextLayoutEngine with injected services."""
        unit_converter = Mock()
        font_processor = Mock()

        layout_engine = TextLayoutEngine(unit_converter, font_processor)
        assert layout_engine._unit_converter is unit_converter
        assert layout_engine._font_processor is font_processor

    def test_create_layout_engine_factory(self):
        """Test layout engine factory function."""
        layout_engine = create_text_layout_engine()
        assert isinstance(layout_engine, TextLayoutEngine)

    def test_basic_text_layout_calculation(self):
        """Test basic text layout calculation."""
        layout_engine = TextLayoutEngine()
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        result = layout_engine.calculate_text_layout(
            svg_x=100.0,
            svg_y=200.0,
            text="Hello World",
            font_metadata=font_metadata,
            anchor=TextAnchor.START
        )

        # Validate result structure
        assert isinstance(result, TextLayoutResult)
        assert result.svg_x == 100.0
        assert result.svg_y == 200.0
        assert result.anchor == TextAnchor.START
        assert result.font_metadata == font_metadata
        assert result.layout_time_ms >= 0

        # Validate coordinates are in reasonable range
        assert result.x_emu > 0
        assert result.y_emu > 0  # Should be positive after baseline adjustment
        assert result.width_emu > 0
        assert result.height_emu > 0

    def test_text_anchor_positioning(self):
        """Test text anchor affects positioning correctly."""
        layout_engine = TextLayoutEngine()
        font_metadata = create_font_metadata("Arial", size_pt=12.0)
        text = "Test"
        svg_x, svg_y = 100.0, 200.0

        # Test all three anchors
        result_start = layout_engine.calculate_text_layout(
            svg_x, svg_y, text, font_metadata, TextAnchor.START
        )
        result_middle = layout_engine.calculate_text_layout(
            svg_x, svg_y, text, font_metadata, TextAnchor.MIDDLE
        )
        result_end = layout_engine.calculate_text_layout(
            svg_x, svg_y, text, font_metadata, TextAnchor.END
        )

        # Middle should be to the left of start
        assert result_middle.x_emu < result_start.x_emu

        # End should be to the left of middle
        assert result_end.x_emu < result_middle.x_emu

        # Y positions should be the same (only X changes with anchor)
        assert result_start.y_emu == result_middle.y_emu == result_end.y_emu

    def test_font_metrics_integration(self):
        """Test font metrics affect layout calculations."""
        layout_engine = TextLayoutEngine()

        # Font with custom metrics
        custom_metrics = FontMetrics(ascent=0.9, descent=0.1, line_height=1.5)
        font_with_metrics = FontMetadata(
            family="Custom Font",
            size_pt=12.0,
            metrics=custom_metrics
        )

        result = layout_engine.calculate_text_layout(
            100.0, 200.0, "Test", font_with_metrics
        )

        # Validate metrics are used
        expected_ascent_emu = int(12.0 * 0.9 * 12700)  # size * ascent * EMU_PER_POINT
        assert result.ascent_emu == expected_ascent_emu

        expected_descent_emu = int(12.0 * 0.1 * 12700)
        assert result.descent_emu == expected_descent_emu

    def test_text_measurement_caching(self):
        """Test text measurement caching."""
        layout_engine = TextLayoutEngine()
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        # First measurement
        measurements1 = layout_engine.measure_text_only("Test", font_metadata)

        # Second measurement (should use cache)
        measurements2 = layout_engine.measure_text_only("Test", font_metadata)

        # Should be identical objects (from cache)
        assert measurements1 is measurements2

        # Cache stats should show usage
        stats = layout_engine.get_cache_stats()
        assert stats["cache_size"] == 1

    def test_coordinate_conversion_with_unit_converter(self):
        """Test coordinate conversion with unit converter service."""
        unit_converter = Mock()
        unit_converter.to_emu.side_effect = lambda x: float(x.replace('px', '')) * 9525

        layout_engine = TextLayoutEngine(unit_converter=unit_converter)
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        result = layout_engine.calculate_text_layout(
            100.0, 200.0, "Test", font_metadata
        )

        # Verify unit converter was called
        unit_converter.to_emu.assert_any_call("100.0px")
        unit_converter.to_emu.assert_any_call("200.0px")

        # Verify conversion results
        assert result.baseline_x_emu == 952500  # 100 * 9525
        assert result.baseline_y_emu == 1905000  # 200 * 9525

    def test_font_processor_integration(self):
        """Test integration with font processor for measurements."""
        font_processor = Mock()
        font_processor.measure_text_width.return_value = 50.0  # 50 points width

        layout_engine = TextLayoutEngine(font_processor=font_processor)
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        result = layout_engine.calculate_text_layout(
            0.0, 0.0, "Test", font_metadata
        )

        # Verify font processor was called
        font_processor.measure_text_width.assert_called_once_with(
            "Test", "Arial", 12.0
        )

        # Verify measurement result
        expected_width_emu = int(50.0 * 12700)  # 50 points * EMU_PER_POINT
        assert result.measurements.width_emu == expected_width_emu
        assert result.measurements.measurement_method == "font_processor"
        assert result.measurements.confidence == 0.95

    def test_fallback_measurement_estimation(self):
        """Test fallback text measurement when font processor unavailable."""
        layout_engine = TextLayoutEngine()  # No font processor
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        measurements = layout_engine.measure_text_only("Hello", font_metadata)

        # Should use estimation
        assert measurements.measurement_method == "estimated"
        assert measurements.confidence == 0.7

        # Width should be reasonable (5 chars * 12pt * 0.6)
        expected_width_pt = 5 * 12.0 * 0.6
        assert measurements.width_pt == expected_width_pt

    def test_cache_management(self):
        """Test cache management functionality."""
        layout_engine = TextLayoutEngine()
        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        # Add measurements to cache
        layout_engine.measure_text_only("Test1", font_metadata)
        layout_engine.measure_text_only("Test2", font_metadata)

        stats_before = layout_engine.get_cache_stats()
        assert stats_before["cache_size"] == 2

        # Clear cache
        layout_engine.clear_measurement_cache()

        stats_after = layout_engine.get_cache_stats()
        assert stats_after["cache_size"] == 0


class TestTextMeasurements:
    """Test TextMeasurements data structure."""

    def test_text_measurements_creation(self):
        """Test TextMeasurements creation and properties."""
        measurements = TextMeasurements(
            width_pt=100.0,
            height_pt=20.0,
            width_emu=1270000,
            height_emu=254000,
            baseline_offset_pt=16.0,
            baseline_offset_emu=203200
        )

        assert measurements.width_pt == 100.0
        assert measurements.height_pt == 20.0
        assert measurements.aspect_ratio == 5.0  # 100/20

    def test_text_measurements_immutability(self):
        """Test TextMeasurements is immutable."""
        measurements = TextMeasurements(
            width_pt=100.0,
            height_pt=20.0,
            width_emu=1270000,
            height_emu=254000,
            baseline_offset_pt=16.0,
            baseline_offset_emu=203200
        )

        # Should not be able to modify
        with pytest.raises(AttributeError):
            measurements.width_pt = 200.0


class TestTextLayoutResult:
    """Test TextLayoutResult data structure."""

    def test_layout_result_properties(self):
        """Test TextLayoutResult properties."""
        measurements = TextMeasurements(
            width_pt=100.0, height_pt=20.0,
            width_emu=1270000, height_emu=254000,
            baseline_offset_pt=16.0, baseline_offset_emu=203200
        )

        font_metadata = create_font_metadata("Arial", size_pt=12.0)

        result = TextLayoutResult(
            x_emu=100000, y_emu=200000,
            width_emu=1270000, height_emu=254000,
            svg_x=100.0, svg_y=200.0,
            anchor=TextAnchor.START,
            measurements=measurements,
            font_metadata=font_metadata,
            layout_time_ms=5.0,
            baseline_x_emu=952500,
            baseline_y_emu=1905000,
            ascent_emu=121600,
            descent_emu=30400
        )

        # Test bounds property
        bounds = result.bounds
        assert isinstance(bounds, Rect)
        assert bounds.x == 100000.0
        assert bounds.y == 200000.0
        assert bounds.width == 1270000.0
        assert bounds.height == 254000.0

        # Test center point
        center = result.center_point
        assert isinstance(center, Point)
        assert center.x == 735000  # 100000 + (1270000 // 2)
        assert center.y == 327000  # 200000 + (254000 // 2)

        # Test baseline point
        baseline = result.baseline_point
        assert isinstance(baseline, Point)
        assert baseline.x == 952500
        assert baseline.y == 1905000


class TestLegacyCompatibility:
    """Test legacy compatibility functions."""

    def test_svg_text_to_ppt_box_modern(self):
        """Test legacy compatibility function."""
        result = svg_text_to_ppt_box_modern(
            svg_x=100.0,
            svg_y=200.0,
            anchor="start",
            text="Hello",
            font_family="Arial",
            font_size_pt=12.0
        )

        # Should return tuple of 4 integers (x, y, width, height)
        assert isinstance(result, tuple)
        assert len(result) == 4
        assert all(isinstance(x, int) for x in result)

        x_emu, y_emu, width_emu, height_emu = result
        assert x_emu >= 0
        assert y_emu >= 0
        assert width_emu > 0
        assert height_emu > 0

    def test_legacy_compatibility_with_services(self):
        """Test legacy compatibility with services parameter."""
        services = Mock()
        services.unit_converter = Mock()
        services.unit_converter.to_emu.side_effect = lambda x: float(x.replace('px', '')) * 9525
        services.font_processor = Mock()
        services.font_processor.measure_text_width.return_value = 60.0

        result = svg_text_to_ppt_box_modern(
            svg_x=50.0,
            svg_y=100.0,
            anchor="middle",
            text="Test",
            font_family="Arial",
            font_size_pt=14.0,
            services=services
        )

        # Verify services were used
        services.unit_converter.to_emu.assert_called()
        services.font_processor.measure_text_width.assert_called_with("Test", "Arial", 14.0)

        # Result should be valid
        assert isinstance(result, tuple)
        assert len(result) == 4


if __name__ == "__main__":
    pytest.main([__file__])