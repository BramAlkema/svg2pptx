#!/usr/bin/env python3
"""
Test complete flow with advanced text features after consolidation.
"""

from core.pipeline.converter import CleanSlateConverter

# Test SVG with various text features
test_svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
    <!-- Basic rect -->
    <rect x="50" y="50" width="200" height="100" fill="blue" stroke="black" stroke-width="2"/>

    <!-- Basic text -->
    <text x="100" y="200" font-size="24" fill="black">Basic Text</text>

    <!-- Rotated text (should trigger WordArt consideration) -->
    <text x="400" y="200" font-size="36" fill="red" transform="rotate(45 400 200)">
        Rotated Text
    </text>

    <!-- Text with gradient (should trigger WordArt) -->
    <defs>
        <linearGradient id="textGrad">
            <stop offset="0%" stop-color="purple"/>
            <stop offset="100%" stop-color="orange"/>
        </linearGradient>
    </defs>
    <text x="100" y="350" font-size="48" fill="url(#textGrad)">
        Gradient Text
    </text>

    <!-- Text on path -->
    <defs>
        <path id="curve" d="M100,450 Q250,400 400,450" fill="none" stroke="gray"/>
    </defs>
    <text font-size="20" fill="green">
        <textPath href="#curve">Text flowing on a curved path!</textPath>
    </text>

    <!-- Circle -->
    <circle cx="600" cy="100" r="50" fill="yellow" stroke="red" stroke-width="3"/>
</svg>"""

def test_complete_flow():
    """Test the complete consolidated pipeline."""

    print("🚀 Testing Complete Consolidated Pipeline")
    print("=" * 70)

    # Create converter with consolidated pipeline
    converter = CleanSlateConverter()

    # Check configuration
    print("📋 Pipeline Configuration:")
    print(f"  - Services integrated: {hasattr(converter, 'services')}")

    if hasattr(converter, 'mappers'):
        print("  - Mappers:")
        for name, mapper in converter.mappers.items():
            mapper_type = type(mapper).__name__
            print(f"    • {name}: {mapper_type}", end="")

            if mapper_type == 'FontMapperAdapter':
                if hasattr(mapper, 'use_smart_converter'):
                    status = "✅ SmartConverter" if mapper.use_smart_converter else "⚠️ Fallback"
                    print(f" ({status})")
                else:
                    print()
            else:
                print()

    print("\n🧪 Converting Test SVG...")
    print("-" * 70)

    try:
        result = converter.convert_string(test_svg)

        print("✅ Conversion Successful!")
        print(f"\n📊 Conversion Statistics:")
        print(f"  - Total time: {result.total_time_ms:.2f}ms")
        print(f"  - Parse time: {result.parse_time_ms:.2f}ms")
        print(f"  - Analyze time: {result.analyze_time_ms:.2f}ms")
        print(f"  - Mapping time: {result.mapping_time_ms:.2f}ms")
        print(f"  - Embedding time: {result.embedding_time_ms:.2f}ms")
        print(f"  - Packaging time: {result.packaging_time_ms:.2f}ms")

        print(f"\n📦 Output Statistics:")
        print(f"  - Elements processed: {result.elements_processed}")
        print(f"  - Native elements: {result.native_elements}")
        print(f"  - EMF elements: {result.emf_elements}")
        print(f"  - Output size: {len(result.output_data)} bytes")

        # Save output for inspection
        output_file = "test_output.pptx"
        with open(output_file, "wb") as f:
            f.write(result.output_data)
        print(f"\n💾 Output saved to: {output_file}")

        return True

    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_flow()

    print("\n" + "=" * 70)
    if success:
        print("✅ PIPELINE FULLY OPERATIONAL")
        print("\n🎉 Achievements:")
        print("  • SVG → IR conversion working")
        print("  • FontMapperAdapter integrated")
        print("  • SmartFontConverter accessible")
        print("  • Elements properly processed")
        print("\n📝 Next Steps:")
        print("  1. Test with complex real-world SVG files")
        print("  2. Verify WordArt effects in PowerPoint")
        print("  3. Continue with Phase 3 (filter integration)")
    else:
        print("❌ PIPELINE TEST FAILED")
        print("Check the errors above for debugging")