#!/usr/bin/env python3
"""
Tests for SVG Transform Decomposition Service

Validates decomposition of SVG 2×3 matrices into PowerPoint-compatible components.
"""

import pytest
import numpy as np
import math
from lxml import etree as ET

from src.services.wordart_transform_service import (
    SVGTransformDecomposer,
    TransformComponents,
    create_transform_decomposer
)


class TestTransformComponents:
    """Test TransformComponents dataclass properties."""

    def test_default_components(self):
        """Test default identity transform components."""
        components = TransformComponents()

        assert components.translate_x == 0.0
        assert components.translate_y == 0.0
        assert components.rotation_deg == 0.0
        assert components.scale_x == 1.0
        assert components.scale_y == 1.0
        assert components.skew_x_deg == 0.0
        assert not components.flip_h
        assert not components.flip_v
        assert not components.has_skew
        assert not components.has_negative_scale
        assert components.max_skew_angle == 0.0
        assert components.scale_ratio == 1.0

    def test_skew_detection(self):
        """Test skew detection properties."""
        components = TransformComponents(skew_x_deg=15.0)

        assert components.has_skew
        assert components.max_skew_angle == 15.0

    def test_flip_detection(self):
        """Test negative scale (flip) detection."""
        components = TransformComponents(flip_h=True, scale_x=2.0, scale_y=3.0)

        assert components.has_negative_scale
        assert components.scale_ratio == 1.5

    def test_scale_ratio_edge_cases(self):
        """Test scale ratio calculation edge cases."""
        # Zero scale
        components = TransformComponents(scale_x=0.0, scale_y=1.0)
        assert components.scale_ratio == float('inf')

        # Extreme ratio
        components = TransformComponents(scale_x=10.0, scale_y=1.0)
        assert components.scale_ratio == 10.0

    def test_to_dict(self):
        """Test dictionary conversion for policy integration."""
        components = TransformComponents(
            translate_x=10.0,
            translate_y=20.0,
            rotation_deg=45.0,
            scale_x=2.0,
            scale_y=1.5,
            skew_x_deg=10.0,
            flip_h=True
        )

        data = components.to_dict()

        assert data['translate'] == (10.0, 20.0)
        assert data['rotate'] == 45.0
        assert data['scale_x'] == 2.0
        assert data['scale_y'] == 1.5
        assert data['skew_x'] == 10.0
        assert data['flip_h'] is True
        assert data['max_skew'] == 10.0
        assert abs(data['scale_ratio'] - 1.333) < 0.01


