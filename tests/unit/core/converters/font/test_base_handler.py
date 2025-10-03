#!/usr/bin/env python3
"""
Unit tests for BaseStrategyHandler

Tests the abstract base class functionality including common methods,
statistics tracking, and error handling.
"""

import pytest
from unittest.mock import Mock, patch
import time

from core.converters.font.handlers.base import BaseStrategyHandler
from core.converters.font.types import HandlerResult
from core.ir import TextFrame, Run, Point, Rect
from core.services.conversion_services import ConversionServices


class ConcreteTestHandler(BaseStrategyHandler):
    """Concrete implementation of BaseStrategyHandler for testing."""

    def can_handle(self, text_frame, context):
        """Test implementation - returns True if frame has runs."""
        return text_frame and text_frame.runs

    def convert(self, text_frame, context):
        """Test implementation - returns success result."""
        return HandlerResult(
            success=True,
            xml_content="<test>converted</test>",
            confidence=0.8,
            metadata={'test_handler': True}
        )


class FailingTestHandler(BaseStrategyHandler):
    """Handler that always fails for testing error scenarios."""

    def can_handle(self, text_frame, context):
        return True

    def convert(self, text_frame, context):
        return HandlerResult(
            success=False,
            xml_content="",
            confidence=0.0,
            warnings=["Test failure"]
        )


class ExceptionTestHandler(BaseStrategyHandler):
    """Handler that raises exceptions for testing error handling."""

    def can_handle(self, text_frame, context):
        return True

    def convert(self, text_frame, context):
        raise RuntimeError("Test exception")


@pytest.fixture
def mock_services():
    """Mock ConversionServices for testing."""
    return Mock(spec=ConversionServices)


@pytest.fixture
def sample_text_frame():
    """Create a sample TextFrame for testing."""
    run = Mock(spec=Run)
    run.text = "Hello World"
    run.font_family = "Arial"
    run.font_size_pt = 12
    run.bold = False
    run.italic = False
    run.underline = False
    run.strike = False
    run.rgb = "000000"

    frame = Mock(spec=TextFrame)
    frame.runs = [run]
    frame.origin = Point(x=100, y=200)
    frame.bbox = Rect(x=100, y=200, width=300, height=50)
    frame.anchor = "start"

    return frame


class TestBaseStrategyHandlerInitialization:
    """Test BaseStrategyHandler initialization."""

    def test_initialization(self, mock_services):
        """Test handler initialization."""
        handler = ConcreteTestHandler(mock_services)

        assert handler.services == mock_services
        assert handler.logger is not None
        assert handler.stats['total_conversions'] == 0
        assert handler.stats['successful_conversions'] == 0
        assert handler.stats['failed_conversions'] == 0
        assert handler.stats['total_time_ms'] == 0.0
        assert handler.stats['average_time_ms'] == 0.0

    def test_logger_name(self, mock_services):
        """Test that logger uses class name."""
        handler = ConcreteTestHandler(mock_services)
        assert handler.logger.name == "ConcreteTestHandler"


