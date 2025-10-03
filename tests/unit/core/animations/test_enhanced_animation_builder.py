#!/usr/bin/env python3
"""
Tests for Enhanced Animation Builder

Tests the template-based animation XML generation with proper lxml.etree DOM manipulation.
"""

import pytest
from unittest.mock import Mock
from lxml import etree as ET

from core.animations.enhanced_animation_builder import (
    EnhancedAnimationBuilder, get_animation_builder,
    create_opacity_animation, create_scale_animation,
    create_rotation_animation, create_color_animation,
    create_motion_animation, create_set_animation,
    create_generic_animation
)
from core.animations.core import (
    AnimationDefinition, AnimationType, TransformType,
    AnimationTiming, CalcMode, FillMode
)


class TestEnhancedAnimationBuilder:
    """Test the enhanced animation builder functionality."""

    @pytest.fixture
    def builder(self):
        """Create enhanced animation builder for testing."""
        return EnhancedAnimationBuilder()

    @pytest.fixture
    def sample_animation(self):
        """Create sample animation definition for testing."""
        timing = AnimationTiming(duration=2.0, begin=0.5)
        return AnimationDefinition(
            element_id="shape1",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["0", "1"],
            timing=timing,
            key_splines=[]
        )

    def test_initialization(self, builder):
        """Test builder initialization and template validation."""
        assert builder is not None
        assert builder.animation_id_counter == 1
        assert builder._template_loader is not None

    def test_id_generation(self, builder):
        """Test unique ID generation."""
        id1 = builder.get_next_animation_id()
        id2 = builder.get_next_animation_id()

        assert id1 == 1
        assert id2 == 2
        assert id1 != id2

    def test_id_counter_reset(self, builder):
        """Test ID counter reset."""
        builder.get_next_animation_id()
        builder.get_next_animation_id()

        builder.reset_animation_id_counter()

        next_id = builder.get_next_animation_id()
        assert next_id == 1

    def test_generate_opacity_animation(self, builder, sample_animation):
        """Test opacity animation generation."""
        anim_element = builder.generate_opacity_animation(sample_animation, 1, 2000, 500)

        # Check element structure
        assert anim_element.tag.endswith('animEffect')

        # Check common behavior
        ctn = anim_element.find('.//a:cBhvr/a:cTn', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert ctn is not None
        assert ctn.get('id') == '1'
        assert ctn.get('dur') == '2000'
        assert ctn.get('delay') == '500'

        # Check target element
        sp_tgt = anim_element.find('.//a:tgtEl/a:spTgt', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert sp_tgt is not None
        assert sp_tgt.get('spid') == 'shape1'

    def test_generate_scale_animation(self, builder):
        """Test scale animation generation."""
        timing = AnimationTiming(duration=1.5, begin=0.0)
        animation = AnimationDefinition(
            element_id="shape2",
            animation_type=AnimationType.ANIMATE_TRANSFORM,
            target_attribute="transform",
            transform_type=TransformType.SCALE,
            values=["1.0", "1.5"],
            timing=timing
        )

        anim_element = builder.generate_scale_animation(animation, 2, 1500, 0)

        # Check element structure
        assert anim_element.tag.endswith('animScale')

        # Check scale values
        from_pt = anim_element.find('.//a:from/a:pt', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert from_pt is not None
        assert from_pt.get('x') == '1.0'
        assert from_pt.get('y') == '1.0'

        to_pt = anim_element.find('.//a:to/a:pt', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert to_pt is not None
        assert to_pt.get('x') == '1.5'
        assert to_pt.get('y') == '1.5'

    def test_generate_rotation_animation(self, builder):
        """Test rotation animation generation."""
        timing = AnimationTiming(duration=3.0, begin=1.0)
        animation = AnimationDefinition(
            element_id="shape3",
            animation_type=AnimationType.ANIMATE_TRANSFORM,
            target_attribute="transform",
            transform_type=TransformType.ROTATE,
            values=["0", "360"],
            timing=timing
        )

        anim_element = builder.generate_rotation_animation(animation, 3, 3000, 1000)

        # Check element structure
        assert anim_element.tag.endswith('animRot')

        # Check rotation value (360 degrees = 21600000 in PowerPoint units)
        by_elem = anim_element.find('.//a:by', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert by_elem is not None
        assert by_elem.get('val') == '21600000'  # 360 * 60000

    def test_generate_color_animation(self, builder):
        """Test color animation generation."""
        timing = AnimationTiming(duration=2.5, begin=0.5)
        animation = AnimationDefinition(
            element_id="shape4",
            animation_type=AnimationType.ANIMATE_COLOR,
            target_attribute="fill",
            values=["#FF0000", "#0000FF"],
            timing=timing
        )

        anim_element = builder.generate_color_animation(animation, 4, 2500, 500)

        # Check element structure
        assert anim_element.tag.endswith('animClr')

        # Check color values
        from_color = anim_element.find('.//a:from/a:srgbClr', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert from_color is not None
        assert from_color.get('val') == 'FF0000'

        to_color = anim_element.find('.//a:to/a:srgbClr', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert to_color is not None
        assert to_color.get('val') == '0000FF'

        # Check attribute name
        attr_name = anim_element.find('.//a:attrNameLst/a:attrName', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert attr_name is not None
        assert attr_name.text == 'fillColor'

    def test_generate_motion_animation(self, builder):
        """Test motion path animation generation."""
        timing = AnimationTiming(duration=4.0, begin=0.0)
        animation = AnimationDefinition(
            element_id="shape5",
            animation_type=AnimationType.ANIMATE_MOTION,
            target_attribute="path",
            values=["M 0,0 L 100,100 L 200,0"],
            timing=timing
        )

        anim_element = builder.generate_motion_animation(animation, 5, 4000, 0)

        # Check element structure
        assert anim_element.tag.endswith('animMotion')

        # Check path data
        path_elem = anim_element.find('.//a:path', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert path_elem is not None
        assert path_elem.get('path') == 'M 0,0 L 100,100 L 200,0'

    def test_generate_set_animation(self, builder):
        """Test set animation generation."""
        timing = AnimationTiming(duration=0.0, begin=1.5)
        animation = AnimationDefinition(
            element_id="shape6",
            animation_type=AnimationType.SET,
            target_attribute="visibility",
            values=["visible"],
            timing=timing
        )

        anim_element = builder.generate_set_animation(animation, 6, 1500)

        # Check element structure
        assert anim_element.tag.endswith('set')

        # Check duration (should be 1 for set animations)
        ctn = anim_element.find('.//a:cBhvr/a:cTn', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert ctn is not None
        assert ctn.get('dur') == '1'

        # Check value
        str_val = anim_element.find('.//a:to/a:strVal', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert str_val is not None
        assert str_val.get('val') == 'visible'

    def test_generate_generic_animation(self, builder):
        """Test generic property animation generation."""
        timing = AnimationTiming(duration=2.0, begin=0.0)
        animation = AnimationDefinition(
            element_id="shape7",
            animation_type=AnimationType.ANIMATE,
            target_attribute="x",
            values=["0", "100"],
            timing=timing
        )

        anim_element = builder.generate_generic_animation(animation, 7, 2000, 0)

        # Check element structure
        assert anim_element.tag.endswith('anim')

        # Check time/value list
        tav_list = anim_element.findall('.//a:tavLst/a:tav', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert len(tav_list) >= 2

        # Check from value
        from_str_val = tav_list[0].find('.//a:strVal', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert from_str_val is not None
        assert from_str_val.get('val') == '0'

        # Check to value
        to_str_val = tav_list[1].find('.//a:strVal', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        assert to_str_val is not None
        assert to_str_val.get('val') == '100'

    def test_element_to_string(self, builder, sample_animation):
        """Test element to XML string conversion."""
        anim_element = builder.generate_opacity_animation(sample_animation, 1, 2000, 500)
        xml_string = builder.element_to_string(anim_element)

        assert isinstance(xml_string, str)
        assert '<a:animEffect' in xml_string
        assert 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"' in xml_string

    def test_element_to_string_pretty_print(self, builder, sample_animation):
        """Test element to XML string conversion with pretty printing."""
        anim_element = builder.generate_opacity_animation(sample_animation, 1, 2000, 500)
        xml_string = builder.element_to_string(anim_element, pretty_print=True)

        assert isinstance(xml_string, str)
        assert '\n' in xml_string  # Should have newlines for pretty printing

    def test_validate_element(self, builder, sample_animation):
        """Test element validation."""
        anim_element = builder.generate_opacity_animation(sample_animation, 1, 2000, 500)

        is_valid = builder.validate_element(anim_element)
        assert is_valid is True

    def test_parse_scale_value(self, builder):
        """Test scale value parsing."""
        assert builder._parse_scale_value("1.5") == 1.5
        assert builder._parse_scale_value("2.0") == 2.0
        assert builder._parse_scale_value("invalid") == 1.0
        assert builder._parse_scale_value(None) == 1.0

    def test_parse_rotation_value(self, builder):
        """Test rotation value parsing."""
        assert builder._parse_rotation_value("90deg") == 90.0
        assert builder._parse_rotation_value("180") == 180.0
        assert builder._parse_rotation_value("invalid") == 0.0
        assert builder._parse_rotation_value(None) == 0.0

    def test_parse_color_value(self, builder):
        """Test color value parsing."""
        assert builder._parse_color_value("#FF0000") == "FF0000"
        assert builder._parse_color_value("FF0000") == "FF0000"
        assert builder._parse_color_value("#F00") == "FF0000"  # 3-char to 6-char expansion
        assert builder._parse_color_value("F00") == "FF0000"
        assert builder._parse_color_value("invalid") == "000000"
        assert builder._parse_color_value(None) == "000000"


class TestFactoryFunctions:
    """Test factory functions for animation creation."""

    @pytest.fixture
    def sample_animation(self):
        """Create sample animation definition for testing."""
        timing = AnimationTiming(duration=1.0, begin=0.0)
        return AnimationDefinition(
            element_id="test_shape",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["0", "1"],
            timing=timing
        )

    def test_create_opacity_animation(self, sample_animation):
        """Test opacity animation factory function."""
        anim_element = create_opacity_animation(sample_animation, 1, 1000, 0)
        assert anim_element.tag.endswith('animEffect')

    def test_create_scale_animation(self, sample_animation):
        """Test scale animation factory function."""
        anim_element = create_scale_animation(sample_animation, 1, 1000, 0)
        assert anim_element.tag.endswith('animScale')

    def test_create_rotation_animation(self, sample_animation):
        """Test rotation animation factory function."""
        anim_element = create_rotation_animation(sample_animation, 1, 1000, 0)
        assert anim_element.tag.endswith('animRot')

    def test_create_color_animation(self, sample_animation):
        """Test color animation factory function."""
        anim_element = create_color_animation(sample_animation, 1, 1000, 0)
        assert anim_element.tag.endswith('animClr')

    def test_create_motion_animation(self, sample_animation):
        """Test motion animation factory function."""
        anim_element = create_motion_animation(sample_animation, 1, 1000, 0)
        assert anim_element.tag.endswith('animMotion')

    def test_create_set_animation(self, sample_animation):
        """Test set animation factory function."""
        anim_element = create_set_animation(sample_animation, 1, 0)
        assert anim_element.tag.endswith('set')

    def test_create_generic_animation(self, sample_animation):
        """Test generic animation factory function."""
        anim_element = create_generic_animation(sample_animation, 1, 1000, 0)
        assert anim_element.tag.endswith('anim')

    def test_get_animation_builder(self):
        """Test singleton animation builder access."""
        builder1 = get_animation_builder()
        builder2 = get_animation_builder()

        assert builder1 is builder2  # Should be the same instance


class TestAnimationIntegration:
    """Test integration with PowerPoint animation generator."""

    def test_powerpoint_integration_smoke_test(self):
        """Smoke test for PowerPoint animation generator integration."""
        from core.animations.powerpoint import PowerPointAnimationGenerator

        generator = PowerPointAnimationGenerator()
        assert generator.animation_builder is not None
        assert hasattr(generator.animation_builder, 'generate_opacity_animation')

    def test_template_validation_on_init(self):
        """Test that all required templates are validated on initialization."""
        # This should not raise an exception
        builder = EnhancedAnimationBuilder()
        assert builder is not None


class TestXMLNamespaces:
    """Test XML namespace handling."""

    @pytest.fixture
    def builder(self):
        return EnhancedAnimationBuilder()

    @pytest.fixture
    def sample_animation(self):
        timing = AnimationTiming(duration=1.0, begin=0.0)
        return AnimationDefinition(
            element_id="test_shape",
            animation_type=AnimationType.ANIMATE,
            target_attribute="opacity",
            values=["0", "1"],
            timing=timing
        )

    def test_namespace_declarations(self, builder, sample_animation):
        """Test proper namespace declarations in generated XML."""
        anim_element = builder.generate_opacity_animation(sample_animation, 1, 1000, 0)
        xml_string = builder.element_to_string(anim_element)

        # Check DrawingML namespace
        assert 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"' in xml_string

    def test_qname_usage(self, builder, sample_animation):
        """Test that elements use proper QNames."""
        anim_element = builder.generate_opacity_animation(sample_animation, 1, 1000, 0)

        # Check that the root element has the correct namespace
        assert anim_element.nsmap is not None
        assert 'a' in anim_element.nsmap
        assert anim_element.nsmap['a'] == 'http://schemas.openxmlformats.org/drawingml/2006/main'

    def test_element_serialization_namespaces(self, builder, sample_animation):
        """Test namespace consistency in element serialization."""
        anim_element = builder.generate_opacity_animation(sample_animation, 1, 1000, 0)
        xml_string = builder.element_to_string(anim_element)

        # Parse back and check namespace consistency
        parsed = ET.fromstring(xml_string)
        assert parsed.nsmap is not None
        assert 'a' in parsed.nsmap


class TestPerformanceAndCompatibility:
    """Test performance aspects and backward compatibility."""

    @pytest.fixture
    def builder(self):
        return EnhancedAnimationBuilder()

    def test_template_caching(self, builder):
        """Test that templates are cached for performance."""
        # Load same template multiple times - should use cache
        template1 = builder._template_loader.load_template("animation_effect.xml")
        template2 = builder._template_loader.load_template("animation_effect.xml")

        # Templates should be independent copies but loaded efficiently
        assert template1 is not template2  # Deep copies for safety
        assert template1.tag == template2.tag  # But same structure

    def test_large_animation_creation(self, builder):
        """Test creating many animations efficiently."""
        timing = AnimationTiming(duration=1.0, begin=0.0)

        animations = []
        for i in range(50):
            animation = AnimationDefinition(
                element_id=f"shape{i}",
                animation_type=AnimationType.ANIMATE,
                target_attribute="opacity",
                values=["0", "1"],
                timing=timing
            )
            anim_element = builder.generate_opacity_animation(animation, i+1, 1000, 0)
            animations.append(anim_element)

        # All animations should be created successfully
        assert len(animations) == 50

        # Each should have unique ID
        ids = set()
        for anim in animations:
            ctn = anim.find('.//a:cBhvr/a:cTn', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
            ids.add(ctn.get('id'))

        assert len(ids) == 50  # All unique IDs