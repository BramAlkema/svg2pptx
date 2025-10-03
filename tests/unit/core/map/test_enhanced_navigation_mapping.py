#!/usr/bin/env python3
"""
Tests for Enhanced Navigation Mapping in Mappers

Validates that mappers properly extract NavigationSpec from IR elements
and provide both new and legacy navigation formats in MapperResult.
"""

import pytest
from unittest.mock import Mock

# Import mapping components
from core.map.base import Mapper, MapperResult, OutputFormat
from core.map.path_mapper import PathMapper
from core.map.group_mapper import GroupMapper
from core.map.text_mapper import TextMapper
from core.map.image_mapper import ImageMapper

# Import IR elements and navigation types
from core.ir import Path, Group, Image, TextFrame
from core.ir.geometry import Point, Rect, LineSegment
from core.ir.text import Run, TextAnchor
from core.pipeline.navigation import (
    NavigationSpec, create_external_navigation, create_slide_navigation,
    create_action_navigation, JumpAction
)
from core.pipeline.hyperlinks import HyperlinkSpec


class TestMapperNavigationExtraction:
    """Test that mappers extract navigation from IR elements correctly."""

    def test_path_mapper_navigation_extraction(self):
        """Test PathMapper extracts NavigationSpec correctly."""
        # Create navigation
        navigation = create_external_navigation("https://example.com", "Test Link")

        # Create path with navigation
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            navigation=navigation
        )

        # Create mock policy
        mock_policy = Mock()
        mock_policy.decide_path_strategy.return_value = Mock(
            output_format=OutputFormat.NATIVE_DML,
            estimated_quality=0.95,
            estimated_performance=0.9
        )

        # Create mapper and extract navigation info
        mapper = PathMapper(mock_policy)
        navigation_info = mapper._extract_hyperlink_info(path)

        # Verify navigation extraction
        assert navigation_info['navigation'] is not None
        assert len(navigation_info['navigation']) == 1
        assert navigation_info['navigation'][0] == navigation
        assert navigation_info['shape_id'] == f"shape_{id(path)}"
        assert navigation_info['hyperlinks'] is None  # No legacy hyperlink

    def test_group_mapper_navigation_extraction(self):
        """Test GroupMapper extracts NavigationSpec correctly."""
        # Create navigation
        navigation = create_slide_navigation(3, "Go to slide 3")

        # Create group with navigation
        group = Group(children=[], navigation=navigation)

        # Create mock policy
        mock_policy = Mock()

        # Create mapper and extract navigation info
        mapper = GroupMapper(mock_policy)
        navigation_info = mapper._extract_hyperlink_info(group)

        # Verify navigation extraction
        assert navigation_info['navigation'] is not None
        assert len(navigation_info['navigation']) == 1
        assert navigation_info['navigation'][0] == navigation
        assert navigation_info['shape_id'] == f"shape_{id(group)}"

    def test_text_mapper_navigation_extraction(self):
        """Test TextMapper extracts NavigationSpec correctly from text elements."""
        # Create navigation
        navigation = create_action_navigation(JumpAction.NEXT, "Next slide")

        # Create text frame with navigation
        runs = [Run(text="Click here", font_family="Arial", font_size_pt=12)]
        textframe = TextFrame(
            origin=Point(0, 0),
            runs=runs,
            anchor=TextAnchor.START,
            bbox=Rect(0, 0, 100, 20),
            navigation=navigation
        )

        # Create mock policy
        mock_policy = Mock()

        # Create mapper and extract navigation info
        mapper = TextMapper(mock_policy)
        navigation_info = mapper._extract_hyperlink_info(textframe)

        # Verify navigation extraction
        assert navigation_info['navigation'] is not None
        assert len(navigation_info['navigation']) == 1
        assert navigation_info['navigation'][0] == navigation
        assert navigation_info['shape_id'] == f"shape_{id(textframe)}"

        # Verify linked runs for text elements
        assert navigation_info['linked_runs'] is not None
        assert len(navigation_info['linked_runs']) == 1
        linked_run = navigation_info['linked_runs'][0]
        assert linked_run['text'] == "Click here"
        assert linked_run['navigation'] == navigation
        assert linked_run['start_index'] == 0
        assert linked_run['end_index'] == 10

    def test_image_mapper_navigation_extraction(self):
        """Test ImageMapper extracts NavigationSpec correctly."""
        # Create navigation
        navigation = create_external_navigation("mailto:contact@example.com", "Send email")

        # Create image with navigation
        image = Image(
            origin=Point(0, 0),
            size=Rect(0, 0, 100, 100),
            data=b"fake_image_data",
            format="png",
            navigation=navigation
        )

        # Create mock policy
        mock_policy = Mock()

        # Create mapper and extract navigation info
        mapper = ImageMapper(mock_policy)
        navigation_info = mapper._extract_hyperlink_info(image)

        # Verify navigation extraction
        assert navigation_info['navigation'] is not None
        assert len(navigation_info['navigation']) == 1
        assert navigation_info['navigation'][0] == navigation
        assert navigation_info['shape_id'] == f"shape_{id(image)}"


