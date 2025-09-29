#!/usr/bin/env python3
"""
Test script for the enhanced pipeline error reporting system.
"""

import sys
sys.path.insert(0, '.')

from core.pipeline.converter import CleanSlateConverter
from core.pipeline.config import PipelineConfig

def test_error_reporting():
    """Test the error reporting functionality"""
    print("🧪 Testing Enhanced Pipeline Error Reporting...")

    # Create converter
    config = PipelineConfig(enable_debug=True)
    converter = CleanSlateConverter(config)

    print("✅ Converter initialized with error reporting")

    # Test 1: Invalid SVG (should trigger parsing error)
    print("\n📝 Test 1: Invalid SVG parsing...")
    try:
        invalid_svg = "<not-valid-xml>"
        result = converter.convert_string(invalid_svg)
    except Exception as e:
        print(f"✅ Expected error caught: {e}")

    # Check error reports
    error_summary = converter.get_error_summary()
    print(f"\n📊 Error Summary:")
    print(f"   Total errors: {error_summary['total_errors']}")
    print(f"   Error counts by category: {error_summary['error_counts_by_category']}")
    print(f"   Has errors: {converter.has_errors()}")

    if converter.has_errors():
        recent_errors = converter.get_recent_errors(limit=3)
        print(f"\n🔍 Recent Errors ({len(recent_errors)}):")
        for i, error in enumerate(recent_errors, 1):
            print(f"   {i}. [{error['severity']}] {error['category']}: {error['message']}")
            if error['recovery_suggestions']:
                print(f"      Suggestions: {error['recovery_suggestions'][:2]}")

    # Test 2: Empty SVG (should process successfully but with minimal elements)
    print("\n📝 Test 2: Empty but valid SVG...")
    try:
        empty_svg = '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        result = converter.convert_string(empty_svg)
        print(f"✅ Empty SVG processed successfully")
        print(f"   Elements processed: {result.elements_processed}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    # Final error summary
    final_summary = converter.get_error_summary()
    print(f"\n📈 Final Error Summary:")
    print(f"   Session duration: {final_summary['session_duration_ms']:.2f}ms")
    print(f"   Total errors: {final_summary['total_errors']}")
    print(f"   Error patterns detected: {len(final_summary.get('error_patterns', []))}")

    print("\n✅ Error reporting test completed!")

if __name__ == "__main__":
    test_error_reporting()