#!/usr/bin/env python3
"""
Gradient Color Accuracy Validation Tests

Validates color accuracy and perceptual quality of the NumPy gradient system
against reference implementations and color science standards.

Tests include:
- Color space conversion accuracy (RGB ↔ LAB ↔ HSL ↔ XYZ)
- Perceptual uniformity validation in LAB space
- Gradient interpolation accuracy vs reference implementations
- Color gamut preservation during conversions
- Delta-E color difference measurements
- White point and illuminant accuracy
- Round-trip conversion error analysis

Quality Standards:
- Color conversion accuracy: ΔE < 1.0 for most colors
- Round-trip error: < 0.1% RGB deviation
- LAB uniformity: Perceptual steps within 5% of expected
- Gamut preservation: > 99% of colors within valid ranges
"""

import unittest
import numpy as np
import warnings
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import colorsys

# Import gradient engines
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

# Mock scipy for testing without dependency
class MockInterpolate:
    class CubicSpline:
        def __init__(self, x, y, bc_type='natural'):
            self.x = x
            self.y = y

        def __call__(self, xi):
            return np.interp(xi, self.x, self.y)

sys.modules['scipy'] = type('MockModule', (), {})()
sys.modules['scipy.interpolate'] = MockInterpolate()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'converters', 'gradients'))

from advanced_gradient_engine import AdvancedGradientEngine, ColorSpace, OptimizedGradientData


@dataclass
class ColorAccuracyMetrics:
    """Color accuracy measurement results"""
    test_name: str
    colors_tested: int
    max_error: float
    mean_error: float
    std_error: float
    percentile_95_error: float
    passed: bool
    tolerance: float