class TestBackwardCompatibilityMapping:
    """Test backward compatibility between NavigationSpec and HyperlinkSpec in mapping."""

    def test_legacy_hyperlink_extraction(self):
        """Test that legacy HyperlinkSpec is extracted and converted."""
        # Create legacy hyperlink
        hyperlink = HyperlinkSpec(href="https://example.com", tooltip="Old Link")

        # Create path with legacy hyperlink
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            hyperlink=hyperlink
        )

        # Create mock policy
        mock_policy = Mock()

        # Create mapper and extract navigation info
        mapper = PathMapper(mock_policy)
        navigation_info = mapper._extract_hyperlink_info(path)

        # Verify conversion to NavigationSpec
        assert navigation_info['navigation'] is not None
        assert len(navigation_info['navigation']) == 1
        navigation = navigation_info['navigation'][0]
        assert navigation.kind.value == "external"
        assert navigation.href == "https://example.com"
        assert navigation.tooltip == "Old Link"

        # Verify legacy format is preserved for backward compatibility
        assert navigation_info['hyperlinks'] is not None
        assert len(navigation_info['hyperlinks']) == 1
        assert navigation_info['hyperlinks'][0] == hyperlink

    def test_mixed_navigation_priority(self):
        """Test that NavigationSpec takes priority when both formats are present."""
        # Create both navigation formats
        hyperlink = HyperlinkSpec(href="https://old.com")
        navigation = create_slide_navigation(5, "New navigation")

        # Create path with both formats
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            hyperlink=hyperlink,
            navigation=navigation
        )

        # Create mock policy
        mock_policy = Mock()

        # Create mapper and extract navigation info
        mapper = PathMapper(mock_policy)
        navigation_info = mapper._extract_hyperlink_info(path)

        # Verify NavigationSpec takes priority
        assert navigation_info['navigation'] is not None
        assert len(navigation_info['navigation']) == 1
        assert navigation_info['navigation'][0] == navigation

        # Verify legacy format is still preserved
        assert navigation_info['hyperlinks'] is not None
        assert navigation_info['hyperlinks'][0] == hyperlink

    def test_text_element_with_legacy_hyperlink(self):
        """Test text element extraction with legacy hyperlink."""
        # Create legacy hyperlink
        hyperlink = HyperlinkSpec(href="slide:7", tooltip="Go to slide 7")

        # Create text frame with legacy hyperlink
        runs = [Run(text="Navigate", font_family="Arial", font_size_pt=12)]
        textframe = TextFrame(
            origin=Point(0, 0),
            runs=runs,
            anchor=TextAnchor.START,
            bbox=Rect(0, 0, 100, 20),
            hyperlink=hyperlink
        )

        # Create mock policy
        mock_policy = Mock()

        # Create mapper and extract navigation info
        mapper = TextMapper(mock_policy)
        navigation_info = mapper._extract_hyperlink_info(textframe)

        # Verify conversion to NavigationSpec
        assert navigation_info['navigation'] is not None
        navigation = navigation_info['navigation'][0]
        assert navigation.kind.value == "slide"
        assert navigation.slide.index == 7

        # Verify linked runs have both formats
        assert navigation_info['linked_runs'] is not None
        linked_run = navigation_info['linked_runs'][0]
        assert linked_run['navigation'] == navigation
        assert linked_run['hyperlink'] == hyperlink
        assert linked_run['text'] == "Navigate"


