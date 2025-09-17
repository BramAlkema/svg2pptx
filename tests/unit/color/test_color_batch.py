#!/usr/bin/env python3
"""
Test suite for ColorBatch class functionality.

Tests batch processing operations, performance improvements, and vectorized
color manipulations using NumPy and colorspacious.
"""

import pytest
import numpy as np
from typing import List

from src.color import Color, ColorBatch


class TestColorBatchInitialization:
    """Test ColorBatch initialization from various inputs."""

    def test_batch_from_color_list(self):
        """Test creating ColorBatch from list of Color objects."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        batch = ColorBatch(colors)

        assert len(batch) == 3
        assert batch[0].hex() == 'ff0000'
        assert batch[1].hex() == '00ff00'
        assert batch[2].hex() == '0000ff'

    def test_batch_from_numpy_array(self):
        """Test creating ColorBatch from NumPy array."""
        rgb_array = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255]], dtype=np.uint8)
        batch = ColorBatch(rgb_array)

        assert len(batch) == 3
        assert batch[0].hex() == 'ff0000'
        assert batch[1].hex() == '00ff00'
        assert batch[2].hex() == '0000ff'

    def test_batch_from_hex_list(self):
        """Test creating ColorBatch from hex color list."""
        hex_colors = ['#ff0000', '#00ff00', '#0000ff']
        batch = ColorBatch.from_hex_list(hex_colors)

        assert len(batch) == 3
        assert batch[0].hex() == 'ff0000'

    def test_empty_list_raises_error(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot create ColorBatch from empty list"):
            ColorBatch([])

    def test_invalid_input_type_raises_error(self):
        """Test that invalid input type raises TypeError."""
        with pytest.raises(TypeError):
            ColorBatch("invalid")


class TestColorBatchOperations:
    """Test ColorBatch vectorized operations."""

    @pytest.fixture
    def sample_batch(self):
        """Provide sample ColorBatch for testing."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        return ColorBatch(colors)

    def test_batch_darken(self, sample_batch):
        """Test batch darkening operation."""
        darkened = sample_batch.darken(0.2)

        # Should return new ColorBatch
        assert isinstance(darkened, ColorBatch)
        assert len(darkened) == len(sample_batch)

        # Colors should be darker than originals
        for i, color in enumerate(darkened):
            original_lab = sample_batch[i].lab()
            darkened_lab = color.lab()
            assert darkened_lab[0] < original_lab[0]  # L* should be lower

    def test_batch_lighten(self, sample_batch):
        """Test batch lightening operation."""
        lightened = sample_batch.lighten(0.2)

        assert isinstance(lightened, ColorBatch)
        assert len(lightened) == len(sample_batch)

        # Colors should be lighter than originals (for most cases)
        for i, color in enumerate(lightened):
            original_lab = sample_batch[i].lab()
            lightened_lab = color.lab()
            # Lightness should generally increase (with some tolerance)
            assert lightened_lab[0] >= original_lab[0] - 1

    def test_batch_saturate(self, sample_batch):
        """Test batch saturation operation."""
        saturated = sample_batch.saturate(0.2)

        assert isinstance(saturated, ColorBatch)
        assert len(saturated) == len(sample_batch)

        # Test that operation completed without error
        assert all(isinstance(c, Color) for c in saturated)

    def test_batch_desaturate(self, sample_batch):
        """Test batch desaturation operation."""
        desaturated = sample_batch.desaturate(0.2)

        assert isinstance(desaturated, ColorBatch)
        assert len(desaturated) == len(sample_batch)

    def test_batch_alpha(self, sample_batch):
        """Test batch alpha setting."""
        alpha_batch = sample_batch.alpha(0.5)

        assert isinstance(alpha_batch, ColorBatch)

        for color in alpha_batch:
            assert abs(color._alpha - 0.5) < 1e-6

    def test_invalid_amount_raises_error(self, sample_batch):
        """Test that invalid amounts raise ValueError."""
        with pytest.raises(ValueError):
            sample_batch.darken(1.5)  # > 1.0

        with pytest.raises(ValueError):
            sample_batch.lighten(-0.1)  # < 0.0


class TestColorBatchBlending:
    """Test ColorBatch blending operations."""

    def test_batch_blend(self):
        """Test blending two ColorBatch instances."""
        batch1 = ColorBatch([Color('#ff0000'), Color('#00ff00')])
        batch2 = ColorBatch([Color('#0000ff'), Color('#ff00ff')])

        blended = batch1.blend(batch2, 0.5)

        assert isinstance(blended, ColorBatch)
        assert len(blended) == 2

    def test_blend_different_lengths_raises_error(self):
        """Test that blending batches of different lengths raises error."""
        batch1 = ColorBatch([Color('#ff0000')])
        batch2 = ColorBatch([Color('#0000ff'), Color('#00ff00')])

        with pytest.raises(ValueError, match="Cannot blend batches of different lengths"):
            batch1.blend(batch2, 0.5)

    def test_blend_invalid_ratio_raises_error(self):
        """Test that invalid blend ratio raises error."""
        batch1 = ColorBatch([Color('#ff0000')])
        batch2 = ColorBatch([Color('#0000ff')])

        with pytest.raises(ValueError):
            batch1.blend(batch2, 1.5)  # > 1.0


