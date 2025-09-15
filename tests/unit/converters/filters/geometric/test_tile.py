"""
Unit tests for feTile filter implementation.

Tests tile filter parsing, region definition, EMF pattern creation,
seamless tiling, and integration with PowerPoint DrawingML generation.
"""

import pytest
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from src.converters.filters.core.base import Filter, FilterResult, FilterContext
from src.converters.filters.geometric.tile import (
    TileFilter,
    TileParameters,
    TileResult,
    TileException,
    TileValidationError,
)


@dataclass
class TileTestCase:
    """Test case data for tile filter tests."""
    name: str
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    expected_emf: bool = True
    expected_pattern: bool = False


class TestTileParameters:
    """Test TileParameters data class and validation."""

    def test_parameters_initialization_default_values(self):
        """Test parameters initialize with correct default values."""
        params = TileParameters(
            tile_region=(0, 0, 100, 100),
            source_region=(0, 0, 50, 50)
        )

        assert params.tile_region == (0, 0, 100, 100)
        assert params.source_region == (0, 0, 50, 50)
        assert params.pattern_type == "auto"
        assert params.seamless is True
        assert params.scaling_x == 1.0
        assert params.scaling_y == 1.0

    def test_parameters_initialization_all_values(self):
        """Test parameters initialize with all custom values."""
        params = TileParameters(
            tile_region=(10, 20, 200, 150),
            source_region=(0, 0, 25, 25),
            pattern_type="hatch_horizontal",
            seamless=False,
            scaling_x=2.0,
            scaling_y=1.5
        )

        assert params.tile_region == (10, 20, 200, 150)
        assert params.source_region == (0, 0, 25, 25)
        assert params.pattern_type == "hatch_horizontal"
        assert params.seamless is False
        assert params.scaling_x == 2.0
        assert params.scaling_y == 1.5

    def test_parameters_tile_region_validation(self):
        """Test tile region validation."""
        # Valid regions
        TileParameters(tile_region=(0, 0, 100, 100), source_region=(0, 0, 50, 50))

        # Invalid region with zero width
        with pytest.raises(TileValidationError, match="Tile region width must be positive"):
            TileParameters(tile_region=(0, 0, 0, 100), source_region=(0, 0, 50, 50))

        # Invalid region with negative height
        with pytest.raises(TileValidationError, match="Tile region height must be positive"):
            TileParameters(tile_region=(0, 0, 100, -50), source_region=(0, 0, 50, 50))


class TestTileFilter:
    """Test TileFilter main functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create mock FilterContext for testing."""
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        context.viewport = {'width': 100, 'height': 100}
        context.element = Mock()
        return context

    @pytest.fixture
    def filter_instance(self):
        """Create TileFilter instance."""
        return TileFilter()

    def test_filter_initialization(self, filter_instance):
        """Test filter initializes correctly."""
        assert isinstance(filter_instance, Filter)
        assert filter_instance.filter_type == "feTile"

    def test_can_apply_valid_element(self, filter_instance, mock_context):
        """Test can_apply returns True for valid feTile element."""
        element = ET.fromstring('<feTile x="0" y="0" width="100" height="100"/>')

        result = filter_instance.can_apply(element, mock_context)

        assert result is True

    def test_can_apply_invalid_element(self, filter_instance, mock_context):
        """Test can_apply returns False for non-feTile element."""
        element = ET.fromstring('<feGaussianBlur stdDeviation="2"/>')

        result = filter_instance.can_apply(element, mock_context)

        assert result is False

    def test_can_apply_missing_required_attributes(self, filter_instance, mock_context):
        """Test can_apply returns False when required attributes are missing."""
        element = ET.fromstring('<feTile/>')

        result = filter_instance.can_apply(element, mock_context)

        assert result is False


