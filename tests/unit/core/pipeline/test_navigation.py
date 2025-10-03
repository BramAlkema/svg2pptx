#!/usr/bin/env python3
"""
Unit tests for NavigationSpec data model.

Tests the comprehensive navigation system including:
- NavigationSpec creation and validation
- Factory functions for common patterns
- Backward compatibility with HyperlinkSpec
- SVG attribute parsing
- PowerPoint format compliance
"""

import pytest
from unittest.mock import Mock

from core.pipeline.navigation import (
    NavKind, JumpAction, SlideTarget, BookmarkTarget, CustomShowTarget,
    NavigationSpec, create_external_navigation, create_slide_navigation,
    create_action_navigation, create_bookmark_navigation, create_custom_show_navigation,
    navigation_from_hyperlink_spec, parse_svg_navigation, validate_navigation_spec,
    get_navigation_summary
)
from core.pipeline.hyperlinks import HyperlinkSpec


class TestNavigationSpecDataModel:
    """Test NavigationSpec core data model."""

    def test_external_navigation_creation(self):
        """Test creation of external navigation."""
        nav = NavigationSpec(
            kind=NavKind.EXTERNAL,
            href="https://example.com",
            tooltip="Visit our website"
        )

        assert nav.kind == NavKind.EXTERNAL
        assert nav.href == "https://example.com"
        assert nav.tooltip == "Visit our website"
        assert nav.visited is True
        assert nav.is_external_link()
        assert nav.requires_relationship()
        assert not nav.is_action_based()

    def test_slide_navigation_creation(self):
        """Test creation of slide navigation."""
        nav = NavigationSpec(
            kind=NavKind.SLIDE,
            slide=SlideTarget(index=5),
            tooltip="Go to slide 5"
        )

        assert nav.kind == NavKind.SLIDE
        assert nav.slide.index == 5
        assert nav.tooltip == "Go to slide 5"
        assert nav.is_slide_jump()
        assert nav.requires_relationship()
        assert not nav.is_action_based()

    def test_action_navigation_creation(self):
        """Test creation of action navigation."""
        nav = NavigationSpec(
            kind=NavKind.ACTION,
            action=JumpAction.NEXT,
            tooltip="Next slide"
        )

        assert nav.kind == NavKind.ACTION
        assert nav.action == JumpAction.NEXT
        assert nav.tooltip == "Next slide"
        assert nav.is_action_based()
        assert not nav.requires_relationship()

    def test_bookmark_navigation_creation(self):
        """Test creation of bookmark navigation."""
        nav = NavigationSpec(
            kind=NavKind.BOOKMARK,
            bookmark=BookmarkTarget(name="intro"),
            tooltip="Jump to intro section"
        )

        assert nav.kind == NavKind.BOOKMARK
        assert nav.bookmark.name == "intro"
        assert nav.tooltip == "Jump to intro section"
        assert nav.is_action_based()
        assert not nav.requires_relationship()

    def test_custom_show_navigation_creation(self):
        """Test creation of custom show navigation."""
        nav = NavigationSpec(
            kind=NavKind.CUSTOM_SHOW,
            custom_show=CustomShowTarget(name="SalesDeck"),
            tooltip="Show sales presentation"
        )

        assert nav.kind == NavKind.CUSTOM_SHOW
        assert nav.custom_show.name == "SalesDeck"
        assert nav.tooltip == "Show sales presentation"
        assert nav.is_action_based()
        assert not nav.requires_relationship()


