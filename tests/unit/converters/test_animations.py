#!/usr/bin/env python3

import pytest
from lxml import etree as ET
from unittest.mock import MagicMock, patch, Mock
import math

from src.converters.animations import (
    AnimationConverter, AnimationType, FillMode, TransformType,
    AnimationTiming, AnimationKeyframe, AnimationDefinition, AnimationScene
)

# Mock the dependencies
class MockConversionContext:
    def __init__(self):
        self.properties = {}

class MockColorParser:
    class MockColor:
        def __init__(self, red=255, green=255, blue=255, alpha=1.0):
            self.red = red
            self.green = green
            self.blue = blue
            self.alpha = alpha
    
    def parse(self, color_str):
        if color_str == "red":
            return self.MockColor(255, 0, 0, 1.0)
        elif color_str == "blue":
            return self.MockColor(0, 0, 255, 1.0)
        elif color_str == "green":
            return self.MockColor(0, 255, 0, 1.0)
        return self.MockColor()

class TestAnimationType:
    """Test AnimationType enum."""
    
    def test_animation_types(self):
        """Test all animation type values."""
        assert AnimationType.ANIMATE.value == "animate"
        assert AnimationType.ANIMATE_TRANSFORM.value == "animateTransform"
        assert AnimationType.ANIMATE_COLOR.value == "animateColor"
        assert AnimationType.ANIMATE_MOTION.value == "animateMotion"
        assert AnimationType.SET.value == "set"

class TestFillMode:
    """Test FillMode enum."""
    
    def test_fill_modes(self):
        """Test fill mode values."""
        assert FillMode.REMOVE.value == "remove"
        assert FillMode.FREEZE.value == "freeze"

class TestTransformType:
    """Test TransformType enum."""
    
    def test_transform_types(self):
        """Test all transform type values."""
        assert TransformType.TRANSLATE.value == "translate"
        assert TransformType.SCALE.value == "scale"
        assert TransformType.ROTATE.value == "rotate"
        assert TransformType.SKEWX.value == "skewX"
        assert TransformType.SKEWY.value == "skewY"

class TestAnimationTiming:
    """Test AnimationTiming dataclass."""
    
    def test_creation(self):
        """Test creating AnimationTiming."""
        timing = AnimationTiming(
            begin=1.0,
            duration=2.0,
            repeat_count=3,
            fill_mode=FillMode.FREEZE
        )
        
        assert timing.begin == 1.0
        assert timing.duration == 2.0
        assert timing.repeat_count == 3
        assert timing.fill_mode == FillMode.FREEZE
    
    def test_get_end_time_finite(self):
        """Test getting end time with finite repeat count."""
        timing = AnimationTiming(
            begin=1.0,
            duration=2.0,
            repeat_count=3,
            fill_mode=FillMode.FREEZE
        )
        
        assert timing.get_end_time() == 7.0  # 1 + 2*3
    
    def test_get_end_time_indefinite(self):
        """Test getting end time with indefinite repeat count."""
        timing = AnimationTiming(
            begin=1.0,
            duration=2.0,
            repeat_count="indefinite",
            fill_mode=FillMode.FREEZE
        )
        
        assert timing.get_end_time() == float('inf')
    
    def test_get_end_time_single(self):
        """Test getting end time without repeat count."""
        timing = AnimationTiming(
            begin=1.0,
            duration=2.0,
            repeat_count=1,
            fill_mode=FillMode.REMOVE
        )
        
        assert timing.get_end_time() == 3.0  # 1 + 2

