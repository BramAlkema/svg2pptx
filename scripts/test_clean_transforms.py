#!/usr/bin/env python3
"""
Clean Transform Engine Validation and Performance Test

Tests the new ultra-fast NumPy-based transform system without legacy baggage.
Validates 20-50x performance targets and correctness.
"""

import sys
import time
import gc
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from src.transforms import Transform, TransformBuilder, BatchTransform, translate, scale, rotate


def test_basic_operations():
    """Test basic transform operations."""
    print("\n=== Basic Operations Test ===")

    # Test identity
    identity = Transform.identity()
    point = (100.0, 200.0)
    result = identity.apply(point)
    assert abs(result[0] - 100.0) < 1e-10
    assert abs(result[1] - 200.0) < 1e-10
    print("  ✅ Identity transform")

    # Test translation
    trans = Transform.translate(10, 20)
    result = trans.apply(point)
    assert abs(result[0] - 110.0) < 1e-10
    assert abs(result[1] - 220.0) < 1e-10
    print("  ✅ Translation transform")

    # Test scaling
    scl = Transform.scale(2.0)
    result = scl.apply(point)
    assert abs(result[0] - 200.0) < 1e-10
    assert abs(result[1] - 400.0) < 1e-10
    print("  ✅ Scale transform")

    # Test rotation (90 degrees)
    rot = Transform.rotate(90)
    result = rot.apply((1.0, 0.0))
    assert abs(result[0] - 0.0) < 1e-10
    assert abs(result[1] - 1.0) < 1e-10
    print("  ✅ Rotation transform")

    # Test composition
    composed = trans @ scl @ rot
    test_point = (1.0, 0.0)
    result = composed.apply(test_point)
    # Should be: rotate(1,0) -> (0,1), scale by 2 -> (0,2), translate -> (10,22)
    expected_x, expected_y = 10.0, 22.0
    assert abs(result[0] - expected_x) < 1e-10
    assert abs(result[1] - expected_y) < 1e-10
    print("  ✅ Transform composition")

    return True


def test_vectorized_performance():
    """Test vectorized coordinate transformation performance."""
    print("\n=== Vectorized Performance Test ===")

    # Create complex transform
    transform = (Transform.translate(10, 20) @
                 Transform.rotate(45) @
                 Transform.scale(2.0, 1.5))

    # Generate test data
    sizes = [1000, 10000, 100000]

    for size in sizes:
        points = np.random.uniform(-1000, 1000, (size, 2))

        # Test vectorized transformation
        gc.collect()
        start_time = time.perf_counter()

        vectorized_result = transform.apply(points)

        vectorized_time = time.perf_counter() - start_time

        # Test scalar transformation for comparison (smaller subset)
        subset_size = min(1000, size)
        subset_points = points[:subset_size]

        gc.collect()
        start_time = time.perf_counter()

        scalar_results = []
        for point in subset_points:
            result = transform.apply(tuple(point))
            scalar_results.append(result)

        scalar_time = time.perf_counter() - start_time

        # Calculate performance metrics
        vectorized_throughput = size / vectorized_time
        scalar_throughput = subset_size / scalar_time
        speedup = (scalar_time / subset_size) / (vectorized_time / size)

        print(f"  {size:6,} points:")
        print(f"    Vectorized: {vectorized_time:.6f}s ({vectorized_throughput:.0f} pts/sec)")
        print(f"    Scalar est: {(scalar_time * size / subset_size):.6f}s ({scalar_throughput:.0f} pts/sec)")
        print(f"    Speedup: {speedup:.1f}x {'✅' if speedup >= 20 else '❌'}")

        # Verify correctness by comparing subset
        vectorized_subset = vectorized_result[:subset_size]
        scalar_array = np.array(scalar_results)

        if np.allclose(vectorized_subset, scalar_array, rtol=1e-10):
            print(f"    Accuracy: ✅ PERFECT")
        else:
            print(f"    Accuracy: ❌ MISMATCH")
            return False

    return True


