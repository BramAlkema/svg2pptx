#!/usr/bin/env python3
"""
Tests for CoordinateSpace - CTM Stack Management
"""

import pytest
from core.transforms import Matrix, CoordinateSpace


class TestCoordinateSpaceInitialization:
    """Test CoordinateSpace initialization."""

    def test_initialization_with_identity(self):
        """Test initialization with identity matrix."""
        coord_space = CoordinateSpace()
        
        assert coord_space.depth == 1
        assert coord_space.current_ctm.is_identity()

    def test_initialization_with_viewport_matrix(self):
        """Test initialization with custom viewport matrix."""
        viewport = Matrix.translate(100, 200)
        coord_space = CoordinateSpace(viewport)
        
        assert coord_space.depth == 1
        assert coord_space.current_ctm == viewport


class TestCTMStackOperations:
    """Test push/pop operations on CTM stack."""

    def test_push_transform(self):
        """Test pushing transform onto stack."""
        coord_space = CoordinateSpace()
        transform = Matrix.translate(10, 20)
        
        coord_space.push_transform(transform)
        
        assert coord_space.depth == 2
        x, y = coord_space.apply_ctm(0, 0)
        assert x == 10
        assert y == 20

    def test_pop_transform(self):
        """Test popping transform from stack."""
        coord_space = CoordinateSpace()
        transform = Matrix.translate(10, 20)
        
        coord_space.push_transform(transform)
        coord_space.pop_transform()
        
        assert coord_space.depth == 1
        assert coord_space.is_identity()

    def test_pop_viewport_raises_error(self):
        """Test that popping viewport matrix raises error."""
        coord_space = CoordinateSpace()
        
        with pytest.raises(ValueError, match="Cannot pop viewport matrix"):
            coord_space.pop_transform()

    def test_nested_transforms(self):
        """Test nested transform push/pop."""
        coord_space = CoordinateSpace()
        
        # Push first transform
        coord_space.push_transform(Matrix.translate(10, 0))
        assert coord_space.depth == 2
        
        # Push second transform (nested)
        coord_space.push_transform(Matrix.translate(5, 0))
        assert coord_space.depth == 3
        
        # Should be at x=15 (10+5)
        x, y = coord_space.apply_ctm(0, 0)
        assert x == 15
        assert y == 0
        
        # Pop second transform
        coord_space.pop_transform()
        assert coord_space.depth == 2
        x, y = coord_space.apply_ctm(0, 0)
        assert x == 10
        
        # Pop first transform
        coord_space.pop_transform()
        assert coord_space.depth == 1
        assert coord_space.is_identity()


class TestCTMComposition:
    """Test CTM composition with various transforms."""

    def test_compose_translate(self):
        """Test composition of translation transforms."""
        coord_space = CoordinateSpace()
        
        coord_space.push_transform(Matrix.translate(10, 20))
        coord_space.push_transform(Matrix.translate(5, 10))
        
        x, y = coord_space.apply_ctm(0, 0)
        assert x == 15  # 10 + 5
        assert y == 30  # 20 + 10

    def test_compose_scale(self):
        """Test composition of scale transforms."""
        coord_space = CoordinateSpace()
        
        coord_space.push_transform(Matrix.scale(2, 2))
        coord_space.push_transform(Matrix.scale(3, 3))
        
        x, y = coord_space.apply_ctm(1, 1)
        assert x == 6  # 1 * 2 * 3
        assert y == 6  # 1 * 2 * 3

    def test_compose_translate_and_scale(self):
        """Test composition of translate and scale."""
        coord_space = CoordinateSpace()

        # Push translate first
        coord_space.push_transform(Matrix.translate(10, 20))
        # Push scale (composes with translate)
        coord_space.push_transform(Matrix.scale(2, 2))

        x, y = coord_space.apply_ctm(0, 0)
        # First push creates: Identity * Translate = Translate
        # Second push creates: Translate * Scale
        # Order of operations: scale happens in local space, then translate
        # Point (0,0) scaled by 2 = (0,0), then translated = (10, 20)
        assert x == 10
        assert y == 20

    def test_compose_rotate_and_translate(self):
        """Test composition of rotation and translation."""
        import math

        coord_space = CoordinateSpace()

        # Rotate 90 degrees, then translate
        coord_space.push_transform(Matrix.rotate(90))
        coord_space.push_transform(Matrix.translate(10, 0))

        x, y = coord_space.apply_ctm(10, 0)
        # Composition: Rotate(90) * Translate(10,0)
        # Point (10, 0) after rotation: (0, 10)
        # Then translate happens in rotated space
        # Final: (0, 20)
        assert abs(x - 0) < 0.001
        assert abs(y - 20) < 0.001