class TestAnimationDefinition:
    """Test AnimationDefinition class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.timing = AnimationTiming(
            begin=0.0,
            duration=2.0,
            repeat_count=1,
            fill_mode=FillMode.FREEZE
        )
        
        self.animation_def = AnimationDefinition(
            element_id="test_elem",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["0", "1"],
            key_times=None,
            key_splines=None,
            timing=self.timing,
            transform_type=None
        )
    
    def test_creation(self):
        """Test creating AnimationDefinition."""
        assert self.animation_def.element_id == "test_elem"
        assert self.animation_def.animation_type == AnimationType.ANIMATE
        assert self.animation_def.target_attribute == "opacity"
        assert self.animation_def.values == ["0", "1"]
    
    def test_get_value_at_time_before_begin(self):
        """Test getting value before animation begins."""
        value = self.animation_def.get_value_at_time(-1.0)
        assert value is None
    
    def test_get_value_at_time_single_value(self):
        """Test getting value with single animation value."""
        single_value_anim = AnimationDefinition(
            element_id="test",
            animation_type=AnimationType.SET,
            target_attribute="fill",
            values=["red"],
            key_times=None,
            key_splines=None,
            timing=self.timing,
            transform_type=None
        )
        
        value = single_value_anim.get_value_at_time(1.0)
        assert value == "red"
    
    def test_get_value_at_time_no_values(self):
        """Test getting value with no animation values."""
        empty_anim = AnimationDefinition(
            element_id="test",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=[],
            key_times=None,
            key_splines=None,
            timing=self.timing,
            transform_type=None
        )
        
        value = empty_anim.get_value_at_time(1.0)
        assert value is None
    
    def test_get_value_at_time_zero_duration(self):
        """Test getting value with zero duration."""
        zero_duration_timing = AnimationTiming(0.0, 0.0, 1, FillMode.FREEZE)
        zero_anim = AnimationDefinition(
            element_id="test",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["0", "1"],
            key_times=None,
            key_splines=None,
            timing=zero_duration_timing,
            transform_type=None
        )
        
        value = zero_anim.get_value_at_time(1.0)
        assert value == "1"
    
    def test_get_value_at_time_linear_interpolation(self):
        """Test linear interpolation between values."""
        value = self.animation_def.get_value_at_time(1.0)  # Middle of animation
        # Should interpolate between "0" and "1" for opacity
        assert isinstance(value, str)
    
    def test_get_value_at_time_with_key_times(self):
        """Test interpolation with specified key times."""
        keyed_anim = AnimationDefinition(
            element_id="test",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["0", "0.5", "1"],
            key_times=[0.0, 0.3, 1.0],
            key_splines=None,
            timing=self.timing,
            transform_type=None
        )
        
        value = keyed_anim.get_value_at_time(0.6)  # 30% through duration (key time 0.3)
        assert isinstance(value, str)
    
    @patch('src.converters.animations.ColorParser', MockColorParser)
    def test_interpolate_colors(self):
        """Test color interpolation."""
        color_anim = AnimationDefinition(
            element_id="test",
            animation_type=AnimationType.ANIMATE_COLOR,
            target_attribute="fill",
            values=["red", "blue"],
            key_times=None,
            key_splines=None,
            timing=self.timing,
            transform_type=None
        )
        
        result = color_anim._interpolate_colors("red", "blue", 0.5)
        assert "rgba(" in result
    
    def test_interpolate_numeric_values(self):
        """Test numeric value interpolation."""
        opacity_result = self.animation_def._interpolate_values("0", "1", 0.5)
        assert opacity_result == "0.5"
    
    def test_interpolate_numeric_values_invalid(self):
        """Test numeric interpolation with invalid values."""
        result = self.animation_def._interpolate_values("invalid", "1", 0.5)
        assert result == "invalid"
    
    def test_interpolate_transform_values_translate(self):
        """Test transform value interpolation for translate."""
        transform_anim = AnimationDefinition(
            element_id="test",
            animation_type=AnimationType.ANIMATE_TRANSFORM,
            target_attribute="transform",
            values=["translate(0, 0)", "translate(100, 50)"],
            key_times=None,
            key_splines=None,
            timing=self.timing,
            transform_type=TransformType.TRANSLATE
        )
        
        result = transform_anim._interpolate_transform_values(
            "translate(0, 0)", "translate(100, 50)", 0.5
        )
        assert "translate(50.0, 25.0)" == result
    
    def test_interpolate_transform_values_scale(self):
        """Test transform value interpolation for scale."""
        transform_anim = AnimationDefinition(
            element_id="test",
            animation_type=AnimationType.ANIMATE_TRANSFORM,
            target_attribute="transform",
            values=["scale(1)", "scale(2)"],
            key_times=None,
            key_splines=None,
            timing=self.timing,
            transform_type=TransformType.SCALE
        )
        
        result = transform_anim._interpolate_transform_values("scale(1)", "scale(2)", 0.5)
        assert "scale(1.5)" == result
    
    def test_interpolate_transform_values_rotate(self):
        """Test transform value interpolation for rotate."""
        transform_anim = AnimationDefinition(
            element_id="test",
            animation_type=AnimationType.ANIMATE_TRANSFORM,
            target_attribute="transform",
            values=["rotate(0)", "rotate(90)"],
            key_times=None,
            key_splines=None,
            timing=self.timing,
            transform_type=TransformType.ROTATE
        )
        
        result = transform_anim._interpolate_transform_values("rotate(0)", "rotate(90)", 0.5)
        assert "rotate(45.0)" == result
    
    def test_interpolate_transform_values_invalid(self):
        """Test transform interpolation with invalid values."""
        transform_anim = AnimationDefinition(
            element_id="test",
            animation_type=AnimationType.ANIMATE_TRANSFORM,
            target_attribute="transform",
            values=["invalid", "transform"],
            key_times=None,
            key_splines=None,
            timing=self.timing,
            transform_type=TransformType.TRANSLATE
        )
        
        result = transform_anim._interpolate_transform_values("invalid", "transform", 0.3)
        assert result == "invalid"  # Should return first value for t < 0.5
    
    def test_interpolate_discrete_values(self):
        """Test discrete value interpolation for unsupported attributes."""
        anim = AnimationDefinition(
            element_id="test",
            animation_type=AnimationType.ANIMATE,
            target_attribute="unknown_attr",
            values=["value1", "value2"],
            key_times=None,
            key_splines=None,
            timing=self.timing,
            transform_type=None
        )
        
        result = anim._interpolate_values("value1", "value2", 0.3)
        assert result == "value1"  # t < 0.5
        
        result = anim._interpolate_values("value1", "value2", 0.7)
        assert result == "value2"  # t >= 0.5

class TestAnimationScene:
    """Test AnimationScene dataclass."""
    
    def test_creation(self):
        """Test creating AnimationScene."""
        scene = AnimationScene(
            time=1.5,
            element_states={
                "elem1": {"opacity": "0.5", "fill": "red"},
                "elem2": {"transform": "scale(1.2)"}
            }
        )
        
        assert scene.time == 1.5
        assert scene.element_states["elem1"]["opacity"] == "0.5"
        assert scene.element_states["elem2"]["transform"] == "scale(1.2)"

class TestableAnimationConverter(AnimationConverter):
    """Testable version of AnimationConverter with required abstract methods."""
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the given element."""
        tag = element.tag.split('}')[-1]  # Remove namespace
        return tag in self.supported_elements