class TestColorBatchUtilities:
    """Test ColorBatch utility methods."""

    def test_gradient_creation(self):
        """Test gradient creation between two colors."""
        start = Color('#ff0000')
        end = Color('#0000ff')

        gradient = ColorBatch.gradient(start, end, 5)

        assert len(gradient) == 5
        assert gradient[0].hex() == 'ff0000'  # Start color
        assert gradient[-1].hex() == '0000ff'  # End color

    def test_gradient_invalid_steps_raises_error(self):
        """Test that invalid gradient steps raise error."""
        with pytest.raises(ValueError, match="Steps must be at least 2"):
            ColorBatch.gradient(Color('#ff0000'), Color('#0000ff'), 1)

    def test_batch_iteration(self):
        """Test iterating over ColorBatch."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        batch = ColorBatch(colors)

        iterated_colors = list(batch)
        assert len(iterated_colors) == 3
        assert all(isinstance(c, Color) for c in iterated_colors)

    def test_batch_indexing(self):
        """Test indexing into ColorBatch."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        batch = ColorBatch(colors)

        assert batch[0].hex() == 'ff0000'
        assert batch[1].hex() == '00ff00'
        assert batch[2].hex() == '0000ff'

    def test_to_colors_conversion(self):
        """Test converting batch back to list of Colors."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        batch = ColorBatch(colors)

        converted = batch.to_colors()

        assert len(converted) == 3
        assert all(isinstance(c, Color) for c in converted)
        assert converted[0].hex() == 'ff0000'

    def test_to_numpy_conversion(self):
        """Test converting batch to NumPy array."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        batch = ColorBatch(colors)

        array = batch.to_numpy()

        assert isinstance(array, np.ndarray)
        assert array.shape == (3, 3)
        assert np.array_equal(array[0], [255, 0, 0])


class TestColorBatchChaining:
    """Test ColorBatch method chaining operations."""

    def test_fluent_chaining(self):
        """Test chaining multiple operations together."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        batch = ColorBatch(colors)

        result = batch.darken(0.1).saturate(0.1).alpha(0.8)

        assert isinstance(result, ColorBatch)
        assert len(result) == 3

        # Check that alpha was set correctly
        for color in result:
            assert abs(color._alpha - 0.8) < 1e-6

    def test_chain_method(self):
        """Test explicit chain method."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        batch = ColorBatch(colors)

        result = batch.chain(
            ('darken', (0.2,), {}),
            ('saturate', (0.1,), {}),
            ('alpha', (0.8,), {})
        )

        assert isinstance(result, ColorBatch)
        assert len(result) == 3


class TestColorBatchAdvanced:
    """Test advanced ColorBatch functionality."""

    def test_apply_to_indices(self):
        """Test applying operations to specific indices."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        batch = ColorBatch(colors)

        # Darken only the first and third colors
        result = batch.apply_to_indices([0, 2], lambda b: b.darken(0.3))

        assert isinstance(result, ColorBatch)
        assert len(result) == 3

        # Second color should be unchanged
        assert result[1].hex() == batch[1].hex()

    def test_apply_to_empty_indices(self):
        """Test applying operations to empty indices list."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        batch = ColorBatch(colors)

        result = batch.apply_to_indices([], lambda b: b.darken(0.3))

        # Should return equivalent batch
        assert len(result) == len(batch)
        for i in range(len(batch)):
            assert result[i].hex() == batch[i].hex()


class TestColorBatchPerformance:
    """Test ColorBatch performance characteristics."""

    def test_large_batch_operations(self):
        """Test operations on large batches complete successfully."""
        # Create a large batch for performance testing
        colors = [Color(f'#{i*2:02x}{(i*3) % 256:02x}{(i*5) % 256:02x}') for i in range(100)]
        batch = ColorBatch(colors)

        # Test that operations complete without error
        darkened = batch.darken(0.2)
        lightened = batch.lighten(0.2)
        saturated = batch.saturate(0.1)

        assert len(darkened) == 100
        assert len(lightened) == 100
        assert len(saturated) == 100

        # Verify all results are valid Color objects
        for color_batch in [darkened, lightened, saturated]:
            for color in color_batch:
                assert isinstance(color, Color)
                rgb = color.rgb()
                assert all(0 <= c <= 255 for c in rgb)

    def test_batch_immutability(self):
        """Test that ColorBatch operations return new instances."""
        colors = [Color('#ff0000'), Color('#00ff00'), Color('#0000ff')]
        batch = ColorBatch(colors)

        darkened = batch.darken(0.2)

        # Original batch should be unchanged
        assert batch is not darkened
        assert batch[0].hex() == 'ff0000'  # Original unchanged

        # New batch should have different colors
        assert darkened[0].hex() != 'ff0000'