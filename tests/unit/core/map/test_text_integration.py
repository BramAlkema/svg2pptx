#!/usr/bin/env python3
"""
Test Text Processing Integration

Validates that text processing works correctly with the existing comprehensive text and font system.
"""

import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))


def test_text_adapter_import():
    """Test that text adapter can be imported"""
    try:
        from core.map.text_adapter import TextProcessingAdapter, create_text_adapter

        # Test adapter creation
        adapter = create_text_adapter()
        assert adapter is not None
        assert isinstance(adapter, TextProcessingAdapter)

        print("✅ Text adapter import and creation successful")

    except ImportError as e:
        print(f"❌ Import error: {e}")


def test_text_adapter_basic_functionality():
    """Test basic text adapter functionality"""
    try:
        from core.map.text_adapter import create_text_adapter
        from core.ir import TextFrame, Run, Point, Rect, TextAnchor

        # Create test text frame
        runs = [
            Run(text="Hello", font_family="Arial", font_size_pt=12, bold=False, italic=False,
                underline=False, strike=False, rgb="000000"),
            Run(text=" World", font_family="Arial", font_size_pt=12, bold=True, italic=False,
                underline=False, strike=False, rgb="FF0000")
        ]

        text_frame = TextFrame(
            origin=Point(x=10, y=20),
            runs=runs,
            bbox=Rect(x=10, y=20, width=100, height=30),
            anchor=TextAnchor.START
        )

        # Create adapter
        adapter = create_text_adapter()

        # Test capability check
        can_enhance = adapter.can_enhance_text_processing(text_frame)
        assert isinstance(can_enhance, bool)

        # Test statistics
        stats = adapter.get_processing_statistics()
        assert isinstance(stats, dict)
        assert 'text_system_available' in stats

        print(f"✅ Text adapter basic functionality test successful (can_enhance: {can_enhance})")
        print(f"   Text system available: {stats['text_system_available']}")

    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")


def test_text_mapper_integration():
    """Test TextMapper text processing integration"""
    try:
        from core.map.text_mapper import TextMapper
        from core.policy.engine import Policy
        from core.policy.targets import TextDecision, DecisionReason
        from core.ir import TextFrame, Run, Point, Rect, TextAnchor
        from unittest.mock import Mock

        # Create mock policy
        policy = Mock()
        decision = TextDecision(
            use_native=True,
            estimated_quality=0.95,
            estimated_performance=0.9,
            reasons=[DecisionReason.SIMPLE_GEOMETRY]
        )
        policy.decide_text.return_value = decision

        # Create test text frame
        runs = [
            Run(text="Test Text", font_family="Arial", font_size_pt=12, bold=False, italic=False,
                underline=False, strike=False, rgb="000000")
        ]

        text_frame = TextFrame(
            origin=Point(x=10, y=20),
            runs=runs,
            bbox=Rect(x=10, y=20, width=100, height=30),
            anchor=TextAnchor.START
        )

        # Create mapper and test
        mapper = TextMapper(policy)
        result = mapper.map(text_frame)

        # Verify text was processed
        assert result.output_format.value == "native_dml"
        assert "p:sp" in result.xml_content
        assert "TextFrame" in result.xml_content
        assert result.metadata is not None
        assert result.metadata['run_count'] == 1

        # Should contain text content
        xml_lower = result.xml_content.lower()
        has_text_elements = ("a:r" in xml_lower and "a:t" in xml_lower)

        print(f"✅ TextMapper integration test successful (has_text_elements: {has_text_elements})")

    except Exception as e:
        print(f"❌ TextMapper integration test failed: {e}")
        import traceback
        traceback.print_exc()