class TestNavigationSpecValidation:
    """Test NavigationSpec validation logic."""

    def test_exactly_one_target_required(self):
        """Test that exactly one navigation target must be set."""
        # No targets
        with pytest.raises(ValueError, match="Exactly one navigation target"):
            NavigationSpec(kind=NavKind.EXTERNAL)

        # Multiple targets
        with pytest.raises(ValueError, match="Exactly one navigation target"):
            NavigationSpec(
                kind=NavKind.EXTERNAL,
                href="https://example.com",
                slide=SlideTarget(index=1)
            )

    def test_target_must_match_kind(self):
        """Test that navigation target must match the kind."""
        # External kind without href
        with pytest.raises(ValueError, match="EXTERNAL navigation requires href"):
            NavigationSpec(kind=NavKind.EXTERNAL, slide=SlideTarget(index=1))

        # Slide kind without slide target
        with pytest.raises(ValueError, match="SLIDE navigation requires slide"):
            NavigationSpec(kind=NavKind.SLIDE, href="https://example.com")

        # Action kind without action
        with pytest.raises(ValueError, match="ACTION navigation requires action"):
            NavigationSpec(kind=NavKind.ACTION, href="https://example.com")

        # Bookmark kind without bookmark
        with pytest.raises(ValueError, match="BOOKMARK navigation requires bookmark"):
            NavigationSpec(kind=NavKind.BOOKMARK, href="https://example.com")

        # Custom show kind without custom show
        with pytest.raises(ValueError, match="CUSTOM_SHOW navigation requires custom_show"):
            NavigationSpec(kind=NavKind.CUSTOM_SHOW, href="https://example.com")

    def test_slide_target_validation(self):
        """Test slide target validation."""
        # Valid slide index
        target = SlideTarget(index=1)
        assert target.index == 1

        # Invalid slide index (too low)
        with pytest.raises(ValueError, match="Slide index must be >= 1"):
            SlideTarget(index=0)

        with pytest.raises(ValueError, match="Slide index must be >= 1"):
            SlideTarget(index=-1)

    def test_bookmark_target_validation(self):
        """Test bookmark target validation."""
        # Valid bookmark name
        target = BookmarkTarget(name="intro")
        assert target.name == "intro"

        # Empty bookmark name
        with pytest.raises(ValueError, match="Bookmark name cannot be empty"):
            BookmarkTarget(name="")

        with pytest.raises(ValueError, match="Bookmark name cannot be empty"):
            BookmarkTarget(name="   ")

        # Too long bookmark name
        with pytest.raises(ValueError, match="Bookmark name too long"):
            BookmarkTarget(name="x" * 256)

    def test_custom_show_target_validation(self):
        """Test custom show target validation."""
        # Valid custom show name
        target = CustomShowTarget(name="SalesDeck")
        assert target.name == "SalesDeck"

        # Empty custom show name
        with pytest.raises(ValueError, match="Custom show name cannot be empty"):
            CustomShowTarget(name="")

        with pytest.raises(ValueError, match="Custom show name cannot be empty"):
            CustomShowTarget(name="   ")

        # Too long custom show name
        with pytest.raises(ValueError, match="Custom show name too long"):
            CustomShowTarget(name="x" * 256)


