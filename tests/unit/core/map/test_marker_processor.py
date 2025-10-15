#!/usr/bin/env python3
"""Unit tests for MarkerProcessor."""

import pytest
from lxml import etree as ET

from core.map.marker_processor import (
    MarkerProcessor,
    MarkerPosition,
    MarkerUnits,
    MarkerDefinition,
    SymbolDefinition,
)


class TestMarkerProcessor:
    """Tests for MarkerProcessor class."""

    def test_processor_initialization(self):
        """MarkerProcessor should initialize with empty registries."""
        processor = MarkerProcessor()
        assert hasattr(processor, 'markers')
        assert hasattr(processor, 'symbols')
        assert isinstance(processor.markers, dict)
        assert isinstance(processor.symbols, dict)

    def test_can_convert_marker_element(self):
        """Should identify marker elements."""
        processor = MarkerProcessor()
        marker_elem = ET.fromstring('<marker id="arrow" xmlns="http://www.w3.org/2000/svg"/>')

        # Should be able to convert marker elements
        assert processor.can_convert(marker_elem)

    def test_can_convert_symbol_element(self):
        """Should identify symbol elements."""
        processor = MarkerProcessor()
        symbol_elem = ET.fromstring('<symbol id="icon" xmlns="http://www.w3.org/2000/svg"/>')

        # Should be able to convert symbol elements
        assert processor.can_convert(symbol_elem)

    def test_can_convert_use_element(self):
        """Should identify use elements."""
        processor = MarkerProcessor()
        use_elem = ET.fromstring('<use href="#icon" xmlns="http://www.w3.org/2000/svg"/>')

        # Should be able to convert use elements
        assert processor.can_convert(use_elem)


class TestMarkerDefinition:
    """Tests for MarkerDefinition dataclass."""

    def test_marker_definition_creation(self):
        """Should create marker definition with required fields."""
        marker_def = MarkerDefinition(
            id="arrow",
            ref_x=0,
            ref_y=0,
            marker_width=10,
            marker_height=10,
            orient="auto",
            marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None,
            overflow="visible",
            content_xml="<path d='M 0 0 L 10 5 L 0 10 Z'/>"
        )

        assert marker_def.id == "arrow"
        assert marker_def.orient == "auto"
        assert marker_def.marker_units == MarkerUnits.STROKE_WIDTH

    def test_get_orientation_angle_auto(self):
        """Should return path angle for auto orientation."""
        marker_def = MarkerDefinition(
            id="arrow",
            ref_x=0,
            ref_y=0,
            marker_width=10,
            marker_height=10,
            orient="auto",
            marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None,
            overflow="visible",
            content_xml=""
        )

        angle = marker_def.get_orientation_angle(45.0)
        assert angle == 45.0

    def test_get_orientation_angle_auto_start_reverse(self):
        """Should return path angle + 180 for auto-start-reverse."""
        marker_def = MarkerDefinition(
            id="arrow",
            ref_x=0,
            ref_y=0,
            marker_width=10,
            marker_height=10,
            orient="auto-start-reverse",
            marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None,
            overflow="visible",
            content_xml=""
        )

        angle = marker_def.get_orientation_angle(45.0)
        assert angle == 225.0  # 45 + 180

    def test_get_orientation_angle_fixed(self):
        """Should return fixed angle when orient is numeric."""
        marker_def = MarkerDefinition(
            id="arrow",
            ref_x=0,
            ref_y=0,
            marker_width=10,
            marker_height=10,
            orient="90",
            marker_units=MarkerUnits.STROKE_WIDTH,
            viewbox=None,
            overflow="visible",
            content_xml=""
        )

        angle = marker_def.get_orientation_angle(45.0)
        assert angle == 90.0  # Ignores path angle


class TestSymbolDefinition:
    """Tests for SymbolDefinition dataclass."""

    def test_symbol_definition_creation(self):
        """Should create symbol definition with required fields."""
        symbol_def = SymbolDefinition(
            id="icon",
            viewbox=(0, 0, 100, 100),
            preserve_aspect_ratio="xMidYMid meet",
            width=100,
            height=100,
            content_xml="<circle cx='50' cy='50' r='40'/>"
        )

        assert symbol_def.id == "icon"
        assert symbol_def.viewbox == (0, 0, 100, 100)
        assert symbol_def.width == 100


class TestMarkerEnums:
    """Tests for marker-related enums."""

    def test_marker_position_enum(self):
        """Should have all marker position types."""
        assert MarkerPosition.START.value == "marker-start"
        assert MarkerPosition.MID.value == "marker-mid"
        assert MarkerPosition.END.value == "marker-end"

    def test_marker_units_enum(self):
        """Should have all marker unit types."""
        assert MarkerUnits.STROKE_WIDTH.value == "strokeWidth"
        assert MarkerUnits.USER_SPACE_ON_USE.value == "userSpaceOnUse"


class TestMarkerImports:
    """Tests for marker module imports."""

    def test_import_marker_processor(self):
        """Should import MarkerProcessor."""
        from core.map.marker_processor import MarkerProcessor
        assert MarkerProcessor is not None

    def test_import_marker_mapper(self):
        """Should import MarkerMapper."""
        from core.map.marker_mapper import MarkerMapper
        assert MarkerMapper is not None

    def test_import_symbol_mapper(self):
        """Should import SymbolMapper."""
        from core.map.marker_mapper import SymbolMapper
        assert SymbolMapper is not None
