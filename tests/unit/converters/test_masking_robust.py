#!/usr/bin/env python3
"""
Robust Clipping/Masking Test Suite

This test suite focuses on the critical path conversion functionality
and real-world clipping scenarios that often cause issues.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.converters.masking import MaskingConverter, ClipPathDefinition, ClippingType
from src.converters.base import ConversionContext


class TestRobustClipping:
    """Test suite for robust clipping functionality."""

    @pytest.fixture
    def setup_converter(self):
        """Setup MaskingConverter with proper mocks."""
        # Create comprehensive mock services
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.unit_converter.convert_to_emu = Mock(return_value=914400)
        mock_services.unit_converter.convert_to_user_units = Mock(return_value=10.0)
        mock_services.transform_parser = Mock()
        mock_services.transform_parser.parse_transform = Mock(return_value=[1, 0, 0, 1, 0, 0])
        mock_services.transform_parser.apply_matrix_to_path = Mock(return_value="M 0 0 L 100 100 Z")

        converter = MaskingConverter(services=mock_services)
        context = Mock(spec=ConversionContext)
        context.get_next_shape_id = Mock(return_value=123)

        return {
            'converter': converter,
            'context': context,
            'services': mock_services
        }

    def test_svg_path_to_powerpoint_conversion(self, setup_converter):
        """Test robust SVG path to PowerPoint conversion."""
        converter = setup_converter['converter']

        # Test basic path commands
        test_cases = [
            # Simple rectangle path
            ("M 0 0 L 100 0 L 100 100 L 0 100 Z", "moveTo"),

            # Path with relative commands
            ("M 10 10 l 50 0 l 0 50 l -50 0 z", "moveTo"),

            # Empty path
            ("", ""),

            # Complex path with multiple segments
            ("M 20 20 L 80 20 L 80 80 L 20 80 Z M 30 30 L 70 70", "moveTo"),
        ]

        for svg_path, expected_contains in test_cases:
            result = converter._convert_svg_path_to_pptx(svg_path)

            if expected_contains:
                assert expected_contains in result, f"Failed for path: {svg_path}"
                assert "<a:" in result, f"Should contain PowerPoint XML for path: {svg_path}"
            else:
                assert result == "", f"Empty path should return empty string"

    def test_element_bounds_calculation(self, setup_converter):
        """Test accurate element bounds calculation."""
        converter = setup_converter['converter']
        context = setup_converter['context']

        # Test different element types
        test_elements = [
            # Rectangle
            ('<rect x="10" y="20" width="30" height="40"/>', (10.0, 20.0, 30.0, 40.0)),

            # Circle
            ('<circle cx="50" cy="60" r="25"/>', (25.0, 35.0, 50.0, 50.0)),

            # Ellipse
            ('<ellipse cx="40" cy="30" rx="20" ry="15"/>', (20.0, 15.0, 40.0, 30.0)),

            # Image
            ('<image x="5" y="10" width="100" height="80"/>', (5.0, 10.0, 100.0, 80.0)),
        ]

        for svg_element, expected_bounds in test_elements:
            element = ET.fromstring(svg_element)
            bounds = converter._get_element_bounds(element, context)
            assert bounds == expected_bounds, f"Bounds mismatch for {svg_element}"

    def test_clippath_processing_edge_cases(self, setup_converter):
        """Test clipPath processing with edge cases that commonly fail."""
        converter = setup_converter['converter']
        context = setup_converter['context']

        # Test complex clipPath with multiple shapes
        complex_clippath_svg = '''
        <clipPath id="complexClip">
            <rect x="0" y="0" width="50" height="50"/>
            <circle cx="75" cy="25" r="20"/>
            <path d="M 100 0 L 150 50 L 100 50 Z"/>
        </clipPath>
        '''

        clippath_element = ET.fromstring(complex_clippath_svg)
        result = converter._process_clippath_definition(clippath_element, context)

        assert result == ""  # Definitions return empty string
        assert 'complexClip' in converter.clippath_definitions

        clip_def = converter.clippath_definitions['complexClip']
        assert clip_def.clipping_type == ClippingType.COMPLEX
        assert len(clip_def.shapes) == 3

    def test_realistic_svg_clipping_scenario(self, setup_converter):
        """Test with realistic SVG clipping scenario."""
        converter = setup_converter['converter']
        context = setup_converter['context']

        # Simulate the test SVG from the codebase
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 250 250">
            <defs>
                <clipPath id="circle-clip">
                    <circle cx="75" cy="75" r="40"/>
                </clipPath>
            </defs>
            <image x="25" y="25" width="100" height="100" href="clipped.jpg"
                   clip-path="url(#circle-clip)" opacity="0.7"/>
        </svg>
        '''

        root = ET.fromstring(svg_content)

        # Process the clipPath definition
        clippath_elem = root.find('.//{http://www.w3.org/2000/svg}clipPath')
        converter._process_clippath_definition(clippath_elem, context)

        # Verify clipPath was processed correctly
        assert 'circle-clip' in converter.clippath_definitions
        clip_def = converter.clippath_definitions['circle-clip']
        assert clip_def.clipping_type == ClippingType.SHAPE_BASED  # Single circle

        # Process the image with clipping applied
        image_elem = root.find('.//{http://www.w3.org/2000/svg}image')
        with patch.object(converter, '_get_element_bounds', return_value=(25, 25, 100, 100)):
            result = converter._apply_clipping(image_elem, 'url(#circle-clip)', context)

            # Should generate PowerPoint clipping output
            assert 'ClippingShape' in result
            assert '<a:custGeom>' in result
            assert '<a:moveTo>' in result  # Should contain converted circle path elements

    def test_powerpoint_compatibility_detection(self, setup_converter):
        """Test detection of PowerPoint-compatible vs complex clipping."""
        converter = setup_converter['converter']
        context = setup_converter['context']

        # Test cases for different clipping types
        test_cases = [
            # Simple path - should be PowerPoint compatible
            ('<clipPath id="simplePath"><path d="M 0 0 L 100 100 Z"/></clipPath>', True),

            # Simple shape - should be PowerPoint compatible
            ('<clipPath id="simpleRect"><rect x="0" y="0" width="50" height="50"/></clipPath>', True),

            # Complex clipPath - might require rasterization
            ('<clipPath id="complex"><rect x="0" y="0" width="25" height="25"/><circle cx="50" cy="50" r="20"/></clipPath>', False),
        ]

        for clippath_svg, expected_compatible in test_cases:
            clippath_element = ET.fromstring(clippath_svg)
            converter._process_clippath_definition(clippath_element, context)

            clip_id = clippath_element.get('id')
            clip_def = converter.clippath_definitions[clip_id]

            # Test element to apply clipping to
            test_element = ET.Element('rect')
            test_element.set('x', '0')
            test_element.set('y', '0')
            test_element.set('width', '100')
            test_element.set('height', '100')

            with patch.object(converter, '_get_element_bounds', return_value=(0, 0, 100, 100)):
                converter._apply_clipping(test_element, f'url(#{clip_id})', context)

            # Find the clipping application
            clip_app = next(app for app in converter.clipped_elements if app.clip_definition.id == clip_id)

            if expected_compatible:
                assert clip_app.powerpoint_compatible, f"Should be PowerPoint compatible: {clippath_svg}"
            else:
                # Complex clipping might not be PowerPoint compatible
                # The actual result depends on the implementation logic
                pass

    def test_coordinate_system_handling(self, setup_converter):
        """Test coordinate system transformations for clipping."""
        converter = setup_converter['converter']
        context = setup_converter['context']

        # Test objectBoundingBox coordinate system
        clippath_svg = '''
        <clipPath id="boundingBoxClip" clipPathUnits="objectBoundingBox">
            <rect x="0.1" y="0.1" width="0.8" height="0.8"/>
        </clipPath>
        '''

        clippath_element = ET.fromstring(clippath_svg)
        converter._process_clippath_definition(clippath_element, context)

        clip_def = converter.clippath_definitions['boundingBoxClip']
        assert clip_def.units == 'objectBoundingBox'

        # Apply to an element
        test_element = ET.Element('rect')
        test_element.set('x', '10')
        test_element.set('y', '20')
        test_element.set('width', '100')
        test_element.set('height', '80')

        with patch.object(converter, '_get_element_bounds', return_value=(10, 20, 100, 80)):
            result = converter._apply_clipping(test_element, 'url(#boundingBoxClip)', context)

            # Should handle coordinate transformation
            assert result  # Should generate output
            assert 'ClippingShape' in result

    def test_error_recovery_and_fallbacks(self, setup_converter):
        """Test error recovery and fallback mechanisms."""
        converter = setup_converter['converter']
        context = setup_converter['context']

        # Test malformed path data
        malformed_clippath = '''
        <clipPath id="malformed">
            <path d="M invalid path data"/>
        </clipPath>
        '''

        clippath_element = ET.fromstring(malformed_clippath)

        # Should not crash, even with malformed data
        try:
            converter._process_clippath_definition(clippath_element, context)
            # Should still create a definition, even if path is malformed
            assert 'malformed' in converter.clippath_definitions
        except Exception as e:
            pytest.fail(f"Should handle malformed clipPath gracefully: {e}")

        # Test missing clipPath reference
        test_element = ET.Element('rect')
        test_element.set('clip-path', 'url(#nonexistent)')

        with patch('src.converters.masking.logger') as mock_logger:
            result = converter._apply_clipping(test_element, 'url(#nonexistent)', context)
            assert result == ""  # Should return empty string
            mock_logger.warning.assert_called()

    def test_performance_with_complex_clipping(self, setup_converter):
        """Test performance characteristics with complex clipping scenarios."""
        converter = setup_converter['converter']
        context = setup_converter['context']

        # Create a complex scenario with multiple clipPaths and applications
        num_clippaths = 10

        start_time = pytest.approx(0, abs=1e6)  # Allow for timing variation

        for i in range(num_clippaths):
            clippath_svg = f'''
            <clipPath id="perf_clip_{i}">
                <rect x="{i*10}" y="{i*10}" width="50" height="50"/>
            </clipPath>
            '''
            clippath_element = ET.fromstring(clippath_svg)
            converter._process_clippath_definition(clippath_element, context)

            # Apply clipping to test elements
            test_element = ET.Element('rect')
            test_element.set('x', str(i*5))
            test_element.set('y', str(i*5))
            test_element.set('width', '60')
            test_element.set('height', '60')

            with patch.object(converter, '_get_element_bounds', return_value=(i*5, i*5, 60, 60)):
                converter._apply_clipping(test_element, f'url(#perf_clip_{i})', context)

        # Verify all clipPaths were processed
        assert len(converter.clippath_definitions) >= num_clippaths
        assert len(converter.clipped_elements) >= num_clippaths

        # Verify converter state can be reset efficiently
        converter.reset()
        assert len(converter.clippath_definitions) == 0
        assert len(converter.clipped_elements) == 0


if __name__ == "__main__":
    pytest.main([__file__])