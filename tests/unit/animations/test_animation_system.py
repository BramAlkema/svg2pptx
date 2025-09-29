#!/usr/bin/env python3
"""
Tests for the new modular animation system.

This test file verifies the functionality of the new src/animations/ system
and ensures it provides the same capabilities as the old monolithic system.
"""

import pytest
from lxml import etree as ET
from unittest.mock import MagicMock, patch, Mock

from src.animations import (
    AnimationBuilder, AnimationComposer,
    AnimationType, FillMode, TransformType, CalcMode,
    AnimationTiming, AnimationDefinition, AnimationScene,
    create_animation_converter, parse_svg_animations
)
from src.converters.animation_converter import AnimationConverter
from src.services.conversion_services import ConversionServices


@pytest.fixture
def mock_services():
    """Create mock ConversionServices for testing."""
    services = Mock(spec=ConversionServices)
    services.logger = Mock()
    services.logger.warning = Mock()
    services.logger.error = Mock()
    return services


@pytest.fixture
def animation_converter(mock_services):
    """Create AnimationConverter instance for testing."""
    return AnimationConverter(services=mock_services)


@pytest.fixture
def sample_svg_with_animations():
    """Create sample SVG with various animation types."""
    svg_content = '''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect id="rect1" x="10" y="10" width="20" height="20" fill="red">
            <animate attributeName="opacity" values="0;1" dur="2s" />
            <animateTransform attributeName="transform" type="scale"
                            values="1;1.5" dur="1s" begin="2s" />
        </rect>
        <circle id="circle1" cx="50" cy="50" r="10" fill="blue">
            <animateColor attributeName="fill" values="blue;red" dur="3s" />
        </circle>
    </svg>
    '''
    return ET.fromstring(svg_content)


class TestAnimationSystem:
    """Test the core animation system functionality."""

    def test_animation_converter_initialization(self, mock_services):
        """Test AnimationConverter initialization."""
        converter = AnimationConverter(services=mock_services)
        assert converter.services == mock_services
        assert converter.parser is not None

    def test_parse_svg_animations(self, sample_svg_with_animations):
        """Test parsing animations from SVG."""
        animations = parse_svg_animations(sample_svg_with_animations)

        assert len(animations) == 3  # opacity, scale, color animations

        # Check animation types
        animation_types = [anim.animation_type for anim in animations]
        assert AnimationType.ANIMATE in animation_types
        assert AnimationType.ANIMATE_TRANSFORM in animation_types
        assert AnimationType.ANIMATE_COLOR in animation_types

    def test_convert_svg_animations(self, animation_converter, sample_svg_with_animations):
        """Test converting SVG animations to PowerPoint format."""
        result = animation_converter.convert_svg_animations(sample_svg_with_animations)

        assert result.success is True
        assert result.powerpoint_xml != ""
        assert len(result.timeline_scenes) > 0
        assert result.summary.total_animations == 3

    def test_animation_statistics(self, animation_converter, sample_svg_with_animations):
        """Test animation statistics generation."""
        stats = animation_converter.get_animation_statistics(sample_svg_with_animations)

        assert stats['total_animations'] == 3
        assert stats['unique_elements'] == 2  # rect1 and circle1
        assert 'complexity' in stats
        assert 'features' in stats

    def test_animation_validation(self, animation_converter, sample_svg_with_animations):
        """Test animation validation."""
        is_valid, issues = animation_converter.validate_svg_for_animations(sample_svg_with_animations)

        assert is_valid is True
        assert len(issues) == 0

    def test_animation_data_export(self, animation_converter, sample_svg_with_animations):
        """Test animation data export."""
        json_data = animation_converter.export_animation_data(sample_svg_with_animations, 'json')

        assert '"animations"' in json_data
        assert '"summary"' in json_data
        assert json_data != ""


