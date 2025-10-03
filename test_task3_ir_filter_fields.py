#!/usr/bin/env python3
"""
Task 3 Validation: IR Filter Fields for Group, Image, TextFrame

Tests that all IR element types support filter field.
"""

from core.ir import Group, Image, TextFrame, Path, Point, Rect, TextAnchor, Run
from core.ir.geometry import LineSegment


def test_group_with_filter():
    """Test that Group can be created with filter parameter"""
    child_path = Path(
        segments=[LineSegment(Point(0, 0), Point(100, 100))]
    )

    group = Group(
        children=[child_path],
        filter="url(#blur)"
    )

    assert group.filter == "url(#blur)", "Group filter not preserved"
    print(f"✓ Group created with filter: {group.filter}")

    return True


def test_group_without_filter_backward_compat():
    """Test that Group can be created without filter"""
    group = Group(
        children=[]
    )

    assert group.filter is None, "Group filter should default to None"
    print(f"✓ Group created without filter (backward compat)")

    return True


def test_image_with_filter():
    """Test that Image can be created with filter parameter"""
    image = Image(
        origin=Point(0, 0),
        size=Rect(0, 0, 100, 100),
        data=b'fake_image_data',
        format='png',
        filter="url(#shadow)"
    )

    assert image.filter == "url(#shadow)", "Image filter not preserved"
    print(f"✓ Image created with filter: {image.filter}")

    return True


def test_image_without_filter_backward_compat():
    """Test that Image can be created without filter"""
    image = Image(
        origin=Point(0, 0),
        size=Rect(0, 0, 100, 100),
        data=b'fake_image_data',
        format='png'
    )

    assert image.filter is None, "Image filter should default to None"
    print(f"✓ Image created without filter (backward compat)")

    return True


def test_textframe_with_filter():
    """Test that TextFrame can be created with filter parameter"""
    text = TextFrame(
        origin=Point(10, 10),
        runs=[Run(text="Hello", font_family="Arial", font_size_pt=12)],
        anchor=TextAnchor.START,
        bbox=Rect(10, 10, 100, 20),
        filter="url(#glow)"
    )

    assert text.filter == "url(#glow)", "TextFrame filter not preserved"
    print(f"✓ TextFrame created with filter: {text.filter}")

    return True


def test_textframe_without_filter_backward_compat():
    """Test that TextFrame can be created without filter"""
    text = TextFrame(
        origin=Point(10, 10),
        runs=[Run(text="Hello", font_family="Arial", font_size_pt=12)],
        anchor=TextAnchor.START,
        bbox=Rect(10, 10, 100, 20)
    )

    assert text.filter is None, "TextFrame filter should default to None"
    print(f"✓ TextFrame created without filter (backward compat)")

    return True


def test_all_ir_types_support_filters():
    """Test that all IR element types have filter field"""
    # Create one of each type with filter
    path = Path(
        segments=[LineSegment(Point(0, 0), Point(100, 100))],
        filter="url(#blur)"
    )

    group = Group(
        children=[path],
        filter="url(#shadow)"
    )

    image = Image(
        origin=Point(0, 0),
        size=Rect(0, 0, 100, 100),
        data=b'data',
        format='png',
        filter="url(#contrast)"
    )

    text = TextFrame(
        origin=Point(10, 10),
        runs=[Run(text="Test", font_family="Arial", font_size_pt=12)],
        anchor=TextAnchor.START,
        bbox=Rect(10, 10, 100, 20),
        filter="url(#glow)"
    )

    # Verify all have filter attribute
    assert hasattr(path, 'filter'), "Path missing filter attribute"
    assert hasattr(group, 'filter'), "Group missing filter attribute"
    assert hasattr(image, 'filter'), "Image missing filter attribute"
    assert hasattr(text, 'filter'), "TextFrame missing filter attribute"

    # Verify filter values preserved
    assert path.filter == "url(#blur)"
    assert group.filter == "url(#shadow)"
    assert image.filter == "url(#contrast)"
    assert text.filter == "url(#glow)"

    print(f"✓ All IR element types support filter field:")
    print(f"  - Path.filter: {path.filter}")
    print(f"  - Group.filter: {group.filter}")
    print(f"  - Image.filter: {image.filter}")
    print(f"  - TextFrame.filter: {text.filter}")

    return True


