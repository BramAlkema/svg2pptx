#!/usr/bin/env python3
"""
Tests for Enhanced Navigation Integration in IR Elements

Validates that IR elements properly support both NavigationSpec and HyperlinkSpec
with seamless conversion between the two formats.
"""

import pytest
from unittest.mock import Mock

# Import IR elements and navigation types
from core.ir import (
    Path, Group, Image, TextFrame, get_effective_navigation,
    has_navigation, update_element_navigation
)
from core.ir.geometry import Point, Rect, LineSegment
from core.ir.text import Run, TextAnchor
from core.pipeline.navigation import (
    NavigationSpec, create_external_navigation, create_slide_navigation,
    create_action_navigation, JumpAction
)
from core.pipeline.hyperlinks import HyperlinkSpec


class TestIRNavigationFields:
    """Test that all IR elements support navigation fields."""

    def test_path_navigation_fields(self):
        """Test Path supports both hyperlink and navigation fields."""
        # Create basic path
        segments = [LineSegment(Point(0, 0), Point(100, 100))]
        path = Path(segments=segments)

        # Should start with no navigation
        assert path.hyperlink is None
        assert path.navigation is None

        # Can set navigation
        navigation = create_external_navigation("https://example.com")
        path_with_nav = Path(segments=segments, navigation=navigation)
        assert path_with_nav.navigation == navigation
        assert path_with_nav.hyperlink is None

    def test_group_navigation_fields(self):
        """Test Group supports both hyperlink and navigation fields."""
        # Create basic group
        group = Group(children=[])

        # Should start with no navigation
        assert group.hyperlink is None
        assert group.navigation is None

        # Can set navigation
        navigation = create_slide_navigation(3)
        group_with_nav = Group(children=[], navigation=navigation)
        assert group_with_nav.navigation == navigation
        assert group_with_nav.hyperlink is None

    def test_image_navigation_fields(self):
        """Test Image supports both hyperlink and navigation fields."""
        # Create basic image
        image = Image(
            origin=Point(0, 0),
            size=Rect(0, 0, 100, 100),
            data=b"fake_image_data",
            format="png"
        )

        # Should start with no navigation
        assert image.hyperlink is None
        assert image.navigation is None

        # Can set navigation
        navigation = create_action_navigation(JumpAction.NEXT)
        image_with_nav = Image(
            origin=Point(0, 0),
            size=Rect(0, 0, 100, 100),
            data=b"fake_image_data",
            format="png",
            navigation=navigation
        )
        assert image_with_nav.navigation == navigation
        assert image_with_nav.hyperlink is None

    def test_textframe_navigation_fields(self):
        """Test TextFrame supports both hyperlink and navigation fields."""
        # Create basic text frame
        runs = [Run(text="Hello", font_family="Arial", font_size_pt=12)]
        textframe = TextFrame(
            origin=Point(0, 0),
            runs=runs,
            anchor=TextAnchor.START,
            bbox=Rect(0, 0, 100, 20)
        )

        # Should start with no navigation
        assert textframe.hyperlink is None
        assert textframe.navigation is None

        # Can set navigation
        navigation = create_external_navigation("mailto:test@example.com")
        textframe_with_nav = TextFrame(
            origin=Point(0, 0),
            runs=runs,
            anchor=TextAnchor.START,
            bbox=Rect(0, 0, 100, 20),
            navigation=navigation
        )
        assert textframe_with_nav.navigation == navigation
        assert textframe_with_nav.hyperlink is None