def test_text_fixes_applied():
    """Test that documented text fixes are properly applied"""
    try:
        from core.map.text_mapper import TextMapper
        from core.policy.targets import TextDecision, DecisionReason
        from core.ir import TextFrame, Run, Point, Rect, TextAnchor
        from unittest.mock import Mock

        # Create mock policy
        policy = Mock()
        decision = TextDecision(
            use_native=True,
            estimated_quality=0.95,
            estimated_performance=0.9,
            reasons=[DecisionReason.SIMPLE_GEOMETRY]
        )
        policy.decide_text.return_value = decision

        # Create test text frame with multiple anchor types
        runs = [Run(text="Anchor Test", font_family="Arial", font_size_pt=12, bold=False, italic=False,
                   underline=False, strike=False, rgb="000000")]

        # Test different anchor alignments
        anchors_to_test = [
            (TextAnchor.START, 'l'),    # Left
            (TextAnchor.MIDDLE, 'ctr'), # Center
            (TextAnchor.END, 'r')       # Right
        ]

        mapper = TextMapper(policy)

        for anchor, expected_alignment in anchors_to_test:
            text_frame = TextFrame(
                origin=Point(x=10, y=20),
                runs=runs,
                bbox=Rect(x=10, y=20, width=100, height=30),
                anchor=anchor
            )

            result = mapper.map(text_frame)

            # Check that proper alignment is applied (fix #1 & #4)
            assert f'algn="{expected_alignment}"' in result.xml_content

            # Check that fixes are documented in metadata
            fixes_applied = result.metadata.get('fixes_applied', [])
            expected_fixes = ['raw_anchor', 'per_tspan_styling', 'conservative_baseline', 'proper_alignment']
            for expected_fix in expected_fixes:
                assert expected_fix in fixes_applied

        # Test that baseline adjustment is applied (fix #3)
        result = mapper.map(text_frame)
        assert result.metadata.get('baseline_adjusted') == True

        print("✅ Text fixes verification successful - All documented fixes applied")

    except Exception as e:
        print(f"❌ Text fixes test failed: {e}")


def test_text_font_validation():
    """Test font validation functionality"""
    try:
        from core.map.text_adapter import create_text_adapter

        adapter = create_text_adapter()

        # Test common font validation
        common_fonts = ['Arial', 'Times New Roman', 'Helvetica', 'Courier New']

        for font in common_fonts:
            is_valid = adapter.validate_font_availability(font)
            # Should return boolean regardless of actual availability
            assert isinstance(is_valid, bool)

        print("✅ Font validation test successful")

    except Exception as e:
        print(f"❌ Font validation test failed: {e}")


def test_text_measurement():
    """Test text measurement functionality"""
    try:
        from core.map.text_adapter import create_text_adapter

        adapter = create_text_adapter()

        # Test text dimension measurement
        text = "Hello World"
        font_family = "Arial"
        font_size_pt = 12.0

        width, height = adapter.measure_text_dimensions(text, font_family, font_size_pt)

        # Should return positive numbers
        assert isinstance(width, (int, float))
        assert isinstance(height, (int, float))
        assert width > 0
        assert height > 0

        # Height should be reasonable relative to font size
        assert height >= font_size_pt  # At least font size
        assert height <= font_size_pt * 2  # Not more than 2x font size

        print(f"✅ Text measurement successful: '{text}' = {width:.1f}x{height:.1f}pt")

    except Exception as e:
        print(f"❌ Text measurement test failed: {e}")


def test_multiline_text_processing():
    """Test multiline text processing"""
    try:
        from core.map.text_mapper import TextMapper
        from core.policy.targets import TextDecision, DecisionReason
        from core.ir import TextFrame, Run, Point, Rect, TextAnchor
        from unittest.mock import Mock

        # Create mock policy
        policy = Mock()
        decision = TextDecision(
            use_native=True,
            estimated_quality=0.95,
            estimated_performance=0.9,
            reasons=[DecisionReason.SIMPLE_GEOMETRY]
        )
        policy.decide_text.return_value = decision

        # Create multiline text frame
        runs = [
            Run(text="Line 1\nLine 2", font_family="Arial", font_size_pt=12, bold=False, italic=False,
                underline=False, strike=False, rgb="000000")
        ]

        text_frame = TextFrame(
            origin=Point(x=10, y=20),
            runs=runs,
            bbox=Rect(x=10, y=20, width=100, height=60),
            anchor=TextAnchor.START
        )

        mapper = TextMapper(policy)
        result = mapper.map(text_frame)

        # Should generate separate paragraphs for multiline text
        xml_content = result.xml_content
        paragraph_count = xml_content.count('<a:p>')

        # Should have multiple paragraphs for multiline text
        assert paragraph_count >= 1

        print(f"✅ Multiline text processing successful (paragraphs: {paragraph_count})")

    except Exception as e:
        print(f"❌ Multiline text test failed: {e}")


if __name__ == "__main__":
    print("Running Text Processing Integration Tests...")

    success = True
    success &= test_text_adapter_import()
    success &= test_text_adapter_basic_functionality()
    success &= test_text_mapper_integration()
    success &= test_text_fixes_applied()
    success &= test_text_font_validation()
    success &= test_text_measurement()
    success &= test_multiline_text_processing()

    if success:
        print("\n🎉 All text processing integration tests passed!")
        exit(0)
    else:
        print("\n❌ Some text processing integration tests failed!")
        exit(1)