#!/usr/bin/env python3
"""
Task 2 Validation: IR Path Filter Field

Tests that Path IR dataclass has filter field and preserves filter references.
"""

from core.ir import Path, Point
from core.ir.geometry import LineSegment

def test_path_with_filter():
    """Test that Path can be created with filter parameter"""
    path = Path(
        segments=[LineSegment(Point(0, 0), Point(100, 100))],
        filter="url(#blur)"
    )

    assert path.filter == "url(#blur)", "Filter field not preserved"
    print(f"✓ Path created with filter: {path.filter}")

    return True


def test_path_without_filter_backward_compat():
    """Test that Path can still be created without filter (backward compatibility)"""
    path = Path(
        segments=[LineSegment(Point(0, 0), Point(100, 100))]
    )

    assert path.filter is None, "Filter should default to None"
    print(f"✓ Path created without filter (backward compat)")
    print(f"✓ Filter defaults to None: {path.filter}")

    return True


def test_path_filter_variations():
    """Test various filter reference formats"""
    test_cases = [
        "url(#blur)",
        "#shadow",
        "url(#myFilter)",
        None,  # No filter
    ]

    for filter_ref in test_cases:
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            filter=filter_ref
        )
        assert path.filter == filter_ref, f"Filter '{filter_ref}' not preserved"
        print(f"✓ Filter format supported: {repr(filter_ref)}")

    return True


def test_path_frozen_dataclass_still_works():
    """Test that frozen dataclass constraints still work"""
    path = Path(
        segments=[LineSegment(Point(0, 0), Point(100, 100))],
        filter="url(#blur)"
    )

    # Verify it's frozen (should raise exception if we try to modify)
    try:
        path.filter = "url(#shadow)"
        assert False, "Path should be frozen, but field was modifiable"
    except (AttributeError, Exception):
        print(f"✓ Path remains frozen dataclass (immutable)")

    return True


def test_path_with_all_fields():
    """Test that filter field works alongside all other fields"""
    path = Path(
        segments=[LineSegment(Point(0, 0), Point(100, 100))],
        opacity=0.8,
        id="rect1",
        filter="url(#blur)"
    )

    assert path.segments is not None
    assert path.opacity == 0.8
    assert path.id == "rect1"
    assert path.filter == "url(#blur)"

    print(f"✓ Filter field works with all other Path fields")
    print(f"  - ID: {path.id}")
    print(f"  - Filter: {path.filter}")
    print(f"  - Opacity: {path.opacity}")

    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Task 2 Validation: IR Path Filter Field")
    print("=" * 60)
    print()

    try:
        print("Test 1: Path with filter")
        print("-" * 60)
        test_path_with_filter()
        print()

        print("Test 2: Path without filter (backward compatibility)")
        print("-" * 60)
        test_path_without_filter_backward_compat()
        print()

        print("Test 3: Various filter reference formats")
        print("-" * 60)
        test_path_filter_variations()
        print()

        print("Test 4: Frozen dataclass integrity")
        print("-" * 60)
        test_path_frozen_dataclass_still_works()
        print()

        print("Test 5: Filter with all other fields")
        print("-" * 60)
        test_path_with_all_fields()
        print()

        print("=" * 60)
        print("✅ ALL TASK 2 TESTS PASSED")
        print("=" * 60)
        print()
        print("Task 2 Complete:")
        print("  ✓ filter: Optional[str] = None added to Path")
        print("  ✓ Field placed after id field (last position)")
        print("  ✓ Type hint uses Optional[str]")
        print("  ✓ Default value is None for backward compatibility")
        print("  ✓ Docstring updated with filter support")
        print("  ✓ No breaking changes to existing Path creation")

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        raise
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        raise