class TestTileParsing:
    """Test parsing of feTile attributes and validation."""

    @pytest.fixture
    def filter_instance(self):
        return TileFilter()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        return context

    def test_parse_basic_tile_region(self, filter_instance, mock_context):
        """Test parsing basic tile region attributes."""
        element = ET.fromstring(
            '<feTile x="10" y="20" width="100" height="150"/>'
        )

        params = filter_instance._parse_parameters(element)

        assert params.tile_region == (10.0, 20.0, 100.0, 150.0)
        assert params.source_region == (0.0, 0.0, 100.0, 150.0)
        assert params.pattern_type == "auto"

    def test_parse_tile_with_source_region(self, filter_instance, mock_context):
        """Test parsing tile with explicit source region."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="200" height="200" sourceX="10" sourceY="15" sourceWidth="50" sourceHeight="50"/>'
        )

        params = filter_instance._parse_parameters(element)

        assert params.tile_region == (0.0, 0.0, 200.0, 200.0)
        assert params.source_region == (10.0, 15.0, 50.0, 50.0)

    def test_parse_tile_with_pattern_type(self, filter_instance, mock_context):
        """Test parsing tile with specific pattern type."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="100" height="100" pattern="crosshatch"/>'
        )

        params = filter_instance._parse_parameters(element)

        assert params.pattern_type == "crosshatch"

    def test_parse_tile_with_scaling(self, filter_instance, mock_context):
        """Test parsing tile with scaling attributes."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="100" height="100" scaleX="1.5" scaleY="2.0"/>'
        )

        params = filter_instance._parse_parameters(element)

        assert params.scaling_x == 1.5
        assert params.scaling_y == 2.0

    def test_parse_invalid_coordinates(self, filter_instance, mock_context):
        """Test parsing fails with invalid coordinate values."""
        element = ET.fromstring(
            '<feTile x="invalid" y="20" width="100" height="150"/>'
        )

        with pytest.raises(TileValidationError, match="Invalid coordinate"):
            filter_instance._parse_parameters(element)

    def test_parse_negative_dimensions(self, filter_instance, mock_context):
        """Test parsing fails with negative dimensions."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="-100" height="150"/>'
        )

        with pytest.raises(TileValidationError, match="Width must be positive"):
            filter_instance._parse_parameters(element)


class TestEMFTileCreation:
    """Test EMF tile creation and seamless patterns."""

    @pytest.fixture
    def filter_instance(self):
        return TileFilter()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        context.viewport = {'width': 100, 'height': 100}
        context.element = Mock()
        return context

    def test_create_emf_tile_auto_pattern(self, filter_instance, mock_context):
        """Test creating EMF tile with auto pattern detection."""
        params = TileParameters(
            tile_region=(0, 0, 100, 100),
            source_region=(0, 0, 25, 25),
            pattern_type="auto"
        )

        result = filter_instance._create_emf_tile(params, mock_context)

        assert result is not None
        assert result.emf_blob is not None
        assert result.pattern_name is not None
        assert result.is_seamless is True

    def test_create_emf_tile_specific_pattern(self, filter_instance, mock_context):
        """Test creating EMF tile with specific pattern."""
        params = TileParameters(
            tile_region=(0, 0, 100, 100),
            source_region=(0, 0, 50, 50),
            pattern_type="hatch_horizontal"
        )

        result = filter_instance._create_emf_tile(params, mock_context)

        assert result is not None
        assert result.pattern_name == "hatch_horizontal"
        assert result.is_seamless is True

    def test_create_emf_tile_custom_scaling(self, filter_instance, mock_context):
        """Test creating EMF tile with custom scaling."""
        params = TileParameters(
            tile_region=(0, 0, 200, 150),
            source_region=(0, 0, 50, 50),
            pattern_type="dots",
            scaling_x=2.0,
            scaling_y=1.5
        )

        result = filter_instance._create_emf_tile(params, mock_context)

        assert result is not None
        assert result.scaling_x == 2.0
        assert result.scaling_y == 1.5

    def test_emf_tile_boundary_handling(self, filter_instance, mock_context):
        """Test EMF tile boundary handling for seamless patterns."""
        params = TileParameters(
            tile_region=(0, 0, 100, 100),
            source_region=(0, 0, 33, 33),  # Non-even division
            pattern_type="grid",
            seamless=True
        )

        result = filter_instance._create_emf_tile(params, mock_context)

        assert result is not None
        assert result.is_seamless is True

    def test_emf_tile_performance_optimization(self, filter_instance, mock_context):
        """Test EMF tile creation uses caching for performance."""
        params = TileParameters(
            tile_region=(0, 0, 100, 100),
            source_region=(0, 0, 25, 25),
            pattern_type="crosshatch"
        )

        # First call
        result1 = filter_instance._create_emf_tile(params, mock_context)

        # Second call with same parameters
        result2 = filter_instance._create_emf_tile(params, mock_context)

        # Should use cached pattern
        assert result1.pattern_name == result2.pattern_name


