#!/usr/bin/env python3
"""
Validation script for Policy Engine
Simple validation without pytest dependency
"""

import sys
sys.path.insert(0, '.')

try:
    from core.ir import (
        Path, TextFrame, Point, Rect, LineSegment, Run, TextAnchor, SolidPaint
    )
    from core.policy import create_policy, OutputTarget, DecisionReason

    def test_policy_creation():
        """Test policy creation"""
        policy = create_policy(OutputTarget.BALANCED)
        print("✅ Policy creation successful")
        print(f"   Target: {policy.config.target}")
        print(f"   Max path segments: {policy.config.thresholds.max_path_segments}")
        return True

    def test_simple_path_decision():
        """Test simple path decision"""
        policy = create_policy(OutputTarget.BALANCED)

        path = Path(
            segments=[
                LineSegment(Point(0, 0), Point(100, 0)),
                LineSegment(Point(100, 0), Point(100, 100)),
                LineSegment(Point(100, 100), Point(0, 100)),
                LineSegment(Point(0, 100), Point(0, 0))
            ],
            fill=SolidPaint("FF0000"),
            opacity=1.0
        )

        decision = policy.decide_path(path)
        print("✅ Simple path decision successful")
        print(f"   Use native: {decision.use_native}")
        print(f"   Confidence: {decision.confidence}")
        print(f"   Explanation: {decision.explain()}")

        assert decision.use_native is True, "Simple path should use native DrawingML"
        return True

    def test_simple_text_decision():
        """Test simple text decision"""
        policy = create_policy(OutputTarget.BALANCED)

        text = TextFrame(
            origin=Point(10, 20),
            runs=[Run(text="Hello World", font_family="Arial", font_size_pt=12.0)],
            anchor=TextAnchor.START,
            bbox=Rect(10, 20, 100, 20)
        )

        decision = policy.decide_text(text)
        print("✅ Simple text decision successful")
        print(f"   Use native: {decision.use_native}")
        print(f"   Run count: {decision.run_count}")
        print(f"   Explanation: {decision.explain()}")

        assert decision.use_native is True, "Simple text should use native DrawingML"
        return True

    def test_complex_path_decision():
        """Test complex path decision (many segments)"""
        policy = create_policy(OutputTarget.BALANCED)

        # Create path with many segments (above threshold)
        segments = []
        for i in range(1200):  # Above default threshold of 1000
            segments.append(LineSegment(Point(i, 0), Point(i+1, 1)))

        path = Path(segments=segments, fill=SolidPaint("FF0000"))
        decision = policy.decide_path(path)

        print("✅ Complex path decision successful")
        print(f"   Use native: {decision.use_native}")
        print(f"   Segment count: {decision.segment_count}")
        print(f"   Explanation: {decision.explain()}")

        assert decision.use_native is False, "Complex path should use EMF fallback"
        assert DecisionReason.ABOVE_THRESHOLDS in decision.reasons
        return True

    def test_policy_metrics():
        """Test policy metrics collection"""
        policy = create_policy(OutputTarget.BALANCED)

        # Make some decisions
        simple_path = Path(
            segments=[LineSegment(Point(0, 0), Point(10, 10))],
            fill=SolidPaint("FF0000")
        )
        policy.decide_path(simple_path)

        simple_text = TextFrame(
            origin=Point(10, 20),
            runs=[Run(text="Test", font_family="Arial", font_size_pt=12.0)],
            anchor=TextAnchor.START,
            bbox=Rect(10, 20, 50, 20)
        )
        policy.decide_text(simple_text)

        metrics = policy.get_metrics()
        print("✅ Policy metrics collection successful")
        print(f"   Total decisions: {metrics.total_decisions}")
        print(f"   Native percentage: {metrics.native_percentage:.1f}%")
        print(f"   Path decisions: {metrics.path_decisions}")
        print(f"   Text decisions: {metrics.text_decisions}")

        assert metrics.total_decisions == 2, "Should have 2 total decisions"
        assert metrics.native_decisions == 2, "Both should be native decisions"
        return True

    def test_output_targets():
        """Test different output targets"""
        speed_policy = create_policy(OutputTarget.SPEED)
        quality_policy = create_policy(OutputTarget.QUALITY)

        print("✅ Output target configuration successful")
        print(f"   Speed max segments: {speed_policy.config.thresholds.max_path_segments}")
        print(f"   Quality max segments: {quality_policy.config.thresholds.max_path_segments}")

        assert speed_policy.config.thresholds.max_path_segments < quality_policy.config.thresholds.max_path_segments
        return True

    def run_all_tests():
        """Run all validation tests"""
        tests = [
            test_policy_creation,
            test_simple_path_decision,
            test_simple_text_decision,
            test_complex_path_decision,
            test_policy_metrics,
            test_output_targets
        ]

        print("🚀 Policy Engine Validation Starting...\n")

        passed = 0
        failed = 0

        for test in tests:
            try:
                test()
                passed += 1
                print()
            except Exception as e:
                print(f"❌ {test.__name__} failed: {e}\n")
                failed += 1

        print(f"📊 Results: {passed} passed, {failed} failed")

        if failed == 0:
            print("🎉 All policy engine tests passed!")
            return True
        else:
            print("💥 Some tests failed!")
            return False

    if __name__ == "__main__":
        success = run_all_tests()
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all core modules are available")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)