class TestHandlerExecution:
    """Test handler execution logic."""

    @patch('core.converters.font.handlers.base.time.perf_counter')
    def test_successful_execution(self, mock_time, mock_services, sample_text_frame):
        """Test successful handler execution."""
        mock_time.side_effect = [0.0, 0.005]  # start, end
        handler = ConcreteTestHandler(mock_services)

        result = handler.execute(sample_text_frame)

        assert result.success is True
        assert result.xml_content == "<test>converted</test>"
        assert result.confidence == 0.8
        assert result.metadata['test_handler'] is True

        # Check statistics
        stats = handler.get_statistics()
        assert stats['total_conversions'] == 1
        assert stats['successful_conversions'] == 1
        assert stats['failed_conversions'] == 0
        assert stats['total_time_ms'] == 5.0
        assert stats['average_time_ms'] == 5.0

    def test_execution_with_context(self, mock_services, sample_text_frame):
        """Test execution with conversion context."""
        handler = ConcreteTestHandler(mock_services)
        context = {'test_key': 'test_value'}

        result = handler.execute(sample_text_frame, context)

        assert result.success is True
        # Verify context was passed (through can_handle and convert calls)

    def test_execution_when_cannot_handle(self, mock_services):
        """Test execution when handler cannot handle the frame."""
        handler = ConcreteTestHandler(mock_services)

        # Frame with no runs
        empty_frame = Mock()
        empty_frame.runs = []

        result = handler.execute(empty_frame)

        assert result.success is False
        assert result.xml_content == ""
        assert result.confidence == 0.0
        assert "ConcreteTestHandler cannot handle this text frame" in result.warnings

    def test_execution_with_handler_failure(self, mock_services, sample_text_frame):
        """Test execution when handler conversion fails."""
        handler = FailingTestHandler(mock_services)

        result = handler.execute(sample_text_frame)

        assert result.success is False
        assert result.confidence == 0.0
        assert "Test failure" in result.warnings

        # Check statistics
        stats = handler.get_statistics()
        assert stats['failed_conversions'] == 1
        assert stats['successful_conversions'] == 0

    def test_execution_with_exception(self, mock_services, sample_text_frame):
        """Test execution when handler raises exception."""
        handler = ExceptionTestHandler(mock_services)

        result = handler.execute(sample_text_frame)

        assert result.success is False
        assert result.xml_content == ""
        assert result.confidence == 0.0
        assert result.error is not None
        assert "Handler execution failed: Test exception" in result.warnings

        # Check statistics
        stats = handler.get_statistics()
        assert stats['failed_conversions'] == 1


class TestHelperMethods:
    """Test helper methods provided by BaseStrategyHandler."""

    def test_extract_font_info_single_font(self, mock_services, sample_text_frame):
        """Test font info extraction with single font."""
        handler = ConcreteTestHandler(mock_services)

        font_info = handler._extract_font_info(sample_text_frame)

        assert font_info['primary_font'] == "Arial"
        assert font_info['all_fonts'] == ["Arial"]
        assert font_info['has_multiple_fonts'] is False

    def test_extract_font_info_multiple_fonts(self, mock_services, sample_text_frame):
        """Test font info extraction with multiple fonts."""
        # Add second run with different font
        run2 = Mock()
        run2.font_family = "Times"
        sample_text_frame.runs.append(run2)

        handler = ConcreteTestHandler(mock_services)
        font_info = handler._extract_font_info(sample_text_frame)

        assert font_info['primary_font'] == "Arial"
        assert len(font_info['all_fonts']) == 2
        assert "Arial" in font_info['all_fonts']
        assert "Times" in font_info['all_fonts']
        assert font_info['has_multiple_fonts'] is True

    def test_extract_font_info_empty_frame(self, mock_services):
        """Test font info extraction with empty frame."""
        empty_frame = Mock()
        empty_frame.runs = []

        handler = ConcreteTestHandler(mock_services)
        font_info = handler._extract_font_info(empty_frame)

        assert font_info['primary_font'] == "Arial"  # Default
        assert font_info['all_fonts'] == []
        assert font_info['has_multiple_fonts'] is False

    def test_calculate_bounds_with_bbox(self, mock_services, sample_text_frame):
        """Test bounds calculation when bbox is available."""
        handler = ConcreteTestHandler(mock_services)
        bounds = handler._calculate_bounds(sample_text_frame)

        assert bounds['x'] == 100
        assert bounds['y'] == 200
        assert bounds['width'] == 300
        assert bounds['height'] == 50

    def test_calculate_bounds_without_bbox(self, mock_services, sample_text_frame):
        """Test bounds calculation when bbox is not available."""
        sample_text_frame.bbox = None

        handler = ConcreteTestHandler(mock_services)
        bounds = handler._calculate_bounds(sample_text_frame)

        assert bounds['x'] == 100  # origin.x
        assert bounds['y'] == 200  # origin.y
        assert bounds['width'] > 0  # Estimated
        assert bounds['height'] > 0  # Estimated

    def test_generate_shape_properties(self, mock_services):
        """Test shape properties XML generation."""
        handler = ConcreteTestHandler(mock_services)
        bounds = {'x': 100, 'y': 200, 'width': 300, 'height': 50}

        xml = handler._generate_shape_properties(bounds)

        assert "<p:spPr>" in xml
        assert 'x="100"' in xml
        assert 'y="200"' in xml
        assert 'cx="300"' in xml
        assert 'cy="50"' in xml
        assert '<a:prstGeom prst="rect">' in xml

    def test_generate_text_properties(self, mock_services, sample_text_frame):
        """Test text properties XML generation."""
        handler = ConcreteTestHandler(mock_services)

        xml = handler._generate_text_properties(sample_text_frame)

        assert "<p:txBody>" in xml
        assert "<a:bodyPr" in xml
        assert "<a:lstStyle/>" in xml
        assert "<a:p>" in xml

    def test_generate_text_run(self, mock_services):
        """Test text run XML generation."""
        handler = ConcreteTestHandler(mock_services)

        run = Mock()
        run.font_size_pt = 12
        run.bold = True
        run.italic = False
        run.underline = True
        run.strike = False
        run.rgb = "FF0000"
        run.font_family = "Arial"
        run.text = "Hello & <World>"

        xml = handler._generate_text_run(run)

        assert "<a:r>" in xml
        assert 'sz="1200"' in xml  # 12pt * 100
        assert 'b="1"' in xml  # bold
        assert 'u="sng"' in xml  # underline
        assert 'typeface="Arial"' in xml
        assert "<a:t>Hello &amp; &lt;World&gt;</a:t>" in xml  # XML escaped

    def test_xml_escaping(self, mock_services):
        """Test XML character escaping."""
        handler = ConcreteTestHandler(mock_services)

        test_text = '&<>"\'test'
        escaped = handler._escape_xml(test_text)

        assert escaped == "&amp;&lt;&gt;&quot;&apos;test"