class TestBlipFillTileIntegration:
    """Test a:blipFill/a:tile integration for EMF-based patterns."""

    @pytest.fixture
    def filter_instance(self):
        return TileFilter()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        context.viewport = {'width': 100, 'height': 100}
        context.element = Mock()
        return context

    def test_generate_blip_fill_tile_xml(self, filter_instance, mock_context):
        """Test generating a:blipFill with a:tile XML."""
        tile_result = TileResult(
            emf_blob=b'mock_emf_data',
            pattern_name="hatch_horizontal",
            is_seamless=True,
            scaling_x=1.0,
            scaling_y=1.0
        )

        xml = filter_instance._generate_blip_fill_tile_xml(tile_result, mock_context)

        assert '<a:blipFill>' in xml
        assert '<a:tile' in xml
        assert 'r:embed=' in xml
        assert 'algn="tl"' in xml

    def test_generate_tile_with_scaling(self, filter_instance, mock_context):
        """Test generating a:tile with custom scaling."""
        tile_result = TileResult(
            emf_blob=b'mock_emf_data',
            pattern_name="dots",
            is_seamless=True,
            scaling_x=2.0,
            scaling_y=1.5
        )

        xml = filter_instance._generate_blip_fill_tile_xml(tile_result, mock_context)

        assert 'sx="200000"' in xml  # 2.0 * 100000
        assert 'sy="150000"' in xml  # 1.5 * 100000

    def test_generate_tile_offset_handling(self, filter_instance, mock_context):
        """Test tile offset handling for proper alignment."""
        tile_result = TileResult(
            emf_blob=b'mock_emf_data',
            pattern_name="grid",
            is_seamless=True,
            scaling_x=1.0,
            scaling_y=1.0,
            offset_x=10.0,
            offset_y=15.0
        )

        xml = filter_instance._generate_blip_fill_tile_xml(tile_result, mock_context)

        # Should include offset values in EMU
        assert 'tx=' in xml
        assert 'ty=' in xml

    def test_generate_non_seamless_tile_handling(self, filter_instance, mock_context):
        """Test handling of non-seamless tiles."""
        tile_result = TileResult(
            emf_blob=b'mock_emf_data',
            pattern_name="custom",
            is_seamless=False,
            scaling_x=1.0,
            scaling_y=1.0
        )

        xml = filter_instance._generate_blip_fill_tile_xml(tile_result, mock_context)

        # Should still generate valid XML but with appropriate handling
        assert '<a:blipFill>' in xml
        assert '<a:tile' in xml


