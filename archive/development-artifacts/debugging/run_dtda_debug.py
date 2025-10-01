#!/usr/bin/env python3
"""
Run DTDA logo through comprehensive debug system
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from comprehensive_debug_system import ComprehensiveDebugSystem

def main():
    """Run comprehensive debug analysis on DTDA logo."""
    print("🚀 SVG2PPTX COMPREHENSIVE DEBUG SYSTEM - DTDA LOGO")
    print("=" * 60)

    debug_system = ComprehensiveDebugSystem()

    # Analyze SVG
    debug_system.analyze_svg_completely('dtda_logo.svg')

    # Debug conversion process
    debug_system.debug_conversion_process('dtda_logo.svg', 'dtda_logo_debug_test.pptx')

    # Analyze PPTX output
    debug_system.analyze_pptx_output('dtda_logo_debug_test.pptx')

    # Compare accuracy
    debug_system.compare_svg_to_pptx()

    # Generate recommendations
    debug_system.generate_recommendations()

    # Save reports
    debug_system.save_debug_report('dtda_logo_debug_report.json')
    debug_system.generate_html_report('dtda_logo_debug_report.html')

    print("\n🎉 DTDA LOGO DEBUG ANALYSIS COMPLETE!")
    print("📊 Reports generated:")
    print("   • dtda_logo_debug_report.json (raw data)")
    print("   • dtda_logo_debug_report.html (visual report)")
    print("   • dtda_logo_debug_test.pptx (test output)")

if __name__ == "__main__":
    main()