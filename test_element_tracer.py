#!/usr/bin/env python3
"""
Test the Element Flow Tracer with filtered SVG elements.

This demonstrates tracing elements through the entire pipeline to verify
they follow the correct flow: Parse → Analyze → IR → Map → Embed → Package
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.debug import enable_tracing, get_tracer
from core.pipeline.converter import CleanSlateConverter

# Complex SVG with multiple filters
test_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600">
  <defs>
    <!-- Filter definitions -->
    <filter id="blur" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="5"/>
    </filter>

    <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur"/>
      <feOffset in="blur" dx="4" dy="4" result="offsetBlur"/>
      <feBlend in="SourceGraphic" in2="offsetBlur" mode="normal"/>
    </filter>

    <filter id="colorMatrix" x="0%" y="0%" width="100%" height="100%">
      <feColorMatrix type="saturate" values="0.3"/>
    </filter>

    <!-- Gradient for testing -->
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
      <stop offset="100%" style="stop-color:rgb(0,0,255);stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Test elements with filters -->
  <rect id="rect1" x="50" y="50" width="200" height="100" fill="red" filter="url(#blur)"/>

  <circle id="circle1" cx="400" cy="100" r="60" fill="green" filter="url(#shadow)"/>

  <ellipse id="ellipse1" cx="600" cy="100" rx="80" ry="50" fill="blue" filter="url(#colorMatrix)"/>

  <!-- Elements without filters for comparison -->
  <rect id="rect2" x="50" y="200" width="200" height="100" fill="yellow"/>

  <path id="path1" d="M 400,200 L 500,200 L 450,280 Z" fill="url(#grad1)" filter="url(#blur)"/>

  <!-- Nested group with filter -->
  <g id="group1" filter="url(#shadow)">
    <rect id="rect3" x="50" y="350" width="100" height="80" fill="orange"/>
    <circle id="circle2" cx="200" cy="390" r="40" fill="purple"/>
  </g>

  <!-- Text with filter -->
  <text id="text1" x="400" y="400" font-size="24" fill="black" filter="url(#colorMatrix)">
    Filtered Text
  </text>

  <!-- Unfiltered elements -->
  <line id="line1" x1="50" y1="500" x2="300" y2="500" stroke="black" stroke-width="3"/>

  <polygon id="polygon1" points="400,500 450,450 500,500 475,550 425,550" fill="cyan"/>
</svg>'''

def main():
    print("🔍 SVG2PPTX Element Flow Tracer Test")
    print("="*80)

    # Enable tracing
    enable_tracing()
    tracer = get_tracer()

    print("\n📊 Processing SVG with filtered elements...")
    print("   - 3 rectangles (1 with blur filter)")
    print("   - 2 circles (1 with shadow filter)")
    print("   - 1 ellipse (colorMatrix filter)")
    print("   - 1 path (blur filter + gradient)")
    print("   - 1 group (shadow filter, contains 2 elements)")
    print("   - 1 text (colorMatrix filter)")
    print("   - 2 unfiltered shapes (line, polygon)")

    # Convert with tracing enabled
    converter = CleanSlateConverter()

    try:
        result = converter.convert_string(test_svg)
        print(f"\n✅ Conversion complete: {len(result.output_data)} bytes")
    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")

    # Generate and print report
    print("\n" + "="*80)
    print("GENERATING TRACE REPORT")
    print("="*80)

    report = tracer.generate_report(focus_on_filtered=True)

    # Print summary
    tracer.print_report(report, verbose=True)

    # Save detailed report
    report_file = "/tmp/element_trace_report.json"
    tracer.save_report(report_file, report)
    print(f"\n💾 Detailed report saved to: {report_file}")

    # Analyze specific elements
    print("\n" + "="*80)
    print("DETAILED ANALYSIS OF FILTERED ELEMENTS")
    print("="*80)

    for elem in report['filtered_elements']:
        print(f"\n🎯 {elem['element_id']} ({elem['svg_tag']})")
        print(f"   Filters: {', '.join(elem['filter_ids'])}")
        print(f"   Compliant: {'✅ Yes' if elem['pipeline_compliant'] else '❌ No'}")

        if elem['violations']:
            print(f"   ⚠️  Violations:")
            for v in elem['violations']:
                print(f"      - {v}")

        # Show stage progression
        stages_visited = [tp['stage'] for tp in elem['trace_points'] if tp['event'] == 'enter']
        print(f"   Pipeline: {' → '.join(stages_visited)}")

        # Show timing
        parse_stage = elem['stages'].get('parse')
        map_stage = elem['stages'].get('map')
        if parse_stage and map_stage and 'duration' in parse_stage and 'duration' in map_stage:
            print(f"   Timing: parse={parse_stage['duration']*1000:.2f}ms, map={map_stage['duration']*1000:.2f}ms")

    # Summary statistics
    print("\n" + "="*80)
    print("COMPLIANCE SUMMARY")
    print("="*80)

    stats = report['summary']
    print(f"✅ Compliant elements: {stats['compliant_elements']}/{stats['total_elements']} ({stats['compliance_rate']*100:.1f}%)")
    print(f"⚠️  Non-compliant: {stats['non_compliant_elements']}")
    print(f"🎨 Filtered elements: {stats['filtered_elements']}")

    if stats['compliance_rate'] == 1.0:
        print("\n🎉 ALL ELEMENTS FOLLOWED PIPELINE CORRECTLY!")
    else:
        print(f"\n⚠️  {stats['non_compliant_elements']} elements deviated from pipeline")

    return stats['compliance_rate'] == 1.0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