class TestApplyCTM:
    """Test applying CTM to coordinates."""

    def test_apply_ctm_with_identity(self):
        """Test applying identity CTM."""
        coord_space = CoordinateSpace()
        
        x, y = coord_space.apply_ctm(100, 200)
        assert x == 100
        assert y == 200

    def test_apply_ctm_with_translation(self):
        """Test applying translation CTM."""
        viewport = Matrix.translate(50, 100)
        coord_space = CoordinateSpace(viewport)
        
        x, y = coord_space.apply_ctm(10, 20)
        assert x == 60  # 10 + 50
        assert y == 120  # 20 + 100

    def test_apply_ctm_with_scale(self):
        """Test applying scale CTM."""
        viewport = Matrix.scale(2, 3)
        coord_space = CoordinateSpace(viewport)
        
        x, y = coord_space.apply_ctm(10, 20)
        assert x == 20  # 10 * 2
        assert y == 60  # 20 * 3

    def test_apply_ctm_to_points_batch(self):
        """Test applying CTM to multiple points."""
        viewport = Matrix.translate(10, 20)
        coord_space = CoordinateSpace(viewport)
        
        points = [(0, 0), (10, 10), (20, 30)]
        transformed = coord_space.apply_ctm_to_points(points)
        
        assert len(transformed) == 3
        assert transformed[0] == (10, 20)
        assert transformed[1] == (20, 30)
        assert transformed[2] == (30, 50)


class TestViewportMatrix:
    """Test viewport matrix integration."""

    def test_viewport_with_transform(self):
        """Test viewport matrix combined with element transform."""
        # Viewport: translate to (100, 100)
        viewport = Matrix.translate(100, 100)
        coord_space = CoordinateSpace(viewport)
        
        # Element transform: scale 2x
        coord_space.push_transform(Matrix.scale(2, 2))
        
        # Apply to point (10, 10)
        x, y = coord_space.apply_ctm(10, 10)
        # After scale: (20, 20)
        # After viewport translate: (120, 120)
        assert x == 120
        assert y == 120

    def test_complex_viewport_scenario(self):
        """Test complex viewport with nested transforms."""
        # Viewport: scale to fit slide
        viewport = Matrix.scale(2, 2)
        coord_space = CoordinateSpace(viewport)
        
        # Group transform: translate
        coord_space.push_transform(Matrix.translate(50, 50))
        
        # Shape transform: scale again
        coord_space.push_transform(Matrix.scale(1.5, 1.5))
        
        # Original SVG coordinate: (10, 10)
        x, y = coord_space.apply_ctm(10, 10)
        # After shape scale 1.5x: (15, 15)
        # After group translate: (65, 65)
        # After viewport scale 2x: (130, 130)
        assert x == 130
        assert y == 130


class TestUtilityMethods:
    """Test utility methods."""

    def test_is_identity(self):
        """Test is_identity check."""
        coord_space = CoordinateSpace()
        assert coord_space.is_identity()
        
        coord_space.push_transform(Matrix.translate(10, 10))
        assert not coord_space.is_identity()

    def test_reset_to_viewport(self):
        """Test resetting to viewport matrix."""
        coord_space = CoordinateSpace()
        
        coord_space.push_transform(Matrix.translate(10, 10))
        coord_space.push_transform(Matrix.scale(2, 2))
        assert coord_space.depth == 3
        
        coord_space.reset_to_viewport()
        assert coord_space.depth == 1
        assert coord_space.is_identity()

    def test_repr(self):
        """Test string representation."""
        coord_space = CoordinateSpace()
        repr_str = repr(coord_space)
        
        assert 'CoordinateSpace' in repr_str
        assert 'depth=1' in repr_str


class TestRealWorldScenarios:
    """Test real-world SVG scenarios."""

    def test_nested_groups_with_transforms(self):
        """Test nested groups like SVG <g> elements."""
        coord_space = CoordinateSpace()
        
        # Outer group: translate(100, 100) scale(2)
        coord_space.push_transform(Matrix.translate(100, 100))
        coord_space.push_transform(Matrix.scale(2, 2))
        
        # Inner group: translate(50, 50)
        coord_space.push_transform(Matrix.translate(50, 50))
        
        # Shape in inner group at (10, 10)
        x, y = coord_space.apply_ctm(10, 10)
        # After inner translate: (60, 60)
        # After scale 2x: (120, 120)
        # After outer translate: (220, 220)
        assert x == 220
        assert y == 220
        
        # Exit inner group
        coord_space.pop_transform()
        
        # Shape in outer group at (10, 10)
        x, y = coord_space.apply_ctm(10, 10)
        # After scale: (20, 20)
        # After translate: (120, 120)
        assert x == 120
        assert y == 120

    def test_transform_inheritance(self):
        """Test transform inheritance through element tree."""
        # Simulate viewport
        viewport = Matrix.scale(914400 / 96, 914400 / 96)  # 96 DPI to EMU (9525.0)
        coord_space = CoordinateSpace(viewport)

        # Root <svg> has viewBox transform
        coord_space.push_transform(Matrix.scale(1.5, 1.5))

        # <g> with transform
        coord_space.push_transform(Matrix.translate(10, 20))

        # <rect> at (5, 5)
        x, y = coord_space.apply_ctm(5, 5)
        # After <g> translate: (15, 25)
        # After viewBox scale: (22.5, 37.5)
        # After viewport scale: (214312.5, 357187.5)
        assert abs(x - 214312.5) < 1
        assert abs(y - 357187.5) < 1