class TestMapperResultIntegration:
    """Test that MapperResult properly supports both navigation formats."""

    def test_mapper_result_navigation_fields(self):
        """Test MapperResult supports both navigation and hyperlinks fields."""
        # Create test data
        navigation = create_external_navigation("https://example.com")
        hyperlink = HyperlinkSpec(href="https://example.com")
        path = Path(segments=[LineSegment(Point(0, 0), Point(100, 100))])

        # Create MapperResult with both formats
        result = MapperResult(
            element=path,
            output_format=OutputFormat.NATIVE_DML,
            xml_content="<test/>",
            policy_decision=Mock(),
            metadata={},
            navigation=[navigation],
            hyperlinks=[hyperlink],
            shape_id="test_shape_123"
        )

        # Verify both fields are accessible
        assert result.navigation is not None
        assert len(result.navigation) == 1
        assert result.navigation[0] == navigation

        assert result.hyperlinks is not None
        assert len(result.hyperlinks) == 1
        assert result.hyperlinks[0] == hyperlink

        assert result.shape_id == "test_shape_123"

    def test_text_content_extraction(self):
        """Test _get_text_content method extracts text correctly."""
        # Create mock policy
        mock_policy = Mock()
        mapper = PathMapper(mock_policy)

        # Test with runs
        runs = [
            Run(text="Hello ", font_family="Arial", font_size_pt=12),
            Run(text="World", font_family="Arial", font_size_pt=12)
        ]
        textframe = TextFrame(
            origin=Point(0, 0),
            runs=runs,
            anchor=TextAnchor.START,
            bbox=Rect(0, 0, 100, 20)
        )

        text_content = mapper._get_text_content(textframe)
        assert text_content == "Hello World"

        # Test with text_content attribute
        mock_element = Mock()
        mock_element.text_content = "Direct text"
        text_content = mapper._get_text_content(mock_element)
        assert text_content == "Direct text"

        # Test with no text
        empty_element = Mock()
        del empty_element.text_content
        del empty_element.runs
        text_content = mapper._get_text_content(empty_element)
        assert text_content == ""


class TestNavigationExtractionEdgeCases:
    """Test edge cases in navigation extraction."""

    def test_no_navigation_present(self):
        """Test extraction when element has no navigation."""
        # Create path without navigation
        path = Path(segments=[LineSegment(Point(0, 0), Point(100, 100))])

        # Create mock policy
        mock_policy = Mock()

        # Create mapper and extract navigation info
        mapper = PathMapper(mock_policy)
        navigation_info = mapper._extract_hyperlink_info(path)

        # Verify no navigation extracted
        assert navigation_info['navigation'] is None
        assert navigation_info['hyperlinks'] is None
        assert navigation_info['shape_id'] is None
        assert navigation_info['linked_runs'] is None

    def test_invalid_hyperlink_handling(self):
        """Test handling of invalid hyperlink specifications."""
        # Create invalid hyperlink (this should be handled gracefully)
        try:
            hyperlink = HyperlinkSpec(href="invalid:")  # Invalid scheme
            path = Path(
                segments=[LineSegment(Point(0, 0), Point(100, 100))],
                hyperlink=hyperlink
            )

            # Create mock policy
            mock_policy = Mock()

            # Create mapper and extract navigation info
            mapper = PathMapper(mock_policy)
            navigation_info = mapper._extract_hyperlink_info(path)

            # Should either extract successfully or return None gracefully
            # Exact behavior depends on validation in NavigationSpec conversion
            assert isinstance(navigation_info, dict)

        except ValueError:
            # This is also acceptable if validation is strict
            pass

    def test_element_without_runs_attribute(self):
        """Test text content extraction for elements without runs."""
        # Create mock policy
        mock_policy = Mock()
        mapper = PathMapper(mock_policy)

        # Test element without runs or text_content
        path = Path(segments=[LineSegment(Point(0, 0), Point(100, 100))])

        text_content = mapper._get_text_content(path)
        assert text_content == ""