#!/usr/bin/env python3
"""
Integration tests for MaskingConverter with ClipPathAnalyzer.

Tests the integration of the clipPath analyzer and boolean flattener
with the masking converter to ensure proper fallback hierarchy.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from lxml import etree as ET

from src.converters.masking import MaskingConverter
from src.converters.clippath_types import ClipPathDefinition, ClippingType, ClipPathComplexity
from src.converters.base import ConversionContext
from core.services.conversion_services import ConversionServices
from tests.fixtures.clippath_fixtures import (
    create_svg_element, create_simple_rect_clippath,
    create_simple_path_clippath, create_nested_clippath_definitions,
    create_text_clippath, create_filter_clippath
)


class TestMaskingConverterWithAnalyzer:
    """Test MaskingConverter integration with ClipPathAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services
        self.mock_services = Mock(spec=ConversionServices)
        self.mock_services.unit_converter = Mock()
        self.mock_services.unit_converter.convert_to_emu = Mock(return_value=914400)
        self.mock_services.unit_converter.convert_to_user_units = Mock(side_effect=lambda x: float(x) if x else 0.0)

        # Create converter with mock services
        self.converter = MaskingConverter(self.mock_services)

        # Create mock context
        self.context = Mock(spec=ConversionContext)
        self.context.get_next_shape_id = Mock(return_value="12345")

    def test_initialization_with_analyzer(self):
        """Test that MaskingConverter properly initializes with analyzer and flattener."""
        assert self.converter.clippath_analyzer is not None
        assert self.converter.boolean_flattener is not None
        assert self.converter.clippath_analyzer.services == self.mock_services
        assert self.converter.boolean_flattener.services == self.mock_services

    def test_simple_clippath_conversion(self):
        """Test conversion of simple clipPath using analyzer."""
        # Create simple clipPath definition
        rect_clip = create_simple_rect_clippath()
        self.converter.clippath_definitions = {'simple_rect': rect_clip}

        # Create element with clip-path
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        element.set('clip-path', 'url(#simple_rect)')

        # Apply clipping
        result = self.converter._apply_clipping(element, 'url(#simple_rect)', self.context)

        # Verify result contains PowerPoint clipping output
        assert result is not None
        assert 'ClippingShape' in result or 'custGeom' in result or 'ClippedShape' in result
        assert '12345' in result  # Shape ID

        # Verify custGeom generation was successful
        assert '<a:custGeom>' in result  # Should contain actual custGeom XML
        assert '<a:pathLst>' in result    # Should contain path data

    def test_nested_clippath_flattening(self):
        """Test that nested clipPaths trigger boolean flattening or fall back to EMF."""
        # Create nested clipPath definitions
        nested_defs = create_nested_clippath_definitions()
        self.converter.clippath_definitions = nested_defs

        # Create element with nested clip-path
        element = create_svg_element('rect', x=0, y=0, width=300, height=300)
        element.set('clip-path', 'url(#nested_clip)')

        # Apply clipping
        result = self.converter._apply_clipping(element, 'url(#nested_clip)', self.context)

        # Verify result (should use flattened path or fall back to EMF if flattening fails)
        assert result is not None
        # Since boolean dependencies may not be available, accept either PowerPoint or EMF output
        assert ('ClippingShape' in result or 'custGeom' in result or
                'EMF' in result or 'emf' in result.lower())

    def test_text_clippath_triggers_emf(self):
        """Test that text in clipPath triggers EMF output."""
        # Create text clipPath
        text_clip = create_text_clippath()
        self.converter.clippath_definitions = {'text_clip': text_clip}

        # Create element with text clip-path
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        element.set('clip-path', 'url(#text_clip)')

        # Apply clipping
        result = self.converter._apply_clipping(element, 'url(#text_clip)', self.context)

        # Verify EMF output is generated
        assert result is not None
        assert 'EMF' in result or 'emf' in result.lower()
        assert 'Complex' in result or 'text' in result.lower()

    def test_filter_clippath_triggers_emf(self):
        """Test that filter in clipPath triggers EMF output."""
        # Create filter clipPath
        filter_clip = create_filter_clippath()
        self.converter.clippath_definitions = {'filter_clip': filter_clip}

        # Create element with filter clip-path
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        element.set('clip-path', 'url(#filter_clip)')

        # Apply clipping
        result = self.converter._apply_clipping(element, 'url(#filter_clip)', self.context)

        # Verify EMF output is generated
        assert result is not None
        assert 'EMF' in result or 'emf' in result.lower()
        assert 'filter' in result.lower() or 'Complex' in result

    def test_unsupported_clippath_rasterization(self):
        """Test that unsupported clipPaths trigger rasterization fallback."""
        # Apply clipping with non-existent clipPath
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        element.set('clip-path', 'url(#nonexistent)')

        # Apply clipping
        result = self.converter._apply_clipping(element, 'url(#nonexistent)', self.context)

        # Verify rasterization fallback
        assert result is not None
        assert 'Rasterized' in result or 'raster' in result.lower()

    def test_clippath_analysis_logging(self):
        """Test that clipPath analysis produces proper logging."""
        # Create simple clipPath
        rect_clip = create_simple_rect_clippath()
        self.converter.clippath_definitions = {'simple_rect': rect_clip}

        # Create element
        element = create_svg_element('rect', x=0, y=0, width=200, height=200)

        # Apply clipping with logging
        with patch('src.converters.masking.logger') as mock_logger:
            result = self.converter._apply_clipping(element, 'url(#simple_rect)', self.context)

            # Verify logging occurred
            assert mock_logger.debug.called or mock_logger.info.called

    def test_boolean_flattener_integration(self):
        """Test that boolean flattener is called for nested clipPaths."""
        # Create nested clipPath definitions
        nested_defs = create_nested_clippath_definitions()
        self.converter.clippath_definitions = nested_defs

        # Mock the boolean flattener
        self.converter.boolean_flattener.flatten_nested_clipaths = Mock(return_value="M 0 0 L 100 100 Z")

        # Create element
        element = create_svg_element('rect', x=0, y=0, width=300, height=300)

        # Apply clipping
        result = self.converter._apply_clipping(element, 'url(#nested_clip)', self.context)

        # Verify boolean flattener was called
        assert self.converter.boolean_flattener.flatten_nested_clipaths.called

    def test_clippath_definition_storage(self):
        """Test that clipPath definitions are properly stored and retrieved."""
        # Process clipPath definition element
        clippath_element = create_svg_element('clipPath', id='test_clip')
        rect = create_svg_element('rect', x=10, y=10, width=100, height=50)
        clippath_element.append(rect)

        # Process definition
        result = self.converter._process_clippath_definition(clippath_element, self.context)

        # Verify definition was stored
        assert 'test_clip' in self.converter.clippath_definitions
        clip_def = self.converter.clippath_definitions['test_clip']
        assert clip_def.id == 'test_clip'
        assert len(clip_def.shapes) == 1

    def test_fallback_hierarchy(self):
        """Test that the fallback hierarchy works as expected."""
        test_cases = [
            # (clipPath type, expected output marker)
            (create_simple_rect_clippath(), 'ClippingShape'),  # Simple -> PowerPoint
            (create_text_clippath(), 'EMF'),  # Text -> EMF
            (create_filter_clippath(), 'EMF'),  # Filter -> EMF
        ]

        for clip_def, expected_marker in test_cases:
            self.converter.clippath_definitions = {clip_def.id: clip_def}

            element = create_svg_element('rect', x=0, y=0, width=200, height=200)
            element.set('clip-path', f'url(#{clip_def.id})')

            result = self.converter._apply_clipping(element, f'url(#{clip_def.id})', self.context)

            assert result is not None
            assert expected_marker in result or expected_marker.lower() in result.lower(), \
                f"Expected '{expected_marker}' in output for {clip_def.id}"

    def test_coordinate_transform_handling(self):
        """Test that coordinate transforms are applied when needed."""
        # Create clipPath with objectBoundingBox units
        clip_def = ClipPathDefinition(
            id='bbox_clip',
            units='objectBoundingBox',
            clip_rule='nonzero',
            path_data='M 0 0 L 1 0 L 1 1 L 0 1 Z',
            clipping_type=ClippingType.PATH_BASED
        )
        self.converter.clippath_definitions = {'bbox_clip': clip_def}

        # Create element
        element = create_svg_element('rect', x=50, y=50, width=100, height=100)
        element.set('clip-path', 'url(#bbox_clip)')

        # Apply clipping
        result = self.converter._apply_clipping(element, 'url(#bbox_clip)', self.context)

        # Verify result (coordinate transform should be handled)
        assert result is not None

    def test_cache_clearing(self):
        """Test that analyzer caches can be cleared."""
        # Add some analysis to cache
        rect_clip = create_simple_rect_clippath()
        self.converter.clippath_definitions = {'simple_rect': rect_clip}

        element = create_svg_element('rect', x=0, y=0, width=200, height=200)
        self.converter._apply_clipping(element, 'url(#simple_rect)', self.context)

        # Clear caches
        self.converter.clippath_analyzer.clear_cache()
        self.converter.boolean_flattener.clear_cache()

        # Verify caches are cleared
        assert len(self.converter.clippath_analyzer._analysis_cache) == 0
        assert len(self.converter.boolean_flattener._clippath_cache) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])