class TestNavigationFactoryFunctions:
    """Test factory functions for common navigation patterns."""

    def test_create_external_navigation(self):
        """Test external navigation factory."""
        nav = create_external_navigation("https://example.com", "Visit us")

        assert nav.kind == NavKind.EXTERNAL
        assert nav.href == "https://example.com"
        assert nav.tooltip == "Visit us"
        assert nav.visited is True

        # Test with minimal parameters
        nav_minimal = create_external_navigation("mailto:test@example.com")
        assert nav_minimal.href == "mailto:test@example.com"
        assert nav_minimal.tooltip is None

        # Test validation
        with pytest.raises(ValueError, match="External href cannot be empty"):
            create_external_navigation("")

        with pytest.raises(ValueError, match="Invalid URL scheme"):
            create_external_navigation("not-a-url")

    def test_create_slide_navigation(self):
        """Test slide navigation factory."""
        nav = create_slide_navigation(5, "Go to slide 5")

        assert nav.kind == NavKind.SLIDE
        assert nav.slide.index == 5
        assert nav.tooltip == "Go to slide 5"
        assert nav.visited is True

        # Test with minimal parameters
        nav_minimal = create_slide_navigation(1)
        assert nav_minimal.slide.index == 1
        assert nav_minimal.tooltip is None

    def test_create_action_navigation(self):
        """Test action navigation factory."""
        nav = create_action_navigation(JumpAction.NEXT, "Next slide")

        assert nav.kind == NavKind.ACTION
        assert nav.action == JumpAction.NEXT
        assert nav.tooltip == "Next slide"
        assert nav.visited is True

        # Test all action types
        for action in JumpAction:
            nav_action = create_action_navigation(action)
            assert nav_action.action == action

    def test_create_bookmark_navigation(self):
        """Test bookmark navigation factory."""
        nav = create_bookmark_navigation("intro", "Jump to intro")

        assert nav.kind == NavKind.BOOKMARK
        assert nav.bookmark.name == "intro"
        assert nav.tooltip == "Jump to intro"
        assert nav.visited is True

        # Test whitespace handling
        nav_stripped = create_bookmark_navigation("  spaced  ")
        assert nav_stripped.bookmark.name == "spaced"

    def test_create_custom_show_navigation(self):
        """Test custom show navigation factory."""
        nav = create_custom_show_navigation("SalesDeck", "Sales presentation")

        assert nav.kind == NavKind.CUSTOM_SHOW
        assert nav.custom_show.name == "SalesDeck"
        assert nav.tooltip == "Sales presentation"
        assert nav.visited is True

        # Test whitespace handling
        nav_stripped = create_custom_show_navigation("  ShowName  ")
        assert nav_stripped.custom_show.name == "ShowName"


class TestBackwardCompatibility:
    """Test backward compatibility with HyperlinkSpec."""

    def test_navigation_from_hyperlink_spec(self):
        """Test conversion from HyperlinkSpec to NavigationSpec."""
        # External hyperlink
        hyperlink = HyperlinkSpec(href="https://example.com", tooltip="Visit us")
        nav = navigation_from_hyperlink_spec(hyperlink)

        assert nav.kind == NavKind.EXTERNAL
        assert nav.href == "https://example.com"
        assert nav.tooltip == "Visit us"

        # Internal slide link
        slide_hyperlink = HyperlinkSpec(href="slide:3", tooltip="Go to slide 3")
        slide_nav = navigation_from_hyperlink_spec(slide_hyperlink)

        assert slide_nav.kind == NavKind.SLIDE
        assert slide_nav.slide.index == 3
        assert slide_nav.tooltip == "Go to slide 3"

        # Email link
        email_hyperlink = HyperlinkSpec(href="mailto:test@example.com")
        email_nav = navigation_from_hyperlink_spec(email_hyperlink)

        assert email_nav.kind == NavKind.EXTERNAL
        assert email_nav.href == "mailto:test@example.com"

    def test_navigation_from_hyperlink_spec_validation(self):
        """Test validation in hyperlink to navigation conversion."""
        # Invalid input type
        with pytest.raises(ValueError, match="Expected HyperlinkSpec"):
            navigation_from_hyperlink_spec("not a hyperlink spec")

        # Invalid slide reference falls back to external
        invalid_slide = HyperlinkSpec(href="slide:invalid", tooltip="Bad slide")
        nav = navigation_from_hyperlink_spec(invalid_slide)
        assert nav.kind == NavKind.EXTERNAL
        assert nav.href == "slide:invalid"


