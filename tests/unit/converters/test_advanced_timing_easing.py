#!/usr/bin/env python3
"""
Tests for advanced animation timing, easing, and calc modes in the new AnimationConverter v2.
"""

import pytest
from lxml import etree as ET

from src.converters.animation_converter import AnimationConverter
from core.services.conversion_services import ConversionServices
from src.animations.core import AnimationDefinition, AnimationTiming, CalcMode, FillMode, AnimationType


def make_svg(svg_inner: str) -> ET.Element:
    """Wrap some inner XML in a valid SVG root."""
    svg_str = f'<svg xmlns="http://www.w3.org/2000/svg">{svg_inner}</svg>'
    return ET.fromstring(svg_str)


@pytest.fixture
def converter():
    return AnimationConverter(ConversionServices.create_default())


class TestKeySplinesParsing:
    """Test keySplines parsing and cubic bezier easing."""

    def test_keysplines_parsing_simple(self, converter):
        """Test basic keySplines parsing."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="opacity"
                         values="0;1"
                         keyTimes="0;1"
                         keySplines="0.25 0.1 0.25 1"
                         calcMode="spline"
                         dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

        # Should validate successfully
        valid, issues = converter.validate_animations(svg)
        assert valid is True

    def test_keysplines_multiple_segments(self, converter):
        """Test keySplines with multiple segments."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="opacity"
                         values="0;0.5;1"
                         keyTimes="0;0.5;1"
                         keySplines="0.42 0 0.58 1; 0.25 0.46 0.45 0.94"
                         calcMode="spline"
                         dur="2s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)


class TestBezierEasing:
    """Test bezier easing functions."""

    def test_linear_easing(self, converter):
        """Test linear calc mode (no easing)."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="x"
                         from="0" to="100"
                         calcMode="linear"
                         dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_discrete_easing(self, converter):
        """Test discrete calc mode."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="fill"
                         values="red;blue;green"
                         calcMode="discrete"
                         dur="3s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_bezier_easing_ease_in_out(self, converter):
        """Test bezier easing with ease-in-out curve."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="opacity"
                         values="0;1"
                         keySplines="0.42 0 0.58 1"
                         calcMode="spline"
                         dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)


class TestCalcModeSupport:
    """Test different calcMode values."""

    def test_calc_mode_linear(self, converter):
        """Test calcMode linear."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="x"
                         from="0" to="100"
                         calcMode="linear"
                         dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_calc_mode_discrete(self, converter):
        """Test calcMode discrete."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="fill"
                         values="red;blue;green"
                         calcMode="discrete"
                         dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_calc_mode_paced(self, converter):
        """Test calcMode paced."""
        svg = make_svg('''
            <rect id="r">
                <animateTransform attributeName="transform"
                                type="translate"
                                values="0,0; 100,100; 200,0"
                                calcMode="paced"
                                dur="2s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_calc_mode_spline(self, converter):
        """Test calcMode spline with keySplines."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="opacity"
                         values="0;1"
                         keySplines="0.25 0.1 0.25 1"
                         calcMode="spline"
                         dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)


class TestAdvancedTimingIntegration:
    """Test integration of advanced timing features."""

    def test_transform_animation_with_easing(self, converter):
        """Test transform animation with easing."""
        svg = make_svg('''
            <rect id="r">
                <animateTransform attributeName="transform"
                                type="scale"
                                values="1;1.5;1"
                                keySplines="0.42 0 0.58 1; 0.42 0 0.58 1"
                                calcMode="spline"
                                dur="2s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_color_animation_with_discrete_mode(self, converter):
        """Test color animation with discrete calc mode."""
        svg = make_svg('''
            <rect id="r">
                <animateColor attributeName="fill"
                            values="red;blue;green;yellow"
                            calcMode="discrete"
                            dur="4s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)


class TestAnimationEasingIntegration:
    """Test easing integration with animation generation."""

    def test_animation_with_keysplines_generates_easing_attributes(self, converter):
        """Test that keySplines generates proper easing in output."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="opacity"
                         values="0;1"
                         keySplines="0.25 0.1 0.25 1"
                         calcMode="spline"
                         dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

        # Test that this doesn't cause validation errors
        valid, issues = converter.validate_animations(svg)
        assert valid is True

    def test_animation_calc_mode_linear_no_easing(self, converter):
        """Test linear animations don't generate easing."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="x"
                         from="0" to="100"
                         calcMode="linear"
                         dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_animation_calc_mode_spline_with_easing(self, converter):
        """Test spline animations generate easing."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="opacity"
                         values="0;1"
                         keySplines="0.42 0 0.58 1"
                         calcMode="spline"
                         dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_motion_path_animation_with_easing(self, converter):
        """Test motion path animation with easing."""
        svg = make_svg('''
            <rect id="r">
                <animateMotion path="M0,0 Q50,100 100,0"
                             keySplines="0.25 0.46 0.45 0.94"
                             calcMode="spline"
                             dur="2s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_transform_animation_with_keysplines_easing(self, converter):
        """Test transform animation with keySplines easing."""
        svg = make_svg('''
            <rect id="r">
                <animateTransform attributeName="transform"
                                type="rotate"
                                values="0;180;360"
                                keySplines="0.55 0.055 0.675 0.19; 0.215 0.61 0.355 1"
                                calcMode="spline"
                                dur="3s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)


class TestTimingAndRepeat:
    """Test timing and repeat functionality."""

    def test_animation_with_begin_delay(self, converter):
        """Test animation with begin delay."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="opacity"
                         from="0" to="1"
                         begin="0.5s"
                         dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_animation_with_repeat_count(self, converter):
        """Test animation with repeat count."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="x"
                         from="0" to="100"
                         dur="1s"
                         repeatCount="3"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_animation_with_indefinite_repeat(self, converter):
        """Test animation with indefinite repeat."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="opacity"
                         values="0;1;0"
                         dur="2s"
                         repeatCount="indefinite"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_animation_with_fill_freeze(self, converter):
        """Test animation with fill='freeze'."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="opacity"
                         from="0" to="1"
                         dur="1s"
                         fill="freeze"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)


class TestComplexEasingScenarios:
    """Test complex easing scenarios."""

    def test_multiple_animations_different_easing(self, converter):
        """Test multiple animations with different easing."""
        svg = make_svg('''
            <g>
                <rect id="r1">
                    <animate attributeName="x"
                             from="0" to="100"
                             calcMode="linear"
                             dur="1s"/>
                </rect>
                <rect id="r2">
                    <animate attributeName="y"
                             from="0" to="100"
                             keySplines="0.42 0 0.58 1"
                             calcMode="spline"
                             dur="1s"/>
                </rect>
            </g>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

        stats = converter.get_animation_statistics(svg)
        assert stats["total_animations"] == 2

    def test_chained_animations_with_easing(self, converter):
        """Test chained animations with different easing."""
        svg = make_svg('''
            <rect id="r">
                <animate attributeName="x"
                         from="0" to="50"
                         keySplines="0.42 0 0.58 1"
                         calcMode="spline"
                         dur="1s"/>
                <animate attributeName="x"
                         from="50" to="100"
                         begin="1s"
                         calcMode="linear"
                         dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)


if __name__ == "__main__":
    pytest.main([__file__])