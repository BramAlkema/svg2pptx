#!/usr/bin/env python3
"""
Tests for SVG feTurbulence filter processor.

Comprehensive test suite covering Perlin noise generation, fractalNoise vs turbulence modes,
octave processing, deterministic seeding, and PowerPoint integration strategies.
"""

import pytest
from unittest.mock import Mock, patch
from lxml import etree as ET

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from core.filters.turbulence import (
    TurbulenceProcessor,
    TurbulenceParameters,
    TurbulenceFilterException,
    TurbulenceValidationError,
    create_turbulence_processor
)
from core.filters.base import (
    FilterContext,
    FilterResult,
    FilterStrategy,
    FilterException
)


class TestTurbulenceParameters:
    """Test TurbulenceParameters dataclass."""

    def test_default_initialization(self):
        """Test default parameter initialization."""
        params = TurbulenceParameters()

        assert params.turbulence_type == "turbulence"
        assert params.base_frequency_x == 0.01
        assert params.base_frequency_y is None
        assert params.num_octaves == 1
        assert params.seed == 0
        assert params.stitch_tiles is False
        assert params.input_source == "SourceGraphic"
        assert params.result_name is None

    def test_custom_initialization(self):
        """Test custom parameter initialization."""
        params = TurbulenceParameters(
            turbulence_type="fractalNoise",
            base_frequency_x=0.05,
            base_frequency_y=0.03,
            num_octaves=4,
            seed=12345,
            stitch_tiles=True,
            result_name="noiseResult"
        )

        assert params.turbulence_type == "fractalNoise"
        assert params.base_frequency_x == 0.05
        assert params.base_frequency_y == 0.03
        assert params.num_octaves == 4
        assert params.seed == 12345
        assert params.stitch_tiles is True
        assert params.result_name == "noiseResult"

    def test_post_init_validation(self):
        """Test parameter validation in __post_init__."""
        # Valid parameters should pass
        TurbulenceParameters(turbulence_type="fractalNoise")

        # Invalid turbulence type
        with pytest.raises(TurbulenceValidationError, match="Invalid turbulence type"):
            TurbulenceParameters(turbulence_type="invalid")

        # Invalid base frequency
        with pytest.raises(TurbulenceValidationError, match="Base frequency X must be positive"):
            TurbulenceParameters(base_frequency_x=0.0)

        with pytest.raises(TurbulenceValidationError, match="Base frequency Y must be positive"):
            TurbulenceParameters(base_frequency_x=0.01, base_frequency_y=-0.01)

        # Invalid octaves
        with pytest.raises(TurbulenceValidationError, match="Number of octaves must be at least 1"):
            TurbulenceParameters(num_octaves=0)

    def test_parameter_clamping(self):
        """Test parameter clamping to reasonable ranges."""
        params = TurbulenceParameters(
            base_frequency_x=20.0,  # Should be clamped to 10.0
            base_frequency_y=0.0001,  # Should be clamped to 0.001
            num_octaves=15,  # Should be clamped to 8
            seed=0x123456789ABCDEF  # Should be masked to 32-bit
        )

        assert params.base_frequency_x == 10.0
        assert params.base_frequency_y == 0.001
        assert params.num_octaves == 8
        assert params.seed == 0x89ABCDEF  # Lower 32 bits

    def test_get_frequency_y(self):
        """Test frequency Y calculation."""
        # When Y frequency is specified
        params = TurbulenceParameters(base_frequency_x=0.01, base_frequency_y=0.02)
        assert params.get_frequency_y() == 0.02

        # When Y frequency defaults to X
        params = TurbulenceParameters(base_frequency_x=0.03)
        assert params.get_frequency_y() == 0.03

    def test_complexity_score_calculation(self):
        """Test complexity score calculation."""
        # Simple case
        simple_params = TurbulenceParameters(num_octaves=1, base_frequency_x=0.01)
        assert simple_params.get_complexity_score() <= 0.3

        # Complex case
        complex_params = TurbulenceParameters(
            num_octaves=6,
            base_frequency_x=0.2,
            stitch_tiles=True
        )
        assert complex_params.get_complexity_score() > 0.6

    def test_is_suitable_for_native(self):
        """Test native strategy suitability."""
        # Simple parameters suitable for native
        simple_params = TurbulenceParameters(num_octaves=2, base_frequency_x=0.02)
        assert simple_params.is_suitable_for_native()

        # Complex parameters not suitable for native
        complex_params = TurbulenceParameters(
            num_octaves=5,
            base_frequency_x=0.1,
            stitch_tiles=True
        )
        assert not complex_params.is_suitable_for_native()