class TestAnimationConverter:
    """Test AnimationConverter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.converter = TestableAnimationConverter()
        self.context = MockConversionContext()
    
    def test_init(self):
        """Test AnimationConverter initialization."""
        assert len(self.converter.animations) == 0
        assert self.converter.max_keyframes == 30
        assert self.converter.frame_rate == 24
        assert self.converter.static_time == 0.5
        assert "animate" in self.converter.supported_elements
        assert "animateTransform" in self.converter.supported_elements
    
    def test_can_convert(self):
        """Test can_convert method."""
        animate_elem = ET.Element("animate")
        transform_elem = ET.Element("animateTransform")
        rect_elem = ET.Element("rect")
        
        assert self.converter.can_convert(animate_elem) is True
        assert self.converter.can_convert(transform_elem) is True
        assert self.converter.can_convert(rect_elem) is False
    
    def test_convert_empty_animation(self):
        """Test converting invalid animation element."""
        elem = ET.Element("invalid")
        result = self.converter.convert(elem, self.context)
        
        assert result == ""
        assert len(self.converter.animations) == 0
    
    def test_convert_valid_animation(self):
        """Test converting valid animation element."""
        # Create proper parent-child relationship with lxml
        parent = ET.Element("rect")
        parent.set("id", "test_rect")
        elem = ET.SubElement(parent, "animate")
        elem.set("attributeName", "opacity")
        elem.set("from", "0")
        elem.set("to", "1")
        elem.set("dur", "2s")
        
        result = self.converter.convert(elem, self.context)
        
        assert result == ""
        assert len(self.converter.animations) == 1
        assert self.converter.animations[0].element_id == "test_rect"
    
    def test_parse_animation_timing_defaults(self):
        """Test parsing animation timing with default values."""
        elem = ET.Element("animate")
        timing = self.converter._parse_animation_timing(elem)
        
        assert timing.begin == 0.0
        assert timing.duration == 1.0
        assert timing.repeat_count == 1
        assert timing.fill_mode == FillMode.REMOVE
    
    def test_parse_animation_timing_custom(self):
        """Test parsing custom animation timing."""
        elem = ET.Element("animate")
        elem.set("begin", "1.5s")
        elem.set("dur", "3s")
        elem.set("repeatCount", "2")
        elem.set("fill", "freeze")
        
        timing = self.converter._parse_animation_timing(elem)
        
        assert timing.begin == 1.5
        assert timing.duration == 3.0
        assert timing.repeat_count == 2
        assert timing.fill_mode == FillMode.FREEZE
    
    def test_parse_animation_timing_indefinite(self):
        """Test parsing indefinite repeat count."""
        elem = ET.Element("animate")
        elem.set("repeatCount", "indefinite")
        
        timing = self.converter._parse_animation_timing(elem)
        assert timing.repeat_count == "indefinite"
    
    def test_parse_time_value_seconds(self):
        """Test parsing time values in seconds."""
        assert self.converter._parse_time_value("2s") == 2.0
        assert self.converter._parse_time_value("1.5s") == 1.5
    
    def test_parse_time_value_milliseconds(self):
        """Test parsing time values in milliseconds."""
        assert self.converter._parse_time_value("2000ms") == 2.0
        assert self.converter._parse_time_value("500ms") == 0.5
    
    def test_parse_time_value_minutes(self):
        """Test parsing time values in minutes."""
        assert self.converter._parse_time_value("2min") == 120.0
        assert self.converter._parse_time_value("0.5min") == 30.0
    
    def test_parse_time_value_hours(self):
        """Test parsing time values in hours."""
        assert self.converter._parse_time_value("1h") == 3600.0
        assert self.converter._parse_time_value("0.5h") == 1800.0
    
    def test_parse_time_value_no_unit(self):
        """Test parsing time values without units."""
        assert self.converter._parse_time_value("2") == 2.0
        assert self.converter._parse_time_value("1.5") == 1.5
    
    def test_parse_time_value_invalid(self):
        """Test parsing invalid time values."""
        assert self.converter._parse_time_value("invalid") == 0.0
        assert self.converter._parse_time_value("") == 0.0
    
    def test_find_parent_id_with_id(self):
        """Test finding parent ID when parent has ID."""
        parent = ET.Element("g")
        parent.set("id", "parent_group")
        child = ET.SubElement(parent, "animate")
        
        parent_id = self.converter._find_parent_id(child)
        assert parent_id == "parent_group"
    
    def test_find_parent_id_no_id(self):
        """Test finding parent ID when parent has no ID."""
        parent = ET.Element("g")
        child = ET.SubElement(parent, "animate")
        
        parent_id = self.converter._find_parent_id(child)
        assert parent_id is None
    
    def test_find_parent_id_no_parent(self):
        """Test finding parent ID when there's no parent."""
        elem = ET.Element("animate")
        parent_id = self.converter._find_parent_id(elem)
        assert parent_id is None
    
    def test_parse_animation_element_animate(self):
        """Test parsing animate element."""
        parent = ET.Element("rect")
        parent.set("id", "test_rect")
        elem = ET.SubElement(parent, "animate")
        elem.set("attributeName", "opacity")
        elem.set("values", "0;0.5;1")
        elem.set("dur", "2s")
        elem.set("keyTimes", "0;0.3;1")
        
        anim_def = self.converter._parse_animation_element(elem)
        
        assert anim_def is not None
        assert anim_def.element_id == "test_rect"
        assert anim_def.animation_type == AnimationType.ANIMATE
        assert anim_def.target_attribute == "opacity"
        assert anim_def.values == ["0", "0.5", "1"]
        assert anim_def.key_times == [0.0, 0.3, 1.0]
    
    def test_parse_animation_element_animate_transform(self):
        """Test parsing animateTransform element."""
        parent = ET.Element("rect")
        parent.set("id", "test_rect")
        elem = ET.SubElement(parent, "animateTransform")
        elem.set("attributeName", "transform")
        elem.set("type", "translate")
        elem.set("from", "0 0")
        elem.set("to", "100 50")
        elem.set("dur", "1s")
        
        anim_def = self.converter._parse_animation_element(elem)
        
        assert anim_def is not None
        assert anim_def.animation_type == AnimationType.ANIMATE_TRANSFORM
        assert anim_def.transform_type == TransformType.TRANSLATE
        assert anim_def.values == ["0 0", "100 50"]
    
    def test_parse_animation_element_missing_attribute(self):
        """Test parsing animation element missing required attributes."""
        elem = ET.Element("animate")
        # Missing attributeName
        elem.set("from", "0")
        elem.set("to", "1")
        
        anim_def = self.converter._parse_animation_element(elem)
        assert anim_def is None
    
    def test_parse_animation_element_missing_values(self):
        """Test parsing animation element with no values."""
        elem = ET.Element("animate")
        elem.set("attributeName", "opacity")
        # No values, from, to, or by
        
        anim_def = self.converter._parse_animation_element(elem)
        assert anim_def is None
    
    def test_parse_animation_element_invalid_key_times(self):
        """Test parsing animation element with invalid key times."""
        parent = ET.Element("rect")
        parent.set("id", "test_rect")
        elem = ET.SubElement(parent, "animate")
        elem.set("attributeName", "opacity")
        elem.set("values", "0;1")
        elem.set("keyTimes", "invalid;values")
        
        anim_def = self.converter._parse_animation_element(elem)
        assert anim_def.key_times is None
    
    def test_process_animated_elements_no_animations(self):
        """Test processing with no animations."""
        result = self.converter.process_animated_elements(self.context, "static")
        assert result == {}
    
    def test_process_animated_elements_static_mode(self):
        """Test processing animations in static mode."""
        # Add a simple animation
        timing = AnimationTiming(0.0, 2.0, 1, FillMode.FREEZE)
        animation = AnimationDefinition(
            element_id="test_elem",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["0", "1"],
            key_times=None,
            key_splines=None,
            timing=timing,
            transform_type=None
        )
        self.converter.animations = [animation]
        
        result = self.converter.process_animated_elements(self.context, "static")
        
        assert "test_elem" in result
        assert "opacity" in result["test_elem"]
    
    def test_process_animated_elements_keyframes_mode(self):
        """Test processing animations in keyframes mode."""
        timing = AnimationTiming(0.0, 2.0, 1, FillMode.FREEZE)
        animation = AnimationDefinition(
            element_id="test_elem",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["0", "1"],
            key_times=None,
            key_splines=None,
            timing=timing,
            transform_type=None
        )
        self.converter.animations = [animation]
        
        result = self.converter.process_animated_elements(self.context, "keyframes")
        
        assert result["animation_type"] == "keyframe_sequence"
        assert "scenes" in result
        assert "total_duration" in result
        assert "frame_count" in result
    
    def test_process_animated_elements_powerpoint_mode(self):
        """Test processing animations in PowerPoint mode."""
        timing = AnimationTiming(0.0, 2.0, 1, FillMode.FREEZE)
        animation = AnimationDefinition(
            element_id="test_elem",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["0", "1"],
            key_times=None,
            key_splines=None,
            timing=timing,
            transform_type=None
        )
        self.converter.animations = [animation]
        
        result = self.converter.process_animated_elements(self.context, "powerpoint_animation")
        
        # Should return PowerPoint effects or fallback to static
        assert isinstance(result, dict)
    
    def test_process_animated_elements_invalid_mode(self):
        """Test processing animations with invalid mode."""
        result = self.converter.process_animated_elements(self.context, "invalid_mode")
        assert result == {}
    
    def test_map_to_powerpoint_effect_fade_in(self):
        """Test mapping fade in animation to PowerPoint."""
        timing = AnimationTiming(0.5, 2.0, 1, FillMode.FREEZE)
        animation = AnimationDefinition(
            element_id="test_elem",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["0", "1"],
            key_times=None,
            key_splines=None,
            timing=timing,
            transform_type=None
        )
        
        effect = self.converter._map_to_powerpoint_effect(animation)
        
        assert effect is not None
        assert effect["type"] == "fade_in"
        assert effect["element_id"] == "test_elem"
        assert effect["duration"] == 2.0
        assert effect["delay"] == 0.5
    
    def test_map_to_powerpoint_effect_fade_out(self):
        """Test mapping fade out animation to PowerPoint."""
        timing = AnimationTiming(0.0, 2.0, 1, FillMode.FREEZE)
        animation = AnimationDefinition(
            element_id="test_elem",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["1", "0"],
            key_times=None,
            key_splines=None,
            timing=timing,
            transform_type=None
        )
        
        effect = self.converter._map_to_powerpoint_effect(animation)
        
        assert effect is not None
        assert effect["type"] == "fade_out"
    
    def test_map_to_powerpoint_effect_motion_path(self):
        """Test mapping translate animation to PowerPoint motion path."""
        timing = AnimationTiming(0.0, 2.0, 1, FillMode.FREEZE)
        animation = AnimationDefinition(
            element_id="test_elem",
            animation_type=AnimationType.ANIMATE_TRANSFORM,
            target_attribute="transform",
            values=["translate(0,0)", "translate(100,50)"],
            key_times=None,
            key_splines=None,
            timing=timing,
            transform_type=TransformType.TRANSLATE
        )
        
        effect = self.converter._map_to_powerpoint_effect(animation)
        
        assert effect is not None
        assert effect["type"] == "motion_path"
    
    def test_map_to_powerpoint_effect_scale(self):
        """Test mapping scale animation to PowerPoint."""
        timing = AnimationTiming(0.0, 2.0, 1, FillMode.FREEZE)
        animation = AnimationDefinition(
            element_id="test_elem",
            animation_type=AnimationType.ANIMATE_TRANSFORM,
            target_attribute="transform",
            values=["scale(1)", "scale(2)"],
            key_times=None,
            key_splines=None,
            timing=timing,
            transform_type=TransformType.SCALE
        )
        
        effect = self.converter._map_to_powerpoint_effect(animation)
        
        assert effect is not None
        assert effect["type"] == "scale"
    
    def test_map_to_powerpoint_effect_spin(self):
        """Test mapping rotate animation to PowerPoint spin."""
        timing = AnimationTiming(0.0, 2.0, 1, FillMode.FREEZE)
        animation = AnimationDefinition(
            element_id="test_elem",
            animation_type=AnimationType.ANIMATE_TRANSFORM,
            target_attribute="transform",
            values=["rotate(0)", "rotate(360)"],
            key_times=None,
            key_splines=None,
            timing=timing,
            transform_type=TransformType.ROTATE
        )
        
        effect = self.converter._map_to_powerpoint_effect(animation)
        
        assert effect is not None
        assert effect["type"] == "spin"
    
    def test_map_to_powerpoint_effect_unsupported(self):
        """Test mapping unsupported animation to PowerPoint."""
        timing = AnimationTiming(0.0, 2.0, 1, FillMode.FREEZE)
        animation = AnimationDefinition(
            element_id="test_elem",
            animation_type=AnimationType.ANIMATE_COLOR,
            target_attribute="fill",
            values=["red", "blue"],
            key_times=None,
            key_splines=None,
            timing=timing,
            transform_type=None
        )
        
        effect = self.converter._map_to_powerpoint_effect(animation)
        assert effect is None
    
    def test_get_animation_summary_no_animations(self):
        """Test getting animation summary with no animations."""
        summary = self.converter.get_animation_summary()
        assert summary["has_animations"] is False
    
    def test_get_animation_summary_simple(self):
        """Test getting animation summary for simple animations."""
        timing = AnimationTiming(0.0, 2.0, 1, FillMode.FREEZE)
        animations = [
            AnimationDefinition(
                element_id="elem1",
                animation_type=AnimationType.ANIMATE,
                target_attribute="opacity",
                values=["0", "1"],
                key_times=None,
                key_splines=None,
                timing=timing,
                transform_type=None
            ),
            AnimationDefinition(
                element_id="elem2",
                animation_type=AnimationType.ANIMATE_TRANSFORM,
                target_attribute="transform",
                values=["scale(1)", "scale(2)"],
                key_times=None,
                key_splines=None,
                timing=timing,
                transform_type=TransformType.SCALE
            )
        ]
        self.converter.animations = animations
        
        summary = self.converter.get_animation_summary()
        
        assert summary["has_animations"] is True
        assert summary["total_animations"] == 2
        assert summary["transform_animations"] == 1
        assert summary["color_animations"] == 0
        assert summary["complex_animations"] == 0
        assert summary["max_duration"] == 2.0
        assert summary["complexity"] == "simple"
        assert summary["recommendation"] == "PowerPoint animation mapping"
    
    def test_get_animation_summary_moderate(self):
        """Test getting animation summary for moderate complexity."""
        timing = AnimationTiming(0.0, 3.0, 1, FillMode.FREEZE)
        animations = []
        
        # Create 5 animations (moderate count)
        for i in range(5):
            animations.append(AnimationDefinition(
                element_id=f"elem{i}",
                animation_type=AnimationType.ANIMATE,
                target_attribute="opacity",
                values=["0", "1"],
                key_times=None,
                key_splines=None,
                timing=timing,
                transform_type=None
            ))
        
        # Add one complex animation
        animations.append(AnimationDefinition(
            element_id="complex_elem",
            animation_type=AnimationType.ANIMATE,
            target_attribute="fill",
            values=["red", "green", "blue", "yellow"],  # > 2 values = complex
            key_times=None,
            key_splines=None,
            timing=timing,
            transform_type=None
        ))
        
        self.converter.animations = animations
        
        summary = self.converter.get_animation_summary()
        
        assert summary["complexity"] == "moderate"
        assert summary["recommendation"] == "Multi-slide keyframe sequence"
        assert summary["complex_animations"] == 1
    
    def test_get_animation_summary_complex(self):
        """Test getting animation summary for complex animations."""
        timing = AnimationTiming(0.0, 2.0, 1, FillMode.FREEZE)
        animations = []
        
        # Create many animations (complex count)
        for i in range(12):
            animations.append(AnimationDefinition(
                element_id=f"elem{i}",
                animation_type=AnimationType.ANIMATE_COLOR,
                target_attribute="fill",
                values=["red", "green", "blue", "yellow"],  # Complex
                key_times=None,
                key_splines=None,
                timing=timing,
                transform_type=None
            ))
        
        self.converter.animations = animations
        
        summary = self.converter.get_animation_summary()
        
        assert summary["complexity"] == "complex"
        assert summary["recommendation"] == "Static representation or rasterization"
        assert summary["color_animations"] == 12
        assert summary["complex_animations"] == 12
    
    def test_get_animation_summary_infinite_duration(self):
        """Test getting animation summary with infinite duration."""
        timing = AnimationTiming(0.0, 2.0, "indefinite", FillMode.FREEZE)
        animation = AnimationDefinition(
            element_id="infinite_elem",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["0", "1"],
            key_times=None,
            key_splines=None,
            timing=timing,
            transform_type=None
        )
        self.converter.animations = [animation]
        
        summary = self.converter.get_animation_summary()
        
        # Should not include infinite duration in max_duration calculation
        assert summary["max_duration"] == 0.0

