#!/usr/bin/env python3
"""
Unit tests for PowerPoint animation generation in AnimationConverter.

Tests the conversion of SMIL animations to PowerPoint DrawingML XML,
validating the proper generation of animation effects, timing, and attributes.
"""

import pytest
from unittest.mock import Mock
from lxml import etree

# Import from new animation system
from src.animations import (
    AnimationType, AnimationDefinition,
    AnimationTiming, FillMode, TransformType
)
from src.converters.animation_converter import AnimationConverter
from src.converters.animation_templates import (
    PowerPointAnimationGenerator, PowerPointAnimationConfig, PowerPointEffectType
)
from src.converters.base import ConversionContext
from src.services.conversion_services import ConversionServices


class TestPowerPointAnimationGenerator:
    """Test PowerPoint animation XML generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = PowerPointAnimationGenerator()

    def test_fade_in_animation_generation(self):
        """Test generation of fade in animation XML."""
        config = PowerPointAnimationConfig(
            effect_type=PowerPointEffectType.FADE_IN,
            duration_ms=2000,
            delay_ms=500,
            target_element_id="rect1"
        )

        xml = self.generator.generate_animation_drawingml(config)

        assert xml is not None
        assert len(xml) > 0
        assert '<a:animEffect>' in xml
        assert '<a:cTn' in xml
        assert 'dur="2000"' in xml
        assert 'delay="500"' in xml
        assert 'spid="rect1"' in xml

    def test_color_change_animation_generation(self):
        """Test generation of color change animation XML."""
        config = PowerPointAnimationConfig(
            effect_type=PowerPointEffectType.COLOR_CHANGE,
            duration_ms=1500,
            target_element_id="circle1",
            custom_attributes={
                'from_color': '#FF0000',
                'to_color': '#00FF00'
            }
        )

        xml = self.generator.generate_animation_drawingml(config)

        assert '<a:animClr>' in xml
        assert 'val="FF0000"' in xml
        assert 'val="00FF00"' in xml
        assert 'dur="1500"' in xml

    def test_scale_animation_generation(self):
        """Test generation of scale animation XML."""
        config = PowerPointAnimationConfig(
            effect_type=PowerPointEffectType.GROW,
            duration_ms=1000,
            target_element_id="shape1",
            custom_attributes={'scale_factor': 2.0}
        )

        xml = self.generator.generate_animation_drawingml(config)

        assert '<a:animScale>' in xml
        assert 'x="2.0"' in xml
        assert 'y="2.0"' in xml

    def test_rotation_animation_generation(self):
        """Test generation of rotation animation XML."""
        config = PowerPointAnimationConfig(
            effect_type=PowerPointEffectType.SPIN,
            duration_ms=3000,
            target_element_id="wheel1",
            custom_attributes={'rotation_degrees': 360}
        )

        xml = self.generator.generate_animation_drawingml(config)

        assert '<a:animRot>' in xml
        assert 'val="21600000"' in xml  # 360 * 60000

    def test_motion_path_animation_generation(self):
        """Test generation of motion path animation XML."""
        config = PowerPointAnimationConfig(
            effect_type=PowerPointEffectType.MOTION_PATH,
            duration_ms=2000,
            target_element_id="mover1",
            custom_attributes={'path_data': 'M 0,0 L 100,50 L 0,100'}
        )

        xml = self.generator.generate_animation_drawingml(config)

        assert '<a:animMotion>' in xml
        assert 'path="M 0,0 L 100,50 L 0,100"' in xml

    def test_repeat_count_handling(self):
        """Test handling of repeat counts in animations."""
        # Test indefinite repeat
        config_indefinite = PowerPointAnimationConfig(
            effect_type=PowerPointEffectType.FADE_IN,
            duration_ms=1000,
            repeat_count=-1,
            target_element_id="test1"
        )

        xml_indefinite = self.generator.generate_animation_drawingml(config_indefinite)
        assert 'repeatCount="indefinite"' in xml_indefinite

        # Test specific repeat count
        config_specific = PowerPointAnimationConfig(
            effect_type=PowerPointEffectType.FADE_IN,
            duration_ms=1000,
            repeat_count=3,
            target_element_id="test2"
        )

        xml_specific = self.generator.generate_animation_drawingml(config_specific)
        assert 'repeatCount="3"' in xml_specific

    def test_animation_xml_validation(self):
        """Test XML validation functionality."""
        # Valid XML
        valid_xml = '''<a:animEffect>
  <a:cBhvr>
    <a:cTn id="1" dur="1000"/>
    <a:tgtEl>
      <a:spTgt spid="test"/>
    </a:tgtEl>
  </a:cBhvr>
</a:animEffect>'''

        assert self.generator.validate_animation_xml(valid_xml)

        # Invalid XML
        invalid_xml = '<invalid>broken</xml>'
        assert not self.generator.validate_animation_xml(invalid_xml)

    def test_animation_sequence_generation(self):
        """Test generation of animation sequences."""
        configs = [
            PowerPointAnimationConfig(
                effect_type=PowerPointEffectType.FADE_IN,
                duration_ms=1000,
                target_element_id="elem1"
            ),
            PowerPointAnimationConfig(
                effect_type=PowerPointEffectType.COLOR_CHANGE,
                duration_ms=1500,
                delay_ms=1000,
                target_element_id="elem2"
            )
        ]

        sequence_xml = self.generator.generate_animation_sequence(configs)

        assert '<a:seq>' in sequence_xml
        assert '<a:childTnLst>' in sequence_xml
        assert sequence_xml.count('<a:animEffect>') == 1
        assert sequence_xml.count('<a:animClr>') == 1


class TestAnimationConverterPowerPoint:
    """Test AnimationConverter PowerPoint integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_services = Mock()
        self.converter = AnimationConverter(self.mock_services)

    def test_opacity_animation_conversion(self):
        """Test conversion of opacity animation to PowerPoint."""
        # Create test SMIL element
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <circle id="test-circle" cx="50" cy="50" r="20">
                    <animate attributeName="opacity" values="0;1;0" dur="2s" repeatCount="indefinite"/>
                </circle>
            </svg>
        ''')

        animate_element = svg_element.find('.//{http://www.w3.org/2000/svg}animate')
        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        # Test conversion
        result = self.converter.convert(animate_element, context)

        assert result is not None
        assert len(result) > 0
        assert '<a:animEffect>' in result
        assert 'dur="2000"' in result  # 2s converted to milliseconds

    def test_color_animation_conversion(self):
        """Test conversion of color animation to PowerPoint."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <rect id="test-rect" x="0" y="0" width="100" height="50">
                    <animate attributeName="fill" values="#FF0000;#00FF00;#0000FF" dur="3s"/>
                </rect>
            </svg>
        ''')

        animate_element = svg_element.find('.//{http://www.w3.org/2000/svg}animate')
        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        result = self.converter.convert(animate_element, context)

        assert '<a:animClr>' in result
        assert 'val="FF0000"' in result  # First color
        assert 'val="0000FF"' in result  # Last color

    def test_transform_animation_conversion(self):
        """Test conversion of transform animation to PowerPoint."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <rect id="test-rect" x="10" y="10" width="50" height="30">
                    <animateTransform attributeName="transform" type="rotate"
                                      values="0 35 25;360 35 25" dur="4s" repeatCount="indefinite"/>
                </rect>
            </svg>
        ''')

        animate_element = svg_element.find('.//{http://www.w3.org/2000/svg}animateTransform')
        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        result = self.converter.convert(animate_element, context)

        assert '<a:animRot>' in result
        assert 'val="21600000"' in result  # 360 degrees in PowerPoint units

    def test_motion_path_animation_conversion(self):
        """Test conversion of motion path animation to PowerPoint."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <circle id="moving-circle" cx="10" cy="10" r="5">
                    <animateMotion path="M 0,0 Q 50,25 100,0" dur="3s"/>
                </circle>
            </svg>
        ''')

        animate_element = svg_element.find('.//{http://www.w3.org/2000/svg}animateMotion')
        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        result = self.converter.convert(animate_element, context)

        assert '<a:animMotion>' in result
        assert 'dur="3000"' in result

    def test_timing_conversion(self):
        """Test proper conversion of SMIL timing to PowerPoint timing."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <rect id="test-rect">
                    <animate attributeName="opacity" values="0;1" dur="1.5s" begin="0.8s"/>
                </rect>
            </svg>
        ''')

        animate_element = svg_element.find('.//{http://www.w3.org/2000/svg}animate')
        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        result = self.converter.convert(animate_element, context)

        assert 'dur="1500"' in result   # 1.5s to milliseconds
        assert 'delay="800"' in result  # 0.8s to milliseconds

    def test_invalid_animation_handling(self):
        """Test handling of invalid or unsupported animations."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <rect id="test-rect">
                    <animate attributeName="unknown-attr" values="a;b;c" dur="1s"/>
                </rect>
            </svg>
        ''')

        animate_element = svg_element.find('.//{http://www.w3.org/2000/svg}animate')
        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        result = self.converter.convert(animate_element, context)

        # Should still generate some form of animation (emphasis effect)
        assert result is not None
        assert len(result) > 0

    def test_animation_storage(self):
        """Test that animations are properly stored for later processing."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <circle id="test-circle">
                    <animate attributeName="opacity" values="0;1" dur="2s"/>
                </circle>
            </svg>
        ''')

        animate_element = svg_element.find('.//{http://www.w3.org/2000/svg}animate')
        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        # Initially no animations stored
        assert len(self.converter.animations) == 0

        # Convert animation
        self.converter.convert(animate_element, context)

        # Animation should be stored
        assert len(self.converter.animations) == 1
        assert self.converter.animations[0].target_attribute == "opacity"

    def test_multiple_animations_processing(self):
        """Test processing multiple animations from the same element."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <rect id="multi-anim">
                    <animate attributeName="opacity" values="0;1" dur="1s"/>
                    <animate attributeName="fill" values="red;blue" dur="2s"/>
                    <animateTransform attributeName="transform" type="scale" values="1;2" dur="1.5s"/>
                </rect>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        results = []

        for animate_elem in svg_element.findall('.//{http://www.w3.org/2000/svg}animate'):
            result = self.converter.convert(animate_elem, context)
            results.append(result)

        for animate_elem in svg_element.findall('.//{http://www.w3.org/2000/svg}animateTransform'):
            result = self.converter.convert(animate_elem, context)
            results.append(result)

        # All animations should generate XML
        assert len(results) == 3
        assert all(len(result) > 0 for result in results)

        # Check that different animation types are generated
        all_xml = ''.join(results)
        assert '<a:animEffect>' in all_xml  # Opacity animation
        assert '<a:animClr>' in all_xml     # Color animation
        assert '<a:animScale>' in all_xml   # Scale animation


@pytest.fixture
def sample_smil_animations():
    """Provide sample SMIL animation elements for testing."""
    return {
        'fade': '''<animate attributeName="opacity" values="0;1;0" dur="2s" repeatCount="indefinite"/>''',
        'color': '''<animate attributeName="fill" values="#FF0000;#00FF00;#0000FF" dur="3s"/>''',
        'rotate': '''<animateTransform attributeName="transform" type="rotate" values="0;360" dur="4s"/>''',
        'scale': '''<animateTransform attributeName="transform" type="scale" values="1;1.5;1" dur="2s"/>''',
        'motion': '''<animateMotion path="M 0,0 Q 50,25 100,0" dur="3s"/>'''
    }


class TestPowerPointAnimationIntegration:
    """Integration tests for PowerPoint animation system."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.mock_services = Mock()
        self.converter = AnimationConverter(self.mock_services)

    def test_end_to_end_animation_processing(self, sample_smil_animations):
        """Test complete animation processing pipeline."""
        svg_template = '''<svg xmlns="http://www.w3.org/2000/svg">
            <rect id="test-element">{animation}</rect>
        </svg>'''

        for anim_type, anim_xml in sample_smil_animations.items():
            svg_content = svg_template.format(animation=anim_xml)
            svg_element = etree.fromstring(svg_content)

            animate_elements = svg_element.xpath('.//*[local-name()="animate" or local-name()="animateTransform" or local-name()="animateMotion"]')

            assert len(animate_elements) == 1

            context = ConversionContext(services=self.mock_services, svg_root=svg_element)
            result = self.converter.convert(animate_elements[0], context)

            # All animations should generate valid XML
            assert result is not None
            assert len(result) > 0
            assert self.converter.powerpoint_generator.validate_animation_xml(result)

    def test_performance_with_many_animations(self):
        """Test performance with multiple animations."""
        import time

        # Create SVG with many animations
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg">'''
        for i in range(50):  # 50 animations
            svg_content += f'''
                <rect id="rect{i}">
                    <animate attributeName="opacity" values="0;1" dur="{i+1}s"/>
                </rect>'''
        svg_content += '</svg>'

        svg_element = etree.fromstring(svg_content)
        animate_elements = svg_element.findall('.//{http://www.w3.org/2000/svg}animate')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        start_time = time.time()
        results = []
        for elem in animate_elements:
            result = self.converter.convert(elem, context)
            results.append(result)

        processing_time = time.time() - start_time

        # Should process quickly (under 1 second for 50 animations)
        assert processing_time < 1.0
        assert len(results) == 50
        assert all(len(result) > 0 for result in results)