class TestStatisticsManagement:
    """Test statistics tracking and management."""

    def test_statistics_tracking_multiple_calls(self, mock_services, sample_text_frame):
        """Test statistics across multiple handler calls."""
        handler = ConcreteTestHandler(mock_services)

        # Execute multiple times
        for _ in range(3):
            handler.execute(sample_text_frame)

        stats = handler.get_statistics()
        assert stats['total_conversions'] == 3
        assert stats['successful_conversions'] == 3
        assert stats['failed_conversions'] == 0

    def test_statistics_with_mixed_results(self, mock_services, sample_text_frame):
        """Test statistics with both success and failure."""
        success_handler = TestStrategyHandler(mock_services)
        fail_handler = FailingTestHandler(mock_services)

        # Mix of successes and failures
        success_handler.execute(sample_text_frame)
        success_handler.execute(sample_text_frame)
        fail_handler.execute(sample_text_frame)

        success_stats = success_handler.get_statistics()
        assert success_stats['successful_conversions'] == 2
        assert success_stats['failed_conversions'] == 0

        fail_stats = fail_handler.get_statistics()
        assert fail_stats['successful_conversions'] == 0
        assert fail_stats['failed_conversions'] == 1

    def test_statistics_reset(self, mock_services, sample_text_frame):
        """Test statistics reset functionality."""
        handler = ConcreteTestHandler(mock_services)

        # Execute some operations
        handler.execute(sample_text_frame)
        handler.execute(sample_text_frame)

        # Reset statistics
        handler.reset_statistics()

        stats = handler.get_statistics()
        assert stats['total_conversions'] == 0
        assert stats['successful_conversions'] == 0
        assert stats['failed_conversions'] == 0
        assert stats['total_time_ms'] == 0.0
        assert stats['average_time_ms'] == 0.0

    def test_get_statistics_returns_copy(self, mock_services, sample_text_frame):
        """Test that get_statistics returns a copy, not reference."""
        handler = ConcreteTestHandler(mock_services)
        handler.execute(sample_text_frame)

        stats1 = handler.get_statistics()
        stats2 = handler.get_statistics()

        # Modify one copy
        stats1['total_conversions'] = 999

        # Other copy should be unchanged
        assert stats2['total_conversions'] == 1
        # Original should be unchanged
        assert handler.stats['total_conversions'] == 1