class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_animation_processing_workflow(self):
        """Test complete animation processing workflow."""
        converter = TestableAnimationConverter()
        context = MockConversionContext()
        
        # Create a complex SVG animation element with lxml
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <rect id="animated_rect" x="10" y="10" width="50" height="30">
                <animate attributeName="opacity" values="0;1;0" dur="3s" repeatCount="2" />
                <animateTransform attributeName="transform" type="scale" 
                                from="1" to="2" dur="2s" begin="1s" />
            </rect>
        </svg>
        '''
        
        # Parse with lxml to maintain parent relationships
        root = ET.fromstring(svg_content.encode())
        animate_elem = root.find('.//*[@attributeName="opacity"]')
        transform_elem = root.find('.//*[@attributeName="transform"]')
        
        # Convert animation elements
        converter.convert(animate_elem, context)
        converter.convert(transform_elem, context)
        
        assert len(converter.animations) == 2
        
        # Process in different modes
        static_result = converter.process_animated_elements(context, "static")
        keyframe_result = converter.process_animated_elements(context, "keyframes")
        powerpoint_result = converter.process_animated_elements(context, "powerpoint_animation")
        
        # Verify results
        assert "animated_rect" in static_result
        assert keyframe_result["animation_type"] == "keyframe_sequence"
        assert isinstance(powerpoint_result, dict)
        
        # Get summary
        summary = converter.get_animation_summary()
        assert summary["has_animations"] is True
        assert summary["total_animations"] == 2


class TestTransformParserEquivalence:
    """Test TransformParser equivalence to hardcoded transform string generation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        from src.transforms import TransformParser, TransformType as TransformParserType, Transform
        self.transform_parser = TransformParser()
        self.Transform = Transform
        
        # Create a basic timing object
        self.timing = AnimationTiming(
            begin=0,
            duration=1,
            repeat_count=1,
            fill_mode=FillMode.FREEZE
        )
        
        # Map between animation TransformType and transforms TransformType
        self.transform_type_map = {
            TransformType.TRANSLATE: TransformParserType.TRANSLATE,
            TransformType.SCALE: TransformParserType.SCALE,
            TransformType.ROTATE: TransformParserType.ROTATE
        }
    
    def test_transform_parser_translate_equivalence(self):
        """Test TransformParser can generate equivalent translate strings"""
        # Test current hardcoded behavior
        anim = AnimationDefinition(
            element_id="test",
            animation_type=AnimationType.ANIMATE_TRANSFORM,
            target_attribute="transform",
            values=["translate(0, 0)", "translate(100, 50)"],
            key_times=None,
            key_splines=None,
            timing=self.timing,
            transform_type=TransformType.TRANSLATE
        )
        
        # Get hardcoded result
        hardcoded_result = anim._interpolate_transform_values(
            "translate(0, 0)", "translate(100, 50)", 0.5
        )
        
        # Create Transform objects using TransformParser approach
        transform1 = self.Transform(
            type=self.transform_type_map[TransformType.TRANSLATE],
            values=[0.0, 0.0],
            original="translate(0, 0)"
        )
        transform2 = self.Transform(
            type=self.transform_type_map[TransformType.TRANSLATE], 
            values=[100.0, 50.0],
            original="translate(100, 50)"
        )
        
        # Manually interpolate values for comparison
        interpolated_values = [
            transform1.values[0] + (transform2.values[0] - transform1.values[0]) * 0.5,
            transform1.values[1] + (transform2.values[1] - transform1.values[1]) * 0.5
        ]
        
        # Generate TransformParser equivalent
        transform_parser_result = f"translate({interpolated_values[0]}, {interpolated_values[1]})"
        
        # They should be equivalent
        assert hardcoded_result == transform_parser_result == "translate(50.0, 25.0)"


if __name__ == "__main__":
    pytest.main([__file__])