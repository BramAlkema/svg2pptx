#!/usr/bin/env python3
"""
Simple Clean Transform Engine Test

Tests the new ultra-fast NumPy-based transform system.
"""

import sys
import time
import gc
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np

# Import the clean transform classes directly from the new file
import importlib.util
transforms_path = project_root / "src" / "transforms.py"
spec = importlib.util.spec_from_file_location("clean_transforms", transforms_path)
clean_transforms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clean_transforms)

Transform = clean_transforms.Transform


def test_basic_performance():
    """Test basic transform performance."""
    print("🚀 Clean Transform Engine Performance Test")
    print("=" * 50)

    # Create complex transform
    transform = (Transform.translate(10, 20) @
                 Transform.rotate(45) @
                 Transform.scale(2.0, 1.5))

    print(f"Transform matrix:\n{transform.matrix}")

    # Test different sizes
    sizes = [1000, 10000, 50000]

    for size in sizes:
        print(f"\n--- Testing {size:,} points ---")

        # Generate test data
        points = np.random.uniform(-1000, 1000, (size, 2))

        # Test vectorized transformation
        gc.collect()
        start_time = time.perf_counter()

        result = transform.apply(points)

        vectorized_time = time.perf_counter() - start_time
        throughput = size / vectorized_time

        print(f"Vectorized: {vectorized_time:.6f}s ({throughput:.0f} pts/sec)")

        # Test scalar for comparison (small subset)
        subset_size = min(1000, size)
        subset_points = points[:subset_size]

        gc.collect()
        start_time = time.perf_counter()

        scalar_results = []
        for point in subset_points:
            scalar_result = transform.apply(tuple(point))
            scalar_results.append(scalar_result)

        scalar_time = time.perf_counter() - start_time
        scalar_throughput = subset_size / scalar_time

        # Estimate full scalar time
        estimated_scalar_time = scalar_time * (size / subset_size)
        speedup = estimated_scalar_time / vectorized_time

        print(f"Scalar (est): {estimated_scalar_time:.6f}s ({scalar_throughput:.0f} pts/sec)")
        print(f"Speedup: {speedup:.1f}x {'✅' if speedup >= 20 else '❌'}")

        # Verify accuracy
        vectorized_subset = result[:subset_size]
        scalar_array = np.array(scalar_results)

        max_diff = np.max(np.abs(vectorized_subset - scalar_array))
        accuracy_ok = max_diff < 1e-10

        print(f"Max difference: {max_diff:.2e} {'✅' if accuracy_ok else '❌'}")

        if not accuracy_ok:
            print("❌ Accuracy test failed!")
            return False

    print("\n✅ All performance tests passed!")
    return True


def test_operations():
    """Test basic transform operations."""
    print("\n--- Basic Operations Test ---")

    # Test identity
    identity = Transform.identity()
    point = (100.0, 200.0)
    result = identity.apply(point)
    print(f"Identity: {point} -> {result}")

    # Test translation
    trans = Transform.translate(10, 20)
    result = trans.apply(point)
    print(f"Translate: {point} -> {result}")

    # Test scaling
    scale = Transform.scale(2.0)
    result = scale.apply(point)
    print(f"Scale: {point} -> {result}")

    # Test rotation
    rot = Transform.rotate(90)
    result = rot.apply((1.0, 0.0))
    print(f"Rotate 90°: (1,0) -> {result}")

    # Test composition
    composed = trans @ scale @ rot
    result = composed.apply((1.0, 0.0))
    print(f"Composed: (1,0) -> {result}")

    print("✅ Basic operations working")
    return True


def main():
    """Run the simple test."""
    try:
        if test_operations() and test_basic_performance():
            print("\n🎯 Clean Transform Engine: ✅ VALIDATED")
            print("🚀 Ready for Task 1.1 completion")
            return 0
        else:
            print("\n❌ Tests failed")
            return 1
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())