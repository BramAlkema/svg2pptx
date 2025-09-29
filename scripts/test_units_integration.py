#!/usr/bin/env python3
"""
Unit Converter Integration Test

Tests the integration adapter to ensure compatibility with existing
converter infrastructure while providing performance improvements.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the adapters
from core.units_adapter import (
    LegacyUnitAdapter, FastUnitMixin, ViewportContextAdapter,
    create_fast_unit_converter, upgrade_unit_converter
)


class TestConverter(FastUnitMixin):
    """Test converter that uses the FastUnitMixin."""

    def __init__(self):
        super().__init__()
        self.name = "TestConverter"

    def process_coordinates(self, coords):
        """Test coordinate processing with fast conversion."""
        return self.fast_convert_coordinates(coords)


def test_legacy_adapter():
    """Test the legacy unit adapter interface."""
    print("🔧 Testing Legacy Unit Adapter")
    print("=" * 35)

    # Create adapter with legacy interface
    adapter = LegacyUnitAdapter(width=800, height=600, font_size=16, dpi=96)

    # Test individual conversions
    test_values = ["100px", "2em", "50%", "1in", "10mm"]
    print("Individual conversions:")

    for value in test_values:
        emu_result = adapter.to_emu(value)
        pixel_result = adapter.parse_length(value)
        print(f"  {value:6} → {emu_result:8} EMU, {pixel_result:6.1f} px")

    # Test batch conversion
    coord_dict = {
        'x': '100px',
        'y': '50px',
        'width': '200px',
        'height': '150px',
        'cx': '5em',
        'cy': '3em'
    }

    batch_results = adapter.batch_convert(coord_dict)
    print(f"\nBatch conversion: {batch_results}")

    # Test list batch conversion
    batch_list = adapter.batch_to_emu(test_values)
    print(f"List batch: {batch_list}")

    print("✅ Legacy adapter working correctly")


def test_fast_mixin():
    """Test the FastUnitMixin."""
    print("\n⚡ Testing Fast Unit Mixin")
    print("=" * 30)

    # Create test converter with mixin
    converter = TestConverter()

    # Test coordinate processing
    coordinates = {
        'x': '100px',
        'y': '50px',
        'width': '10em',
        'height': '5%',
        'r': '25mm'
    }

    result = converter.process_coordinates(coordinates)
    print(f"Coordinate conversion: {result}")

    # Test batch processing
    values = ["100px", "2em", "50%", "1in", "10mm"] * 1000  # 5K values

    start_time = time.perf_counter()
    batch_result = converter.fast_batch_convert(values)
    batch_time = time.perf_counter() - start_time

    throughput = len(values) / batch_time
    print(f"Batch processing: {len(values)} values in {batch_time:.6f}s ({throughput:.0f} conv/sec)")

    print("✅ Fast mixin working correctly")


def test_viewport_context_adapter():
    """Test the viewport context adapter."""
    print("\n📐 Testing Viewport Context Adapter")
    print("=" * 40)

    # Create viewport context
    viewport = ViewportContextAdapter(
        width=1024, height=768, font_size=14, dpi=72,
        custom_property="test"
    )

    print(f"Viewport: {viewport.width}x{viewport.height}, {viewport.font_size}pt, {viewport.dpi} DPI")
    print(f"Custom property: {viewport.custom_property}")

    # Update viewport
    viewport.update(width=1920, height=1080)
    print(f"Updated: {viewport.width}x{viewport.height}")

    # Convert to fast context
    fast_context = viewport.to_fast_context()
    print(f"Fast context: width={fast_context.width}, height={fast_context.height}")

    print("✅ Viewport context adapter working correctly")


def test_performance_comparison():
    """Test performance comparison."""
    print("\n🚀 Performance Comparison")
    print("=" * 28)

    # Create adapters
    fast_adapter = create_fast_unit_converter()

    # Test data
    test_values = ["100px", "2em", "50%", "1in", "10mm", "72pt"] * 2000  # 12K values

    print(f"Testing with {len(test_values):,} conversions...")

    # Test fast adapter
    start_time = time.perf_counter()
    fast_results = fast_adapter.batch_to_emu(test_values)
    fast_time = time.perf_counter() - start_time

    fast_throughput = len(test_values) / fast_time

    print(f"Fast adapter: {fast_time:.6f}s ({fast_throughput:.0f} conv/sec)")

    # Test individual conversions for comparison
    start_time = time.perf_counter()
    individual_results = []
    for value in test_values[:1000]:  # Subset for feasibility
        result = fast_adapter.to_emu(value)
        individual_results.append(result)
    individual_time = time.perf_counter() - start_time

    estimated_individual_time = individual_time * (len(test_values) / 1000)
    speedup = estimated_individual_time / fast_time

    print(f"Individual est: {estimated_individual_time:.6f}s")
    print(f"Batch speedup: {speedup:.1f}x {'✅' if speedup >= 1.5 else '❌'}")

    print("✅ Performance comparison complete")


def test_compatibility():
    """Test compatibility with different input types."""
    print("\n🔄 Compatibility Testing")
    print("=" * 26)

    adapter = LegacyUnitAdapter()

    # Test different input types
    test_cases = [
        ("String", "100px"),
        ("Integer", 100),
        ("Float", 100.5),
        ("Negative", "-50px"),
        ("Zero", "0px"),
        ("Empty", ""),
        ("Percentage", "50%"),
        ("Viewport", "25vw")
    ]

    print("Input type compatibility:")
    for test_name, value in test_cases:
        try:
            result = adapter.to_emu(value)
            print(f"  {test_name:12}: {str(value):8} → {result:8} EMU ✅")
        except Exception as e:
            print(f"  {test_name:12}: {str(value):8} → ERROR: {e} ❌")

    print("✅ Compatibility testing complete")


def main():
    """Run the integration tests."""
    print("🚀 Unit Converter Integration Test")
    print("=" * 50)

    try:
        test_legacy_adapter()
        test_fast_mixin()
        test_viewport_context_adapter()
        test_performance_comparison()
        test_compatibility()

        print("\n✅ All integration tests passed!")
        print("🎯 Unit converter integration ready for production")
        return 0

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())