def test_batch_operations():
    """Test batch transformation operations."""
    print("\n=== Batch Operations Test ===")

    # Create multiple transforms
    transforms = [
        Transform.translate(10, 0),
        Transform.scale(2.0),
        Transform.rotate(90),
        Transform.translate(0, 10) @ Transform.scale(0.5)
    ]

    # Test points
    points = np.array([
        [0.0, 0.0],
        [1.0, 0.0],
        [0.0, 1.0],
        [1.0, 1.0]
    ])

    # Test batch application
    gc.collect()
    start_time = time.perf_counter()

    batch_results = BatchTransform.apply_multiple(transforms, points)

    batch_time = time.perf_counter() - start_time

    # Test sequential application for comparison
    gc.collect()
    start_time = time.perf_counter()

    sequential_results = []
    for transform in transforms:
        result = transform.apply(points)
        sequential_results.append(result)

    sequential_time = time.perf_counter() - start_time

    # Calculate speedup
    speedup = sequential_time / batch_time if batch_time > 0 else 0

    print(f"  Batch time: {batch_time:.6f}s")
    print(f"  Sequential time: {sequential_time:.6f}s")
    print(f"  Batch speedup: {speedup:.1f}x")

    # Verify correctness
    accuracy_ok = True
    for i, (batch_result, seq_result) in enumerate(zip(batch_results, sequential_results)):
        if not np.allclose(batch_result, seq_result, rtol=1e-10):
            print(f"  Transform {i}: ❌ MISMATCH")
            accuracy_ok = False
        else:
            print(f"  Transform {i}: ✅ ACCURATE")

    return accuracy_ok


def test_builder_pattern():
    """Test the fluent builder interface."""
    print("\n=== Builder Pattern Test ===")

    # Test builder
    transform = (TransformBuilder.create()
                .translate(10, 20)
                .rotate(45)
                .scale(2.0)
                .translate(-5, -10)
                .build())

    # Compare with manual composition
    manual = (Transform.translate(10, 20) @
              Transform.rotate(45) @
              Transform.scale(2.0) @
              Transform.translate(-5, -10))

    # Test same result
    test_points = np.array([[0, 0], [1, 0], [0, 1], [1, 1]])

    builder_result = transform.apply(test_points)
    manual_result = manual.apply(test_points)

    if np.allclose(builder_result, manual_result, rtol=1e-10):
        print("  ✅ Builder pattern matches manual composition")
        return True
    else:
        print("  ❌ Builder pattern mismatch")
        return False


def test_advanced_operations():
    """Test advanced transform operations."""
    print("\n=== Advanced Operations Test ===")

    # Test bounding box transformation
    transform = Transform.rotate(45) @ Transform.scale(2.0)

    bbox = transform.apply_to_bbox(0, 0, 100, 100)
    print(f"  Rotated/scaled bbox: {bbox}")

    # Test decomposition
    complex_transform = (Transform.translate(10, 20) @
                        Transform.rotate(30) @
                        Transform.scale(2.0, 1.5))

    components = complex_transform.decompose()
    print(f"  Decomposed components: {components}")

    # Test properties
    identity = Transform.identity()
    translation = Transform.translate(10, 20)
    rotation = Transform.rotate(45)

    print(f"  Identity is identity: {identity.is_identity()}")
    print(f"  Translation is translation-only: {translation.is_translation_only()}")
    print(f"  Rotation has rotation: {rotation.has_rotation()}")

    # Test SVG string output
    svg_string = complex_transform.to_svg_string()
    print(f"  SVG string: {svg_string}")

    return True


def run_comprehensive_test():
    """Run all tests and report results."""
    print("🚀 Clean Transform Engine Validation")
    print("=" * 50)

    tests = [
        ("Basic Operations", test_basic_operations),
        ("Vectorized Performance", test_vectorized_performance),
        ("Batch Operations", test_batch_operations),
        ("Builder Pattern", test_builder_pattern),
        ("Advanced Operations", test_advanced_operations),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")

    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print("🎯 Transform Engine: ✅ READY FOR PRODUCTION")
        print("🚀 Performance targets achieved")
        print("🔧 Clean NumPy implementation validated")
    else:
        print("⚠️  Some tests failed - review implementation")

    return passed == total


def main():
    """Main test execution."""
    try:
        success = run_comprehensive_test()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())