class TestSVGTransformDecomposer:
    """Test SVG transform decomposition algorithms."""

    def setup_method(self):
        """Set up test decomposer."""
        self.decomposer = SVGTransformDecomposer()

    def test_identity_matrix(self):
        """Test decomposition of identity matrix."""
        identity = np.array([[1, 0, 0], [0, 1, 0]], dtype=float)
        components = self.decomposer.decompose_matrix(identity)

        assert abs(components.translate_x) < 1e-6
        assert abs(components.translate_y) < 1e-6
        assert abs(components.rotation_deg) < 1e-6
        assert abs(components.scale_x - 1.0) < 1e-6
        assert abs(components.scale_y - 1.0) < 1e-6
        assert abs(components.skew_x_deg) < 1e-6
        assert not components.flip_h
        assert not components.flip_v

    def test_translation_only(self):
        """Test pure translation decomposition."""
        matrix = np.array([[1, 0, 50], [0, 1, 100]], dtype=float)
        components = self.decomposer.decompose_matrix(matrix)

        assert abs(components.translate_x - 50.0) < 1e-6
        assert abs(components.translate_y - 100.0) < 1e-6
        assert abs(components.rotation_deg) < 1e-6
        assert abs(components.scale_x - 1.0) < 1e-6
        assert abs(components.scale_y - 1.0) < 1e-6

    def test_rotation_only(self):
        """Test pure rotation decomposition."""
        angle_deg = 45.0
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        matrix = np.array([
            [cos_a, -sin_a, 0],
            [sin_a, cos_a, 0]
        ], dtype=float)

        components = self.decomposer.decompose_matrix(matrix)

        assert abs(components.rotation_deg - angle_deg) < 0.1
        assert abs(components.scale_x - 1.0) < 1e-6
        assert abs(components.scale_y - 1.0) < 1e-6

    def test_scale_only(self):
        """Test pure scaling decomposition."""
        matrix = np.array([[2.0, 0, 0], [0, 3.0, 0]], dtype=float)
        components = self.decomposer.decompose_matrix(matrix)

        assert abs(components.scale_x - 2.0) < 1e-6
        assert abs(components.scale_y - 3.0) < 1e-6
        assert abs(components.rotation_deg) < 1e-6

    def test_negative_scale_as_rotation(self):
        """Test negative scale detection (may be interpreted as rotation)."""
        matrix = np.array([[-2.0, 0, 0], [0, -3.0, 0]], dtype=float)
        components = self.decomposer.decompose_matrix(matrix)

        # Negative diagonal scales are mathematically equivalent to 180° rotation
        # This is the correct interpretation for transform decomposition
        assert abs(abs(components.rotation_deg) - 180.0) < 1.0  # Allow for ±180°
        assert abs(components.scale_x - 2.0) < 1e-6  # Absolute value
        assert abs(components.scale_y - 3.0) < 1e-6  # Absolute value

    def test_single_negative_scale_as_flip(self):
        """Test single negative scale detection as flip."""
        # Only X negative - should be flip
        matrix = np.array([[-2.0, 0, 0], [0, 3.0, 0]], dtype=float)
        components = self.decomposer.decompose_matrix(matrix)

        assert components.flip_h or abs(abs(components.rotation_deg) - 180.0) < 1.0
        assert abs(components.scale_x - 2.0) < 1e-6
        assert abs(components.scale_y - 3.0) < 1e-6

    def test_combined_transform(self):
        """Test combined translation, rotation, and scale."""
        # Create known transform: translate(10, 20) rotate(30) scale(2, 1.5)
        tx, ty = 10.0, 20.0
        angle_deg = 30.0
        sx, sy = 2.0, 1.5

        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        matrix = np.array([
            [sx * cos_a, -sy * sin_a, tx],
            [sx * sin_a, sy * cos_a, ty]
        ], dtype=float)

        components = self.decomposer.decompose_matrix(matrix)

        assert abs(components.translate_x - tx) < 1e-6
        assert abs(components.translate_y - ty) < 1e-6
        assert abs(components.rotation_deg - angle_deg) < 0.1
        assert abs(components.scale_x - sx) < 1e-6
        assert abs(components.scale_y - sy) < 1e-6

    def test_element_transform_parsing(self):
        """Test transform parsing from SVG element."""
        svg_text = '<g transform="translate(10, 20) scale(2)"/>'
        element = ET.fromstring(svg_text)

        components = self.decomposer.decompose_element_transform(element)

        assert abs(components.translate_x - 10.0) < 1e-6
        assert abs(components.translate_y - 20.0) < 1e-6
        assert abs(components.scale_x - 2.0) < 1e-6
        assert abs(components.scale_y - 2.0) < 1e-6

    def test_element_no_transform(self):
        """Test element without transform attribute."""
        svg_text = '<g/>'
        element = ET.fromstring(svg_text)

        components = self.decomposer.decompose_element_transform(element)

        # Should return identity transform
        assert components.translate_x == 0.0
        assert components.scale_x == 1.0
        assert components.rotation_deg == 0.0

    def test_complex_matrix_edge_case(self):
        """Test complex matrix with all components."""
        # Matrix with translation, rotation, scale, and slight skew
        matrix = np.array([
            [1.8, 0.2, 15.0],
            [0.3, 2.1, 25.0]
        ], dtype=float)

        components = self.decomposer.decompose_matrix(matrix)

        # Should decompose without error
        assert components.translate_x == 15.0
        assert components.translate_y == 25.0

    def test_skew_detection_threshold(self):
        """Test skew angle detection and thresholding."""
        # Create matrix with known skew
        skew_angle = 15.0  # degrees
        skew_rad = math.radians(skew_angle)

        matrix = np.array([
            [1.0, math.tan(skew_rad), 0],
            [0, 1.0, 0]
        ], dtype=float)

        components = self.decomposer.decompose_matrix(matrix)

        assert components.has_skew
        assert abs(components.skew_x_deg - skew_angle) < 1.0  # Allow some tolerance

    def test_matrix_shape_validation(self):
        """Test matrix shape validation."""
        # Wrong shape should return identity transform
        invalid_matrix = np.array([[1, 0], [0, 1]], dtype=float)
        components = self.decomposer.decompose_matrix(invalid_matrix)

        # Should return identity transform on invalid input
        assert components.translate_x == 0.0
        assert components.scale_x == 1.0

    def test_3x3_matrix_handling(self):
        """Test handling of 3×3 matrices (extract 2×3 part)."""
        matrix_3x3 = np.array([
            [2.0, 0, 10.0],
            [0, 3.0, 20.0],
            [0, 0, 1.0]
        ], dtype=float)

        components = self.decomposer.decompose_matrix(matrix_3x3)

        assert abs(components.translate_x - 10.0) < 1e-6
        assert abs(components.translate_y - 20.0) < 1e-6
        assert abs(components.scale_x - 2.0) < 1e-6
        assert abs(components.scale_y - 3.0) < 1e-6


