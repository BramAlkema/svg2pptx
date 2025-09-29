#!/usr/bin/env python3
"""
Tests for combined transform animations in the new AnimationConverter v2.
"""

import pytest
from lxml import etree as ET

from src.converters.animation_converter import AnimationConverter
from src.services.conversion_services import ConversionServices


def make_svg(svg_inner: str) -> ET.Element:
    """Wrap some inner XML in a valid SVG root."""
    svg_str = f'<svg xmlns="http://www.w3.org/2000/svg">{svg_inner}</svg>'
    return ET.fromstring(svg_str)


@pytest.fixture
def converter():
    return AnimationConverter(ConversionServices.create_default())


class TestCombinedTransformSupport:
    """Test combined transform animation support."""

    def test_simple_combined_transform(self, converter):
        """Test simple combined transform animation."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="translate"
                                from="0,0"
                                to="100,100"
                                dur="2s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

        # Should validate successfully
        valid, issues = converter.validate_animations(svg)
        assert valid is True

    def test_additive_transform(self, converter):
        """Test additive transform animations."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="translate"
                                values="0,0; 50,50; 100,100"
                                dur="2s"
                                additive="sum"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_translate_transform_animation(self, converter):
        """Test translate transform animation."""
        svg = make_svg('''
            <circle id="c" r="25">
                <animateTransform attributeName="transform"
                                type="translate"
                                values="0,0; 50,25; 100,0"
                                dur="3s"/>
            </circle>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_skew_transform_animation(self, converter):
        """Test skew transform animation."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="skewX"
                                from="0"
                                to="30"
                                dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_build_transform_string(self, converter):
        """Test transform string building."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="scale"
                                values="1; 1.5; 2; 1"
                                dur="4s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_no_animation_for_single_value(self, converter):
        """Test that single values don't create animations."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="rotate"
                                values="45"
                                dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

        # Should still validate
        valid, issues = converter.validate_animations(svg)
        assert valid is True


class TestMatrixIntegration:
    """Test transform matrix integration."""

    def test_transform_processor_integration(self, converter):
        """Test integration with transform processing."""
        svg = make_svg('''
            <g transform="translate(10,10)">
                <rect id="r" width="50" height="50">
                    <animateTransform attributeName="transform"
                                    type="rotate"
                                    from="0"
                                    to="360"
                                    dur="2s"/>
                </rect>
            </g>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_complex_path_translation(self, converter):
        """Test complex path with translation."""
        svg = make_svg('''
            <path id="p" d="M10,10 L50,50">
                <animateTransform attributeName="transform"
                                type="translate"
                                path="M0,0 Q25,50 50,0"
                                dur="3s"/>
            </path>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)


class TestAccumulativeTransforms:
    """Test accumulative transform animations."""

    def test_combined_additive_and_accumulate(self, converter):
        """Test combined additive and accumulate behaviors."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="rotate"
                                values="0; 90; 180"
                                dur="2s"
                                additive="sum"
                                accumulate="sum"
                                repeatCount="3"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)


class TestMultipleTransforms:
    """Test multiple transform animations on the same element."""

    def test_sequential_transforms(self, converter):
        """Test sequential transform animations."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="translate"
                                from="0,0"
                                to="100,0"
                                dur="1s"/>
                <animateTransform attributeName="transform"
                                type="rotate"
                                from="0"
                                to="90"
                                begin="1s"
                                dur="1s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

        # Should consolidate or sequence properly
        stats = converter.get_animation_statistics(svg)
        assert stats["total_animations"] >= 1

    def test_simultaneous_transforms(self, converter):
        """Test simultaneous transform animations."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="translate"
                                from="0,0"
                                to="100,100"
                                dur="2s"/>
                <animateTransform attributeName="transform"
                                type="scale"
                                from="1"
                                to="2"
                                dur="2s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)


class TestTransformValidation:
    """Test transform animation validation."""

    def test_missing_transform_type(self, converter):
        """Test validation of missing transform type."""
        svg = make_svg('''
            <rect id="r">
                <animateTransform attributeName="transform"
                                from="0"
                                to="100"
                                dur="1s"/>
            </rect>
        ''')

        valid, issues = converter.validate_animations(svg)
        assert not valid
        assert any("type" in issue for issue in issues)

    def test_valid_transform_types(self, converter):
        """Test validation of all valid transform types."""
        transform_types = ["translate", "scale", "rotate", "skewX", "skewY"]

        for transform_type in transform_types:
            svg = make_svg(f'''
                <rect id="r">
                    <animateTransform attributeName="transform"
                                    type="{transform_type}"
                                    from="0"
                                    to="100"
                                    dur="1s"/>
                </rect>
            ''')

            valid, issues = converter.validate_animations(svg)
            assert valid is True, f"Transform type {transform_type} should be valid"


class TestTransformComplexity:
    """Test complex transform scenarios."""

    def test_matrix_transform_animation(self, converter):
        """Test matrix transform animation."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="matrix"
                                values="1,0,0,1,0,0; 2,0,0,2,50,50"
                                dur="2s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_path_based_motion(self, converter):
        """Test path-based motion with animateMotion."""
        svg = make_svg('''
            <circle id="c" r="10">
                <animateMotion path="M0,0 Q50,100 100,0"
                             dur="3s"
                             rotate="auto"/>
            </circle>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_complex_transform_sequence(self, converter):
        """Test complex sequence of transforms."""
        svg = make_svg('''
            <g>
                <rect id="r1" width="30" height="30">
                    <animateTransform attributeName="transform"
                                    type="translate"
                                    values="0,0; 50,0; 50,50; 0,50; 0,0"
                                    dur="4s"/>
                </rect>
                <rect id="r2" width="30" height="30">
                    <animateTransform attributeName="transform"
                                    type="rotate"
                                    values="0; 180; 360"
                                    dur="3s"/>
                    <animateTransform attributeName="transform"
                                    type="scale"
                                    values="1; 0.5; 1"
                                    begin="1s"
                                    dur="2s"/>
                </rect>
            </g>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

        stats = converter.get_animation_statistics(svg)
        assert stats["total_animations"] >= 2


class TestTransformTimingAndEasing:
    """Test transform animations with timing and easing."""

    def test_transform_with_keysplines(self, converter):
        """Test transform animation with keySplines easing."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="rotate"
                                values="0; 180; 360"
                                keySplines="0.42 0 0.58 1; 0.42 0 0.58 1"
                                calcMode="spline"
                                dur="3s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_transform_with_begin_delay(self, converter):
        """Test transform animation with begin delay."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="scale"
                                from="1"
                                to="2"
                                begin="0.5s"
                                dur="1.5s"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)

    def test_transform_with_repeat(self, converter):
        """Test transform animation with repeat."""
        svg = make_svg('''
            <rect id="r" width="50" height="50">
                <animateTransform attributeName="transform"
                                type="rotate"
                                from="0"
                                to="360"
                                dur="2s"
                                repeatCount="indefinite"/>
            </rect>
        ''')

        xml = converter.convert_slide_animations(svg)
        assert isinstance(xml, str)


if __name__ == "__main__":
    pytest.main([__file__])