class TestNavigationUtilities:
    """Test navigation utility functions."""

    def test_get_effective_navigation_with_navigation_spec(self):
        """Test getting navigation when NavigationSpec is set."""
        navigation = create_external_navigation("https://example.com")
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            navigation=navigation
        )

        result = get_effective_navigation(path)
        assert result == navigation

    def test_get_effective_navigation_with_hyperlink_conversion(self):
        """Test converting HyperlinkSpec to NavigationSpec."""
        hyperlink = HyperlinkSpec(href="https://example.com", tooltip="Test")
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            hyperlink=hyperlink
        )

        result = get_effective_navigation(path)
        assert result is not None
        assert result.kind.value == "external"
        assert result.href == "https://example.com"
        assert result.tooltip == "Test"

    def test_get_effective_navigation_priority(self):
        """Test that NavigationSpec takes priority over HyperlinkSpec."""
        navigation = create_slide_navigation(5)
        hyperlink = HyperlinkSpec(href="https://example.com")
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            hyperlink=hyperlink,
            navigation=navigation
        )

        result = get_effective_navigation(path)
        assert result == navigation  # NavigationSpec should take priority

    def test_get_effective_navigation_none(self):
        """Test getting navigation when no navigation is set."""
        path = Path(segments=[LineSegment(Point(0, 0), Point(100, 100))])

        result = get_effective_navigation(path)
        assert result is None

    def test_has_navigation_with_navigation_spec(self):
        """Test has_navigation with NavigationSpec."""
        navigation = create_external_navigation("https://example.com")
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            navigation=navigation
        )

        assert has_navigation(path) is True

    def test_has_navigation_with_hyperlink_spec(self):
        """Test has_navigation with HyperlinkSpec."""
        hyperlink = HyperlinkSpec(href="https://example.com")
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            hyperlink=hyperlink
        )

        assert has_navigation(path) is True

    def test_has_navigation_none(self):
        """Test has_navigation with no navigation."""
        path = Path(segments=[LineSegment(Point(0, 0), Point(100, 100))])

        assert has_navigation(path) is False

    def test_update_element_navigation_path(self):
        """Test updating navigation for Path element."""
        original_path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            hyperlink=HyperlinkSpec(href="https://old.com")
        )

        new_navigation = create_slide_navigation(3)
        updated_path = update_element_navigation(original_path, new_navigation)

        assert updated_path.navigation == new_navigation
        assert updated_path.hyperlink is None  # Should clear legacy field
        assert updated_path.segments == original_path.segments  # Other fields preserved

    def test_update_element_navigation_group(self):
        """Test updating navigation for Group element."""
        original_group = Group(
            children=[],
            hyperlink=HyperlinkSpec(href="https://old.com")
        )

        new_navigation = create_action_navigation(JumpAction.LAST)
        updated_group = update_element_navigation(original_group, new_navigation)

        assert updated_group.navigation == new_navigation
        assert updated_group.hyperlink is None  # Should clear legacy field
        assert updated_group.children == original_group.children  # Other fields preserved

    def test_update_element_navigation_image(self):
        """Test updating navigation for Image element."""
        original_image = Image(
            origin=Point(0, 0),
            size=Rect(0, 0, 100, 100),
            data=b"fake_data",
            format="png",
            hyperlink=HyperlinkSpec(href="https://old.com")
        )

        new_navigation = create_external_navigation("tel:+1234567890")
        updated_image = update_element_navigation(original_image, new_navigation)

        assert updated_image.navigation == new_navigation
        assert updated_image.hyperlink is None  # Should clear legacy field
        assert updated_image.data == original_image.data  # Other fields preserved

    def test_update_element_navigation_textframe(self):
        """Test updating navigation for TextFrame element."""
        runs = [Run(text="Hello", font_family="Arial", font_size_pt=12)]
        original_textframe = TextFrame(
            origin=Point(0, 0),
            runs=runs,
            anchor=TextAnchor.START,
            bbox=Rect(0, 0, 100, 20),
            hyperlink=HyperlinkSpec(href="https://old.com")
        )

        new_navigation = create_external_navigation("mailto:new@example.com")
        updated_textframe = update_element_navigation(original_textframe, new_navigation)

        assert updated_textframe.navigation == new_navigation
        assert updated_textframe.hyperlink is None  # Should clear legacy field
        assert updated_textframe.runs == original_textframe.runs  # Other fields preserved


class TestBackwardCompatibility:
    """Test backward compatibility between navigation formats."""

    def test_legacy_hyperlink_still_works(self):
        """Test that existing HyperlinkSpec usage still works."""
        hyperlink = HyperlinkSpec(href="slide:3", tooltip="Go to slide 3")
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            hyperlink=hyperlink
        )

        # Should be able to create element with legacy hyperlink
        assert path.hyperlink == hyperlink
        assert path.navigation is None

        # Should be able to extract effective navigation
        navigation = get_effective_navigation(path)
        assert navigation is not None
        assert navigation.kind.value == "slide"
        assert navigation.slide.index == 3

    def test_mixed_usage_navigation_priority(self):
        """Test that NavigationSpec takes priority when both formats present."""
        hyperlink = HyperlinkSpec(href="https://old.com")
        navigation = create_slide_navigation(5)

        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            hyperlink=hyperlink,
            navigation=navigation
        )

        effective_nav = get_effective_navigation(path)
        assert effective_nav == navigation  # NavigationSpec should win
        assert effective_nav.kind.value == "slide"
        assert effective_nav.slide.index == 5

    def test_conversion_preserves_functionality(self):
        """Test that conversion preserves all navigation functionality."""
        # Test external link conversion
        external_hyperlink = HyperlinkSpec(href="https://example.com", tooltip="Visit site")
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            hyperlink=external_hyperlink
        )

        navigation = get_effective_navigation(path)
        assert navigation.kind.value == "external"
        assert navigation.href == "https://example.com"
        assert navigation.tooltip == "Visit site"

        # Test slide link conversion
        slide_hyperlink = HyperlinkSpec(href="slide:7")
        path2 = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            hyperlink=slide_hyperlink
        )

        navigation2 = get_effective_navigation(path2)
        assert navigation2.kind.value == "slide"
        assert navigation2.slide.index == 7