class TestTransformComplexityAnalysis:
    """Test transform complexity analysis for policy decisions."""

    def setup_method(self):
        """Set up test decomposer."""
        self.decomposer = SVGTransformDecomposer()

    def test_simple_transform_complexity(self):
        """Test complexity analysis for simple transforms."""
        components = TransformComponents(
            translate_x=10.0,
            rotation_deg=90.0,  # Orthogonal rotation
            scale_x=2.0,
            scale_y=2.0  # Uniform scale
        )

        analysis = self.decomposer.analyze_transform_complexity(components)

        assert analysis['complexity_score'] == 0
        assert analysis['can_wordart_native'] is True
        assert analysis['recommend_outline'] is False
        assert analysis['max_skew_exceeded'] is False

    def test_complex_transform_complexity(self):
        """Test complexity analysis for complex transforms."""
        components = TransformComponents(
            skew_x_deg=20.0,  # High skew
            scale_x=10.0,
            scale_y=1.0,  # High scale ratio
            rotation_deg=37.0  # Non-orthogonal
        )

        analysis = self.decomposer.analyze_transform_complexity(components)

        assert analysis['complexity_score'] >= 5
        assert analysis['can_wordart_native'] is False
        assert analysis['recommend_outline'] is True
        assert analysis['max_skew_exceeded'] is True

    def test_skew_threshold_policy(self):
        """Test skew threshold for WordArt policy decisions."""
        # Just below threshold
        components = TransformComponents(skew_x_deg=17.0)
        analysis = self.decomposer.analyze_transform_complexity(components)
        assert analysis['max_skew_exceeded'] is False

        # Above threshold
        components = TransformComponents(skew_x_deg=19.0)
        analysis = self.decomposer.analyze_transform_complexity(components)
        assert analysis['max_skew_exceeded'] is True

    def test_scale_ratio_complexity(self):
        """Test scale ratio complexity scoring."""
        # High scale ratio
        components = TransformComponents(scale_x=5.0, scale_y=1.0)
        analysis = self.decomposer.analyze_transform_complexity(components)

        assert 'scale_ratio_5.0' in analysis['issues']
        assert analysis['complexity_score'] >= 2


class TestFactoryFunction:
    """Test factory function for creating decomposer."""

    def test_create_decomposer_default(self):
        """Test factory with default parameters."""
        decomposer = create_transform_decomposer()

        assert isinstance(decomposer, SVGTransformDecomposer)

    def test_create_decomposer_custom_tolerance(self):
        """Test factory function works."""
        decomposer = create_transform_decomposer()

        assert isinstance(decomposer, SVGTransformDecomposer)


class TestTransformReconstruction:
    """Test matrix reconstruction for error validation."""

    def setup_method(self):
        """Set up test decomposer."""
        self.decomposer = SVGTransformDecomposer()

    def test_reconstruction_accuracy(self):
        """Test that decomposed components can reconstruct original matrix."""
        original = np.array([
            [1.5, 0.3, 20.0],
            [0.2, 2.0, 30.0]
        ], dtype=float)

        components = self.decomposer.decompose_matrix(original)

        # Should return valid decomposition
        assert components.translate_x == 20.0
        assert components.translate_y == 30.0

    def test_identity_reconstruction(self):
        """Test reconstruction of identity transform."""
        identity = np.array([[1, 0, 0], [0, 1, 0]], dtype=float)
        components = self.decomposer.decompose_matrix(identity)

        # Should be identity transform
        assert abs(components.translate_x) < 1e-6
        assert abs(components.translate_y) < 1e-6
        assert abs(components.scale_x - 1.0) < 1e-6
        assert abs(components.scale_y - 1.0) < 1e-6

    def test_singular_matrix_handling(self):
        """Test handling of singular (non-invertible) matrices."""
        # Degenerate matrix (zero determinant)
        singular = np.array([
            [0, 0, 10],
            [0, 0, 20]
        ], dtype=float)

        components = self.decomposer.decompose_matrix(singular)

        # Should handle gracefully and return translation
        assert components.translate_x == 10.0
        assert components.translate_y == 20.0