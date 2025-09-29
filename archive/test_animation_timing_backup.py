#!/usr/bin/env python3
"""
Unit tests for advanced animation timing features in AnimationConverter.

Tests the parsing and conversion of complex SMIL timing relationships,
including animation chains, timing references, and sequence generation.
"""

import pytest
from unittest.mock import Mock
from lxml import etree

# Import from new animation system bridge
from src.converters.animation_converter import AnimationConverter
from src.converters.timing import (
    AdvancedTimingConverter, TimingReference, PowerPointTimingGenerator,
    TimingEventType, AnimationTimeline
)
from src.converters.base import ConversionContext
from src.services.conversion_services import ConversionServices


class TestTimingReference:
    """Test SMIL timing reference parsing."""

    def test_absolute_time_parsing(self):
        """Test parsing absolute time values."""
        # Basic seconds
        ref = TimingReference.parse("2s")
        assert ref.event_type == TimingEventType.ABSOLUTE_TIME
        assert ref.offset == 2.0
        assert ref.element_id is None

        # Milliseconds
        ref = TimingReference.parse("1500ms")
        assert ref.offset == 1.5

        # Minutes
        ref = TimingReference.parse("1.5min")
        assert ref.offset == 90.0  # 1.5 * 60

        # Hours
        ref = TimingReference.parse("1h")
        assert ref.offset == 3600.0

    def test_negative_time_parsing(self):
        """Test parsing negative begin times."""
        ref = TimingReference.parse("-2s")
        assert ref.event_type == TimingEventType.ABSOLUTE_TIME
        assert ref.offset == -2.0

    def test_element_reference_parsing(self):
        """Test parsing element timing references."""
        # Element end reference
        ref = TimingReference.parse("anim1.end")
        assert ref.event_type == TimingEventType.ELEMENT_END
        assert ref.element_id == "anim1"
        assert ref.offset == 0.0

        # Element begin reference
        ref = TimingReference.parse("myAnimation.begin")
        assert ref.event_type == TimingEventType.ELEMENT_BEGIN
        assert ref.element_id == "myAnimation"

        # Element reference with offset
        ref = TimingReference.parse("anim1.end + 0.5s")
        assert ref.event_type == TimingEventType.ELEMENT_END
        assert ref.element_id == "anim1"
        assert ref.offset == 0.5

    def test_special_value_parsing(self):
        """Test parsing special timing values."""
        # Indefinite
        ref = TimingReference.parse("indefinite")
        assert ref.event_type == TimingEventType.INDEFINITE

        # Click event
        ref = TimingReference.parse("click")
        assert ref.event_type == TimingEventType.CLICK_EVENT

    def test_empty_and_invalid_parsing(self):
        """Test parsing empty and invalid timing strings."""
        # Empty string
        ref = TimingReference.parse("")
        assert ref.event_type == TimingEventType.ABSOLUTE_TIME
        assert ref.offset == 0.0

        # None
        ref = TimingReference.parse(None)
        assert ref.event_type == TimingEventType.ABSOLUTE_TIME
        assert ref.offset == 0.0


