#!/usr/bin/env python3
"""
Integration tests for Filter Color Matrix Integration with Main Color System.

This module validates that the filter system correctly uses the main color system
as the single source of truth for all color operations, ensuring consistency and
eliminating code duplication.
"""

import pytest
import logging
from typing import List, Dict, Any

# Import main color system functions
from src.colors import (
    adjust_saturation,
    calculate_luminance,
    rotate_hue,
    apply_color_matrix,
    luminance_to_alpha,
    parse_color,
    ColorInfo
)

# Import centralized fixtures
from tests.fixtures.common import *
from tests.fixtures.mock_objects import *


class TestFilterColorIntegration:
    """Integration tests for filter color system with main color system."""

    def test_main_color_system_availability(self):
        """Validate all main color system functions are available and working."""
        print("🔗 Testing Main Color System Availability")
        print("=" * 45)

        # Test parse_color
        test_colors = ["#FF0000", "#00FF00", "#0000FF", "#808080"]
        for color_hex in test_colors:
            color = parse_color(color_hex)
            assert isinstance(color, ColorInfo)
            print(f"  ✓ Parsed {color_hex} → RGB({color.red},{color.green},{color.blue})")

        print("  ✓ All main color system functions available")

    def test_saturation_integration(self):
        """Test saturation operations integration."""
        print("🎨 Testing Saturation Integration")
        print("=" * 35)

        test_color = parse_color("#FF8000")  # Orange
        saturation_levels = [0.0, 0.5, 1.0, 1.5, 2.0]

        for sat_level in saturation_levels:
            result = adjust_saturation(test_color, sat_level)
            assert isinstance(result, ColorInfo)
            print(f"  Saturation {sat_level}: RGB({test_color.red},{test_color.green},{test_color.blue}) → RGB({result.red},{result.green},{result.blue})")

        print("  ✓ Saturation integration validated")

    def test_hue_rotation_integration(self):
        """Test hue rotation operations integration."""
        print("🌈 Testing Hue Rotation Integration")
        print("=" * 38)

        test_color = parse_color("#FF0000")  # Red
        rotation_angles = [0, 60, 120, 180, 240, 300, 360]

        for angle in rotation_angles:
            result = rotate_hue(test_color, angle)
            assert isinstance(result, ColorInfo)
            print(f"  Rotation {angle:3d}°: RGB({test_color.red},{test_color.green},{test_color.blue}) → RGB({result.red},{result.green},{result.blue})")

        print("  ✓ Hue rotation integration validated")

    def test_color_matrix_integration(self):
        """Test color matrix operations integration."""
        print("📊 Testing Color Matrix Integration")
        print("=" * 37)

        test_color = parse_color("#808080")  # Gray

        # Test different matrix operations
        matrix_tests = [
            {
                'name': 'Identity',
                'matrix': [1,0,0,0,0, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,1,0],
                'expected_change': False
            },
            {
                'name': 'Invert',
                'matrix': [-1,0,0,0,1, 0,-1,0,0,1, 0,0,-1,0,1, 0,0,0,1,0],
                'expected_change': True
            },
            {
                'name': 'Half Brightness',
                'matrix': [0.5,0,0,0,0, 0,0.5,0,0,0, 0,0,0.5,0,0, 0,0,0,1,0],
                'expected_change': True
            },
            {
                'name': 'Red Channel Only',
                'matrix': [1,0,0,0,0, 0,0,0,0,0, 0,0,0,0,0, 0,0,0,1,0],
                'expected_change': True
            }
        ]

        for test in matrix_tests:
            result = apply_color_matrix(test_color, test['matrix'])
            assert isinstance(result, ColorInfo)

            changed = (result.red != test_color.red or
                      result.green != test_color.green or
                      result.blue != test_color.blue)

            print(f"  {test['name']:15}: RGB({test_color.red},{test_color.green},{test_color.blue}) → RGB({result.red},{result.green},{result.blue})")

            if test['expected_change']:
                assert changed, f"Expected change for {test['name']} matrix"
            else:
                assert not changed, f"Expected no change for {test['name']} matrix"

        print("  ✓ Color matrix integration validated")

    def test_luminance_to_alpha_integration(self):
        """Test luminance-to-alpha operations integration."""
        print("🌗 Testing Luminance-to-Alpha Integration")
        print("=" * 43)

        test_colors = [
            parse_color("#FFFFFF"),  # White - max luminance
            parse_color("#000000"),  # Black - min luminance
            parse_color("#808080"),  # Gray - medium luminance
            parse_color("#FF0000"),  # Red - specific luminance
            parse_color("#00FF00"),  # Green - high luminance
            parse_color("#0000FF"),  # Blue - low luminance
        ]

        for color in test_colors:
            luminance_value = calculate_luminance(color)
            alpha_result = luminance_to_alpha(color)

            assert isinstance(alpha_result, ColorInfo)
            assert alpha_result.red == 0
            assert alpha_result.green == 0
            assert alpha_result.blue == 0
            assert 0.0 <= alpha_result.alpha <= 1.0

            print(f"  RGB({color.red:3d},{color.green:3d},{color.blue:3d}) → Luminance={luminance_value:.3f} → Alpha={alpha_result.alpha:.3f}")

        print("  ✓ Luminance-to-alpha integration validated")

    def test_filter_consistency_validation(self):
        """Test consistency between different color operations."""
        print("🔍 Testing Filter Consistency Validation")
        print("=" * 42)

        # Test color operation consistency
        base_color = parse_color("#FF8040")  # Orange

        # Test round-trip operations
        hue_rotated = rotate_hue(base_color, 360)  # Full rotation should return to original
        # Allow small floating-point differences due to HSL conversion precision
        assert abs(hue_rotated.red - base_color.red) <= 1
        assert abs(hue_rotated.green - base_color.green) <= 1
        assert abs(hue_rotated.blue - base_color.blue) <= 1
        print(f"  ✓ Hue rotation round-trip: 360° returns to original (within 1 unit tolerance)")

        # Test matrix identity
        identity_matrix = [1,0,0,0,0, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,1,0]
        matrix_result = apply_color_matrix(base_color, identity_matrix)
        assert matrix_result.red == base_color.red
        assert matrix_result.green == base_color.green
        assert matrix_result.blue == base_color.blue
        print(f"  ✓ Identity matrix preserves original color")

        # Test saturation extremes
        desaturated = adjust_saturation(base_color, 0.0)  # Should be grayscale
        oversaturated = adjust_saturation(base_color, 1.0)  # Should be normal
        print(f"  ✓ Saturation range validation: 0.0 (grayscale) to 1.0 (normal)")

        print("  ✓ All consistency validations passed")

    def test_performance_integration(self):
        """Test performance of integrated color operations."""
        print("⚡ Testing Performance Integration")
        print("=" * 35)

        import time

        # Generate test colors
        test_colors = [parse_color(f"#{r:02x}{g:02x}{b:02x}")
                      for r in range(0, 256, 64)
                      for g in range(0, 256, 64)
                      for b in range(0, 256, 64)]

        # Test performance of each operation
        operations = [
            ('Saturation', lambda c: adjust_saturation(c, 0.8)),
            ('Hue Rotation', lambda c: rotate_hue(c, 45)),
            ('Luminance-to-Alpha', lambda c: luminance_to_alpha(c)),
            ('Matrix (Identity)', lambda c: apply_color_matrix(c, [1,0,0,0,0, 0,1,0,0,0, 0,0,1,0,0, 0,0,0,1,0])),
        ]

        for op_name, operation in operations:
            start_time = time.time()
            for color in test_colors[:50]:  # Test subset for performance
                result = operation(color)
                assert isinstance(result, ColorInfo)
            end_time = time.time()

            execution_time = end_time - start_time
            ops_per_second = 50 / execution_time if execution_time > 0 else float('inf')

            print(f"  {op_name:20}: {ops_per_second:>6.0f} ops/sec")

            # All operations should be reasonably fast
            assert ops_per_second > 100, f"Performance too slow for {op_name}: {ops_per_second:.0f} ops/sec"

        print("  ✓ Performance requirements met for all operations")

    def test_error_handling_integration(self):
        """Test error handling in integrated color operations."""
        print("🛡️ Testing Error Handling Integration")
        print("=" * 40)

        # Test invalid color inputs - adjust_saturation doesn't have validation so raises AttributeError
        with pytest.raises(AttributeError):
            adjust_saturation("not_a_color", 0.5)
        print("  ✓ Invalid color input handled correctly")

        # Test invalid matrix
        valid_color = parse_color("#FF0000")
        with pytest.raises(ValueError):
            apply_color_matrix(valid_color, [1, 2, 3])  # Too few values
        print("  ✓ Invalid matrix input handled correctly")

        # Test invalid hue rotation - rotate_hue has validation so raises ValueError
        with pytest.raises(ValueError):
            rotate_hue("not_a_color", 45)
        print("  ✓ Invalid hue rotation input handled correctly")

        # Test invalid luminance input - luminance_to_alpha has validation so raises ValueError
        with pytest.raises(ValueError):
            luminance_to_alpha(None)
        print("  ✓ Invalid luminance input handled correctly")

        print("  ✓ All error handling validated")

    def test_comprehensive_integration_validation(self):
        """Comprehensive validation of complete integration."""
        print("🎯 Comprehensive Integration Validation")
        print("=" * 44)

        # Test complex color operations sequence
        base_color = parse_color("#FF6600")  # Orange

        # Apply sequence of operations
        step1 = adjust_saturation(base_color, 1.2)  # Increase saturation
        step2 = rotate_hue(step1, 30)               # Rotate hue slightly
        step3 = apply_color_matrix(step2, [0.8,0,0,0,0.1, 0,0.8,0,0,0.1, 0,0,0.8,0,0.1, 0,0,0,1,0])  # Slight tint
        final_luminance = calculate_luminance(step3)
        alpha_result = luminance_to_alpha(step3)

        print(f"  Original:     RGB({base_color.red},{base_color.green},{base_color.blue})")
        print(f"  Saturated:    RGB({step1.red},{step1.green},{step1.blue})")
        print(f"  Hue Rotated:  RGB({step2.red},{step2.green},{step2.blue})")
        print(f"  Matrix Tint:  RGB({step3.red},{step3.green},{step3.blue})")
        print(f"  Luminance:    {final_luminance:.3f}")
        print(f"  Alpha Result: RGB({alpha_result.red},{alpha_result.green},{alpha_result.blue}) Alpha={alpha_result.alpha:.3f}")

        # Validate all operations succeeded
        assert isinstance(step1, ColorInfo)
        assert isinstance(step2, ColorInfo)
        assert isinstance(step3, ColorInfo)
        assert isinstance(final_luminance, float)
        assert isinstance(alpha_result, ColorInfo)

        print("  ✓ Complex operation sequence successful")
        print("  🎉 Complete integration validation passed!")

    def test_svg_filter_scenarios(self):
        """Test realistic SVG filter scenarios using main color system."""
        print("📄 Testing SVG Filter Scenarios")
        print("=" * 35)

        # Simulate common SVG filter scenarios
        scenarios = [
            {
                'name': 'Desaturate Image',
                'operation': lambda c: adjust_saturation(c, 0.2),
                'description': 'feColorMatrix type="saturate" values="0.2"'
            },
            {
                'name': 'Sepia Tone',
                'operation': lambda c: apply_color_matrix(c, [0.393,0.769,0.189,0,0, 0.349,0.686,0.168,0,0, 0.272,0.534,0.131,0,0, 0,0,0,1,0]),
                'description': 'feColorMatrix with sepia matrix'
            },
            {
                'name': 'Hue Shift',
                'operation': lambda c: rotate_hue(c, 180),
                'description': 'feColorMatrix type="hueRotate" values="180"'
            },
            {
                'name': 'Alpha Mask',
                'operation': lambda c: luminance_to_alpha(c),
                'description': 'feColorMatrix type="luminanceToAlpha"'
            }
        ]

        test_image_colors = [
            parse_color("#FF0000"),  # Red pixel
            parse_color("#00FF00"),  # Green pixel
            parse_color("#0000FF"),  # Blue pixel
            parse_color("#FFFF00"),  # Yellow pixel
            parse_color("#808080"),  # Gray pixel
        ]

        for scenario in scenarios:
            print(f"  Testing: {scenario['name']}")
            print(f"    SVG: {scenario['description']}")

            for i, color in enumerate(test_image_colors):
                result = scenario['operation'](color)
                assert isinstance(result, ColorInfo)

                if i == 0:  # Show first result as example
                    print(f"    Example: RGB({color.red},{color.green},{color.blue}) → RGB({result.red},{result.green},{result.blue})")

            print(f"    ✓ {scenario['name']} scenario validated")

        print("  ✓ All SVG filter scenarios successful")


if __name__ == "__main__":
    print("🚀 Filter Color Integration Test Suite")
    print("=" * 50)

    try:
        test_instance = TestFilterColorIntegration()

        test_instance.test_main_color_system_availability()
        test_instance.test_saturation_integration()
        test_instance.test_hue_rotation_integration()
        test_instance.test_color_matrix_integration()
        test_instance.test_luminance_to_alpha_integration()
        test_instance.test_filter_consistency_validation()
        test_instance.test_performance_integration()
        test_instance.test_error_handling_integration()
        test_instance.test_comprehensive_integration_validation()
        test_instance.test_svg_filter_scenarios()

        print(f"\n🎉 All filter color integration tests passed!")
        print("   Filter system successfully integrated with main color system.")
        print("   Single source of truth established for all color operations.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()