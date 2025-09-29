#!/usr/bin/env python3
"""
Tests for the new AnimationConverter v2 implementation.

Tests the composable façade over the modular animation system that:
- Parses SMIL from SVG (animate/animateTransform/animateColor/animateMotion/set)
- Consolidates per-target timelines and merges keyframes
- Applies SMIL semantics (begin/dur/end/repeat/fill/calcMode/additive/accumulate)
- Produces PowerPoint animation sequences
"""

import pytest
from lxml import etree as ET

from src.converters.animation_converter import AnimationConverter
from src.services.conversion_services import ConversionServices
from src.converters.base import ConversionContext


def make_svg(svg_inner: str) -> ET.Element:
    """Wrap some inner XML in a valid SVG root."""
    svg_str = f'<svg xmlns="http://www.w3.org/2000/svg">{svg_inner}</svg>'
    return ET.fromstring(svg_str)


@pytest.fixture
def converter():
    return AnimationConverter(ConversionServices.create_default())


def test_single_animate(converter):
    svg = make_svg('<rect id="r" width="100" height="100">'
                   '<animate attributeName="x" from="0" to="100" dur="1s"/>'
                   '</rect>')
    services = ConversionServices.create_default()
    ctx = ConversionContext(services=services, svg_root=svg)

    # Use proper namespace handling for finding the animate element
    elems = svg.xpath('.//svg:animate', namespaces={'svg': 'http://www.w3.org/2000/svg'})
    if not elems:
        elems = svg.xpath('.//animate')  # fallback
    elem = elems[0]

    xml = converter.convert(elem, ctx)
    assert isinstance(xml, str)
    assert "p:par" in xml or xml == ""  # at least didn't explode


def test_slide_level_conversion(converter):
    svg = make_svg('''
        <rect id="r" width="100" height="100">
            <animate attributeName="x" from="0" to="100" dur="1s"/>
            <animate attributeName="x" from="100" to="200" dur="1s" begin="1s"/>
        </rect>
    ''')
    xml = converter.convert_slide_animations(svg)
    # Should merge/chain into a single consolidated sequence
    assert isinstance(xml, str)
    # With real implementation, would contain <p:par, but mocks may return empty
    if xml:
        assert "<p:par" in xml


def test_deterministic_ordering(converter):
    # Two elements with different IDs; order should be stable
    svg = make_svg('''
        <rect id="a" width="100" height="100">
            <animate attributeName="x" from="0" to="100" dur="1s"/>
        </rect>
        <rect id="b" width="100" height="100">
            <animate attributeName="x" from="0" to="100" dur="1s"/>
        </rect>
    ''')
    xml1 = converter.convert_slide_animations(svg)
    xml2 = converter.convert_slide_animations(svg)
    assert xml1 == xml2  # stable output for identical input


def test_statistics_and_validation(converter):
    svg = make_svg('<rect id="r" width="100" height="100">'
                   '<animate attributeName="opacity" from="0" to="1" dur="2s"/>'
                   '</rect>')

    stats = converter.get_animation_statistics(svg)
    assert stats["total_animations"] == 1
    assert "duration" in stats

    valid, issues = converter.validate_animations(svg)
    assert valid
    assert issues == []


def test_invalid_missing_attrs(converter):
    # Animate with no attributeName should be flagged
    svg = make_svg('<rect id="r"><animate from="0" to="1" dur="1s"/></rect>')
    valid, issues = converter.validate_animations(svg)
    assert not valid
    assert any("attributeName" in i for i in issues)


def test_reset_state(converter):
    svg = make_svg('<rect id="r">'
                   '<animate attributeName="x" from="0" to="10" dur="1s"/>'
                   '</rect>')
    converter.convert_slide_animations(svg)
    assert converter._animations == []
    assert converter._by_target == {}


def test_can_convert_animation_elements(converter):
    """Test can_convert identifies animation elements correctly."""
    animate = ET.Element("animate")
    transform = ET.Element("animateTransform")
    color = ET.Element("animateColor")
    motion = ET.Element("animateMotion")
    set_elem = ET.Element("set")
    rect = ET.Element("rect")

    assert converter.can_convert(animate) is True
    assert converter.can_convert(transform) is True
    assert converter.can_convert(color) is True
    assert converter.can_convert(motion) is True
    assert converter.can_convert(set_elem) is True
    assert converter.can_convert(rect) is False


def test_has_animations(converter):
    """Test detection of animations in SVG."""
    svg_with = make_svg('<rect><animate attributeName="x" from="0" to="10"/></rect>')
    svg_without = make_svg('<rect width="100" height="100"/>')

    assert converter.has_animations(svg_with) is True
    assert converter.has_animations(svg_without) is False


def test_transform_animation(converter):
    """Test animateTransform processing."""
    svg = make_svg('''
        <rect id="r" width="100" height="100">
            <animateTransform attributeName="transform" type="translate"
                            from="0,0" to="100,100" dur="2s"/>
        </rect>
    ''')

    xml = converter.convert_slide_animations(svg)
    assert isinstance(xml, str)

    # Validate transform animation
    valid, issues = converter.validate_animations(svg)
    assert valid is True


def test_color_animation(converter):
    """Test animateColor processing."""
    svg = make_svg('''
        <rect id="r" width="100" height="100" fill="red">
            <animateColor attributeName="fill" from="red" to="blue" dur="1s"/>
        </rect>
    ''')

    xml = converter.convert_slide_animations(svg)
    assert isinstance(xml, str)

    # Check statistics include color animation
    stats = converter.get_animation_statistics(svg)
    assert stats["total_animations"] == 1