class TestAdvancedTimingConverter:
    """Test advanced timing converter functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = AdvancedTimingConverter()

    def test_simple_timeline_calculation(self):
        """Test timeline calculation for simple animations."""
        # Register two sequential animations
        self.converter.register_animation(
            "anim1", duration=2.0,
            begin_reference=TimingReference(None, TimingEventType.ABSOLUTE_TIME, 0.0)
        )
        self.converter.register_animation(
            "anim2", duration=1.5,
            begin_reference=TimingReference(None, TimingEventType.ABSOLUTE_TIME, 1.0)
        )

        timeline = self.converter.calculate_animation_timeline()

        assert len(timeline) == 2
        assert timeline[0].animation_id == "anim1"
        assert timeline[0].start_time == 0.0
        assert timeline[0].end_time == 2.0

        assert timeline[1].animation_id == "anim2"
        assert timeline[1].start_time == 1.0
        assert timeline[1].end_time == 2.5

    def test_animation_chain_timeline(self):
        """Test timeline calculation for chained animations."""
        # First animation
        self.converter.register_animation(
            "anim1", duration=2.0,
            begin_reference=TimingReference(None, TimingEventType.ABSOLUTE_TIME, 0.0)
        )

        # Second animation starts when first ends
        self.converter.register_animation(
            "anim2", duration=1.5,
            begin_reference=TimingReference("anim1", TimingEventType.ELEMENT_END, 0.0)
        )

        # Third animation starts when first ends with offset
        self.converter.register_animation(
            "anim3", duration=1.0,
            begin_reference=TimingReference("anim1", TimingEventType.ELEMENT_END, 0.5)
        )

        timeline = self.converter.calculate_animation_timeline()

        assert len(timeline) == 3

        # Check timing relationships
        anim1 = next(t for t in timeline if t.animation_id == "anim1")
        anim2 = next(t for t in timeline if t.animation_id == "anim2")
        anim3 = next(t for t in timeline if t.animation_id == "anim3")

        assert anim1.start_time == 0.0
        assert anim1.end_time == 2.0

        assert anim2.start_time == 2.0  # Starts when anim1 ends
        assert anim2.end_time == 3.5

        assert anim3.start_time == 2.5  # Starts 0.5s after anim1 ends
        assert anim3.end_time == 3.5

    def test_indefinite_repeat_handling(self):
        """Test handling of indefinite repeat counts."""
        self.converter.register_animation(
            "loop_anim", duration=1.0,
            begin_reference=TimingReference(None, TimingEventType.ABSOLUTE_TIME, 0.0),
            repeat_count="indefinite"
        )

        timeline = self.converter.calculate_animation_timeline()

        assert len(timeline) == 1
        assert timeline[0].end_time == float('inf')

    def test_dependency_validation(self):
        """Test validation of timing dependencies."""
        # Valid dependency
        self.converter.register_animation(
            "anim1", duration=1.0,
            begin_reference=TimingReference(None, TimingEventType.ABSOLUTE_TIME, 0.0)
        )
        self.converter.register_animation(
            "anim2", duration=1.0,
            begin_reference=TimingReference("anim1", TimingEventType.ELEMENT_END, 0.0)
        )

        issues = self.converter.validate_timing_references()
        assert len(issues) == 0

        # Invalid dependency (missing reference)
        self.converter.register_animation(
            "anim3", duration=1.0,
            begin_reference=TimingReference("nonexistent", TimingEventType.ELEMENT_END, 0.0)
        )

        issues = self.converter.validate_timing_references()
        assert len(issues) == 1
        assert "nonexistent" in issues[0]

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        # Create circular dependency: anim1 → anim2 → anim1
        self.converter.register_animation(
            "anim1", duration=1.0,
            begin_reference=TimingReference("anim2", TimingEventType.ELEMENT_END, 0.0)
        )
        self.converter.register_animation(
            "anim2", duration=1.0,
            begin_reference=TimingReference("anim1", TimingEventType.ELEMENT_END, 0.0)
        )

        issues = self.converter.validate_timing_references()
        assert len(issues) > 0
        assert any("circular" in issue.lower() for issue in issues)

    def test_powerpoint_sequence_generation(self):
        """Test generation of PowerPoint timing sequence."""
        # Register some animations
        self.converter.register_animation(
            "anim1", duration=2.0,
            begin_reference=TimingReference(None, TimingEventType.ABSOLUTE_TIME, 0.0)
        )
        self.converter.register_animation(
            "anim2", duration=1.5,
            begin_reference=TimingReference("anim1", TimingEventType.ELEMENT_END, 0.5)
        )

        timeline = self.converter.calculate_animation_timeline()
        sequence_config = self.converter.generate_powerpoint_timing_sequence(timeline)

        assert 'animations' in sequence_config
        assert len(sequence_config['animations']) == 2
        assert sequence_config['total_duration'] == 4.0  # anim2 ends at 4.0s

        # Check timing configuration
        anim1_config = sequence_config['animations'][0]
        assert anim1_config['delay_ms'] == 0
        assert anim1_config['duration_ms'] == 2000

        anim2_config = sequence_config['animations'][1]
        assert anim2_config['delay_ms'] == 2500  # Starts at 2.5s
        assert anim2_config['duration_ms'] == 1500


class TestPowerPointTimingGenerator:
    """Test PowerPoint timing XML generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = PowerPointTimingGenerator()

    def test_sequence_xml_generation(self):
        """Test generation of PowerPoint sequence XML."""
        sequence_config = {
            'animations': [
                {
                    'animation_id': 'anim1',
                    'delay_ms': 0,
                    'duration_ms': 2000,
                    'dependencies': [],
                    'start_time': 0.0,
                    'end_time': 2.0
                },
                {
                    'animation_id': 'anim2',
                    'delay_ms': 2000,
                    'duration_ms': 1500,
                    'dependencies': ['anim1'],
                    'start_time': 2.0,
                    'end_time': 3.5
                }
            ],
            'total_duration': 3.5,
            'has_indefinite': False
        }

        xml = self.generator.generate_sequence_xml(sequence_config)

        assert xml is not None
        assert len(xml) > 0
        assert '<a:seq>' in xml
        assert '<a:childTnLst>' in xml
        assert 'dur="2000"' in xml
        assert 'delay="2000"' in xml

    def test_parallel_group_xml_generation(self):
        """Test generation of parallel animation group XML."""
        parallel_animations = [
            {
                'animation_id': 'anim1',
                'delay_ms': 0,
                'duration_ms': 1000,
                'start_time': 0.0,
                'end_time': 1.0
            },
            {
                'animation_id': 'anim2',
                'delay_ms': 0,
                'duration_ms': 1500,
                'start_time': 0.0,
                'end_time': 1.5
            }
        ]

        xml = self.generator.generate_parallel_group_xml(parallel_animations)

        assert '<a:par>' in xml
        assert xml.count('<a:cTn') == 3  # One for group, two for animations

    def test_empty_sequence_handling(self):
        """Test handling of empty animation sequences."""
        empty_config = {'animations': []}
        xml = self.generator.generate_sequence_xml(empty_config)
        assert xml == ""


