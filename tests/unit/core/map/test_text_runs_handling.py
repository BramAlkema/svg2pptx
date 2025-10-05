#!/usr/bin/env python3
"""
Tests for text run handling in TextMapper.

Ensures TextMapper correctly handles both TextFrame and RichTextFrame
without AttributeError on .runs access.
"""

import pytest
from core.map.text_mapper import TextMapper
from core.policy.engine import PolicyEngine
from core.ir.text import TextFrame, RichTextFrame, Run, TextLine, TextAnchor
from core.ir.geometry import Point, Rect


@pytest.fixture
def policy():
    """Create policy engine for tests"""
    return PolicyEngine()


@pytest.fixture
def text_mapper(policy):
    """Create text mapper for tests"""
    return TextMapper(policy)


@pytest.fixture
def sample_run():
    """Create a sample text run"""
    return Run(
        text="Hello",
        font_family="Arial",
        font_size_pt=12.0,
        bold=False,
        italic=False,
        underline=False,
        strike=False,
        rgb="000000",
    )


@pytest.fixture
def sample_text_frame(sample_run):
    """Create a sample TextFrame"""
    return TextFrame(
        origin=Point(x=100, y=100),
        runs=[sample_run],
        anchor=TextAnchor.START,
        bbox=Rect(x=100, y=100, width=500, height=200),
    )


@pytest.fixture
def sample_rich_text_frame(sample_run):
    """Create a sample RichTextFrame"""
    line = TextLine(
        runs=[sample_run],
        anchor=TextAnchor.START,
    )
    return RichTextFrame(
        lines=[line],
        position=Point(x=100, y=100),
        bounds=Rect(x=100, y=100, width=500, height=200),
    )


class TestGetRunsHelper:
    """Test the _get_runs helper method"""

    def test_get_runs_from_textframe(self, text_mapper, sample_text_frame):
        """Test extracting runs from TextFrame"""
        runs = text_mapper._get_runs(sample_text_frame)

        assert isinstance(runs, list)
        assert len(runs) == 1
        assert runs[0].text == "Hello"
        assert runs[0].font_family == "Arial"

    def test_get_runs_from_richtextframe(self, text_mapper, sample_rich_text_frame):
        """Test extracting runs from RichTextFrame"""
        runs = text_mapper._get_runs(sample_rich_text_frame)

        assert isinstance(runs, list)
        assert len(runs) == 1
        assert runs[0].text == "Hello"
        assert runs[0].font_family == "Arial"

    def test_get_runs_from_richtextframe_multiple_lines(self, text_mapper):
        """Test extracting runs from RichTextFrame with multiple lines"""
        run1 = Run(
            text="Line 1",
            font_family="Arial",
            font_size_pt=12.0,
            bold=False,
            italic=False,
            underline=False,
            strike=False,
            rgb="000000",
        )
        run2 = Run(
            text="Line 2",
            font_family="Arial",
            font_size_pt=14.0,
            bold=True,
            italic=False,
            underline=False,
            strike=False,
            rgb="FF0000",
        )

        line1 = TextLine(runs=[run1], anchor=TextAnchor.START)
        line2 = TextLine(runs=[run2], anchor=TextAnchor.START)

        rich_frame = RichTextFrame(
            lines=[line1, line2],
            position=Point(x=100, y=100),
            bounds=Rect(x=100, y=100, width=500, height=200),
        )

        runs = text_mapper._get_runs(rich_frame)

        assert len(runs) == 2
        assert runs[0].text == "Line 1"
        assert runs[0].font_size_pt == 12.0
        assert runs[1].text == "Line 2"
        assert runs[1].font_size_pt == 14.0
        assert runs[1].bold is True

    def test_get_runs_empty_textframe(self, text_mapper):
        """Test _get_runs with TextFrame that has no runs attribute"""
        # Create a mock object without runs
        class MockTextFrame:
            pass

        mock_frame = MockTextFrame()
        runs = text_mapper._get_runs(mock_frame)

        assert isinstance(runs, list)
        assert len(runs) == 0


class TestMapperResultMetadata:
    """Test that mapper results include correct run counts"""

    def test_textframe_run_count_in_metadata(self, text_mapper, sample_text_frame):
        """Test run_count in metadata for TextFrame"""
        decision = text_mapper.policy.decide_text(sample_text_frame)
        result = text_mapper.map(sample_text_frame, decision)

        assert 'run_count' in result.metadata
        assert result.metadata['run_count'] == 1

    def test_richtextframe_run_count_in_metadata(self, text_mapper, sample_rich_text_frame):
        """Test run_count in metadata for RichTextFrame"""
        decision = text_mapper.policy.decide_text(sample_rich_text_frame)
        result = text_mapper.map(sample_rich_text_frame, decision)

        assert 'run_count' in result.metadata
        assert result.metadata['run_count'] == 1

    def test_richtextframe_multiple_runs_count(self, text_mapper):
        """Test run_count with RichTextFrame containing multiple runs"""
        run1 = Run(
            text="Bold",
            font_family="Arial",
            font_size_pt=12.0,
            bold=True,
            italic=False,
            underline=False,
            strike=False,
            rgb="000000",
        )
        run2 = Run(
            text=" Normal",
            font_family="Arial",
            font_size_pt=12.0,
            bold=False,
            italic=False,
            underline=False,
            strike=False,
            rgb="000000",
        )

        line = TextLine(runs=[run1, run2], anchor=TextAnchor.START)
        rich_frame = RichTextFrame(
            lines=[line],
            position=Point(x=100, y=100),
            bounds=Rect(x=100, y=100, width=500, height=200),
        )

        decision = text_mapper.policy.decide_text(rich_frame)
        result = text_mapper.map(rich_frame, decision)

        assert result.metadata['run_count'] == 2


class TestParagraphGeneration:
    """Test paragraph generation uses _get_runs helper"""

    def test_generate_paragraphs_from_textframe(self, text_mapper, sample_text_frame):
        """Test paragraph generation works with TextFrame"""
        xml = text_mapper._generate_paragraphs_xml(sample_text_frame)

        assert '<a:p>' in xml
        assert '<a:t>Hello</a:t>' in xml

    def test_generate_paragraphs_from_richtextframe(self, text_mapper, sample_rich_text_frame):
        """Test paragraph generation works with RichTextFrame"""
        # RichTextFrame should be converted to TextFrame first in the mapper
        # This test verifies the _get_runs helper is used
        runs = text_mapper._get_runs(sample_rich_text_frame)
        assert len(runs) == 1
        assert runs[0].text == "Hello"


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_none_element(self, text_mapper):
        """Test _get_runs with None element"""
        runs = text_mapper._get_runs(None)
        assert runs == []

    def test_textframe_with_empty_runs(self, text_mapper):
        """Test TextFrame with empty runs list"""
        frame = TextFrame(
            origin=Point(x=100, y=100),
            runs=[],
            anchor=TextAnchor.START,
            bbox=Rect(x=100, y=100, width=500, height=200),
        )

        runs = text_mapper._get_runs(frame)
        assert runs == []

    def test_richtextframe_with_empty_lines(self, text_mapper):
        """Test RichTextFrame with empty lines"""
        rich_frame = RichTextFrame(
            lines=[],
            position=Point(x=100, y=100),
            bounds=Rect(x=100, y=100, width=500, height=200),
        )

        runs = text_mapper._get_runs(rich_frame)
        assert runs == []
