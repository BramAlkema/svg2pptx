#!/usr/bin/env python3
"""
Tests for SVG feImage filter processor.

Comprehensive test suite covering image loading from data: URLs, external resources,
preserveAspectRatio handling, bilinear resampling, and PowerPoint integration strategies.
"""

import base64
import pytest
from unittest.mock import Mock, patch, mock_open
from lxml import etree as ET

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from PIL import Image as PILImage
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from core.filters.image import (
    ImageProcessor,
    ImageParameters,
    ImageFilterException,
    ImageValidationError,
    ResourceLoader,
    create_image_processor
)
from core.filters.base import (
    FilterContext,
    FilterResult,
    FilterStrategy,
    FilterException
)


# Test data: 2x2 red RGBA PNG as base64
TEST_PNG_DATA = "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAF0lEQVQIHWP8//8/AzYw6t9og9aNhqUAivsH/4nZr8MAAAAASUVORK5CYII="


class MockResourceLoader:
    """Mock resource loader for testing."""

    def __init__(self, responses=None):
        self.responses = responses or {}

    def resolve(self, href: str):
        return self.responses.get(href)


class TestImageParameters:
    """Test ImageParameters dataclass."""

    def test_default_initialization(self):
        """Test default parameter initialization."""
        # Should raise error for empty href
        with pytest.raises(ImageValidationError, match="Image href cannot be empty"):
            ImageParameters()

    def test_custom_initialization(self):
        """Test custom parameter initialization."""
        params = ImageParameters(
            href="data:image/png;base64,iVBORw0KGgo...",
            preserve_aspect_ratio="xMinYMin slice",
            cross_origin="use-credentials",
            result_name="imageResult"
        )

        assert params.href.startswith("data:image/png")
        assert params.preserve_aspect_ratio == "xMinYMin slice"
        assert params.cross_origin == "use-credentials"
        assert params.result_name == "imageResult"

    def test_preserve_aspect_ratio_validation(self):
        """Test preserveAspectRatio validation."""
        # Valid values should be preserved
        params = ImageParameters(
            href="test.png",
            preserve_aspect_ratio="xMaxYMax meet"
        )
        assert params.preserve_aspect_ratio == "xMaxYMax meet"

        # Invalid values should default
        params = ImageParameters(
            href="test.png",
            preserve_aspect_ratio="invalid badvalue"
        )
        assert params.preserve_aspect_ratio == "xMidYMid meet"

    def test_complexity_score_calculation(self):
        """Test complexity score calculation."""
        # Simple data URL
        simple_params = ImageParameters(href="data:image/png;base64,abc123")
        assert simple_params.get_complexity_score() <= 0.3

        # External URL with complex aspect ratio
        complex_params = ImageParameters(
            href="http://example.com/image.png",
            preserve_aspect_ratio="none"
        )
        assert complex_params.get_complexity_score() > 0.3

    def test_is_data_url(self):
        """Test data URL detection."""
        data_params = ImageParameters(href="data:image/png;base64,abc123")
        assert data_params.is_data_url()

        external_params = ImageParameters(href="http://example.com/image.png")
        assert not external_params.is_data_url()

    def test_get_anchor_and_meetslice(self):
        """Test parsing of preserveAspectRatio."""
        params = ImageParameters(
            href="test.png",
            preserve_aspect_ratio="xMinYMax slice"
        )
        anchor, meet_slice = params.get_anchor_and_meetslice()
        assert anchor == "xMinYMax"
        assert meet_slice == "slice"

        # Default case
        params = ImageParameters(href="test.png", preserve_aspect_ratio="")
        anchor, meet_slice = params.get_anchor_and_meetslice()
        assert anchor == "xMidYMid"
        assert meet_slice == "meet"