class TestSVGNavigationParsing:
    """Test SVG attribute parsing for navigation."""

    def test_parse_data_slide_attribute(self):
        """Test parsing data-slide attribute."""
        nav = parse_svg_navigation(None, {"data-slide": "5"}, "Go to slide 5")

        assert nav is not None
        assert nav.kind == NavKind.SLIDE
        assert nav.slide.index == 5
        assert nav.tooltip == "Go to slide 5"

        # Invalid slide index
        nav_invalid = parse_svg_navigation(None, {"data-slide": "invalid"})
        assert nav_invalid is None

    def test_parse_data_jump_attribute(self):
        """Test parsing data-jump attribute."""
        nav = parse_svg_navigation(None, {"data-jump": "next"}, "Next slide")

        assert nav is not None
        assert nav.kind == NavKind.ACTION
        assert nav.action == JumpAction.NEXT
        assert nav.tooltip == "Next slide"

        # Test all jump actions
        for action in JumpAction:
            nav_action = parse_svg_navigation(None, {"data-jump": action.value})
            assert nav_action.action == action

        # Case insensitive (enum values are lowercase)
        nav_upper = parse_svg_navigation(None, {"data-jump": "PREVIOUSSLIDE"})
        assert nav_upper.action == JumpAction.PREVIOUS

        # Invalid action
        nav_invalid = parse_svg_navigation(None, {"data-jump": "invalid"})
        assert nav_invalid is None

    def test_parse_data_bookmark_attribute(self):
        """Test parsing data-bookmark attribute."""
        nav = parse_svg_navigation(None, {"data-bookmark": "intro"}, "Jump to intro")

        assert nav is not None
        assert nav.kind == NavKind.BOOKMARK
        assert nav.bookmark.name == "intro"
        assert nav.tooltip == "Jump to intro"

        # Empty bookmark
        nav_empty = parse_svg_navigation(None, {"data-bookmark": ""})
        assert nav_empty is None

        nav_whitespace = parse_svg_navigation(None, {"data-bookmark": "   "})
        assert nav_whitespace is None

    def test_parse_data_custom_show_attribute(self):
        """Test parsing data-custom-show attribute."""
        nav = parse_svg_navigation(None, {"data-custom-show": "SalesDeck"}, "Sales presentation")

        assert nav is not None
        assert nav.kind == NavKind.CUSTOM_SHOW
        assert nav.custom_show.name == "SalesDeck"
        assert nav.tooltip == "Sales presentation"

        # Empty custom show
        nav_empty = parse_svg_navigation(None, {"data-custom-show": ""})
        assert nav_empty is None

    def test_parse_href_fallback(self):
        """Test fallback to href-based parsing."""
        # External URL
        nav = parse_svg_navigation("https://example.com", {}, "Visit us")

        assert nav is not None
        assert nav.kind == NavKind.EXTERNAL
        assert nav.href == "https://example.com"
        assert nav.tooltip == "Visit us"

        # Internal slide reference
        nav_slide = parse_svg_navigation("slide:3", {}, "Go to slide 3")

        assert nav_slide is not None
        assert nav_slide.kind == NavKind.SLIDE
        assert nav_slide.slide.index == 3

        # Bookmark reference
        nav_bookmark = parse_svg_navigation("#intro", {}, "Jump to intro")

        assert nav_bookmark is not None
        assert nav_bookmark.kind == NavKind.BOOKMARK
        assert nav_bookmark.bookmark.name == "intro"

        # Invalid href
        nav_invalid = parse_svg_navigation("", {})
        assert nav_invalid is None

    def test_parse_attribute_precedence(self):
        """Test that data attributes take precedence over href."""
        # data-slide should override href
        nav = parse_svg_navigation(
            "https://example.com",
            {"data-slide": "5"},
            "Should be slide navigation"
        )

        assert nav.kind == NavKind.SLIDE
        assert nav.slide.index == 5

        # data-jump should override href
        nav_action = parse_svg_navigation(
            "slide:3",
            {"data-jump": "next"},
            "Should be action navigation"
        )

        assert nav_action.kind == NavKind.ACTION
        assert nav_action.action == JumpAction.NEXT


