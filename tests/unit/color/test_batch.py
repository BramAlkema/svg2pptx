#!/usr/bin/env python3
"""
Comprehensive unit tests for ColorBatch class.

Tests cover batch color processing utilities for vectorized operations
including initialization, color manipulation, blending, gradients,
and performance-optimized batch operations.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.color import Color
from src.color.batch import ColorBatch


class TestColorBatchInitialization:
    """Test ColorBatch initialization and basic setup."""

    def test_init_from_color_list(self):
        """Test ColorBatch initialization from list of Color objects."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        batch = ColorBatch(colors)

        assert isinstance(batch, ColorBatch)
        assert len(batch) == 3

    def test_init_from_hex_list(self):
        """Test ColorBatch initialization from list of hex strings."""
        hex_colors = ['#ff0000', '#00ff00', '#0000ff']
        batch = ColorBatch(hex_colors)

        assert isinstance(batch, ColorBatch)
        assert len(batch) == 3

    def test_init_from_mixed_list(self):
        """Test ColorBatch initialization from mixed Color objects and hex strings."""
        mixed_colors = [Color('#ff0000'), '#00ff00', Color('#0000ff')]
        batch = ColorBatch(mixed_colors)

        assert isinstance(batch, ColorBatch)
        assert len(batch) == 3

    def test_init_from_numpy_array(self):
        """Test ColorBatch initialization from NumPy array."""
        rgb_array = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255]], dtype=np.uint8)
        batch = ColorBatch(rgb_array)

        assert isinstance(batch, ColorBatch)
        assert len(batch) == 3

    def test_init_empty_list_validation(self):
        """Test ColorBatch initialization with empty list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot create ColorBatch from empty list"):
            ColorBatch([])

    def test_init_invalid_type_validation(self):
        """Test ColorBatch initialization with invalid types."""
        with pytest.raises(TypeError, match="Unsupported input type"):
            ColorBatch("invalid")

        with pytest.raises(TypeError, match="Unsupported color type in list"):
            ColorBatch([Color('#ff0000'), 123, Color('#0000ff')])

    def test_init_with_alpha_colors(self):
        """Test ColorBatch initialization with colors having alpha channels."""
        colors = [
            Color((255, 0, 0, 0.8)),
            Color((0, 255, 0, 0.6)),
            Color((0, 0, 255, 0.4))
        ]
        batch = ColorBatch(colors)

        assert len(batch) == 3
        # Check that alpha values are preserved
        converted_colors = batch.to_colors()
        assert hasattr(converted_colors[0], '_alpha')
        assert abs(converted_colors[0]._alpha - 0.8) < 0.01


class TestColorBatchBasicOperations:
    """Test basic ColorBatch operations and properties."""

    def setup_method(self):
        self.colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        self.batch = ColorBatch(self.colors)

    def test_len(self):
        """Test ColorBatch length."""
        assert len(self.batch) == 3

    def test_getitem(self):
        """Test ColorBatch indexing."""
        first_color = self.batch[0]
        assert isinstance(first_color, Color)
        assert first_color.rgb() == (255, 0, 0)

        second_color = self.batch[1]
        assert second_color.rgb() == (0, 255, 0)

    def test_iter(self):
        """Test ColorBatch iteration."""
        iterated_colors = list(self.batch)
        assert len(iterated_colors) == 3
        assert all(isinstance(color, Color) for color in iterated_colors)

        # Check RGB values
        assert iterated_colors[0].rgb() == (255, 0, 0)
        assert iterated_colors[1].rgb() == (0, 255, 0)
        assert iterated_colors[2].rgb() == (0, 0, 255)

    def test_to_colors(self):
        """Test conversion back to Color list."""
        colors = self.batch.to_colors()
        assert len(colors) == 3
        assert all(isinstance(color, Color) for color in colors)

        # Check that RGB values are preserved
        assert colors[0].rgb() == (255, 0, 0)
        assert colors[1].rgb() == (0, 255, 0)
        assert colors[2].rgb() == (0, 0, 255)

    def test_to_numpy(self):
        """Test conversion to NumPy array."""
        rgb_array = self.batch.to_numpy()
        assert isinstance(rgb_array, np.ndarray)
        assert rgb_array.shape == (3, 3)
        assert rgb_array.dtype == np.uint8

        # Check RGB values
        np.testing.assert_array_equal(rgb_array[0], [255, 0, 0])
        np.testing.assert_array_equal(rgb_array[1], [0, 255, 0])
        np.testing.assert_array_equal(rgb_array[2], [0, 0, 255])


class TestColorBatchDarkening:
    """Test ColorBatch darkening operations."""

    def setup_method(self):
        self.colors = [Color('#ff0000'), Color('#808080'), Color('#ffffff')]
        self.batch = ColorBatch(self.colors)

    def test_darken_basic(self):
        """Test basic darkening operation."""
        darkened = self.batch.darken(0.2)

        assert isinstance(darkened, ColorBatch)
        assert len(darkened) == len(self.batch)

        # Check that colors are indeed darker
        original_colors = self.batch.to_colors()
        darkened_colors = darkened.to_colors()

        for orig, dark in zip(original_colors, darkened_colors):
            orig_sum = sum(orig.rgb())
            dark_sum = sum(dark.rgb())
            assert dark_sum <= orig_sum  # Should be darker or same

    def test_darken_amount_validation(self):
        """Test darken amount validation."""
        with pytest.raises(ValueError, match="Amount must be between 0.0 and 1.0"):
            self.batch.darken(-0.1)

        with pytest.raises(ValueError, match="Amount must be between 0.0 and 1.0"):
            self.batch.darken(1.1)

    def test_darken_zero_amount(self):
        """Test darkening with zero amount returns similar colors."""
        darkened = self.batch.darken(0.0)
        original_colors = self.batch.to_colors()
        darkened_colors = darkened.to_colors()

        for orig, dark in zip(original_colors, darkened_colors):
            # Should be very close (allowing for colorspace conversion differences)
            orig_rgb = orig.rgb()
            dark_rgb = dark.rgb()
            for orig_val, dark_val in zip(orig_rgb, dark_rgb):
                assert abs(orig_val - dark_val) <= 2

    def test_darken_full_amount(self):
        """Test darkening with full amount produces dark colors."""
        darkened = self.batch.darken(1.0)
        darkened_colors = darkened.to_colors()

        # Check that colors are significantly darker than originals
        original_colors = self.batch.to_colors()
        for orig, dark in zip(original_colors, darkened_colors):
            orig_sum = sum(orig.rgb())
            dark_sum = sum(dark.rgb())
            # Should be significantly darker (at least 30% reduction)
            assert dark_sum <= orig_sum * 0.7

    @patch('src.color.batch.colorspacious.cspace_convert')
    def test_darken_fallback(self, mock_convert):
        """Test darkening fallback when colorspacious fails."""
        mock_convert.side_effect = Exception("Mock error")

        darkened = self.batch.darken(0.3)
        assert isinstance(darkened, ColorBatch)
        assert len(darkened) == len(self.batch)


class TestColorBatchLightening:
    """Test ColorBatch lightening operations."""

    def setup_method(self):
        self.colors = [Color('#800000'), Color('#404040'), Color('#000000')]
        self.batch = ColorBatch(self.colors)

    def test_lighten_basic(self):
        """Test basic lightening operation."""
        lightened = self.batch.lighten(0.2)

        assert isinstance(lightened, ColorBatch)
        assert len(lightened) == len(self.batch)

        # Check that colors are indeed lighter
        original_colors = self.batch.to_colors()
        lightened_colors = lightened.to_colors()

        for orig, light in zip(original_colors, lightened_colors):
            orig_sum = sum(orig.rgb())
            light_sum = sum(light.rgb())
            assert light_sum >= orig_sum  # Should be lighter or same

    def test_lighten_amount_validation(self):
        """Test lighten amount validation."""
        with pytest.raises(ValueError, match="Amount must be between 0.0 and 1.0"):
            self.batch.lighten(-0.1)

        with pytest.raises(ValueError, match="Amount must be between 0.0 and 1.0"):
            self.batch.lighten(1.5)

    def test_lighten_zero_amount(self):
        """Test lightening with zero amount returns similar colors."""
        lightened = self.batch.lighten(0.0)
        original_colors = self.batch.to_colors()
        lightened_colors = lightened.to_colors()

        for orig, light in zip(original_colors, lightened_colors):
            # Should be very close (allowing for colorspace conversion differences)
            orig_rgb = orig.rgb()
            light_rgb = light.rgb()
            for orig_val, light_val in zip(orig_rgb, light_rgb):
                assert abs(orig_val - light_val) <= 2

    def test_lighten_full_amount(self):
        """Test lightening with full amount produces light colors."""
        lightened = self.batch.lighten(1.0)
        lightened_colors = lightened.to_colors()

        # Check that colors are significantly lighter than originals
        original_colors = self.batch.to_colors()
        for orig, light in zip(original_colors, lightened_colors):
            orig_sum = sum(orig.rgb())
            light_sum = sum(light.rgb())
            # Should be significantly lighter (at least 30% increase)
            assert light_sum >= orig_sum * 1.3

    @patch('src.color.batch.colorspacious.cspace_convert')
    def test_lighten_fallback(self, mock_convert):
        """Test lightening fallback when colorspacious fails."""
        mock_convert.side_effect = Exception("Mock error")

        lightened = self.batch.lighten(0.3)
        assert isinstance(lightened, ColorBatch)
        assert len(lightened) == len(self.batch)


class TestColorBatchSaturation:
    """Test ColorBatch saturation operations."""

    def setup_method(self):
        self.colors = [Color('#ff0000'), Color('#808080'), Color('#ffff00')]
        self.batch = ColorBatch(self.colors)

    def test_saturate_basic(self):
        """Test basic saturation operation."""
        saturated = self.batch.saturate(0.2)

        assert isinstance(saturated, ColorBatch)
        assert len(saturated) == len(self.batch)

    def test_desaturate_basic(self):
        """Test basic desaturation operation."""
        desaturated = self.batch.desaturate(0.2)

        assert isinstance(desaturated, ColorBatch)
        assert len(desaturated) == len(self.batch)

        # Desaturate should be equivalent to saturate with negative amount
        saturated_negative = self.batch.saturate(-0.2)
        desat_colors = desaturated.to_colors()
        sat_neg_colors = saturated_negative.to_colors()

        for desat, sat_neg in zip(desat_colors, sat_neg_colors):
            assert desat.rgb() == sat_neg.rgb()





class TestColorBatchAlphaOperations:
    """Test ColorBatch alpha channel operations."""

    def setup_method(self):
        self.colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        self.batch = ColorBatch(self.colors)

    def test_alpha_basic(self):
        """Test setting alpha for all colors."""
        alpha_batch = self.batch.alpha(0.5)

        assert isinstance(alpha_batch, ColorBatch)
        assert len(alpha_batch) == len(self.batch)

        # Check that all colors have the specified alpha
        colors_with_alpha = alpha_batch.to_colors()
        for color in colors_with_alpha:
            assert hasattr(color, '_alpha')
            assert color._alpha == 0.5

    def test_alpha_validation(self):
        """Test alpha value validation."""
        with pytest.raises(ValueError, match="Alpha must be between 0.0 and 1.0"):
            self.batch.alpha(-0.1)

        with pytest.raises(ValueError, match="Alpha must be between 0.0 and 1.0"):
            self.batch.alpha(1.1)

    def test_alpha_boundary_values(self):
        """Test alpha with boundary values."""
        # Test with 0.0 alpha
        transparent = self.batch.alpha(0.0)
        transparent_colors = transparent.to_colors()
        for color in transparent_colors:
            assert color._alpha == 0.0

        # Test with 1.0 alpha
        opaque = self.batch.alpha(1.0)
        opaque_colors = opaque.to_colors()
        for color in opaque_colors:
            assert color._alpha == 1.0


class TestColorBatchBlending:
    """Test ColorBatch blending operations."""

    def setup_method(self):
        self.batch1 = ColorBatch([Color('#ff0000'), Color('#00ff00'), Color('#0000ff')])
        self.batch2 = ColorBatch([Color('#ffffff'), Color('#000000'), Color('#808080')])

    def test_blend_basic(self):
        """Test basic blending operation."""
        blended = self.batch1.blend(self.batch2, 0.5)

        assert isinstance(blended, ColorBatch)
        assert len(blended) == len(self.batch1)

        # Check that blended colors are between original colors
        blended_colors = blended.to_colors()
        batch1_colors = self.batch1.to_colors()
        batch2_colors = self.batch2.to_colors()

        for blended_color, color1, color2 in zip(blended_colors, batch1_colors, batch2_colors):
            # Each RGB component should be between the two original colors
            blended_rgb = blended_color.rgb()
            rgb1 = color1.rgb()
            rgb2 = color2.rgb()

            for b, c1, c2 in zip(blended_rgb, rgb1, rgb2):
                min_val = min(c1, c2)
                max_val = max(c1, c2)
                assert min_val <= b <= max_val

    def test_blend_ratio_validation(self):
        """Test blend ratio validation."""
        with pytest.raises(ValueError, match="Ratio must be between 0.0 and 1.0"):
            self.batch1.blend(self.batch2, -0.1)

        with pytest.raises(ValueError, match="Ratio must be between 0.0 and 1.0"):
            self.batch1.blend(self.batch2, 1.1)

    def test_blend_length_validation(self):
        """Test blending with different batch lengths."""
        shorter_batch = ColorBatch([Color('#ff0000'), Color('#00ff00')])

        with pytest.raises(ValueError, match="Cannot blend batches of different lengths"):
            self.batch1.blend(shorter_batch, 0.5)

    def test_blend_extreme_ratios(self):
        """Test blending with extreme ratios."""
        # Ratio 0.0 should return colors similar to batch1
        blended_0 = self.batch1.blend(self.batch2, 0.0)
        batch1_colors = self.batch1.to_colors()
        blended_0_colors = blended_0.to_colors()

        for orig, blended in zip(batch1_colors, blended_0_colors):
            assert orig.rgb() == blended.rgb()

        # Ratio 1.0 should return colors similar to batch2
        blended_1 = self.batch1.blend(self.batch2, 1.0)
        batch2_colors = self.batch2.to_colors()
        blended_1_colors = blended_1.to_colors()

        for orig, blended in zip(batch2_colors, blended_1_colors):
            assert orig.rgb() == blended.rgb()

    def test_blend_alpha_channels(self):
        """Test blending with alpha channels."""
        # Create batches with alpha
        batch1_alpha = self.batch1.alpha(0.8)
        batch2_alpha = self.batch2.alpha(0.4)

        blended = batch1_alpha.blend(batch2_alpha, 0.5)
        blended_colors = blended.to_colors()

        # Alpha should be blended too
        for color in blended_colors:
            assert hasattr(color, '_alpha')
            # 0.5 * 0.8 + 0.5 * 0.4 = 0.6
            assert abs(color._alpha - 0.6) < 0.01


class TestColorBatchChaining:
    """Test ColorBatch method chaining operations."""

    def setup_method(self):
        self.colors = [Color('#ff0000'), Color('#808080'), Color('#0000ff')]
        self.batch = ColorBatch(self.colors)

    def test_chain_basic(self):
        """Test basic method chaining."""
        chained = self.batch.chain(
            ('darken', (0.1,), {}),
            ('saturate', (0.2,), {}),
            ('alpha', (0.8,), {})
        )

        assert isinstance(chained, ColorBatch)
        assert len(chained) == len(self.batch)

        # Check that operations were applied
        result_colors = chained.to_colors()
        for color in result_colors:
            assert hasattr(color, '_alpha')
            assert color._alpha == 0.8

    def test_chain_invalid_method(self):
        """Test chaining with invalid method name."""
        with pytest.raises(AttributeError, match="ColorBatch has no method 'invalid_method'"):
            self.batch.chain(
                ('darken', (0.1,), {}),
                ('invalid_method', (), {})
            )

    def test_chain_empty(self):
        """Test chaining with no operations."""
        chained = self.batch.chain()
        assert chained is self.batch  # Should return the same instance

    def test_chain_complex(self):
        """Test complex method chaining."""
        chained = self.batch.chain(
            ('lighten', (0.1,), {}),
            ('saturate', (0.3,), {}),
            ('darken', (0.05,), {}),
            ('alpha', (0.9,), {})
        )

        assert isinstance(chained, ColorBatch)
        result_colors = chained.to_colors()

        # Should have applied all operations
        for color in result_colors:
            assert hasattr(color, '_alpha')
            assert color._alpha == 0.9


class TestColorBatchSelectiveOperations:
    """Test ColorBatch selective operations on specific indices."""

    def setup_method(self):
        self.colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff'), Color('#ffff00')]
        self.batch = ColorBatch(self.colors)

    def test_apply_to_indices_basic(self):
        """Test applying operations to specific indices."""
        # Darken only the first and third colors (indices 0 and 2)
        result = self.batch.apply_to_indices([0, 2], lambda batch: batch.darken(0.3))

        assert isinstance(result, ColorBatch)
        assert len(result) == len(self.batch)

        original_colors = self.batch.to_colors()
        result_colors = result.to_colors()

        # Indices 0 and 2 should be darker
        assert sum(result_colors[0].rgb()) < sum(original_colors[0].rgb())
        assert sum(result_colors[2].rgb()) < sum(original_colors[2].rgb())

        # Indices 1 and 3 should be unchanged
        assert result_colors[1].rgb() == original_colors[1].rgb()
        assert result_colors[3].rgb() == original_colors[3].rgb()

    def test_apply_to_indices_empty(self):
        """Test applying operations to empty indices list."""
        result = self.batch.apply_to_indices([], lambda batch: batch.darken(0.5))

        # Should return equivalent batch
        original_colors = self.batch.to_colors()
        result_colors = result.to_colors()

        for orig, res in zip(original_colors, result_colors):
            assert orig.rgb() == res.rgb()

    def test_apply_to_indices_all(self):
        """Test applying operations to all indices."""
        all_indices = list(range(len(self.batch)))
        result = self.batch.apply_to_indices(all_indices, lambda batch: batch.lighten(0.2))

        # Should be equivalent to applying operation to entire batch
        direct_result = self.batch.lighten(0.2)

        result_colors = result.to_colors()
        direct_colors = direct_result.to_colors()

        for res, direct in zip(result_colors, direct_colors):
            assert res.rgb() == direct.rgb()

    def test_apply_to_indices_complex_operation(self):
        """Test applying complex operations to specific indices."""
        def complex_operation(batch):
            return batch.darken(0.1).saturate(0.2).alpha(0.7)

        result = self.batch.apply_to_indices([1, 3], complex_operation)

        result_colors = result.to_colors()

        # Check that only indices 1 and 3 have the alpha value
        assert not hasattr(result_colors[0], '_alpha') or abs(result_colors[0]._alpha - 1.0) < 0.01
        assert abs(result_colors[1]._alpha - 0.7) < 0.01
        assert not hasattr(result_colors[2], '_alpha') or abs(result_colors[2]._alpha - 1.0) < 0.01
        assert abs(result_colors[3]._alpha - 0.7) < 0.01


class TestColorBatchFactoryMethods:
    """Test ColorBatch factory methods."""

    def test_from_hex_list(self):
        """Test creating ColorBatch from hex list."""
        hex_colors = ['#ff0000', '#00ff00', '#0000ff']
        batch = ColorBatch.from_hex_list(hex_colors)

        assert isinstance(batch, ColorBatch)
        assert len(batch) == 3

        colors = batch.to_colors()
        assert colors[0].rgb() == (255, 0, 0)
        assert colors[1].rgb() == (0, 255, 0)
        assert colors[2].rgb() == (0, 0, 255)

    def test_gradient_basic(self):
        """Test creating gradient ColorBatch."""
        start_color = Color('#ff0000')
        end_color = Color('#0000ff')
        gradient = ColorBatch.gradient(start_color, end_color, 5)

        assert isinstance(gradient, ColorBatch)
        assert len(gradient) == 5

        colors = gradient.to_colors()
        # First color should be close to start color
        assert colors[0].rgb()[0] > 200  # High red
        assert colors[0].rgb()[2] < 50   # Low blue

        # Last color should be close to end color
        assert colors[-1].rgb()[0] < 50  # Low red
        assert colors[-1].rgb()[2] > 200 # High blue

    def test_gradient_steps_validation(self):
        """Test gradient steps validation."""
        start_color = Color('#ff0000')
        end_color = Color('#0000ff')

        with pytest.raises(ValueError, match="Steps must be at least 2"):
            ColorBatch.gradient(start_color, end_color, 1)

    def test_gradient_with_alpha(self):
        """Test gradient creation with alpha channels."""
        start_color = Color((255, 0, 0, 0.2))
        end_color = Color((0, 0, 255, 0.8))
        gradient = ColorBatch.gradient(start_color, end_color, 5)

        colors = gradient.to_colors()

        # Check alpha interpolation
        assert hasattr(colors[0], '_alpha')
        assert hasattr(colors[-1], '_alpha')
        assert abs(colors[0]._alpha - 0.2) < 0.01
        assert abs(colors[-1]._alpha - 0.8) < 0.01

        # Middle colors should have interpolated alpha
        assert 0.2 < colors[2]._alpha < 0.8

    def test_gradient_minimum_steps(self):
        """Test gradient with minimum number of steps."""
        start_color = Color('#ff0000')
        end_color = Color('#0000ff')
        gradient = ColorBatch.gradient(start_color, end_color, 2)

        assert len(gradient) == 2
        colors = gradient.to_colors()

        # Should be close to start and end colors
        assert colors[0].rgb()[0] > 200
        assert colors[1].rgb()[2] > 200


class TestColorBatchPerformance:
    """Test ColorBatch performance characteristics."""

    def setup_method(self):
        # Create larger batches for performance testing
        self.large_batch = ColorBatch([Color(f'#{i:06x}') for i in range(0, 1000)])
        self.medium_batch = ColorBatch([Color(f'#{i:06x}') for i in range(0, 100)])

    def test_vectorized_operations_performance(self):
        """Test that vectorized operations complete in reasonable time."""
        import time

        # Test darken operation on large batch
        start_time = time.perf_counter()
        darkened = self.large_batch.darken(0.2)
        darken_time = time.perf_counter() - start_time

        assert isinstance(darkened, ColorBatch)
        assert len(darkened) == 1000
        assert darken_time < 1.0  # Should complete in under 1 second

        # Test lighten operation
        start_time = time.perf_counter()
        lightened = self.large_batch.lighten(0.2)
        lighten_time = time.perf_counter() - start_time

        assert isinstance(lightened, ColorBatch)
        assert lighten_time < 1.0

        # Test saturate operation
        start_time = time.perf_counter()
        saturated = self.large_batch.saturate(0.2)
        saturate_time = time.perf_counter() - start_time

        assert isinstance(saturated, ColorBatch)
        assert saturate_time < 1.0

    def test_batch_vs_individual_performance_conceptual(self):
        """Test that batch operations should be faster than individual operations (conceptual)."""
        # This test demonstrates the concept rather than timing individual operations
        # which would be slower and unreliable in unit tests

        # Batch operation
        batch_result = self.medium_batch.darken(0.2)
        assert isinstance(batch_result, ColorBatch)
        assert len(batch_result) == 100

        # The expectation is that the batch operation above is faster than
        # processing 100 individual colors, but we don't time it in unit tests

    def test_memory_efficiency(self):
        """Test memory efficiency of batch operations."""
        import gc

        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Perform batch operations
        result1 = self.medium_batch.darken(0.1)
        result2 = self.medium_batch.lighten(0.1)
        result3 = self.medium_batch.saturate(0.1)

        # Operations should create new batches
        assert isinstance(result1, ColorBatch)
        assert isinstance(result2, ColorBatch)
        assert isinstance(result3, ColorBatch)

        # Clean up
        del result1, result2, result3
        gc.collect()
        final_objects = len(gc.get_objects())

        # Should not have excessive object growth
        object_growth = final_objects - initial_objects
        assert object_growth < 5000, f"Created {object_growth} objects, expected < 5000"

    def test_numpy_array_efficiency(self):
        """Test NumPy array operations are efficient."""
        # Convert to numpy and back should be fast
        rgb_array = self.medium_batch.to_numpy()
        assert isinstance(rgb_array, np.ndarray)
        assert rgb_array.shape == (100, 3)

        # Create new batch from array
        new_batch = ColorBatch(rgb_array)
        assert len(new_batch) == 100


class TestColorBatchIntegration:
    """Test ColorBatch integration with other components."""

    def setup_method(self):
        self.colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        self.batch = ColorBatch(self.colors)

    def test_integration_with_color_objects(self):
        """Test integration between ColorBatch and individual Color objects."""
        # Get individual colors from batch
        individual_colors = self.batch.to_colors()

        # Apply same operation to batch and individual colors
        batch_darkened = self.batch.darken(0.2)
        individual_darkened = [color.darken(0.2) for color in individual_colors]

        batch_result_colors = batch_darkened.to_colors()

        # Results should be similar (allowing for precision differences)
        for batch_color, individual_color in zip(batch_result_colors, individual_darkened):
            batch_rgb = batch_color.rgb()
            individual_rgb = individual_color.rgb()

            for b, i in zip(batch_rgb, individual_rgb):
                assert abs(b - i) <= 5  # Allow small differences

    def test_round_trip_conversion(self):
        """Test round-trip conversion preserves color data."""
        # ColorBatch -> Color list -> ColorBatch
        color_list = self.batch.to_colors()
        new_batch = ColorBatch(color_list)

        # Should preserve original colors
        original_colors = self.batch.to_colors()
        new_colors = new_batch.to_colors()

        for orig, new in zip(original_colors, new_colors):
            assert orig.rgb() == new.rgb()

    def test_numpy_integration(self):
        """Test integration with NumPy arrays."""
        # Create batch from numpy array
        rgb_array = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255]], dtype=np.uint8)
        numpy_batch = ColorBatch(rgb_array)

        # Should create equivalent batch
        numpy_colors = numpy_batch.to_colors()
        original_colors = self.batch.to_colors()

        for numpy_color, orig_color in zip(numpy_colors, original_colors):
            assert numpy_color.rgb() == orig_color.rgb()

    def test_chained_operations_integration(self):
        """Test complex chained operations work correctly."""
        result = (self.batch
                 .darken(0.1)
                 .saturate(0.2)
                 .lighten(0.05)
                 .alpha(0.8)
                 .blend(self.batch, 0.3))

        assert isinstance(result, ColorBatch)
        assert len(result) == len(self.batch)

        # Should have applied all operations
        result_colors = result.to_colors()
        for color in result_colors:
            assert hasattr(color, '_alpha')
            # Alpha should be blended: 0.8 * 0.7 + 1.0 * 0.3 = 0.56 + 0.3 = 0.86
            assert abs(color._alpha - 0.86) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v'])