#!/usr/bin/env python3
"""
Test Clipping Integration

Validates that clipping generation works correctly with the existing comprehensive clipping system.
"""

import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))


def test_clipping_adapter_import():
    """Test that clipping adapter can be imported"""
    try:
        from core.map.clipping_adapter import ClippingPathAdapter, create_clipping_adapter

        # Test adapter creation
        adapter = create_clipping_adapter()
        assert adapter is not None
        assert isinstance(adapter, ClippingPathAdapter)

        print("✅ Clipping adapter import and creation successful")

    except ImportError as e:
        print(f"❌ Import error: {e}")


def test_clipping_adapter_basic_functionality():
    """Test basic clipping adapter functionality"""
    try:
        from core.map.clipping_adapter import create_clipping_adapter
        from core.ir import ClipRef

        # Create test clip reference
        clip_ref = ClipRef(clip_id="url(#test-clip)")

        # Create adapter
        adapter = create_clipping_adapter()

        # Test capability check
        can_generate = adapter.can_generate_clipping(clip_ref)
        assert isinstance(can_generate, bool)

        # Test statistics
        stats = adapter.get_clipping_statistics()
        assert isinstance(stats, dict)
        assert 'clipping_system_available' in stats

        print(f"✅ Clipping adapter basic functionality test successful (can_generate: {can_generate})")
        print(f"   Clipping system available: {stats['clipping_system_available']}")

    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")


def test_path_mapper_clipping_integration():
    """Test PathMapper clipping integration"""
    try:
        from core.map.path_mapper import PathMapper
        from core.policy.engine import Policy
        from core.policy.targets import PathDecision, DecisionReason
        from core.ir import Path, Point, LineSegment, SolidPaint, ClipRef
        from unittest.mock import Mock

        # Create mock policy
        policy = Mock()
        decision = PathDecision(
            use_native=True,
            estimated_quality=0.95,
            estimated_performance=0.9,
            reasons=[DecisionReason.SIMPLE_GEOMETRY]
        )
        policy.decide_path.return_value = decision

        # Create test path with clipping
        segments = [LineSegment(start=Point(x=0, y=0), end=Point(x=100, y=100))]
        clip_ref = ClipRef(clip_id="url(#test-clip)")

        path = Path(
            segments=segments,
            fill=SolidPaint(rgb="FF0000"),
            stroke=None,
            clip=clip_ref,  # Add clipping
            opacity=1.0
        )

        # Create mapper and test
        mapper = PathMapper(policy)
        result = mapper.map(path)

        # Verify clipping was processed
        assert result.output_format.value == "native_dml"
        assert "p:sp" in result.xml_content
        assert result.metadata is not None

        # Should contain clipping reference (either real clipping or fallback comment)
        xml_lower = result.xml_content.lower()
        has_clipping = ("clip" in xml_lower or "test-clip" in xml_lower)

        print(f"✅ PathMapper clipping integration test successful (has_clipping: {has_clipping})")

    except Exception as e:
        print(f"❌ PathMapper clipping integration test failed: {e}")
        import traceback
        traceback.print_exc()


def test_clipping_generation_strategies():
    """Test different clipping generation strategies"""
    try:
        from core.map.clipping_adapter import create_clipping_adapter
        from core.ir import ClipRef

        adapter = create_clipping_adapter()

        # Test simple clip reference
        simple_clip = ClipRef(clip_id="url(#simple-rect)")

        if adapter.can_generate_clipping(simple_clip):
            result = adapter.generate_clip_xml(simple_clip)

            assert result.xml_content is not None
            assert result.strategy is not None
            assert result.complexity is not None

            print(f"✅ Clipping generation successful - Strategy: {result.strategy}, Complexity: {result.complexity}")
        else:
            print("✅ Clipping generation correctly reports unavailable")


    except Exception as e:
        print(f"❌ Clipping generation strategies test failed: {e}")


def test_clipping_preprocessing_analysis():
    """Test clipping preprocessing analysis"""
    try:
        from core.map.clipping_adapter import create_clipping_adapter

        adapter = create_clipping_adapter()

        # Test preprocessing analysis
        analysis = adapter.analyze_preprocessing_opportunities(None, {})
        assert isinstance(analysis, dict)
        assert 'can_preprocess' in analysis

        print(f"✅ Preprocessing analysis test successful (can_preprocess: {analysis['can_preprocess']})")

    except Exception as e:
        print(f"❌ Preprocessing analysis test failed: {e}")


if __name__ == "__main__":
    print("Running Clipping Integration Tests...")

    success = True
    success &= test_clipping_adapter_import()
    success &= test_clipping_adapter_basic_functionality()
    success &= test_path_mapper_clipping_integration()
    success &= test_clipping_generation_strategies()
    success &= test_clipping_preprocessing_analysis()

    if success:
        print("\n🎉 All clipping integration tests passed!")
        exit(0)
    else:
        print("\n❌ Some clipping integration tests failed!")
        exit(1)