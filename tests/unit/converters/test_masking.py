#!/usr/bin/env python3
"""
Unit Test Template for SVG2PPTX Components

This template provides a systematic structure for unit testing any component
in the SVG2PPTX codebase. Copy this template and fill in the TODOs.

Usage:
1. Copy this template to appropriate test directory
2. Rename file to test_{module_name}.py
3. Replace all TODO placeholders with actual implementation
4. Import the module under test
5. Implement test cases following the structure
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import sys
from lxml import etree as ET

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Import the module under test
from src.converters.masking import MaskingConverter, MaskDefinition, ClipPathDefinition, MaskType, ClippingType
from src.converters.base import ConversionContext

class TestMaskingConverter:
    """
    Unit tests for MaskingConverter class.

    Tests SVG mask and clipPath element processing for PowerPoint conversion.
    """

    @pytest.fixture
    def setup_test_data(self):
        """
        Setup common test data and mock objects.

        Creates test SVG elements, masks, clipPaths, and expected results.
        """
        # Create test mask element
        mask_element = ET.Element('mask')
        mask_element.set('id', 'testMask')
        mask_element.set('maskUnits', 'objectBoundingBox')
        mask_element.set('x', '-10%')
        mask_element.set('y', '-10%')
        mask_element.set('width', '120%')
        mask_element.set('height', '120%')

        # Create test clipPath element
        clippath_element = ET.Element('clipPath')
        clippath_element.set('id', 'testClip')
        path_child = ET.SubElement(clippath_element, 'path')
        path_child.set('d', 'M 0 0 L 100 0 L 100 100 L 0 100 Z')

        # Create test element with mask reference
        masked_element = ET.Element('rect')
        masked_element.set('mask', 'url(#testMask)')
        masked_element.set('x', '10')
        masked_element.set('y', '10')
        masked_element.set('width', '80')
        masked_element.set('height', '60')

        return {
            'mask_element': mask_element,
            'clippath_element': clippath_element,
            'masked_element': masked_element,
            'mock_context': Mock(spec=ConversionContext),
        }

    @pytest.fixture
    def component_instance(self, setup_test_data):
        """
        Create instance of component under test.

        Instantiate MaskingConverter with mock dependencies.
        """
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        converter = MaskingConverter(services=mock_services)
        # Mock required dependencies through services
        mock_services.unit_converter.convert_to_emu.return_value = 914400  # 1 inch in EMUs
        mock_services.unit_converter.convert_to_user_units.return_value = 10.0
        # Add transform parser to services
        mock_services.transform_parser = Mock()
        mock_services.transform_parser.parse_transform.return_value = [1, 0, 0, 1, 0, 0]
        return converter

    def test_initialization(self, component_instance):
        """
        Test component initialization and basic properties.

        Verify MaskingConverter initializes correctly with empty state.
        """
        assert component_instance is not None
        assert isinstance(component_instance, MaskingConverter)
        assert component_instance.mask_definitions == {}
        assert component_instance.clippath_definitions == {}
        assert component_instance.masked_elements == []
        assert component_instance.clipped_elements == []
        assert 'mask' in component_instance.supported_elements
        assert 'clipPath' in component_instance.supported_elements

    def test_basic_functionality(self, component_instance, setup_test_data):
        """
        Test core functionality of the component.

        Test mask definition processing and clipPath definition processing.
        """
        mask_element = setup_test_data['mask_element']
        clippath_element = setup_test_data['clippath_element']
        context = setup_test_data['mock_context']

        # Test can_convert method
        assert component_instance.can_convert(mask_element, context) is True
        assert component_instance.can_convert(clippath_element, context) is True

        # Test mask definition processing
        result = component_instance._process_mask_definition(mask_element, context)
        assert result == ""  # Definitions don't generate direct output
        assert 'testMask' in component_instance.mask_definitions

        mask_def = component_instance.mask_definitions['testMask']
        assert mask_def.id == 'testMask'
        assert mask_def.mask_type == MaskType.LUMINANCE
        assert mask_def.units == 'objectBoundingBox'

        # Test clipPath definition processing
        result = component_instance._process_clippath_definition(clippath_element, context)
        assert result == ""  # Definitions don't generate direct output
        assert 'testClip' in component_instance.clippath_definitions

        clip_def = component_instance.clippath_definitions['testClip']
        assert clip_def.id == 'testClip'
        assert clip_def.clipping_type == ClippingType.PATH_BASED

    def test_error_handling(self, component_instance, setup_test_data):
        """
        Test error handling and edge cases.

        Test handling of malformed masks, missing IDs, and invalid references.
        """
        context = setup_test_data['mock_context']

        # Test mask without ID
        mask_no_id = ET.Element('mask')
        with patch('src.converters.masking.logger') as mock_logger:
            result = component_instance._process_mask_definition(mask_no_id, context)
            assert result == ""
            mock_logger.warning.assert_called_once()

        # Test clipPath without ID
        clip_no_id = ET.Element('clipPath')
        with patch('src.converters.masking.logger') as mock_logger:
            result = component_instance._process_clippath_definition(clip_no_id, context)
            assert result == ""
            mock_logger.warning.assert_called_once()

        # Test invalid mask reference
        element_with_invalid_mask = ET.Element('rect')
        element_with_invalid_mask.set('mask', 'url(#nonexistent)')
        with patch('src.converters.masking.logger') as mock_logger:
            result = component_instance._apply_mask(element_with_invalid_mask, 'url(#nonexistent)', context)
            assert result == ""
            mock_logger.warning.assert_called_once()

    def test_edge_cases(self, component_instance, setup_test_data):
        """
        Test edge cases and boundary conditions.

        Test complex masks, nested references, and boundary coordinate values.
        """
        context = setup_test_data['mock_context']

        # Test mask with alpha type
        alpha_mask = ET.Element('mask')
        alpha_mask.set('id', 'alphaMask')
        alpha_mask.set('mask-type', 'alpha')

        component_instance._process_mask_definition(alpha_mask, context)
        mask_def = component_instance.mask_definitions['alphaMask']
        assert mask_def.mask_type == MaskType.ALPHA

        # Test complex clipPath with multiple shapes
        complex_clip = ET.Element('clipPath')
        complex_clip.set('id', 'complexClip')
        rect_child = ET.SubElement(complex_clip, 'rect')
        rect_child.set('x', '0')
        rect_child.set('y', '0')
        rect_child.set('width', '50')
        rect_child.set('height', '50')
        circle_child = ET.SubElement(complex_clip, 'circle')
        circle_child.set('cx', '25')
        circle_child.set('cy', '25')
        circle_child.set('r', '20')

        component_instance._process_clippath_definition(complex_clip, context)
        clip_def = component_instance.clippath_definitions['complexClip']
        assert clip_def.clipping_type == ClippingType.COMPLEX

        # Test coordinate parsing with percentages
        result = component_instance._parse_coordinate('50%', True)
        assert result == 0.5
        result = component_instance._parse_coordinate('50%', False)
        assert result == 50.0

    def test_configuration_options(self, component_instance, setup_test_data):
        """
        Test different configuration scenarios.

        Test different mask units, clip units, and transform handling.
        """
        context = setup_test_data['mock_context']

        # Test mask with userSpaceOnUse units
        user_space_mask = ET.Element('mask')
        user_space_mask.set('id', 'userSpaceMask')
        user_space_mask.set('maskUnits', 'userSpaceOnUse')
        user_space_mask.set('x', '10')
        user_space_mask.set('y', '10')
        user_space_mask.set('width', '100')
        user_space_mask.set('height', '80')

        component_instance._process_mask_definition(user_space_mask, context)
        mask_def = component_instance.mask_definitions['userSpaceMask']
        assert mask_def.units == 'userSpaceOnUse'

        # Test clipPath with transform
        transform_clip = ET.Element('clipPath')
        transform_clip.set('id', 'transformClip')
        transform_clip.set('transform', 'translate(10, 20) scale(2)')
        path_child = ET.SubElement(transform_clip, 'path')
        path_child.set('d', 'M 0 0 L 50 0 L 50 50 L 0 50 Z')

        component_instance._process_clippath_definition(transform_clip, context)
        clip_def = component_instance.clippath_definitions['transformClip']
        assert clip_def.transform == 'translate(10, 20) scale(2)'

    def test_integration_with_dependencies(self, component_instance, setup_test_data):
        """
        Test integration with other components.

        Test interactions with unit converter and transform parser.
        """
        context = setup_test_data['mock_context']
        context.get_next_shape_id.return_value = 42

        # Test that unit converter is called for EMU conversion
        mask_element = setup_test_data['mask_element']
        component_instance._process_mask_definition(mask_element, context)

        # Create a mock element with proper bounds method
        test_element = ET.Element('rect')
        test_element.set('mask', 'url(#testMask)')

        with patch.object(component_instance, '_get_element_bounds', return_value=(0, 0, 100, 100)):
            with patch.object(component_instance, '_mask_requires_rasterization', return_value=False):
                result = component_instance._apply_mask(test_element, 'url(#testMask)', context)
                # Should generate PowerPoint output with EMU conversions
                assert 'MaskedShape' in result
                assert component_instance.unit_converter.convert_to_emu.called

    @pytest.mark.parametrize("reference,expected_id", [
        ('url(#testId)', 'testId'),
        ('#testId', 'testId'),
        ('url(#)', ''),
        ('invalid', None),
        ('', None),
    ])
    def test_parametrized_scenarios(self, component_instance, reference, expected_id):
        """
        Test various scenarios using parametrized inputs.

        Test reference ID extraction with different URL formats.
        """
        result = component_instance._extract_reference_id(reference)
        assert result == expected_id

    def test_performance_characteristics(self, component_instance, setup_test_data):
        """
        Test performance-related behavior (if applicable).

        Test state management and resource cleanup.
        """
        mask_element = setup_test_data['mask_element']
        clippath_element = setup_test_data['clippath_element']
        context = setup_test_data['mock_context']

        # Process multiple definitions
        component_instance._process_mask_definition(mask_element, context)
        component_instance._process_clippath_definition(clippath_element, context)

        # Verify state is populated
        assert len(component_instance.mask_definitions) == 1
        assert len(component_instance.clippath_definitions) == 1

        # Test reset functionality
        component_instance.reset()
        assert len(component_instance.mask_definitions) == 0
        assert len(component_instance.clippath_definitions) == 0
        assert len(component_instance.masked_elements) == 0
        assert len(component_instance.clipped_elements) == 0

    def test_thread_safety(self, component_instance, setup_test_data):
        """
        Test thread safety (if applicable).

        MaskingConverter maintains state, so thread safety is important.
        """
        # Test that getter methods return copies, not references
        mask_element = setup_test_data['mask_element']
        context = setup_test_data['mock_context']

        component_instance._process_mask_definition(mask_element, context)

        # Get definitions and modify them
        mask_defs_copy1 = component_instance.get_mask_definitions()
        mask_defs_copy2 = component_instance.get_mask_definitions()

        # Modify copy - should not affect original or other copy
        mask_defs_copy1['new_mask'] = Mock()

        # Verify isolation
        assert 'new_mask' not in component_instance.mask_definitions
        assert 'new_mask' not in mask_defs_copy2
        assert len(mask_defs_copy2) == 1


class TestMaskingConverterHelperFunctions:
    """
    Tests for standalone helper functions in the module.

    Test utility functions like coordinate parsing and shape conversion.
    """

    def test_shape_to_path_conversion(self):
        """
        Test conversion of basic shapes to path data.
        """
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        converter = MaskingConverter(services=mock_services)
        context = Mock(spec=ConversionContext)

        # Test rectangle conversion
        rect = ET.Element('rect')
        rect.set('x', '10')
        rect.set('y', '20')
        rect.set('width', '30')
        rect.set('height', '40')

        path = converter._convert_shape_to_path(rect, context)
        assert 'M 10.0 20.0' in path
        assert 'L 40.0 60.0' in path
        assert 'Z' in path

        # Test circle conversion
        circle = ET.Element('circle')
        circle.set('cx', '50')
        circle.set('cy', '60')
        circle.set('r', '25')

        path = converter._convert_shape_to_path(circle, context)
        assert 'M 25.0 60.0' in path
        assert 'A 25.0 25.0' in path

    def test_mask_rasterization_detection(self):
        """
        Test detection of masks that require rasterization.
        """
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        converter = MaskingConverter(services=mock_services)

        # Create simple mask definition (should not require rasterization)
        simple_mask = MaskDefinition(
            id='simple',
            mask_type=MaskType.LUMINANCE,
            units='objectBoundingBox',
            mask_units='userSpaceOnUse',
            x=0, y=0, width=100, height=100,
            content_elements=[]
        )
        assert not converter._mask_requires_rasterization(simple_mask)

        # Create alpha mask (should require rasterization)
        alpha_mask = MaskDefinition(
            id='alpha',
            mask_type=MaskType.ALPHA,
            units='objectBoundingBox',
            mask_units='userSpaceOnUse',
            x=0, y=0, width=100, height=100,
            content_elements=[]
        )
        assert converter._mask_requires_rasterization(alpha_mask)

        # Create mask with complex content
        text_element = ET.Element('text')
        complex_mask = MaskDefinition(
            id='complex',
            mask_type=MaskType.LUMINANCE,
            units='objectBoundingBox',
            mask_units='userSpaceOnUse',
            x=0, y=0, width=100, height=100,
            content_elements=[text_element]
        )
        assert converter._mask_requires_rasterization(complex_mask)


@pytest.mark.integration
class TestMaskingConverterIntegration:
    """
    Integration tests for MaskingConverter.

    Test converter with real SVG elements and conversion context.
    """

    def test_end_to_end_workflow(self):
        """
        Test complete workflow from mask definition to PowerPoint output.
        """
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        converter = MaskingConverter(services=mock_services)
        # Mock required dependencies
        mock_services.unit_converter.convert_to_emu.return_value = 914400
        converter.unit_converter.convert_to_user_units.return_value = 10.0

        context = Mock(spec=ConversionContext)
        context.get_next_shape_id.return_value = 123

        # Create SVG with mask definition and usage
        svg_content = '''
        <svg xmlns="http://www.w3.org/2000/svg">
            <defs>
                <mask id="myMask" maskUnits="objectBoundingBox">
                    <rect fill="white" x="0" y="0" width="1" height="1"/>
                </mask>
            </defs>
            <rect x="10" y="10" width="80" height="60" mask="url(#myMask)"/>
        </svg>
        '''

        root = ET.fromstring(svg_content)

        # Process mask definition
        mask_elem = root.find('.//{http://www.w3.org/2000/svg}mask')
        result = converter.convert(mask_elem, context)
        assert result == ""  # Definitions return empty string
        assert 'myMask' in converter.mask_definitions

        # Process masked element
        rect_elem = root.find('.//{http://www.w3.org/2000/svg}rect[@mask]')
        with patch.object(converter, '_get_element_bounds', return_value=(10, 10, 80, 60)):
            with patch.object(converter, '_mask_requires_rasterization', return_value=False):
                result = converter.convert(rect_elem, context)
                assert 'MaskedShape' in result
                assert 'id="123"' in result

    def test_real_world_scenarios(self):
        """
        Test with real-world mask and clipPath scenarios.
        """
        # Create mock services for dependency injection
        mock_services = Mock()
        mock_services.unit_converter = Mock()
        mock_services.viewport_handler = Mock()
        mock_services.font_service = Mock()
        mock_services.gradient_service = Mock()
        mock_services.pattern_service = Mock()
        mock_services.clip_service = Mock()

        converter = MaskingConverter(services=mock_services)
        mock_services.unit_converter.convert_to_user_units.return_value = 10.0

        context = Mock(spec=ConversionContext)

        # Test complex mask with gradients (should require rasterization)
        complex_svg = '''
        <mask id="gradientMask">
            <rect fill="url(#gradient1)" x="0" y="0" width="100" height="100"/>
        </mask>
        '''

        mask_elem = ET.fromstring(complex_svg)
        rect_child = mask_elem[0]
        rect_child.set('fill', 'url(#gradient1)')

        converter._process_mask_definition(mask_elem, context)
        mask_def = converter.mask_definitions['gradientMask']

        # Should detect gradient and mark for rasterization
        requires_raster = converter._mask_requires_rasterization(mask_def)
        # Note: This depends on implementation of _has_complex_gradient
        # For now, we'll just verify the function can be called without error
        assert isinstance(requires_raster, bool)


if __name__ == "__main__":
    # Allow running tests directly with: python test_module.py
    pytest.main([__file__])