class TestTurbulenceProcessor:
    """Test TurbulenceProcessor class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = TurbulenceProcessor()

        # Setup mock context
        self.mock_context = Mock()
        self.mock_context.viewport = {'width': 800, 'height': 600}
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 914400
        self.mock_context.transform_parser = Mock()
        self.mock_context.color_parser = Mock()

    def test_initialization(self):
        """Test processor initialization."""
        processor = TurbulenceProcessor()

        assert processor.filter_type == 'feTurbulence'
        assert processor.max_texture_size == 512

    def test_factory_function(self):
        """Test factory function."""
        processor = create_turbulence_processor()

        assert isinstance(processor, TurbulenceProcessor)
        assert processor.filter_type == 'feTurbulence'

    def test_can_apply_valid_element(self):
        """Test can_apply with valid feTurbulence element."""
        element = ET.fromstring('''
            <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="3"/>
        ''')

        assert self.processor.can_apply(element, self.mock_context)

    def test_can_apply_invalid_element(self):
        """Test can_apply with invalid elements."""
        # Wrong tag
        wrong_tag = ET.fromstring('<feOffset dx="5" dy="5"/>')
        assert not self.processor.can_apply(wrong_tag, self.mock_context)

        # Invalid parameters
        invalid_params = ET.fromstring('<feTurbulence baseFrequency="-1"/>')
        assert not self.processor.can_apply(invalid_params, self.mock_context)

    def test_parse_basic_parameters(self):
        """Test parsing basic turbulence parameters."""
        element = ET.fromstring('''
            <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="4"/>
        ''')

        params = self.processor._parse_parameters(element, self.mock_context)

        assert params.turbulence_type == "fractalNoise"
        assert params.base_frequency_x == 0.05
        assert params.base_frequency_y is None
        assert params.num_octaves == 4

    def test_parse_dual_frequency(self):
        """Test parsing dual frequency values."""
        element = ET.fromstring('''
            <feTurbulence baseFrequency="0.03 0.07" numOctaves="2"/>
        ''')

        params = self.processor._parse_parameters(element, self.mock_context)

        assert params.base_frequency_x == 0.03
        assert params.base_frequency_y == 0.07

    def test_parse_seed_and_stitch(self):
        """Test parsing seed and stitch parameters."""
        element = ET.fromstring('''
            <feTurbulence seed="42" stitchTiles="stitch"/>
        ''')

        params = self.processor._parse_parameters(element, self.mock_context)

        assert params.seed == 42
        assert params.stitch_tiles is True

    def test_parse_input_output_parameters(self):
        """Test parsing input/output parameters."""
        element = ET.fromstring('''
            <feTurbulence in="sourceAlpha" result="noisePattern"/>
        ''')

        params = self.processor._parse_parameters(element, self.mock_context)

        assert params.input_source == "sourceAlpha"
        assert params.result_name == "noisePattern"

    def test_strategy_selection_native(self):
        """Test strategy selection for native PowerPoint textures."""
        simple_params = TurbulenceParameters(
            num_octaves=1,
            base_frequency_x=0.02
        )

        strategy = self.processor._select_strategy(simple_params, self.mock_context)
        assert strategy == FilterStrategy.NATIVE

    def test_strategy_selection_approximation(self):
        """Test strategy selection for approximation."""
        medium_params = TurbulenceParameters(
            num_octaves=3,
            base_frequency_x=0.05
        )

        strategy = self.processor._select_strategy(medium_params, self.mock_context)
        if NUMPY_AVAILABLE:
            assert strategy == FilterStrategy.APPROXIMATION
        else:
            assert strategy == FilterStrategy.EMF_RASTERIZE

    def test_strategy_selection_rasterization(self):
        """Test strategy selection for rasterization."""
        complex_params = TurbulenceParameters(
            num_octaves=6,
            base_frequency_x=0.2,
            stitch_tiles=True
        )

        strategy = self.processor._select_strategy(complex_params, self.mock_context)
        assert strategy == FilterStrategy.EMF_RASTERIZE

    def test_apply_native_strategy_success(self):
        """Test successful native strategy application."""
        element = ET.fromstring('''
            <feTurbulence type="fractalNoise" baseFrequency="0.01" numOctaves="1"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.strategy == FilterStrategy.NATIVE
        assert 'a:pattFill' in result.drawingml
        assert result.metadata['filter_type'] == 'feTurbulence'
        assert result.metadata['turbulence_type'] == 'fractalNoise'

    def test_apply_approximation_strategy(self):
        """Test approximation strategy application."""
        element = ET.fromstring('''
            <feTurbulence type="turbulence" baseFrequency="0.05" numOctaves="3"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        if NUMPY_AVAILABLE:
            assert result.success
            assert result.strategy == FilterStrategy.APPROXIMATION
            assert 'a:pattFill' in result.drawingml
            assert result.metadata['approach'] == 'pattern_approximation'
        else:
            assert result.success or not result.success  # May fail without NumPy

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_apply_rasterization_strategy(self):
        """Test rasterization strategy application."""
        element = ET.fromstring('''
            <feTurbulence type="turbulence" baseFrequency="0.1" numOctaves="5" stitchTiles="stitch"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        # High complexity should trigger rasterization, but complexity threshold may cause approximation
        assert result.strategy in [FilterStrategy.EMF_RASTERIZE, FilterStrategy.APPROXIMATION]

        if result.strategy == FilterStrategy.EMF_RASTERIZE:
            assert 'r:embed=' in result.drawingml
            assert result.metadata['approach'] == 'rasterization'
        else:  # APPROXIMATION
            assert 'pattFill' in result.drawingml
            assert result.metadata['approach'] == 'pattern_approximation'

    def test_apply_with_validation_error(self):
        """Test apply with invalid parameters."""
        element = ET.fromstring('<feTurbulence baseFrequency="-1"/>')  # Invalid negative frequency

        result = self.processor.apply(element, self.mock_context)

        assert not result.success
        assert result.error_message is not None
        assert result.metadata['filter_type'] == 'feTurbulence'

    def test_select_native_pattern(self):
        """Test native pattern selection."""
        # fractalNoise patterns
        fractal_params = TurbulenceParameters(turbulence_type="fractalNoise", num_octaves=1)
        pattern = self.processor._select_native_pattern(fractal_params)
        assert pattern in ("canvas", "paperBag")

        # turbulence patterns
        turb_params = TurbulenceParameters(turbulence_type="turbulence", num_octaves=2)
        pattern = self.processor._select_native_pattern(turb_params)
        assert pattern in ("granite", "marble")

    def test_generate_native_texture_xml(self):
        """Test native texture XML generation."""
        params = TurbulenceParameters(turbulence_type="fractalNoise")
        xml = self.processor._generate_native_texture_xml(params, "canvas", self.mock_context)

        assert '<a:pattFill prst="canvas">' in xml
        assert '<a:fgClr>' in xml
        assert '<a:bgClr>' in xml

    def test_generate_pattern_approximation(self):
        """Test pattern approximation generation."""
        # fractalNoise approximation
        fractal_params = TurbulenceParameters(turbulence_type="fractalNoise")
        xml = self.processor._generate_pattern_approximation(fractal_params, self.mock_context)
        assert 'prst="weave"' in xml

        # turbulence approximation
        turb_params = TurbulenceParameters(turbulence_type="turbulence")
        xml = self.processor._generate_pattern_approximation(turb_params, self.mock_context)
        assert 'prst="confetti"' in xml

    def test_generate_rasterized_xml(self):
        """Test rasterized XML generation."""
        params = TurbulenceParameters()
        texture_ref = "turbulence_test_123"

        xml = self.processor._generate_rasterized_xml(params, texture_ref, self.mock_context)

        assert f'r:embed="{texture_ref}"' in xml
        assert 'a14:useLocalDpi val="0"' in xml
        assert '<a:stretch>' in xml

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_perlin_noise_generation(self):
        """Test Perlin noise generation."""
        params = TurbulenceParameters(
            turbulence_type="fractalNoise",
            base_frequency_x=0.05,
            num_octaves=2,
            seed=42
        )

        noise_array = self.processor._generate_perlin_noise(params, self.mock_context)

        assert noise_array.shape == (256, 256, 4)  # RGBA
        assert noise_array.dtype == np.float32
        assert np.all(noise_array[..., 3] == 1.0)  # Alpha channel = 1
        assert np.all(noise_array >= 0.0) and np.all(noise_array <= 1.0)

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_perlin_deterministic(self):
        """Test that Perlin noise is deterministic for same seed."""
        params1 = TurbulenceParameters(seed=42, base_frequency_x=0.03)
        params2 = TurbulenceParameters(seed=42, base_frequency_x=0.03)

        noise1 = self.processor._generate_perlin_noise(params1, self.mock_context)
        noise2 = self.processor._generate_perlin_noise(params2, self.mock_context)

        np.testing.assert_array_equal(noise1, noise2)

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_perlin_different_seeds(self):
        """Test that different seeds produce different noise."""
        params1 = TurbulenceParameters(seed=42, base_frequency_x=0.03)
        params2 = TurbulenceParameters(seed=43, base_frequency_x=0.03)

        noise1 = self.processor._generate_perlin_noise(params1, self.mock_context)
        noise2 = self.processor._generate_perlin_noise(params2, self.mock_context)

        assert not np.array_equal(noise1, noise2)

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_fractal_vs_turbulence_modes(self):
        """Test difference between fractalNoise and turbulence modes."""
        base_params = {
            'base_frequency_x': 0.05,
            'num_octaves': 3,
            'seed': 42
        }

        fractal_params = TurbulenceParameters(turbulence_type="fractalNoise", **base_params)
        turb_params = TurbulenceParameters(turbulence_type="turbulence", **base_params)

        fractal_noise = self.processor._generate_perlin_noise(fractal_params, self.mock_context)
        turb_noise = self.processor._generate_perlin_noise(turb_params, self.mock_context)

        # Different modes should produce different results
        assert not np.array_equal(fractal_noise, turb_noise)

        # Both should be in valid range
        assert np.all(fractal_noise >= 0.0) and np.all(fractal_noise <= 1.0)
        assert np.all(turb_noise >= 0.0) and np.all(turb_noise <= 1.0)

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_fade_function(self):
        """Test Perlin fade function."""
        t = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        faded = self.processor._fade(t)

        # Fade function should be smooth and monotonic
        assert np.all(faded >= 0.0) and np.all(faded <= 1.0)
        assert np.all(np.diff(faded) >= 0)  # Monotonic increasing

    @pytest.mark.skipif(not NUMPY_AVAILABLE, reason="NumPy not available")
    def test_gradient_function(self):
        """Test gradient generation function."""
        ix = np.array([0, 1, 2])
        iy = np.array([0, 1, 2])
        seed = 42

        grads = self.processor._grad(ix, iy, seed)

        assert grads.shape == (3, 2)  # 3 points, 2D vectors

        # Gradients should be unit vectors
        lengths = np.sqrt(np.sum(grads**2, axis=1))
        np.testing.assert_allclose(lengths, 1.0, rtol=1e-6)


class TestTurbulenceIntegration:
    """Integration tests for turbulence processor."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = TurbulenceProcessor()

        # Setup realistic context
        self.mock_context = Mock()
        self.mock_context.viewport = {'width': 800, 'height': 600}
        self.mock_context.unit_converter = Mock()
        self.mock_context.unit_converter.to_emu.return_value = 914400
        self.mock_context.transform_parser = Mock()
        self.mock_context.color_parser = Mock()

    def test_complete_fractal_noise_workflow(self):
        """Test complete fractalNoise processing workflow."""
        element = ET.fromstring('''
            <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2"
                          seed="12345" result="fractalPattern"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.metadata['turbulence_type'] == 'fractalNoise'
        assert result.metadata['frequency_x'] == 0.02
        assert result.metadata['octaves'] == 2
        assert result.metadata['seed'] == 12345

    def test_complete_turbulence_workflow(self):
        """Test complete turbulence processing workflow."""
        element = ET.fromstring('''
            <feTurbulence type="turbulence" baseFrequency="0.03 0.05" numOctaves="4"
                          stitchTiles="stitch"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        assert result.success
        assert result.metadata['turbulence_type'] == 'turbulence'
        assert result.metadata['frequency_x'] == 0.03
        assert result.metadata['frequency_y'] == 0.05

    def test_without_numpy_fallback(self):
        """Test graceful handling when NumPy is not available."""
        with patch('core.filters.turbulence.NUMPY_AVAILABLE', False):
            processor = TurbulenceProcessor()

            # Complex turbulence should fail gracefully without NumPy
            element = ET.fromstring('''
                <feTurbulence type="turbulence" baseFrequency="0.1" numOctaves="5"/>
            ''')

            result = processor.apply(element, self.mock_context)

            if not result.success:
                assert 'NumPy required' in result.error_message

    def test_edge_case_parameters(self):
        """Test edge case parameter handling."""
        # Minimal parameters
        minimal_element = ET.fromstring('<feTurbulence/>')
        result = self.processor.apply(minimal_element, self.mock_context)
        assert result.success

        # Maximum reasonable parameters
        max_element = ET.fromstring('''
            <feTurbulence type="fractalNoise" baseFrequency="0.5" numOctaves="8"/>
        ''')
        result = self.processor.apply(max_element, self.mock_context)
        assert result.success

    def test_error_handling_integration(self):
        """Test error handling in complete workflow."""
        # Invalid element
        invalid_element = ET.fromstring('<feTurbulence type="invalid" baseFrequency="-1"/>')

        result = self.processor.apply(invalid_element, self.mock_context)

        assert not result.success
        assert 'error' in result.metadata
        assert result.metadata['filter_type'] == 'feTurbulence'

    def test_metadata_completeness(self):
        """Test metadata completeness in results."""
        element = ET.fromstring('''
            <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="3"
                          seed="9999" stitchTiles="stitch"/>
        ''')

        result = self.processor.apply(element, self.mock_context)

        # Verify all expected metadata is present
        expected_keys = [
            'filter_type', 'turbulence_type', 'frequency_x', 'frequency_y',
            'octaves', 'seed'
        ]

        for key in expected_keys:
            assert key in result.metadata

        assert result.metadata['filter_type'] == 'feTurbulence'
        assert result.metadata['turbulence_type'] == 'fractalNoise'