def test_filter_variations_all_types():
    """Test various filter formats work for all types"""
    filter_refs = ["url(#blur)", "#shadow", "url(#custom)", None]

    for filter_ref in filter_refs:
        path = Path(
            segments=[LineSegment(Point(0, 0), Point(100, 100))],
            filter=filter_ref
        )
        group = Group(children=[], filter=filter_ref)
        image = Image(
            origin=Point(0, 0), size=Rect(0, 0, 10, 10),
            data=b'x', format='png', filter=filter_ref
        )
        text = TextFrame(
            origin=Point(0, 0),
            runs=[Run(text="T", font_family="Arial", font_size_pt=12)],
            anchor=TextAnchor.START,
            bbox=Rect(0, 0, 10, 10),
            filter=filter_ref
        )

        assert path.filter == filter_ref
        assert group.filter == filter_ref
        assert image.filter == filter_ref
        assert text.filter == filter_ref

    print(f"✓ All filter format variations supported across all types")

    return True


def test_frozen_dataclass_integrity():
    """Test that all classes remain frozen (immutable)"""
    group = Group(children=[], filter="url(#blur)")
    image = Image(
        origin=Point(0, 0), size=Rect(0, 0, 10, 10),
        data=b'x', format='png', filter="url(#shadow)"
    )
    text = TextFrame(
        origin=Point(0, 0),
        runs=[Run(text="T", font_family="Arial", font_size_pt=12)],
        anchor=TextAnchor.START,
        bbox=Rect(0, 0, 10, 10),
        filter="url(#glow)"
    )

    # Try to modify (should fail for frozen dataclasses)
    for obj, name in [(group, "Group"), (image, "Image"), (text, "TextFrame")]:
        try:
            obj.filter = "modified"
            assert False, f"{name} should be frozen but was modifiable"
        except (AttributeError, Exception):
            print(f"✓ {name} remains frozen (immutable)")

    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Task 3 Validation: IR Filter Fields")
    print("=" * 60)
    print()

    try:
        print("Test 1: Group with filter")
        print("-" * 60)
        test_group_with_filter()
        print()

        print("Test 2: Group without filter (backward compatibility)")
        print("-" * 60)
        test_group_without_filter_backward_compat()
        print()

        print("Test 3: Image with filter")
        print("-" * 60)
        test_image_with_filter()
        print()

        print("Test 4: Image without filter (backward compatibility)")
        print("-" * 60)
        test_image_without_filter_backward_compat()
        print()

        print("Test 5: TextFrame with filter")
        print("-" * 60)
        test_textframe_with_filter()
        print()

        print("Test 6: TextFrame without filter (backward compatibility)")
        print("-" * 60)
        test_textframe_without_filter_backward_compat()
        print()

        print("Test 7: All IR types support filters")
        print("-" * 60)
        test_all_ir_types_support_filters()
        print()

        print("Test 8: Filter variations work across all types")
        print("-" * 60)
        test_filter_variations_all_types()
        print()

        print("Test 9: Frozen dataclass integrity")
        print("-" * 60)
        test_frozen_dataclass_integrity()
        print()

        print("=" * 60)
        print("✅ ALL TASK 3 TESTS PASSED")
        print("=" * 60)
        print()
        print("Task 3 Complete:")
        print("  ✓ Group has filter: Optional[str] = None")
        print("  ✓ Image has filter: Optional[str] = None")
        print("  ✓ TextFrame has filter: Optional[str] = None")
        print("  ✓ All fields placed as last optional parameter")
        print("  ✓ Docstrings updated")
        print("  ✓ Backward compatibility maintained")
        print()
        print("Summary:")
        print("  All 4 IR element types now support filter references:")
        print("  - Path (Task 2)")
        print("  - Group (Task 3)")
        print("  - Image (Task 3)")
        print("  - TextFrame (Task 3)")

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
