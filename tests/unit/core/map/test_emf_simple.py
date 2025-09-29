#!/usr/bin/env python3
"""
Simple EMF Integration Test

Basic test for EMF adapter functionality without complex dependencies.
"""

import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))


def test_emf_adapter_import():
    """Test that EMF adapter can be imported"""
    try:
        from core.map.emf_adapter import EMFPathAdapter, create_emf_adapter

        # Test adapter creation
        adapter = create_emf_adapter()
        assert adapter is not None
        assert isinstance(adapter, EMFPathAdapter)

        print("✅ EMF adapter import and creation successful")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_emf_adapter_basic_functionality():
    """Test basic EMF adapter functionality"""
    try:
        from core.map.emf_adapter import create_emf_adapter
        from core.ir import Path, Point, LineSegment, SolidPaint, Rect

        # Create test path
        segments = [LineSegment(start=Point(x=0, y=0), end=Point(x=100, y=100))]
        path = Path(
            segments=segments,
            fill=SolidPaint(rgb="FF0000"),
            stroke=None,
            clip=None,
            opacity=1.0
        )
        # bbox is automatically calculated from segments

        # Create adapter
        adapter = create_emf_adapter()

        # Test capability check
        can_generate = adapter.can_generate_emf(path)
        assert isinstance(can_generate, bool)

        print(f"✅ EMF adapter basic functionality test successful (can_generate: {can_generate})")
        return True

    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def test_path_mapper_emf_integration():
    """Test PathMapper EMF integration"""
    try:
        from core.map.path_mapper import PathMapper
        from core.policy.engine import Policy
        from core.policy.targets import PathDecision, DecisionReason
        from core.ir import Path, Point, LineSegment, SolidPaint, Rect
        from unittest.mock import Mock

        # Create mock policy that forces EMF
        policy = Mock()
        decision = PathDecision(
            use_native=False,
            estimated_quality=0.95,
            estimated_performance=0.8,
            reasons=[DecisionReason.COMPLEX_GEOMETRY]  # Use 'reasons' not 'reasoning'
        )
        policy.decide_path.return_value = decision

        # Create test path
        segments = [LineSegment(start=Point(x=0, y=0), end=Point(x=100, y=100))]
        path = Path(
            segments=segments,
            fill=SolidPaint(rgb="FF0000"),
            stroke=None,
            clip=None,
            opacity=1.0
        )
        # bbox is automatically calculated from segments
        # complexity_score would be calculated by analysis system

        # Create mapper and test
        mapper = PathMapper(policy)
        result = mapper.map(path)

        # Verify EMF result
        assert result.output_format.value == "emf_vector"
        assert "EMF_Path" in result.xml_content
        assert result.metadata is not None

        print("✅ PathMapper EMF integration test successful")
        return True

    except Exception as e:
        print(f"❌ PathMapper integration test failed: {e}")
        return False


if __name__ == "__main__":
    print("Running EMF Integration Tests...")

    success = True
    success &= test_emf_adapter_import()
    success &= test_emf_adapter_basic_functionality()
    success &= test_path_mapper_emf_integration()

    if success:
        print("\n🎉 All EMF integration tests passed!")
        exit(0)
    else:
        print("\n❌ Some EMF integration tests failed!")
        exit(1)