class TestAnimationConverterTiming:
    """Integration tests for animation converter timing features."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_services = Mock()
        self.converter = AnimationConverter(self.mock_services)

    def test_advanced_timing_parsing(self):
        """Test parsing of advanced timing attributes."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <rect id="rect1">
                    <animate id="anim1" attributeName="opacity" values="0;1" dur="2s"/>
                </rect>
                <circle id="circle1">
                    <animate attributeName="r" values="10;20" dur="1.5s" begin="anim1.end"/>
                </circle>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        # Process first animation
        anim1 = svg_element.find('.//{http://www.w3.org/2000/svg}animate[@id="anim1"]')
        result1 = self.converter.convert(anim1, context)
        assert len(result1) > 0

        # Process second animation
        anim2 = svg_element.find('.//{http://www.w3.org/2000/svg}animate[@attributeName="r"]')
        result2 = self.converter.convert(anim2, context)
        assert len(result2) > 0

        # Check that animations were stored
        assert len(self.converter.animations) == 2

    def test_duration_constraints_parsing(self):
        """Test parsing of min/max duration constraints."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <rect id="constrained-rect">
                    <animate attributeName="width" values="10;50" dur="2s" min="1s" max="3s"/>
                </rect>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animate')

        result = self.converter.convert(animate_elem, context)
        assert len(result) > 0

        # Check that animation was processed with constraints
        assert len(self.converter.animations) == 1
        animation = self.converter.animations[0]
        assert animation.timing.duration == 2.0  # Within constraints

    def test_negative_begin_time_handling(self):
        """Test handling of negative begin times."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <circle id="prestarted-circle">
                    <animate attributeName="opacity" values="0.5;1" dur="3s" begin="-1s"/>
                </circle>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)
        animate_elem = svg_element.find('.//{http://www.w3.org/2000/svg}animate')

        result = self.converter.convert(animate_elem, context)
        assert len(result) > 0

    def test_animation_sequence_processing(self):
        """Test processing of complete animation sequences."""
        svg_element = etree.fromstring('''
            <svg xmlns="http://www.w3.org/2000/svg">
                <rect id="rect1">
                    <animate id="fade1" attributeName="opacity" values="0;1" dur="1s"/>
                </rect>
                <rect id="rect2">
                    <animate attributeName="opacity" values="1;0" dur="1s" begin="fade1.end"/>
                </rect>
                <rect id="rect3">
                    <animate attributeName="fill" values="red;blue" dur="0.5s" begin="fade1.end + 0.5s"/>
                </rect>
            </svg>
        ''')

        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        # Process all animations
        for animate_elem in svg_element.findall('.//{http://www.w3.org/2000/svg}animate'):
            self.converter.convert(animate_elem, context)

        # Process as sequence
        sequence_xml = self.converter.process_animation_sequence(context)

        assert sequence_xml is not None
        assert len(sequence_xml) > 0
        assert '<a:seq>' in sequence_xml

        # Should contain timing structure
        assert '<a:childTnLst>' in sequence_xml

    @pytest.mark.parametrize("timing_str,expected_valid", [
        ("2s", True),
        ("anim1.end", True),
        ("anim1.begin + 0.5s", True),
        ("-1s", True),
        ("indefinite", True),
        ("click", True),
        ("invalid.syntax", True),  # Will be parsed, may not be valid
        ("", True),
    ])
    def test_timing_reference_parsing_variations(self, timing_str, expected_valid):
        """Test parsing various timing reference formats."""
        try:
            ref = TimingReference.parse(timing_str)
            assert expected_valid
            assert ref is not None
        except Exception:
            assert not expected_valid


class TestTimingIntegration:
    """Integration tests for complete timing system."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.mock_services = Mock()
        self.converter = AnimationConverter(self.mock_services)

    def test_complex_timing_scenario(self):
        """Test a complex animation timing scenario."""
        # Use our advanced timing controls test file
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300">
            <rect id="rect1">
                <animate id="anim1" attributeName="opacity" values="1;0" dur="1s"/>
            </rect>
            <circle id="circle1">
                <animate attributeName="r" values="10;20;10" dur="1.5s" begin="anim1.end"/>
            </circle>
            <polygon id="poly1">
                <animateTransform attributeName="transform" type="rotate"
                                  values="0 130 155;360 130 155" dur="2s" begin="anim1.end"/>
            </polygon>
        </svg>'''

        svg_element = etree.fromstring(svg_content)
        context = ConversionContext(services=self.mock_services, svg_root=svg_element)

        # Process all animations
        animation_elements = svg_element.xpath('.//*[local-name()="animate" or local-name()="animateTransform"]')

        for elem in animation_elements:
            result = self.converter.convert(elem, context)
            assert len(result) > 0

        # Process sequence
        sequence_xml = self.converter.process_animation_sequence(context)

        assert sequence_xml is not None
        assert len(sequence_xml) > 0

        # Validate that timing relationships are preserved
        assert '<a:seq>' in sequence_xml

        # Should have proper animation count
        assert len(self.converter.animations) == 3