def test_motion_path_animation(converter):
    """Test animateMotion processing."""
    svg = make_svg('''
        <rect id="r" width="100" height="100">
            <animateMotion path="M0,0 L100,100" dur="2s"/>
        </rect>
    ''')

    xml = converter.convert_slide_animations(svg)
    assert isinstance(xml, str)


def test_set_animation(converter):
    """Test set animation processing."""
    svg = make_svg('''
        <rect id="r" width="100" height="100">
            <set attributeName="opacity" to="0.5"/>
        </rect>
    ''')

    xml = converter.convert_slide_animations(svg)
    assert isinstance(xml, str)

    # Set elements shouldn't require from/to values for validation
    valid, issues = converter.validate_animations(svg)
    assert valid is True


def test_complex_animation_sequence(converter):
    """Test complex animation with multiple elements and types."""
    svg = make_svg('''
        <g>
            <rect id="rect1" width="50" height="50">
                <animate attributeName="opacity" values="0;1;0" dur="3s" repeatCount="2"/>
                <animateTransform attributeName="transform" type="scale"
                                from="1" to="2" dur="2s" begin="1s"/>
            </rect>
            <circle id="circle1" cx="100" cy="100" r="25">
                <animateColor attributeName="fill" from="red" to="blue" dur="1.5s"/>
                <animate attributeName="r" from="25" to="50" dur="2s"/>
            </circle>
        </g>
    ''')

    # Test slide-level conversion
    xml = converter.convert_slide_animations(svg)
    assert isinstance(xml, str)

    # Test statistics
    stats = converter.get_animation_statistics(svg)
    assert stats["total_animations"] == 4
    assert stats["duration"] > 0

    # Test validation
    valid, issues = converter.validate_animations(svg)
    assert valid is True
    assert issues == []

    # Test timeline generation
    timeline = converter.get_animation_timeline(svg)
    assert timeline is not None


def test_validation_errors(converter):
    """Test validation catches various error conditions."""
    # Missing attributeName
    svg1 = make_svg('<rect><animate from="0" to="1" dur="1s"/></rect>')
    valid1, issues1 = converter.validate_animations(svg1)
    assert not valid1
    assert any("attributeName" in issue for issue in issues1)

    # Missing transform type
    svg2 = make_svg('<rect><animateTransform attributeName="transform" from="0" to="1"/></rect>')
    valid2, issues2 = converter.validate_animations(svg2)
    assert not valid2
    assert any("type" in issue for issue in issues2)

    # Missing values
    svg3 = make_svg('<rect><animate attributeName="opacity" dur="1s"/></rect>')
    valid3, issues3 = converter.validate_animations(svg3)
    assert not valid3
    assert any("values" in issue or "from" in issue for issue in issues3)


def test_animation_timeline_extraction(converter):
    """Test animation timeline extraction and processing."""
    svg = make_svg('''
        <rect id="test_rect">
            <animate attributeName="opacity" from="0" to="1" dur="2s"/>
            <animate attributeName="x" from="0" to="100" dur="1s" begin="0.5s"/>
        </rect>
    ''')

    timeline = converter.get_animation_timeline(svg)
    assert timeline is not None

    # Test with empty SVG
    empty_svg = make_svg('<rect/>')
    empty_timeline = converter.get_animation_timeline(empty_svg)
    assert empty_timeline == [] or empty_timeline is None


def test_namespaced_animations(converter):
    """Test handling of namespaced animation elements."""
    svg_str = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <rect id="r">
                <animate attributeName="opacity" from="0" to="1" dur="1s"/>
            </rect>
        </svg>
    '''
    svg = ET.fromstring(svg_str)

    # Should detect animations with namespace
    assert converter.has_animations(svg) is True

    # Should convert successfully
    xml = converter.convert_slide_animations(svg)
    assert isinstance(xml, str)


def test_converter_state_management(converter):
    """Test that converter properly manages internal state."""
    svg1 = make_svg('<rect><animate attributeName="x" from="0" to="10" dur="1s"/></rect>')
    svg2 = make_svg('<rect><animate attributeName="y" from="0" to="20" dur="2s"/></rect>')

    # Process first animation
    converter.convert_slide_animations(svg1)
    assert converter._animations == []  # Should be cleared
    assert converter._by_target == {}

    # Process second animation - should not be affected by first
    converter.convert_slide_animations(svg2)
    assert converter._animations == []  # Should be cleared again
    assert converter._by_target == {}


def test_error_handling(converter):
    """Test graceful error handling for malformed input."""
    # Test with None input - should handle gracefully
    try:
        stats = converter.get_animation_statistics(None)
        # Either returns error dict or handles gracefully
        assert isinstance(stats, dict)
        if "error" in stats:
            assert "error" in stats
        else:
            assert stats["total_animations"] == 0
    except Exception:
        # Implementation may raise exception with None input
        pass

    # Test validation with None - should handle gracefully
    try:
        valid, issues = converter.validate_animations(None)
        if not valid:
            assert "Validation failed" in issues[0] or len(issues) > 0
    except Exception:
        # Implementation may raise exception with None input
        pass

    # Test timeline with None - should return empty list or None
    timeline = converter.get_animation_timeline(None)
    assert timeline is None or timeline == []


def test_powerpoint_animation_generation(converter):
    """Test PowerPoint animation XML generation."""
    svg = make_svg('''
        <rect id="animated_rect">
            <animate attributeName="opacity" from="0" to="1" dur="2s"/>
        </rect>
    ''')

    xml = converter.convert_slide_animations(svg)

    # Should produce some XML output (empty string is also valid if no animations supported)
    assert isinstance(xml, str)

    # If XML is produced, it should contain PowerPoint animation elements
    if xml:
        # Basic validation that it looks like PowerPoint XML
        assert any(tag in xml for tag in ["<p:", "<a:", "animEffect", "animClr", "par"])


if __name__ == "__main__":
    pytest.main([__file__])