class TestNavigationUtilities:
    """Test navigation utility functions."""

    def test_validate_navigation_spec(self):
        """Test navigation spec validation utility."""
        # Valid external navigation
        valid_external = create_external_navigation("https://example.com")
        assert validate_navigation_spec(valid_external) is True

        # Valid slide navigation
        valid_slide = create_slide_navigation(5)
        assert validate_navigation_spec(valid_slide) is True

        # Valid action navigation
        valid_action = create_action_navigation(JumpAction.NEXT)
        assert validate_navigation_spec(valid_action) is True

        # Valid bookmark navigation
        valid_bookmark = create_bookmark_navigation("intro")
        assert validate_navigation_spec(valid_bookmark) is True

        # Valid custom show navigation
        valid_custom = create_custom_show_navigation("SalesDeck")
        assert validate_navigation_spec(valid_custom) is True

        # Invalid input
        assert validate_navigation_spec("not a navigation spec") is False
        assert validate_navigation_spec(None) is False

    def test_get_navigation_summary(self):
        """Test navigation summary statistics."""
        # Empty list
        summary = get_navigation_summary([])
        assert summary['total'] == 0
        assert summary['by_kind'] == {}
        assert summary['requires_relationships'] == 0
        assert summary['uses_action_uris'] == 0
        assert summary['has_tooltips'] == 0

        # Mixed navigation types
        nav_specs = [
            create_external_navigation("https://example.com", "External link"),
            create_slide_navigation(5, "Slide jump"),
            create_action_navigation(JumpAction.NEXT),
            create_bookmark_navigation("intro", "Bookmark"),
            create_custom_show_navigation("SalesDeck")
        ]

        summary = get_navigation_summary(nav_specs)
        assert summary['total'] == 5
        assert summary['by_kind']['external'] == 1
        assert summary['by_kind']['slide'] == 1
        assert summary['by_kind']['action'] == 1
        assert summary['by_kind']['bookmark'] == 1
        assert summary['by_kind']['custom_show'] == 1
        assert summary['requires_relationships'] == 2  # external + slide
        assert summary['uses_action_uris'] == 3  # action + bookmark + custom_show
        assert summary['has_tooltips'] == 3  # external + slide + bookmark

    def test_get_target_description(self):
        """Test navigation target description generation."""
        external_nav = create_external_navigation("https://example.com")
        assert external_nav.get_target_description() == "External: https://example.com"

        slide_nav = create_slide_navigation(5)
        assert slide_nav.get_target_description() == "Slide: 5"

        action_nav = create_action_navigation(JumpAction.NEXT)
        assert action_nav.get_target_description() == "Action: nextslide"

        bookmark_nav = create_bookmark_navigation("intro")
        assert bookmark_nav.get_target_description() == "Bookmark: intro"

        custom_nav = create_custom_show_navigation("SalesDeck")
        assert custom_nav.get_target_description() == "Custom Show: SalesDeck"


class TestNavigationSpecMethods:
    """Test NavigationSpec utility methods."""

    def test_navigation_type_detection(self):
        """Test navigation type detection methods."""
        external_nav = create_external_navigation("https://example.com")
        assert external_nav.is_external_link() is True
        assert external_nav.is_slide_jump() is False
        assert external_nav.is_action_based() is False
        assert external_nav.requires_relationship() is True

        slide_nav = create_slide_navigation(5)
        assert slide_nav.is_external_link() is False
        assert slide_nav.is_slide_jump() is True
        assert slide_nav.is_action_based() is False
        assert slide_nav.requires_relationship() is True

        action_nav = create_action_navigation(JumpAction.NEXT)
        assert action_nav.is_external_link() is False
        assert action_nav.is_slide_jump() is False
        assert action_nav.is_action_based() is True
        assert action_nav.requires_relationship() is False

        bookmark_nav = create_bookmark_navigation("intro")
        assert bookmark_nav.is_external_link() is False
        assert bookmark_nav.is_slide_jump() is False
        assert bookmark_nav.is_action_based() is True
        assert bookmark_nav.requires_relationship() is False

        custom_nav = create_custom_show_navigation("SalesDeck")
        assert custom_nav.is_external_link() is False
        assert custom_nav.is_slide_jump() is False
        assert custom_nav.is_action_based() is True
        assert custom_nav.requires_relationship() is False