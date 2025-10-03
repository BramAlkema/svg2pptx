#!/usr/bin/env python3
"""
Tests for SVG feTile filter processor.

Comprehensive test suite covering parameter parsing, strategy selection,
native PowerPoint tiling, pattern generation, and EMF fallbacks.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

from core.filters.tile import (
    TileProcessor,
    TileParameters,
    TileFilterException,
    TileValidationError,
    create_tile_processor
)
from core.filters.base import (
    FilterContext,
    FilterResult,
    FilterStrategy,
    FilterException
)


class TestTileParameters:
    """Test TileParameters dataclass."""

    def test_default_initialization(self):
        """Test default parameter initialization."""
        params = TileParameters()

        assert params.tile_x == 0.0
        assert params.tile_y == 0.0
        assert params.tile_width == 100.0
        assert params.tile_height == 100.0
        assert params.source_x == 0.0
        assert params.source_y == 0.0
        assert params.source_width == 100.0
        assert params.source_height == 100.0
        assert params.pattern_type == "auto"
        assert params.seamless is True
        assert params.scaling_x == 1.0
        assert params.scaling_y == 1.0
        assert params.input_source == "SourceGraphic"
        assert params.result_name is None

    def test_custom_initialization(self):
        """Test custom parameter initialization."""
        params = TileParameters(
            tile_x=10.0,
            tile_y=20.0,
            tile_width=200.0,
            tile_height=150.0,
            pattern_type="grid",
            seamless=False,
            scaling_x=2.0,
            scaling_y=1.5,
            result_name="tileResult"
        )

        assert params.tile_x == 10.0
        assert params.tile_y == 20.0
        assert params.tile_width == 200.0
        assert params.tile_height == 150.0
        assert params.pattern_type == "grid"
        assert params.seamless is False
        assert params.scaling_x == 2.0
        assert params.scaling_y == 1.5
        assert params.result_name == "tileResult"

    def test_post_init_validation(self):
        """Test parameter validation in __post_init__."""
        # Valid parameters should pass
        TileParameters(tile_width=100.0, tile_height=100.0)

        # Invalid tile dimensions should raise error
        with pytest.raises(TileValidationError, match="Tile width must be positive"):
            TileParameters(tile_width=0.0)

        with pytest.raises(TileValidationError, match="Tile height must be positive"):
            TileParameters(tile_height=-10.0)

        with pytest.raises(TileValidationError, match="Source width must be positive"):
            TileParameters(source_width=0.0)

        with pytest.raises(TileValidationError, match="Source height must be positive"):
            TileParameters(source_height=-5.0)

    def test_scaling_clamping(self):
        """Test scaling factor clamping."""
        params = TileParameters(scaling_x=15.0, scaling_y=0.05)

        # Should be clamped to [0.1, 10.0] range
        assert params.scaling_x == 10.0
        assert params.scaling_y == 0.1

    def test_complexity_score_calculation(self):
        """Test complexity score calculation."""
        # Simple case
        simple_params = TileParameters(tile_width=50.0, tile_height=50.0)
        assert simple_params.get_complexity_score() <= 0.3

        # Complex case with large size
        complex_params = TileParameters(
            tile_width=500.0,
            tile_height=500.0,
            pattern_type="hatch_diagonal",
            scaling_x=2.5,
            scaling_y=0.5,
            seamless=True
        )
        assert complex_params.get_complexity_score() > 0.5

    def test_aspect_ratio_calculation(self):
        """Test aspect ratio calculation."""
        params = TileParameters(tile_width=200.0, tile_height=100.0)
        assert params.get_aspect_ratio() == 2.0

        # Test zero height handling
        params = TileParameters(tile_width=100.0, tile_height=0.1)
        assert params.get_aspect_ratio() == 1000.0

    def test_scaling_ratio_calculation(self):
        """Test scaling ratio calculation."""
        params = TileParameters(scaling_x=2.0, scaling_y=4.0)
        assert params.get_scaling_ratio() == 3.0

    def test_pattern_density_calculation(self):
        """Test pattern density calculation."""
        # Dots pattern
        dots_params = TileParameters(tile_width=100.0, tile_height=100.0, pattern_type="dots")
        density = dots_params.get_pattern_density()
        assert 0.0 <= density <= 1.0

        # Hatch pattern
        hatch_params = TileParameters(tile_width=100.0, tile_height=100.0, pattern_type="hatch_horizontal")
        hatch_density = hatch_params.get_pattern_density()
        assert 0.0 <= hatch_density <= 1.0

        # Hatch should have higher density potential
        assert hatch_density >= density


class TestTileProcessor:
    """Test TileProcessor class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = TileProcessor()

        # Setup mock context
        self.mock_context = Mock()
        self.mock_context.viewport = {'width': 800, 'height': 600}
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 914400
        self.mock_context.transform_parser = Mock()
        self.mock_context.color_parser = Mock()

    def test_initialization(self):
        """Test processor initialization."""
        processor = TileProcessor()

        assert processor.filter_type == 'feTile'
        assert processor.max_tile_size == 512
        assert isinstance(processor.pattern_cache, dict)

    def test_factory_function(self):
        """Test factory function."""
        processor = create_tile_processor()

        assert isinstance(processor, TileProcessor)
        assert processor.filter_type == 'feTile'

    def test_can_apply_valid_element(self):
        """Test can_apply with valid feTile element."""
        element = ET.fromstring('''
            <feTile x="0" y="0" width="100" height="100"/>
        ''')

        assert self.processor.can_apply(element, self.mock_context)

    def test_can_apply_invalid_element(self):
        """Test can_apply with invalid elements."""
        # Wrong tag
        wrong_tag = ET.fromstring('<feOffset dx="5" dy="5"/>')
        assert not self.processor.can_apply(wrong_tag, self.mock_context)

        # Invalid parameters
        invalid_params = ET.fromstring('<feTile width="0" height="100"/>')
        assert not self.processor.can_apply(invalid_params, self.mock_context)

    def test_parse_basic_parameters(self):
        """Test parsing basic tile parameters."""
        element = ET.fromstring('''
            <feTile x="10" y="20" width="200" height="150"/>
        ''')

        params = self.processor._parse_parameters(element, self.mock_context)

        assert params.tile_x == 10.0
        assert params.tile_y == 20.0
        assert params.tile_width == 200.0
        assert params.tile_height == 150.0

    def test_parse_source_parameters(self):
        """Test parsing source region parameters."""
        element = ET.fromstring('''
            <feTile x="0" y="0" width="100" height="100"
                    sourceX="5" sourceY="10" sourceWidth="50" sourceHeight="75"/>
        ''')

        params = self.processor._parse_parameters(element, self.mock_context)

        assert params.source_x == 5.0
        assert params.source_y == 10.0
        assert params.source_width == 50.0
        assert params.source_height == 75.0

    def test_parse_pattern_parameters(self):
        """Test parsing pattern-specific parameters."""
        element = ET.fromstring('''
            <feTile x="0" y="0" width="100" height="100"
                    pattern="grid" seamless="false" scaleX="2.0" scaleY="1.5"/>
        ''')

        params = self.processor._parse_parameters(element, self.mock_context)

        assert params.pattern_type == "grid"
        assert params.seamless is False
        assert params.scaling_x == 2.0
        assert params.scaling_y == 1.5

    def test_parse_input_output_parameters(self):
        """Test parsing input/output parameters."""
        element = ET.fromstring('''
            <feTile in="backgroundImage" result="tiledResult"
                    x="0" y="0" width="100" height="100"/>
        ''')

        params = self.processor._parse_parameters(element, self.mock_context)

        assert params.input_source == "backgroundImage"
        assert params.result_name == "tiledResult"

    def test_strategy_selection_native(self):
        """Test strategy selection for native PowerPoint tiling."""
        # Simple parameters should select native strategy
        simple_params = TileParameters(
            tile_width=100.0,
            tile_height=100.0,
            pattern_type="grid"
        )

        strategy = self.processor._select_strategy(simple_params, self.mock_context)
        assert strategy == FilterStrategy.NATIVE

    def test_strategy_selection_approximation(self):
        """Test strategy selection for approximation."""
        # Medium complexity should select approximation
        medium_params = TileParameters(
            tile_width=80.0,  # Area = 6400 < 10,000, so no size complexity
            tile_height=80.0,
            pattern_type="hatch_horizontal",  # Non-simple pattern adds 0.2
            scaling_x=1.0,  # No scaling complexity
            scaling_y=1.0
        )
        # Expected complexity: 0.0 (size) + 0.2 (pattern) + 0.0 (scaling) = 0.2
        # 0.2 < 0.7 but pattern not in simple list, so should be APPROXIMATION

        strategy = self.processor._select_strategy(medium_params, self.mock_context)
        assert strategy == FilterStrategy.APPROXIMATION

    def test_strategy_selection_emf(self):
        """Test strategy selection for EMF rasterization."""
        # Complex parameters should select EMF strategy
        complex_params = TileParameters(
            tile_width=400.0,
            tile_height=400.0,
            pattern_type="crosshatch",
            scaling_x=3.0,
            scaling_y=0.3,
            seamless=True
        )

        strategy = self.processor._select_strategy(complex_params, self.mock_context)
        assert strategy == FilterStrategy.EMF_RASTERIZE

    def test_apply_native_strategy_success(self):
        """Test successful native strategy application."""
        element = ET.fromstring('''
            <feTile x="0" y="0" width="100" height="100" pattern="grid"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.NATIVE
        assert 'a:blipFill' in result.drawingml
        assert 'a:tile' in result.drawingml
        assert result.metadata['filter_type'] == 'feTile'
        assert result.metadata['pattern'] == 'grid'

    def test_apply_approximation_strategy(self):
        """Test approximation strategy application."""
        element = ET.fromstring('''
            <feTile x="0" y="0" width="300" height="300" pattern="hatch_horizontal"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.APPROXIMATION
        assert 'a:pattFill' in result.drawingml
        assert result.metadata['approach'] == 'pattern_approximation'

    def test_apply_emf_strategy(self):
        """Test EMF strategy application."""
        element = ET.fromstring('''
            <feTile x="0" y="0" width="500" height="500"
                    pattern="crosshatch" scaleX="3.0" scaleY="0.3"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert 'r:embed="emf_tile_' in result.drawingml
        assert result.metadata['approach'] == 'emf_rasterization'

    def test_apply_with_validation_error(self):
        """Test apply with invalid parameters."""
        element = ET.fromstring('<feTile width="0" height="100"/>')

        result = self.processor.apply(element, self.mock_context)

        assert not result.success
        assert 'Tile width must be positive' in result.error_message
        assert result.metadata['filter_type'] == 'feTile'

    def test_pattern_type_selection_auto(self):
        """Test automatic pattern type selection."""
        # Square aspect ratio should select dots
        square_params = TileParameters(tile_width=100.0, tile_height=100.0)
        assert self.processor._select_pattern_type(square_params) == "dots"

        # Wide aspect ratio should select horizontal hatch
        wide_params = TileParameters(tile_width=300.0, tile_height=100.0)
        assert self.processor._select_pattern_type(wide_params) == "hatch_horizontal"

        # Tall aspect ratio should select vertical hatch
        tall_params = TileParameters(tile_width=100.0, tile_height=300.0)
        assert self.processor._select_pattern_type(tall_params) == "hatch_vertical"

        # Normal aspect ratio should select grid
        normal_params = TileParameters(tile_width=150.0, tile_height=100.0)
        assert self.processor._select_pattern_type(normal_params) == "grid"

    def test_pattern_type_selection_explicit(self):
        """Test explicit pattern type selection."""
        params = TileParameters(pattern_type="brick")
        assert self.processor._select_pattern_type(params) == "brick"

    def test_native_tile_xml_generation(self):
        """Test native tile XML generation."""
        params = TileParameters(
            tile_x=10.0,
            tile_y=20.0,
            scaling_x=2.0,
            scaling_y=1.5
        )

        xml = self.processor._generate_native_tile_xml(params, "grid", self.mock_context)

        assert '<a:blipFill>' in xml
        assert '<a:tile tx="127000" ty="254000"' in xml  # 10*12700, 20*12700
        assert 'sx="200000" sy="150000"' in xml  # 2.0*100000, 1.5*100000
        assert 'algn="tl" flip="none"' in xml

    def test_pattern_fill_xml_generation(self):
        """Test pattern fill XML generation."""
        params = TileParameters(pattern_type="dots")

        # Test dots pattern
        dots_xml = self.processor._generate_pattern_fill_xml(params, "dots", self.mock_context)
        assert 'prst="dotGrid"' in dots_xml

        # Test horizontal hatch
        hatch_xml = self.processor._generate_pattern_fill_xml(params, "hatch_horizontal", self.mock_context)
        assert 'prst="horz"' in hatch_xml

        # Test vertical hatch
        vert_xml = self.processor._generate_pattern_fill_xml(params, "hatch_vertical", self.mock_context)
        assert 'prst="vert"' in vert_xml

        # Test grid
        grid_xml = self.processor._generate_pattern_fill_xml(params, "grid", self.mock_context)
        assert 'prst="grid"' in grid_xml

    def test_emf_tile_xml_generation(self):
        """Test EMF tile XML generation."""
        params = TileParameters(
            tile_x=5.0,
            tile_y=10.0,
            scaling_x=1.5,
            scaling_y=2.0
        )
        emf_ref = "emf_tile_pattern_123"

        xml = self.processor._generate_emf_tile_xml(params, emf_ref, self.mock_context)

        assert f'r:embed="{emf_ref}"' in xml
        assert 'tx="63500" ty="127000"' in xml  # 5*12700, 10*12700
        assert 'sx="150000" sy="200000"' in xml  # 1.5*100000, 2.0*100000
        assert 'a14:useLocalDpi val="0"' in xml

    def test_tile_size_optimization(self):
        """Test tile size optimization."""
        # Should round up to multiples of 8
        width, height = self.processor._optimize_tile_size(50.0, 75.0)
        assert width == 56.0  # ceil(50/8)*8
        assert height == 80.0  # ceil(75/8)*8

        # Should cap at max size
        large_width, large_height = self.processor._optimize_tile_size(1000.0, 800.0)
        assert large_width == 512.0  # Capped at max_tile_size
        assert large_height == 512.0

    def test_available_patterns_list(self):
        """Test available patterns list."""
        patterns = self.processor._get_available_patterns()

        expected_patterns = [
            "auto", "grid", "dots", "hatch_horizontal", "hatch_vertical",
            "hatch_diagonal", "crosshatch", "brick"
        ]

        for pattern in expected_patterns:
            assert pattern in patterns

    def test_dot_pattern_fill_generation(self):
        """Test dot pattern fill generation."""
        fill_xml = self.processor._generate_dot_pattern_fill()

        assert 'r:embed="dotPattern"' in fill_xml
        assert '<a:lum bright="0" contrast="0"/>' in fill_xml

    def test_hatch_pattern_fill_generation(self):
        """Test hatch pattern fill generation."""
        # Horizontal hatch
        h_fill = self.processor._generate_hatch_pattern_fill("hatch_horizontal")
        assert 'r:embed="hatchHorizontal"' in h_fill

        # Vertical hatch
        v_fill = self.processor._generate_hatch_pattern_fill("hatch_vertical")
        assert 'r:embed="hatchVertical"' in v_fill

    def test_grid_pattern_fill_generation(self):
        """Test grid pattern fill generation."""
        fill_xml = self.processor._generate_grid_pattern_fill()

        assert 'r:embed="gridPattern"' in fill_xml
        assert '<a:lum bright="0" contrast="0"/>' in fill_xml


class TestTileIntegration:
    """Integration tests for tile processor."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = TileProcessor()

        # Setup realistic context
        self.mock_context = Mock()
        self.mock_context.viewport = {'width': 800, 'height': 600}
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 914400
        self.mock_context.transform_parser = Mock()
        self.mock_context.color_parser = Mock()

    def test_complete_tile_workflow(self):
        """Test complete tile processing workflow."""
        element = ET.fromstring('''
            <feTile x="0" y="0" width="150" height="150"
                    pattern="grid" scaleX="1.5" scaleY="1.5"
                    seamless="true" result="tiledBackground"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.APPROXIMATION  # 150x150 + scaling = complexity > 0.3
        assert result.metadata['pattern'] == 'grid'
        assert result.metadata['scaling_x'] == 1.5
        assert result.metadata['scaling_y'] == 1.5
        assert result.metadata['seamless'] is True
        assert 'a:pattFill' in result.drawingml  # Approximation uses pattern fills, not blipFill

    def test_complex_pattern_handling(self):
        """Test handling of complex patterns."""
        element = ET.fromstring('''
            <feTile x="10" y="20" width="400" height="300"
                    sourceX="0" sourceY="0" sourceWidth="50" sourceHeight="50"
                    pattern="crosshatch" scaleX="2.5" scaleY="0.4"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        # Should use EMF strategy for complex crosshatch pattern
        assert result.strategy == FilterStrategy.EMF_RASTERIZE
        assert result.metadata['pattern'] == 'crosshatch'
        assert 'emf_tile_' in result.metadata['emf_reference']

    def test_error_handling_integration(self):
        """Test error handling in complete workflow."""
        # Invalid dimensions
        invalid_element = ET.fromstring('<feTile width="-10" height="100"/>')

        result = self.processor.apply(invalid_element, self.mock_context)

        assert not result.success
        assert 'error' in result.metadata
        assert result.metadata['filter_type'] == 'feTile'

    def test_metadata_completeness(self):
        """Test metadata completeness in results."""
        element = ET.fromstring('''
            <feTile x="5" y="10" width="200" height="100"
                    pattern="hatch_diagonal" seamless="false"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        # Verify all expected metadata is present
        expected_keys = [
            'filter_type', 'pattern', 'scaling_x', 'scaling_y'
        ]

        for key in expected_keys:
            assert key in result.metadata

        assert result.metadata['filter_type'] == 'feTile'
        assert result.metadata['pattern'] == 'hatch_diagonal'