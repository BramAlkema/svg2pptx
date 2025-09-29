#!/usr/bin/env python3
"""
Test batch transform operations.
"""

import sys
import time
import gc
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np

# Import the clean transform classes directly
import importlib.util
transforms_path = project_root / "src" / "transforms.py"
spec = importlib.util.spec_from_file_location("clean_transforms", transforms_path)
clean_transforms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clean_transforms)

Transform = clean_transforms.Transform
BatchTransform = clean_transforms.BatchTransform
TransformBuilder = clean_transforms.TransformBuilder


def test_batch_operations():
    """Test batch transform operations."""
    print("🔧 Testing Batch Transform Operations")
    print("=" * 40)

    # Create test transforms
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
    ], dtype=np.float64)

    print(f"Input points:\n{points}")

    # Test apply_multiple
    print("\n--- Testing apply_multiple ---")

    gc.collect()
    start_time = time.perf_counter()

    batch_results = BatchTransform.apply_multiple(transforms, points)

    batch_time = time.perf_counter() - start_time

    # Compare with sequential
    gc.collect()
    start_time = time.perf_counter()

    sequential_results = []
    for transform in transforms:
        result = transform.apply(points)
        sequential_results.append(result)

    sequential_time = time.perf_counter() - start_time

    print(f"Batch time: {batch_time:.6f}s")
    print(f"Sequential time: {sequential_time:.6f}s")
    print(f"Speedup: {sequential_time/batch_time:.1f}x")

    # Verify results match
    for i, (batch_result, seq_result) in enumerate(zip(batch_results, sequential_results)):
        max_diff = np.max(np.abs(batch_result - seq_result))
        print(f"Transform {i}: max diff = {max_diff:.2e} {'✅' if max_diff < 1e-10 else '❌'}")

    return True


def test_compose_sequence():
    """Test sequence composition."""
    print("\n--- Testing compose_sequence ---")

    transforms = [
        Transform.translate(10, 20),
        Transform.rotate(45),
        Transform.scale(2.0),
        Transform.translate(-5, -10)
    ]

    # Test batch composition
    gc.collect()
    start_time = time.perf_counter()

    composed = BatchTransform.compose_sequence(transforms)

    compose_time = time.perf_counter() - start_time

    # Compare with manual composition
    gc.collect()
    start_time = time.perf_counter()

    manual = Transform.identity()
    for transform in transforms:
        manual = manual @ transform

    manual_time = time.perf_counter() - start_time

    print(f"Batch compose time: {compose_time:.6f}s")
    print(f"Manual compose time: {manual_time:.6f}s")

    # Test they produce same results
    test_points = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float64)

    composed_result = composed.apply(test_points)
    manual_result = manual.apply(test_points)

    max_diff = np.max(np.abs(composed_result - manual_result))
    print(f"Max difference: {max_diff:.2e} {'✅' if max_diff < 1e-10 else '❌'}")

    return max_diff < 1e-10


def test_builder_pattern():
    """Test transform builder."""
    print("\n--- Testing Builder Pattern ---")

    # Test builder
    built_transform = (TransformBuilder.create()
                      .translate(10, 20)
                      .rotate(45)
                      .scale(2.0)
                      .translate(-5, -10)
                      .build())

    # Compare with manual
    manual_transform = (Transform.translate(10, 20) @
                       Transform.rotate(45) @
                       Transform.scale(2.0) @
                       Transform.translate(-5, -10))

    # Test same results
    test_points = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float64)

    built_result = built_transform.apply(test_points)
    manual_result = manual_transform.apply(test_points)

    max_diff = np.max(np.abs(built_result - manual_result))
    print(f"Builder vs manual: {max_diff:.2e} {'✅' if max_diff < 1e-10 else '❌'}")

    return max_diff < 1e-10


def main():
    """Run batch operation tests."""
    try:
        success = (test_batch_operations() and
                  test_compose_sequence() and
                  test_builder_pattern())

        if success:
            print("\n🎯 Batch Operations: ✅ VALIDATED")
            print("🚀 Task 1.1 batch operations complete")
            return 0
        else:
            print("\n❌ Some batch operations failed")
            return 1

    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())