class TestPatternDensityAndScaling:
    """Test pattern density and scaling algorithms for EMF tiles."""

    @pytest.fixture
    def filter_instance(self):
        return TileFilter()

    def test_calculate_optimal_pattern_density(self, filter_instance):
        """Test calculating optimal pattern density based on region size."""
        region_width = 200.0
        region_height = 150.0
        pattern_type = "hatch_horizontal"

        density = filter_instance._calculate_optimal_density(
            region_width, region_height, pattern_type
        )

        assert density > 0.0
        assert density <= 1.0

    def test_calculate_scaling_factors(self, filter_instance):
        """Test calculating scaling factors for different tile sizes."""
        tile_size = (100, 100)
        source_size = (25, 25)

        scale_x, scale_y = filter_instance._calculate_scaling_factors(tile_size, source_size)

        assert scale_x == 4.0  # 100/25
        assert scale_y == 4.0  # 100/25

    def test_optimize_tile_size_for_performance(self, filter_instance):
        """Test tile size optimization for performance."""
        requested_width = 37.0  # Non-power-of-2
        requested_height = 53.0

        optimized_width, optimized_height = filter_instance._optimize_tile_size(
            requested_width, requested_height
        )

        # Should round to efficient sizes
        assert optimized_width >= requested_width
        assert optimized_height >= requested_height
        assert optimized_width % 8 == 0  # Should be multiple of 8 for efficiency
        assert optimized_height % 8 == 0

    def test_pattern_density_adaptive_scaling(self, filter_instance):
        """Test adaptive scaling based on pattern density."""
        # High density pattern
        high_density_scale = filter_instance._calculate_adaptive_scaling(
            pattern_type="dots",
            density=0.9,
            region_size=(200, 200)
        )

        # Low density pattern
        low_density_scale = filter_instance._calculate_adaptive_scaling(
            pattern_type="dots",
            density=0.1,
            region_size=(200, 200)
        )

        # High density should use smaller scale
        assert high_density_scale < low_density_scale


class TestTileIntegration:
    """Test full tile filter application and integration."""

    @pytest.fixture
    def filter_instance(self):
        return TileFilter()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        context.viewport = {'width': 100, 'height': 100}
        context.element = Mock()
        return context

    def test_apply_basic_tile_success(self, filter_instance, mock_context):
        """Test applying basic tile filter returns successful result."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="100" height="100"/>'
        )

        result = filter_instance.apply(element, mock_context)

        assert result.is_success()
        assert result.get_metadata()['filter_type'] == 'feTile'
        assert result.get_metadata()['approach'] == 'emf'
        assert '<a:blipFill>' in result.get_drawingml()

    def test_apply_tile_with_pattern_type(self, filter_instance, mock_context):
        """Test applying tile with specific pattern type."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="100" height="100" pattern="crosshatch"/>'
        )

        result = filter_instance.apply(element, mock_context)

        assert result.is_success()
        assert result.get_metadata()['pattern'] == 'crosshatch'

    def test_apply_tile_with_custom_scaling(self, filter_instance, mock_context):
        """Test applying tile with custom scaling parameters."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="200" height="150" scaleX="2.0" scaleY="1.5"/>'
        )

        result = filter_instance.apply(element, mock_context)

        assert result.is_success()
        assert result.get_metadata()['scaling_x'] == 2.0
        assert result.get_metadata()['scaling_y'] == 1.5

    def test_apply_invalid_tile_validation_error(self, filter_instance, mock_context):
        """Test applying invalid tile returns validation error."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="-100" height="100"/>'  # Negative width
        )

        result = filter_instance.apply(element, mock_context)

        assert not result.is_success()
        assert "Width must be positive" in result.get_error_message()
        assert result.get_metadata()['filter_type'] == 'feTile'

    def test_validate_parameters_valid_element(self, filter_instance, mock_context):
        """Test parameter validation passes for valid element."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="100" height="100"/>'
        )

        result = filter_instance.validate_parameters(element, mock_context)

        assert result is True

    def test_validate_parameters_invalid_element(self, filter_instance, mock_context):
        """Test parameter validation fails for invalid element."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="0" height="100"/>'  # Zero width
        )

        result = filter_instance.validate_parameters(element, mock_context)

        assert result is False