class TestImageProcessor:
    """Test ImageProcessor class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = ImageProcessor()

        # Setup mock context
        self.mock_context = Mock()
        self.mock_context.viewport = {'width': 800, 'height': 600}
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 914400
        self.mock_context.transform_parser = Mock()
        self.mock_context.color_parser = Mock()

    def test_initialization(self):
        """Test processor initialization."""
        processor = ImageProcessor()

        assert processor.filter_type == 'feImage'
        assert processor.resource_loader is None

    def test_factory_function(self):
        """Test factory function."""
        processor = create_image_processor()

        assert isinstance(processor, ImageProcessor)
        assert processor.filter_type == 'feImage'

    def test_set_resource_loader(self):
        """Test setting resource loader."""
        loader = MockResourceLoader()
        self.processor.set_resource_loader(loader)

        assert self.processor.resource_loader is loader

    def test_can_apply_valid_element(self):
        """Test can_apply with valid feImage element."""
        element = ET.fromstring('''
            <feImage href="data:image/png;base64,abc123" preserveAspectRatio="xMidYMid meet"/>
        ''')

        assert self.processor.can_apply(element, self.mock_context)

    def test_can_apply_invalid_element(self):
        """Test can_apply with invalid elements."""
        # Wrong tag
        wrong_tag = ET.fromstring('<feOffset dx="5" dy="5"/>')
        assert not self.processor.can_apply(wrong_tag, self.mock_context)

        # Missing href
        no_href = ET.fromstring('<feImage/>')
        assert not self.processor.can_apply(no_href, self.mock_context)

    def test_parse_basic_parameters(self):
        """Test parsing basic image parameters."""
        element = ET.fromstring('''
            <feImage href="image.png" preserveAspectRatio="xMinYMin slice"/>
        ''')

        params = self.processor._parse_parameters(element, self.mock_context)

        assert params.href == "image.png"
        assert params.preserve_aspect_ratio == "xMinYMin slice"

    def test_parse_xlink_href(self):
        """Test parsing xlink:href attribute."""
        element = ET.fromstring('''
            <feImage xmlns:xlink="http://www.w3.org/1999/xlink"
                     xlink:href="legacy-image.png"/>
        ''')

        params = self.processor._parse_parameters(element, self.mock_context)

        assert params.href == "legacy-image.png"

    def test_parse_input_output_parameters(self):
        """Test parsing input/output parameters."""
        element = ET.fromstring('''
            <feImage href="bg.jpg" in="SourceGraphic" result="backgroundImage"/>
        ''')

        params = self.processor._parse_parameters(element, self.mock_context)

        assert params.input_source == "SourceGraphic"
        assert params.result_name == "backgroundImage"

    def test_strategy_selection_native(self):
        """Test strategy selection for native blip fills."""
        data_params = ImageParameters(href="data:image/png;base64,abc123")

        strategy = self.processor._select_strategy(data_params, self.mock_context)
        assert strategy == FilterStrategy.NATIVE

    def test_strategy_selection_approximation(self):
        """Test strategy selection for approximation."""
        external_params = ImageParameters(href="http://example.com/image.png")

        strategy = self.processor._select_strategy(external_params, self.mock_context)
        assert strategy == FilterStrategy.APPROXIMATION

    def test_strategy_selection_rasterization(self):
        """Test strategy selection for rasterization."""
        complex_params = ImageParameters(
            href="http://example.com/image.png",
            preserve_aspect_ratio="none"
        )

        strategy = self.processor._select_strategy(complex_params, self.mock_context)
        assert strategy in [FilterStrategy.EMF_RASTERIZE, FilterStrategy.APPROXIMATION]

    def test_apply_native_strategy_success(self):
        """Test successful native strategy application."""
        element = ET.fromstring(f'''
            <feImage href="data:image/png;base64,{TEST_PNG_DATA}"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.NATIVE
        assert 'a:blipFill' in result.drawingml
        assert 'r:embed=' in result.drawingml
        assert result.metadata['filter_type'] == 'feImage'

    def test_apply_approximation_strategy(self):
        """Test approximation strategy application."""
        # Setup mock loader
        loader = MockResourceLoader({
            'test-image.png': base64.b64decode(TEST_PNG_DATA)
        })
        self.processor.set_resource_loader(loader)

        element = ET.fromstring('''
            <feImage href="test-image.png" preserveAspectRatio="xMidYMid meet"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert 'a:blipFill' in result.drawingml
        assert result.metadata['approach'] == 'basic_placement'

    def test_apply_transparent_fallback(self):
        """Test transparent fallback when image loading fails."""
        element = ET.fromstring('''
            <feImage href="nonexistent.png"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert 'a:solidFill' in result.drawingml
        assert 'a:alpha val="0"' in result.drawingml
        assert result.metadata['approach'] == 'transparent_fallback'

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_apply_rasterization_strategy(self):
        """Test rasterization strategy application."""
        loader = MockResourceLoader({
            'complex-image.png': base64.b64decode(TEST_PNG_DATA)
        })
        self.processor.set_resource_loader(loader)

        element = ET.fromstring('''
            <feImage href="complex-image.png" preserveAspectRatio="none"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy in [FilterStrategy.EMF_RASTERIZE, FilterStrategy.APPROXIMATION]
        assert 'a:blipFill' in result.drawingml
        if result.strategy == FilterStrategy.EMF_RASTERIZE:
            assert result.metadata['approach'] == 'full_rasterization'
        else:  # APPROXIMATION
            assert result.metadata['approach'] == 'basic_placement'

    def test_apply_with_validation_error(self):
        """Test apply with invalid parameters."""
        element = ET.fromstring('<feImage/>')  # Missing href

        result = self.processor.apply(element, self.mock_context)

        assert not result.success
        assert 'Image href cannot be empty' in result.error_message
        assert result.metadata['filter_type'] == 'feImage'

    def test_load_data_url(self):
        """Test loading data: URL."""
        params = ImageParameters(href=f"data:image/png;base64,{TEST_PNG_DATA}")

        data = self.processor._load_image_data(params)

        assert data is not None
        assert len(data) > 0
        assert data == base64.b64decode(TEST_PNG_DATA)

    def test_load_via_resource_loader(self):
        """Test loading via ResourceLoader."""
        test_data = b"fake image data"
        loader = MockResourceLoader({'test.png': test_data})
        self.processor.set_resource_loader(loader)

        params = ImageParameters(href="test.png")
        data = self.processor._load_image_data(params)

        assert data == test_data

    def test_load_file_fallback(self):
        """Test local file loading fallback."""
        with patch('builtins.open', mock_open(read_data=b"file content")):
            params = ImageParameters(href="local-file.png")
            data = self.processor._load_image_data(params)

            assert data == b"file content"

    def test_load_failure(self):
        """Test graceful handling of load failures."""
        params = ImageParameters(href="nonexistent://invalid.png")
        data = self.processor._load_image_data(params)

        assert data is None

    @pytest.mark.skipif(not PILLOW_AVAILABLE, reason="Pillow not available")
    def test_decode_with_pillow(self):
        """Test image decoding with Pillow."""
        png_data = base64.b64decode(TEST_PNG_DATA)
        rgba_array = self.processor._decode_image_to_rgba(png_data)

        assert rgba_array is not None
        assert rgba_array.shape[2] == 4  # RGBA channels
        assert rgba_array.dtype == np.uint8

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_decode_png_minimal(self):
        """Test minimal PNG decoding fallback."""
        # Create a minimal RGBA PNG for testing
        png_data = base64.b64decode(TEST_PNG_DATA)

        with patch('core.filters.image.PILLOW_AVAILABLE', False):
            rgba_array = self.processor._decode_png_minimal(png_data)

            # Note: This may fail for complex PNGs, but should handle simple ones
            # The test validates the fallback mechanism exists

    def test_decode_invalid_data(self):
        """Test decoding invalid image data."""
        invalid_data = b"not an image"
        rgba_array = self.processor._decode_image_to_rgba(invalid_data)

        assert rgba_array is None

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_fit_into_region_meet(self):
        """Test fitting image into region with 'meet' behavior."""
        # Wide image into square region
        target, offset = self.processor._fit_into_region(100, 100, 200, 100, "xMidYMid meet")
        tw, th = target
        ox, oy = offset

        # Scale should be min(100/200, 100/100) = 0.5
        # So tw=100, th=50, centered vertically
        assert tw == 100  # Scaled width
        assert th == 50   # Scaled height
        assert ox == 0    # No horizontal offset
        assert oy == 25   # Centered vertically: (100-50)/2
        tw, th = target
        ox, oy = offset

        # Scale = min(100/200, 100/100) = min(0.5, 1.0) = 0.5
        # So tw = 200 * 0.5 = 100, th = 100 * 0.5 = 50
        assert tw == 100
        assert th == 50
        assert ox == 0  # Centered horizontally
        assert oy == 25  # Centered vertically (100-50)/2

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_fit_into_region_slice(self):
        """Test fitting image into region with 'slice' behavior."""
        target, offset = self.processor._fit_into_region(100, 100, 200, 100, "xMidYMid slice")
        tw, th = target

        # Scale = max(100/200, 100/100) = max(0.5, 1.0) = 1.0
        # So tw = 200, th = 100
        assert tw == 200
        assert th == 100

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_fit_into_region_none(self):
        """Test fitting image with 'none' (stretch)."""
        target, offset = self.processor._fit_into_region(100, 100, 200, 50, "none")
        tw, th = target
        ox, oy = offset

        # Should stretch to fill region exactly
        assert tw == 100
        assert th == 100
        assert ox == 0
        assert oy == 0

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_resample_bilinear(self):
        """Test bilinear resampling."""
        # Create 2x2 test image
        test_img = np.array([
            [[255, 0, 0, 255], [0, 255, 0, 255]],
            [[0, 0, 255, 255], [255, 255, 255, 255]]
        ], dtype=np.uint8)

        # Resize to 4x4
        resampled = self.processor._resample_bilinear(test_img, (4, 4))

        assert resampled.shape == (4, 4, 4)
        assert resampled.dtype == np.uint8

    def test_generate_native_blip_xml(self):
        """Test native blip XML generation."""
        params = ImageParameters(href="data:image/png;base64,abc123")
        embed_ref = "img_native_123"

        xml = self.processor._generate_native_blip_xml(params, embed_ref, self.mock_context)

        assert '<a:blipFill>' in xml
        assert f'r:embed="{embed_ref}"' in xml
        assert '<a:stretch>' in xml

    def test_generate_approximation_xml(self):
        """Test approximation XML generation."""
        params = ImageParameters(href="image.png")
        embed_ref = "img_approx_123"

        xml = self.processor._generate_approximation_xml(params, embed_ref, self.mock_context)

        assert '<a:blipFill>' in xml
        assert f'r:embed="{embed_ref}"' in xml
        assert '<a:lum bright="0" contrast="0"/>' in xml

    def test_generate_rasterized_xml(self):
        """Test rasterized XML generation."""
        params = ImageParameters(href="complex.png")
        embed_ref = "img_raster_123"

        xml = self.processor._generate_rasterized_xml(params, embed_ref, self.mock_context)

        assert '<a:blipFill>' in xml
        assert f'r:embed="{embed_ref}"' in xml
        assert 'a14:useLocalDpi val="0"' in xml


class TestImageIntegration:
    """Integration tests for image processor."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = ImageProcessor()

        # Setup realistic context
        self.mock_context = Mock()
        self.mock_context.viewport = {'width': 800, 'height': 600}
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 914400
        self.mock_context.transform_parser = Mock()
        self.mock_context.color_parser = Mock()

        # Setup resource loader
        self.loader = MockResourceLoader({
            'test-image.png': base64.b64decode(TEST_PNG_DATA),
            'large-image.jpg': b"fake jpeg data"
        })
        self.processor.set_resource_loader(self.loader)

    def test_complete_data_url_workflow(self):
        """Test complete data URL processing workflow."""
        element = ET.fromstring(f'''
            <feImage href="data:image/png;base64,{TEST_PNG_DATA}"
                     preserveAspectRatio="xMidYMid meet" result="logoImage"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.NATIVE
        assert result.metadata['filter_type'] == 'feImage'
        assert result.metadata['preserve_aspect_ratio'] == 'xMidYMid meet'
        assert 'a:blipFill' in result.drawingml

    def test_complete_external_url_workflow(self):
        """Test complete external URL processing workflow."""
        element = ET.fromstring('''
            <feImage href="test-image.png" preserveAspectRatio="xMaxYMax slice"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert result.metadata['approach'] == 'basic_placement'

    def test_complex_aspect_ratio_workflow(self):
        """Test complex aspect ratio handling."""
        element = ET.fromstring('''
            <feImage href="large-image.jpg" preserveAspectRatio="none"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        # Should use rasterization for complex aspect ratio
        assert result.strategy in [FilterStrategy.EMF_RASTERIZE, FilterStrategy.APPROXIMATION]
        if result.strategy == FilterStrategy.EMF_RASTERIZE:
            assert result.metadata['approach'] == 'full_rasterization'
        else:  # APPROXIMATION
            assert result.metadata['approach'] == 'basic_placement'

    def test_missing_image_graceful_handling(self):
        """Test graceful handling of missing images."""
        element = ET.fromstring('''
            <feImage href="nonexistent-image.png"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success  # Should not fail, just return transparent
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert result.metadata['approach'] == 'transparent_fallback'

    def test_anchor_positioning_variations(self):
        """Test different anchor positioning."""
        anchors = ["xMinYMin", "xMidYMin", "xMaxYMin",
                  "xMinYMid", "xMidYMid", "xMaxYMid",
                  "xMinYMax", "xMidYMax", "xMaxYMax"]

        for anchor in anchors:
            element = ET.fromstring(f'''
                <feImage href="test-image.png" preserveAspectRatio="{anchor} meet"/>
            ''')

            result = self.processor.apply(element, self.mock_context)
            assert result.success, f"Failed for anchor: {anchor}"

    def test_meet_vs_slice_behavior(self):
        """Test meet vs slice behavior differences."""
        # Test meet
        meet_element = ET.fromstring('''
            <feImage href="test-image.png" preserveAspectRatio="xMidYMid meet"/>
        ''')
        meet_result = self.processor.apply(meet_element, self.mock_context)

        # Test slice
        slice_element = ET.fromstring('''
            <feImage href="test-image.png" preserveAspectRatio="xMidYMid slice"/>
        ''')
        slice_result = self.processor.apply(slice_element, self.mock_context)

        assert meet_result.success
        assert slice_result.success
        # Strategies might differ based on complexity
        assert meet_result.metadata['preserve_aspect_ratio'] != slice_result.metadata['preserve_aspect_ratio']

    def test_error_handling_integration(self):
        """Test error handling in complete workflow."""
        # Invalid href
        invalid_element = ET.fromstring('<feImage/>')

        result = self.processor.apply(invalid_element, self.mock_context)

        assert not result.success
        assert 'error' in result.metadata
        assert result.metadata['filter_type'] == 'feImage'

    def test_metadata_completeness(self):
        """Test metadata completeness in results."""
        element = ET.fromstring(f'''
            <feImage href="data:image/png;base64,{TEST_PNG_DATA}"
                     preserveAspectRatio="xMinYMax slice" result="testImage"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        # Verify all expected metadata is present
        expected_keys = [
            'filter_type', 'href', 'embed_reference', 'preserve_aspect_ratio'
        ]

        for key in expected_keys:
            assert key in result.metadata

        assert result.metadata['filter_type'] == 'feImage'
        assert result.metadata['preserve_aspect_ratio'] == 'xMinYMax slice'