class TestAnimationBuilder:
    """Test the fluent animation builder API."""

    def test_basic_animation_building(self):
        """Test building a basic animation."""
        animation = (AnimationBuilder()
                    .target("rect1")
                    .animate("opacity")
                    .from_to("0", "1")
                    .duration("2s")
                    .build())

        assert animation.element_id == "rect1"
        assert animation.animation_type == AnimationType.ANIMATE
        assert animation.target_attribute == "opacity"
        assert animation.values == ["0", "1"]
        assert animation.timing.duration == 2.0

    def test_transform_animation_building(self):
        """Test building a transform animation."""
        animation = (AnimationBuilder()
                    .target("rect1")
                    .animate_transform("scale")
                    .from_to("1", "1.5")
                    .duration("1s")
                    .delay("0.5s")
                    .build())

        assert animation.animation_type == AnimationType.ANIMATE_TRANSFORM
        assert animation.transform_type == TransformType.SCALE
        assert animation.timing.begin == 0.5

    def test_easing_animation_building(self):
        """Test building animation with easing."""
        animation = (AnimationBuilder()
                    .target("rect1")
                    .animate("opacity")
                    .from_to("0", "1")
                    .duration("2s")
                    .with_easing("ease-in-out")
                    .build())

        assert animation.calc_mode == CalcMode.SPLINE
        assert animation.key_splines is not None
        assert len(animation.key_splines[0]) == 4

    def test_color_animation_building(self):
        """Test building a color animation."""
        animation = (AnimationBuilder()
                    .target("circle1")
                    .animate_color("fill")
                    .from_to("red", "blue")
                    .duration("3s")
                    .build())

        assert animation.animation_type == AnimationType.ANIMATE_COLOR
        assert animation.target_attribute == "fill"
        assert animation.values == ["red", "blue"]

    def test_repeat_animation_building(self):
        """Test building animation with repeat."""
        animation = (AnimationBuilder()
                    .target("rect1")
                    .animate("opacity")
                    .from_to("0", "1")
                    .duration("1s")
                    .repeat("indefinite")
                    .build())

        assert animation.timing.repeat_count == "indefinite"

    def test_animation_validation_errors(self):
        """Test animation builder validation."""
        builder = AnimationBuilder()

        # Missing required fields should raise ValueError
        with pytest.raises(ValueError, match="Target element ID is required"):
            builder.build()

        builder.target("rect1")
        with pytest.raises(ValueError, match="Animation type is required"):
            builder.build()


class TestAnimationComposer:
    """Test the high-level animation composer."""

    def test_fade_in_animation(self):
        """Test creating fade in animation."""
        composer = AnimationComposer()
        animations = composer.fade_in("rect1", "2s").build()

        assert len(animations) == 1
        animation = animations[0]
        assert animation.element_id == "rect1"
        assert animation.target_attribute == "opacity"
        assert animation.values == ["0", "1"]

    def test_animation_sequence(self):
        """Test creating animation sequence."""
        composer = AnimationComposer()
        animations = (composer
                     .fade_in("rect1", "1s")
                     .then_after("0.5s")
                     .scale_up("rect1", "1s")
                     .build())

        assert len(animations) == 2
        assert animations[1].timing.begin == 1.5  # 1s + 0.5s delay

    def test_simultaneous_animations(self):
        """Test creating simultaneous animations."""
        composer = AnimationComposer()
        animations = (composer
                     .fade_in("rect1", "2s")
                     .simultaneously()
                     .color_change("rect1", "2s", "red", "blue")
                     .build())

        assert len(animations) == 2
        assert animations[0].timing.begin == animations[1].timing.begin


class TestAnimationTiming:
    """Test animation timing functionality."""

    def test_timing_calculation(self):
        """Test animation timing calculations."""
        timing = AnimationTiming(begin=1.0, duration=2.0, repeat_count=3)

        assert timing.get_end_time() == 7.0  # 1 + (2 * 3)
        assert timing.is_active_at_time(0.5) is False
        assert timing.is_active_at_time(2.0) is True
        assert timing.is_active_at_time(8.0) is False

    def test_indefinite_timing(self):
        """Test indefinite animation timing."""
        timing = AnimationTiming(begin=0.0, duration=1.0, repeat_count="indefinite")

        assert timing.get_end_time() == float('inf')
        assert timing.is_active_at_time(100.0) is True

    def test_local_time_calculation(self):
        """Test local time calculation."""
        timing = AnimationTiming(begin=1.0, duration=2.0, repeat_count=1, fill_mode=FillMode.FREEZE)

        assert timing.get_local_time(0.5) == 0.0  # Before start
        assert timing.get_local_time(2.0) == 0.5  # Halfway through
        assert timing.get_local_time(3.0) == 1.0  # At end (with freeze mode)


class TestBackwardCompatibility:
    """Test backward compatibility with old animation system."""

    def test_animation_types_compatibility(self):
        """Test that animation types match old system."""
        # These should match the old AnimationType enum values
        assert AnimationType.ANIMATE.value == "animate"
        assert AnimationType.ANIMATE_TRANSFORM.value == "animateTransform"
        assert AnimationType.ANIMATE_COLOR.value == "animateColor"
        assert AnimationType.ANIMATE_MOTION.value == "animateMotion"
        assert AnimationType.SET.value == "set"

    def test_fill_mode_compatibility(self):
        """Test that fill modes match old system."""
        assert FillMode.REMOVE.value == "remove"
        assert FillMode.FREEZE.value == "freeze"

    def test_transform_type_compatibility(self):
        """Test that transform types match old system."""
        assert TransformType.TRANSLATE.value == "translate"
        assert TransformType.SCALE.value == "scale"
        assert TransformType.ROTATE.value == "rotate"

    def test_convenience_functions(self):
        """Test module-level convenience functions."""
        # Test that convenience functions work
        converter = create_animation_converter()
        assert converter is not None

        # Test parsing function
        svg_content = '<svg><rect><animate attributeName="opacity" dur="1s"/></rect></svg>'
        svg_element = ET.fromstring(svg_content)
        animations = parse_svg_animations(svg_element)
        assert isinstance(animations, list)


if __name__ == "__main__":
    pytest.main([__file__])