class TestTilePerformance:
    """Test performance considerations and optimizations."""

    @pytest.fixture
    def filter_instance(self):
        return TileFilter()

    def test_emf_pattern_caching(self, filter_instance):
        """Test EMF pattern caching for performance."""
        # Same pattern parameters
        params1 = TileParameters(
            tile_region=(0, 0, 100, 100),
            source_region=(0, 0, 25, 25),
            pattern_type="hatch_horizontal"
        )
        params2 = TileParameters(
            tile_region=(0, 0, 100, 100),
            source_region=(0, 0, 25, 25),
            pattern_type="hatch_horizontal"
        )

        # Should use cached EMF pattern
        assert filter_instance._should_use_cached_pattern(params1, params2) is True

    def test_tile_size_optimization_for_memory(self, filter_instance):
        """Test tile size optimization for memory efficiency."""
        large_region = (0, 0, 2000, 2000)
        small_source = (0, 0, 10, 10)

        optimized_params = filter_instance._optimize_for_memory(large_region, small_source)

        # Should optimize tile size to reduce memory usage
        assert optimized_params.tile_region[2] <= 512  # Width - reasonable upper limit
        assert optimized_params.tile_region[3] <= 512  # Height - reasonable upper limit


class TestTileEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def filter_instance(self):
        return TileFilter()

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.unit_converter = Mock()
        context.unit_converter.to_emu.return_value = 63500
        context.viewport = {'width': 100, 'height': 100}
        return context

    def test_very_small_tile_region(self, filter_instance, mock_context):
        """Test handling of very small tile regions."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="1" height="1"/>'
        )

        result = filter_instance.apply(element, mock_context)

        # Should handle gracefully
        assert result.is_success()

    def test_very_large_tile_region(self, filter_instance, mock_context):
        """Test handling of very large tile regions."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="10000" height="10000"/>'
        )

        result = filter_instance.apply(element, mock_context)

        # Should handle gracefully with memory optimizations
        assert result.is_success()

    def test_non_integer_coordinates(self, filter_instance, mock_context):
        """Test handling of non-integer coordinates."""
        element = ET.fromstring(
            '<feTile x="10.5" y="20.7" width="100.3" height="150.9"/>'
        )

        result = filter_instance.apply(element, mock_context)

        assert result.is_success()

    def test_unsupported_pattern_type(self, filter_instance, mock_context):
        """Test handling of unsupported pattern types."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="100" height="100" pattern="unsupported_pattern"/>'
        )

        result = filter_instance.apply(element, mock_context)

        # Should fallback to auto pattern selection
        assert result.is_success()
        assert result.get_metadata()['pattern'] != 'unsupported_pattern'

    def test_extreme_scaling_values(self, filter_instance, mock_context):
        """Test handling of extreme scaling values."""
        element = ET.fromstring(
            '<feTile x="0" y="0" width="100" height="100" scaleX="0.001" scaleY="1000.0"/>'
        )

        result = filter_instance.apply(element, mock_context)

        # Should clamp to reasonable values
        assert result.is_success()
        metadata = result.get_metadata()
        assert metadata['scaling_x'] >= 0.1  # Minimum reasonable scale
        assert metadata['scaling_y'] <= 10.0  # Maximum reasonable scale


class TestEMFTileLibraryIntegration:
    """Test integration with existing EMF tile library."""

    @pytest.fixture
    def filter_instance(self):
        return TileFilter()

    def test_use_existing_emf_patterns(self, filter_instance):
        """Test using existing EMF patterns from library."""
        # Standard patterns should be available
        available_patterns = filter_instance._get_available_patterns()

        assert "hatch_horizontal" in available_patterns
        assert "hatch_vertical" in available_patterns
        assert "crosshatch" in available_patterns
        assert "dots" in available_patterns
        assert "grid" in available_patterns

    def test_create_custom_emf_pattern(self, filter_instance):
        """Test creating custom EMF pattern for unique tiles."""
        source_data = b'mock_svg_data'

        custom_pattern = filter_instance._create_custom_pattern(source_data)

        assert custom_pattern is not None
        assert hasattr(custom_pattern, 'emf_blob')

    def test_emf_pattern_library_fallback(self, filter_instance):
        """Test fallback to pattern library when custom generation fails."""
        invalid_source = b'invalid_data'

        fallback_pattern = filter_instance._get_pattern_with_fallback(
            "custom", invalid_source
        )

        # Should fallback to a standard pattern
        assert fallback_pattern is not None