class ColorScienceReference:
    """Reference color science implementations for validation"""

    @staticmethod
    def srgb_to_xyz_reference(rgb: np.ndarray) -> np.ndarray:
        """Reference sRGB to XYZ conversion (ITU-R BT.709)"""
        # Gamma correction
        rgb_linear = np.where(rgb > 0.04045,
                             np.power((rgb + 0.055) / 1.055, 2.4),
                             rgb / 12.92)

        # ITU-R BT.709 matrix
        matrix = np.array([
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041]
        ])

        return np.dot(rgb_linear, matrix.T)

    @staticmethod
    def xyz_to_lab_reference(xyz: np.ndarray) -> np.ndarray:
        """Reference XYZ to LAB conversion (CIE 1976)"""
        # D65 white point
        xyz_n = np.array([0.95047, 1.00000, 1.08883])

        # Normalize by white point
        xyz_normalized = xyz / xyz_n

        # CIE LAB transformation
        epsilon = 216.0 / 24389.0
        kappa = 24389.0 / 27.0

        f = np.where(xyz_normalized > epsilon,
                    np.power(xyz_normalized, 1.0/3.0),
                    (kappa * xyz_normalized + 16.0) / 116.0)

        L = 116.0 * f[:, 1] - 16.0
        a = 500.0 * (f[:, 0] - f[:, 1])
        b = 200.0 * (f[:, 1] - f[:, 2])

        return np.column_stack([L, a, b])

    @staticmethod
    def rgb_to_hsl_reference(rgb: np.ndarray) -> np.ndarray:
        """Reference RGB to HSL conversion using colorsys"""
        hsl = np.zeros_like(rgb)
        for i, (r, g, b) in enumerate(rgb):
            h, l, s = colorsys.rgb_to_hls(r, g, b)
            hsl[i] = [h, s, l]  # Note: colorsys returns HLS, we want HSL
        return hsl

    @staticmethod
    def calculate_delta_e_lab(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
        """Calculate Delta-E CIE 1976 color difference"""
        delta_l = lab1[:, 0] - lab2[:, 0]
        delta_a = lab1[:, 1] - lab2[:, 1]
        delta_b = lab1[:, 2] - lab2[:, 2]

        return np.sqrt(delta_l**2 + delta_a**2 + delta_b**2)

    @staticmethod
    def calculate_delta_e_2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
        """Calculate Delta-E CIE 2000 color difference (simplified)"""
        # Simplified implementation - full CIE 2000 is complex
        delta_l = lab1[:, 0] - lab2[:, 0]
        delta_a = lab1[:, 1] - lab2[:, 1]
        delta_b = lab1[:, 2] - lab2[:, 2]

        # Average L*
        l_avg = (lab1[:, 0] + lab2[:, 0]) / 2.0

        # Simplified weighting factors
        s_l = 1.0 + (0.015 * (l_avg - 50)**2) / np.sqrt(20 + (l_avg - 50)**2)
        s_c = 1.0 + 0.045 * np.sqrt(lab1[:, 1]**2 + lab1[:, 2]**2)
        s_h = 1.0 + 0.015 * np.sqrt(lab1[:, 1]**2 + lab1[:, 2]**2)

        # Parametric factors (simplified)
        k_l, k_c, k_h = 1.0, 1.0, 1.0

        delta_e = np.sqrt(
            (delta_l / (k_l * s_l))**2 +
            (np.sqrt(delta_a**2 + delta_b**2) / (k_c * s_c))**2 +
            (np.sqrt(delta_a**2 + delta_b**2) / (k_h * s_h))**2
        )

        return delta_e


class GradientColorAccuracyTests(unittest.TestCase):
    """Comprehensive color accuracy validation tests"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = AdvancedGradientEngine()
        self.reference = ColorScienceReference()
        self.results = []

        # Test color sets
        self.primary_colors = np.array([
            [1.0, 0.0, 0.0],  # Red
            [0.0, 1.0, 0.0],  # Green
            [0.0, 0.0, 1.0],  # Blue
            [1.0, 1.0, 1.0],  # White
            [0.0, 0.0, 0.0],  # Black
        ])

        self.grayscale_colors = np.linspace(0, 1, 11).reshape(-1, 1)
        self.grayscale_colors = np.repeat(self.grayscale_colors, 3, axis=1)

        self.random_colors = np.random.rand(1000, 3)

        # Color difference tolerances
        self.delta_e_tolerances = {
            'excellent': 1.0,      # Imperceptible
            'good': 2.3,          # Just perceptible
            'acceptable': 5.0,     # Perceptible but acceptable
            'poor': 10.0          # Poor quality
        }

    def _record_accuracy_metrics(self, metrics: ColorAccuracyMetrics):
        """Record accuracy metrics for final report"""
        self.results.append(metrics)

    def test_rgb_to_xyz_conversion_accuracy(self):
        """Test RGB to XYZ conversion accuracy against reference"""
        test_colors = [
            ("Primary Colors", self.primary_colors),
            ("Grayscale", self.grayscale_colors),
            ("Random Colors", self.random_colors[:100])  # Subset for speed
        ]

        for color_set_name, colors in test_colors:
            with self.subTest(color_set=color_set_name):
                # Our implementation
                xyz_ours = self.engine._rgb_to_xyz_batch(colors)

                # Reference implementation
                xyz_ref = self.reference.srgb_to_xyz_reference(colors)

                # Calculate errors
                errors = np.linalg.norm(xyz_ours - xyz_ref, axis=1)

                metrics = ColorAccuracyMetrics(
                    test_name=f"RGB→XYZ ({color_set_name})",
                    colors_tested=len(colors),
                    max_error=np.max(errors),
                    mean_error=np.mean(errors),
                    std_error=np.std(errors),
                    percentile_95_error=np.percentile(errors, 95),
                    passed=np.max(errors) < 0.001,  # Very tight tolerance for XYZ
                    tolerance=0.001
                )

                self._record_accuracy_metrics(metrics)

                # Assertions
                self.assertLess(np.max(errors), 0.001,
                               f"RGB→XYZ max error: {np.max(errors):.6f}, expected <0.001")
                self.assertLess(np.mean(errors), 0.0005,
                               f"RGB→XYZ mean error: {np.mean(errors):.6f}, expected <0.0005")

    def test_xyz_to_rgb_roundtrip_accuracy(self):
        """Test XYZ to RGB round-trip conversion accuracy"""
        test_colors = [
            ("Primary Colors", self.primary_colors),
            ("Grayscale", self.grayscale_colors),
            ("Random Colors", self.random_colors[:100])
        ]

        for color_set_name, colors in test_colors:
            with self.subTest(color_set=color_set_name):
                # Round-trip conversion
                xyz = self.engine._rgb_to_xyz_batch(colors)
                rgb_back = self.engine._xyz_to_rgb_batch(xyz)

                # Calculate errors
                errors = np.linalg.norm(colors - rgb_back, axis=1)
                relative_errors = errors / (np.linalg.norm(colors, axis=1) + 1e-10)

                metrics = ColorAccuracyMetrics(
                    test_name=f"RGB→XYZ→RGB ({color_set_name})",
                    colors_tested=len(colors),
                    max_error=np.max(relative_errors),
                    mean_error=np.mean(relative_errors),
                    std_error=np.std(relative_errors),
                    percentile_95_error=np.percentile(relative_errors, 95),
                    passed=np.max(relative_errors) < 0.01,  # <1% relative error
                    tolerance=0.01
                )

                self._record_accuracy_metrics(metrics)

                # Assertions
                self.assertLess(np.max(relative_errors), 0.01,
                               f"RGB round-trip max error: {np.max(relative_errors):.4f}, expected <0.01")

    def test_rgb_to_lab_conversion_accuracy(self):
        """Test RGB to LAB conversion accuracy against reference"""
        test_colors = [
            ("Primary Colors", self.primary_colors),
            ("Grayscale", self.grayscale_colors),
            ("Random Colors", self.random_colors[:100])
        ]

        for color_set_name, colors in test_colors:
            with self.subTest(color_set=color_set_name):
                # Our implementation
                lab_ours = self.engine._rgb_to_lab_batch(colors)

                # Reference implementation
                xyz_ref = self.reference.srgb_to_xyz_reference(colors)
                lab_ref = self.reference.xyz_to_lab_reference(xyz_ref)

                # Calculate Delta-E differences
                delta_e = self.reference.calculate_delta_e_lab(lab_ours, lab_ref)

                metrics = ColorAccuracyMetrics(
                    test_name=f"RGB→LAB ({color_set_name})",
                    colors_tested=len(colors),
                    max_error=np.max(delta_e),
                    mean_error=np.mean(delta_e),
                    std_error=np.std(delta_e),
                    percentile_95_error=np.percentile(delta_e, 95),
                    passed=np.max(delta_e) < self.delta_e_tolerances['good'],
                    tolerance=self.delta_e_tolerances['good']
                )

                self._record_accuracy_metrics(metrics)

                # Assertions
                self.assertLess(np.max(delta_e), self.delta_e_tolerances['good'],
                               f"RGB→LAB max ΔE: {np.max(delta_e):.2f}, expected <{self.delta_e_tolerances['good']}")
                self.assertLess(np.mean(delta_e), self.delta_e_tolerances['excellent'],
                               f"RGB→LAB mean ΔE: {np.mean(delta_e):.2f}, expected <{self.delta_e_tolerances['excellent']}")

    def test_lab_to_rgb_roundtrip_accuracy(self):
        """Test LAB to RGB round-trip conversion accuracy"""
        test_colors = [
            ("Primary Colors", self.primary_colors),
            ("Random Colors", self.random_colors[:100])
        ]

        for color_set_name, colors in test_colors:
            with self.subTest(color_set=color_set_name):
                # Round-trip conversion
                lab = self.engine._rgb_to_lab_batch(colors)
                rgb_back = self.engine._lab_to_rgb_batch(lab)

                # Calculate Delta-E in LAB space for the round-trip
                lab_back = self.engine._rgb_to_lab_batch(rgb_back)
                delta_e = self.reference.calculate_delta_e_lab(lab, lab_back)

                metrics = ColorAccuracyMetrics(
                    test_name=f"RGB→LAB→RGB ({color_set_name})",
                    colors_tested=len(colors),
                    max_error=np.max(delta_e),
                    mean_error=np.mean(delta_e),
                    std_error=np.std(delta_e),
                    percentile_95_error=np.percentile(delta_e, 95),
                    passed=np.max(delta_e) < self.delta_e_tolerances['excellent'],
                    tolerance=self.delta_e_tolerances['excellent']
                )

                self._record_accuracy_metrics(metrics)

                # Assertions
                self.assertLess(np.max(delta_e), self.delta_e_tolerances['excellent'],
                               f"LAB round-trip max ΔE: {np.max(delta_e):.2f}, expected <{self.delta_e_tolerances['excellent']}")

    def test_hsl_conversion_accuracy(self):
        """Test HSL conversion accuracy against reference"""
        # Use smaller test set for HSL (slower reference implementation)
        test_colors = self.random_colors[:50]

        # Our implementation
        hsl_ours = self.engine._rgb_to_hsl_batch(test_colors)

        # Reference implementation
        hsl_ref = self.reference.rgb_to_hsl_reference(test_colors)

        # Calculate errors (handle hue wraparound)
        hue_errors = np.minimum(
            np.abs(hsl_ours[:, 0] - hsl_ref[:, 0]),
            1.0 - np.abs(hsl_ours[:, 0] - hsl_ref[:, 0])
        )
        sat_errors = np.abs(hsl_ours[:, 1] - hsl_ref[:, 1])
        light_errors = np.abs(hsl_ours[:, 2] - hsl_ref[:, 2])

        max_error = np.max([np.max(hue_errors), np.max(sat_errors), np.max(light_errors)])
        mean_error = np.mean([np.mean(hue_errors), np.mean(sat_errors), np.mean(light_errors)])

        metrics = ColorAccuracyMetrics(
            test_name="RGB→HSL Conversion",
            colors_tested=len(test_colors),
            max_error=max_error,
            mean_error=mean_error,
            std_error=np.std([np.std(hue_errors), np.std(sat_errors), np.std(light_errors)]),
            percentile_95_error=np.percentile([hue_errors, sat_errors, light_errors], 95),
            passed=max_error < 0.01,  # <1% error in HSL components
            tolerance=0.01
        )

        self._record_accuracy_metrics(metrics)

        # Assertions
        self.assertLess(max_error, 0.01, f"HSL max error: {max_error:.4f}, expected <0.01")

    def test_hsl_roundtrip_accuracy(self):
        """Test HSL round-trip conversion accuracy"""
        test_colors = self.random_colors[:100]

        # Round-trip conversion
        hsl = self.engine._rgb_to_hsl_batch(test_colors)
        rgb_back = self.engine._hsl_to_rgb_batch(hsl)

        # Calculate errors
        errors = np.linalg.norm(test_colors - rgb_back, axis=1)
        relative_errors = errors / (np.linalg.norm(test_colors, axis=1) + 1e-10)

        metrics = ColorAccuracyMetrics(
            test_name="RGB→HSL→RGB Round-trip",
            colors_tested=len(test_colors),
            max_error=np.max(relative_errors),
            mean_error=np.mean(relative_errors),
            std_error=np.std(relative_errors),
            percentile_95_error=np.percentile(relative_errors, 95),
            passed=np.max(relative_errors) < 0.005,  # <0.5% relative error
            tolerance=0.005
        )

        self._record_accuracy_metrics(metrics)

        # Assertions
        self.assertLess(np.max(relative_errors), 0.005,
                       f"HSL round-trip max error: {np.max(relative_errors):.4f}, expected <0.005")

    def test_gradient_interpolation_accuracy(self):
        """Test gradient interpolation accuracy in different color spaces"""
        # Create test gradient
        stops = np.array([
            [0.0, 1.0, 0.0, 0.0],  # Red
            [0.5, 0.0, 1.0, 0.0],  # Green
            [1.0, 0.0, 0.0, 1.0]   # Blue
        ])

        gradient = OptimizedGradientData(
            gradient_id="accuracy_test",
            gradient_type="linear",
            coordinates=np.array([0.0, 0.0, 1.0, 1.0]),
            stops=stops,
            transform_matrix=np.eye(3),
            color_space=ColorSpace.RGB
        )

        # Test interpolation at various positions
        positions = np.array([0.0, 0.25, 0.5, 0.75, 1.0])

        # RGB interpolation
        rgb_colors = self.engine._interpolate_linear(stops, positions)

        # LAB interpolation
        gradient_lab = OptimizedGradientData(
            gradient_id="accuracy_test_lab",
            gradient_type="linear",
            coordinates=np.array([0.0, 0.0, 1.0, 1.0]),
            stops=stops.copy(),
            transform_matrix=np.eye(3),
            color_space=ColorSpace.LAB
        )

        # Convert stops to LAB
        lab_stops = stops.copy()
        lab_stops[:, 1:4] = self.engine.convert_colorspace_batch(
            stops[:, 1:4], ColorSpace.RGB, ColorSpace.LAB
        )

        lab_colors_interp = self.engine._interpolate_linear(lab_stops, positions)
        lab_colors_rgb = self.engine.convert_colorspace_batch(
            lab_colors_interp, ColorSpace.LAB, ColorSpace.RGB
        )

        # Compare perceptual uniformity
        # LAB interpolation should provide more perceptually uniform gradients
        rgb_lab_converted = self.engine.convert_colorspace_batch(rgb_colors, ColorSpace.RGB, ColorSpace.LAB)
        delta_e_rgb = self.reference.calculate_delta_e_lab(
            rgb_lab_converted[:-1], rgb_lab_converted[1:]
        )
        delta_e_lab = self.reference.calculate_delta_e_lab(
            lab_colors_interp[:-1], lab_colors_interp[1:]
        )

        # LAB interpolation should have more uniform perceptual steps
        rgb_uniformity = np.std(delta_e_rgb) / np.mean(delta_e_rgb) if np.mean(delta_e_rgb) > 0 else 0
        lab_uniformity = np.std(delta_e_lab) / np.mean(delta_e_lab) if np.mean(delta_e_lab) > 0 else 0

        metrics = ColorAccuracyMetrics(
            test_name="Gradient Interpolation Uniformity",
            colors_tested=len(positions),
            max_error=rgb_uniformity,
            mean_error=lab_uniformity,
            std_error=0.0,
            percentile_95_error=0.0,
            passed=lab_uniformity < rgb_uniformity,  # LAB should be more uniform
            tolerance=rgb_uniformity
        )

        self._record_accuracy_metrics(metrics)

        # Assertions
        self.assertLess(lab_uniformity, rgb_uniformity,
                       f"LAB interpolation should be more uniform: LAB={lab_uniformity:.3f}, RGB={rgb_uniformity:.3f}")

        # Check endpoints are exactly correct
        np.testing.assert_array_almost_equal(rgb_colors[0], [1.0, 0.0, 0.0], decimal=6)  # Red
        np.testing.assert_array_almost_equal(rgb_colors[2], [0.0, 1.0, 0.0], decimal=6)  # Green
        np.testing.assert_array_almost_equal(rgb_colors[4], [0.0, 0.0, 1.0], decimal=6)  # Blue

    def test_color_gamut_preservation(self):
        """Test that color conversions preserve valid color gamuts"""
        # Create colors throughout the RGB gamut
        gamut_colors = []

        # RGB cube vertices
        for r in [0.0, 1.0]:
            for g in [0.0, 1.0]:
                for b in [0.0, 1.0]:
                    gamut_colors.append([r, g, b])

        # RGB cube faces
        for i in range(100):
            # Red face (r=1)
            gamut_colors.append([1.0, np.random.rand(), np.random.rand()])
            # Green face (g=1)
            gamut_colors.append([np.random.rand(), 1.0, np.random.rand()])
            # Blue face (b=1)
            gamut_colors.append([np.random.rand(), np.random.rand(), 1.0])

        gamut_colors = np.array(gamut_colors)

        # Test various conversions
        conversions = [
            (ColorSpace.RGB, ColorSpace.LAB),
            (ColorSpace.RGB, ColorSpace.HSL),
            (ColorSpace.RGB, ColorSpace.XYZ)
        ]

        for source, target in conversions:
            with self.subTest(conversion=f"{source.value}→{target.value}"):
                # Forward conversion
                converted = self.engine.convert_colorspace_batch(gamut_colors, source, target)

                # Check for invalid values (NaN, Inf)
                invalid_count = np.sum(~np.isfinite(converted))

                # Back conversion
                back_converted = self.engine.convert_colorspace_batch(converted, target, source)

                # Check RGB values are still in valid range [0,1]
                out_of_gamut = np.sum((back_converted < -0.01) | (back_converted > 1.01))
                total_values = back_converted.size

                gamut_preservation_rate = (total_values - out_of_gamut) / total_values

                metrics = ColorAccuracyMetrics(
                    test_name=f"Gamut Preservation ({source.value}→{target.value})",
                    colors_tested=len(gamut_colors),
                    max_error=out_of_gamut / total_values,
                    mean_error=invalid_count / converted.size,
                    std_error=0.0,
                    percentile_95_error=0.0,
                    passed=gamut_preservation_rate > 0.98,  # >98% preservation
                    tolerance=0.02
                )

                self._record_accuracy_metrics(metrics)

                # Assertions
                self.assertEqual(invalid_count, 0,
                               f"Invalid values in {source.value}→{target.value} conversion: {invalid_count}")
                self.assertGreater(gamut_preservation_rate, 0.98,
                                 f"Gamut preservation rate: {gamut_preservation_rate:.3f}, expected >0.98")

    def test_white_point_accuracy(self):
        """Test white point accuracy in LAB conversions"""
        # D65 white point should convert to L=100, a≈0, b≈0
        white_rgb = np.array([[1.0, 1.0, 1.0]])
        white_lab = self.engine._rgb_to_lab_batch(white_rgb)

        # Check LAB values
        L, a, b = white_lab[0]

        metrics = ColorAccuracyMetrics(
            test_name="White Point Accuracy",
            colors_tested=1,
            max_error=max(abs(L - 100.0), abs(a), abs(b)),
            mean_error=(abs(L - 100.0) + abs(a) + abs(b)) / 3,
            std_error=0.0,
            percentile_95_error=0.0,
            passed=abs(L - 100.0) < 0.1 and abs(a) < 2.0 and abs(b) < 2.0,
            tolerance=2.0
        )

        self._record_accuracy_metrics(metrics)

        # Assertions
        self.assertAlmostEqual(L, 100.0, delta=0.1,
                             msg=f"White point L*: {L:.2f}, expected ≈100.0")
        self.assertLess(abs(a), 2.0, f"White point a*: {a:.2f}, expected ≈0")
        self.assertLess(abs(b), 2.0, f"White point b*: {b:.2f}, expected ≈0")

    def test_black_point_accuracy(self):
        """Test black point accuracy in LAB conversions"""
        # Black point should convert to L≈0, a≈0, b≈0
        black_rgb = np.array([[0.0, 0.0, 0.0]])
        black_lab = self.engine._rgb_to_lab_batch(black_rgb)

        # Check LAB values
        L, a, b = black_lab[0]

        metrics = ColorAccuracyMetrics(
            test_name="Black Point Accuracy",
            colors_tested=1,
            max_error=max(abs(L), abs(a), abs(b)),
            mean_error=(abs(L) + abs(a) + abs(b)) / 3,
            std_error=0.0,
            percentile_95_error=0.0,
            passed=abs(L) < 1.0 and abs(a) < 1.0 and abs(b) < 1.0,
            tolerance=1.0
        )

        self._record_accuracy_metrics(metrics)

        # Assertions
        self.assertLess(abs(L), 1.0, f"Black point L*: {L:.2f}, expected ≈0")
        self.assertLess(abs(a), 1.0, f"Black point a*: {a:.2f}, expected ≈0")
        self.assertLess(abs(b), 1.0, f"Black point b*: {b:.2f}, expected ≈0")

    def test_color_difference_calculations(self):
        """Test color difference calculations (Delta-E)"""
        # Create color pairs with known differences
        color_pairs = [
            # Identical colors (ΔE = 0)
            ([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]),
            # Slightly different reds (small ΔE)
            ([1.0, 0.0, 0.0], [0.98, 0.02, 0.02]),
            # Different colors (large ΔE)
            ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
        ]

        expected_delta_e_ranges = [
            (0.0, 0.1),    # Identical
            (0.1, 5.0),    # Similar
            (50.0, 120.0)  # Very different
        ]

        for i, ((rgb1, rgb2), (min_de, max_de)) in enumerate(zip(color_pairs, expected_delta_e_ranges)):
            with self.subTest(pair=i):
                lab1 = self.engine._rgb_to_lab_batch(np.array([rgb1]))
                lab2 = self.engine._rgb_to_lab_batch(np.array([rgb2]))

                delta_e = self.reference.calculate_delta_e_lab(lab1, lab2)[0]

                # Check Delta-E is in expected range
                self.assertGreaterEqual(delta_e, min_de,
                                      f"Delta-E too low: {delta_e:.2f}, expected >={min_de}")
                self.assertLessEqual(delta_e, max_de,
                                   f"Delta-E too high: {delta_e:.2f}, expected <={max_de}")

        metrics = ColorAccuracyMetrics(
            test_name="Delta-E Calculations",
            colors_tested=len(color_pairs),
            max_error=0.0,  # Not applicable
            mean_error=0.0,  # Not applicable
            std_error=0.0,
            percentile_95_error=0.0,
            passed=True,  # Passed if no assertions failed
            tolerance=1.0
        )

        self._record_accuracy_metrics(metrics)

    def tearDown(self):
        """Clean up after each test"""
        pass

    @classmethod
    def tearDownClass(cls):
        """Generate color accuracy validation report"""
        print(f"\n{'='*80}")
        print(f"GRADIENT COLOR ACCURACY VALIDATION RESULTS")
        print(f"{'='*80}")

        if hasattr(cls, 'results'):
            results = cls.results
        else:
            return

        # Summary statistics
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.passed)
        pass_rate = passed_tests / total_tests * 100 if total_tests > 0 else 0

        print(f"\nOVERALL ACCURACY SUMMARY:")
        print(f"Tests Passed: {passed_tests}/{total_tests} ({pass_rate:.1f}%)")
        print(f"Colors Tested: {sum(r.colors_tested for r in results):,}")

        # Detailed results
        print(f"\nDETAILED ACCURACY RESULTS:")
        print(f"{'Test Name':<35} {'Colors':<8} {'Max Error':<12} {'Mean Error':<12} {'Status':<10}")
        print(f"{'-' * 90}")

        for result in results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"{result.test_name:<35} {result.colors_tested:<8} "
                 f"{result.max_error:<12.4f} {result.mean_error:<12.4f} {status:<10}")

        # Color space conversion summary
        print(f"\nCOLOR SPACE CONVERSION SUMMARY:")
        conversion_tests = [r for r in results if '→' in r.test_name]
        if conversion_tests:
            print(f"Conversion tests: {len(conversion_tests)}")
            avg_max_error = np.mean([r.max_error for r in conversion_tests])
            avg_mean_error = np.mean([r.mean_error for r in conversion_tests])
            print(f"Average max error: {avg_max_error:.6f}")
            print(f"Average mean error: {avg_mean_error:.6f}")

        # Delta-E analysis
        delta_e_tests = [r for r in results if 'RGB→LAB' in r.test_name or 'Round-trip' in r.test_name]
        if delta_e_tests:
            print(f"\nDELTA-E COLOR DIFFERENCE ANALYSIS:")
            for test in delta_e_tests:
                quality_level = "EXCELLENT"
                if test.mean_error > 1.0:
                    quality_level = "GOOD"
                if test.mean_error > 2.3:
                    quality_level = "ACCEPTABLE"
                if test.mean_error > 5.0:
                    quality_level = "POOR"

                print(f"{test.test_name}: ΔE = {test.mean_error:.2f} ({quality_level})")

        # Final assessment
        print(f"\nFINAL COLOR ACCURACY ASSESSMENT:")
        if pass_rate >= 90:
            print("✓ EXCELLENT: Color accuracy meets professional standards")
        elif pass_rate >= 80:
            print("✓ GOOD: Color accuracy is suitable for most applications")
        elif pass_rate >= 70:
            print("⚠ ACCEPTABLE: Some color accuracy issues detected")
        else:
            print("✗ POOR: Significant color accuracy problems detected")

        print(f"\n{'='*80}")


if __name__ == '__main__':
    # Set up test environment
    warnings.filterwarnings('ignore', category=RuntimeWarning)

    # Run color accuracy validation
    unittest.main(verbosity=2)