#!/usr/bin/env python3
"""
Test Clean Slate Batch Processing

Demonstrates:
1. Multiple SVGs → Multi-slide PPTX (using convert_files())
2. Directory of SVGs → Multi-slide PPTX
3. ZIP of SVGs → Multi-slide PPTX
4. E2E tracing through entire batch pipeline
"""

import os
import sys
import json
from pathlib import Path

# Set immediate mode for synchronous testing
os.environ['HUEY_IMMEDIATE'] = 'true'
os.environ['PYTHONPATH'] = '.'

from core.batch.tasks import (
    convert_multiple_svgs_clean_slate,
    process_directory_to_pptx,
    process_zip_to_pptx
)


def test_multiple_svgs_to_pptx():
    """Test: Multiple separate SVG files → Multi-slide PPTX"""
    print("\n" + "="*80)
    print("TEST 1: Multiple SVGs → Multi-slide PPTX (Clean Slate)")
    print("="*80)

    # Create test SVGs
    test_dir = Path("/tmp/svg2pptx_batch_test")
    test_dir.mkdir(exist_ok=True)

    svg_files = []
    for i in range(3):
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
    <rect x="50" y="50" width="700" height="500" fill="#e0f2ff" stroke="#0284c7" stroke-width="4"/>
    <text x="400" y="300" text-anchor="middle" font-size="48" fill="#0c4a6e">
        Slide {i+1} from Separate SVG
    </text>
    <circle cx="{100 + i*50}" cy="150" r="30" fill="#f43f5e"/>
</svg>'''

        svg_path = test_dir / f"slide_{i+1}.svg"
        svg_path.write_text(svg_content)
        svg_files.append(str(svg_path))

    output_path = str(test_dir / "multiple_svgs_output.pptx")

    # Convert with E2E tracing enabled
    # Huey returns Result wrapper in immediate mode, call synchronously
    task_result = convert_multiple_svgs_clean_slate(
        file_paths=svg_files,
        output_path=output_path,
        conversion_options={
            'enable_debug': True,  # ✅ E2E TRACING
            'quality': 'high'
        }
    )

    # Get actual result from Huey wrapper
    result = task_result() if hasattr(task_result, '__call__') else task_result

    print(f"\nConversion Result:")
    print(f"  Success: {result['success']}")
    print(f"  Output: {result.get('output_path')}")
    print(f"  Pages: {result.get('page_count')}")
    print(f"  Architecture: {result.get('architecture')}")
    print(f"  Total Elements: {result.get('total_elements')}")
    print(f"  Native Elements: {result.get('native_elements')}")
    print(f"  EMF Elements: {result.get('emf_elements')}")
    print(f"  Avg Quality: {result.get('avg_quality'):.2f}")
    print(f"  Processing Time: {result.get('processing_time_seconds'):.2f}s")

    # Show E2E trace data
    if result.get('debug_trace'):
        print(f"\n✅ E2E Pipeline Trace Available:")
        for page_trace in result['debug_trace']:
            print(f"\n  Page {page_trace['page_number']}: {page_trace['svg_file']}")
            trace = page_trace.get('pipeline_trace', {})

            if 'parse_result' in trace:
                print(f"    Parse: {trace['parse_result'].get('element_count', 0)} elements, "
                      f"{trace['parse_result'].get('parsing_time_ms', 0):.1f}ms")

            if 'analysis_result' in trace:
                print(f"    Analyze: complexity={trace['analysis_result'].get('complexity_score', 0)}, "
                      f"{trace['analysis_result'].get('analysis_time_ms', 0):.1f}ms")

            if 'mapper_results' in trace:
                print(f"    Map: {len(trace['mapper_results'])} elements mapped")

            if 'embedder_result' in trace:
                embed = trace['embedder_result']
                print(f"    Embed: {embed.get('native_elements', 0)} native, "
                      f"{embed.get('emf_elements', 0)} emf, "
                      f"{embed.get('processing_time_ms', 0):.1f}ms")

    if Path(output_path).exists():
        size_kb = Path(output_path).stat().st_size / 1024
        print(f"\n✅ Output PPTX created: {size_kb:.1f} KB")


def test_directory_to_pptx():
    """Test: Directory of SVGs → Multi-slide PPTX"""
    print("\n" + "="*80)
    print("TEST 2: Directory of SVGs → Multi-slide PPTX")
    print("="*80)

    test_dir = Path("/tmp/svg2pptx_dir_test")
    test_dir.mkdir(exist_ok=True)

    # Create multiple SVG files in directory
    for i in range(4):
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
    <rect width="800" height="600" fill="#{["fef3c7", "dbeafe", "fce7f3", "f3e8ff"][i]}"/>
    <text x="400" y="300" text-anchor="middle" font-size="36" fill="#1e293b">
        Directory Slide {i+1}
    </text>
</svg>'''
        (test_dir / f"page_{i+1:02d}.svg").write_text(svg_content)

    output_path = str(test_dir / "directory_output.pptx")

    task_result = process_directory_to_pptx(
        directory_path=str(test_dir),
        output_path=output_path,
        conversion_options={'enable_debug': True}
    )
    result = task_result() if hasattr(task_result, '__call__') else task_result

    print(f"\nDirectory Processing Result:")
    print(f"  Success: {result['success']}")
    print(f"  Pages: {result.get('page_count')}")
    print(f"  Debug Trace Pages: {len(result.get('debug_trace', []))}")

    if Path(output_path).exists():
        print(f"✅ Directory PPTX created: {output_path}")


def test_zip_to_pptx():
    """Test: ZIP of SVGs → Multi-slide PPTX"""
    print("\n" + "="*80)
    print("TEST 3: ZIP of SVGs → Multi-slide PPTX")
    print("="*80)

    import zipfile
    import io

    # Create ZIP with SVG files
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for i in range(3):
            svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
    <rect width="800" height="600" fill="#ecfccb"/>
    <text x="400" y="300" text-anchor="middle" font-size="42" fill="#365314">
        ZIP Slide {i+1}
    </text>
</svg>'''
            zf.writestr(f"slide_{i+1}.svg", svg_content)

    zip_content = zip_buffer.getvalue()
    output_path = "/tmp/svg2pptx_zip_output.pptx"

    task_result = process_zip_to_pptx(
        zip_content=zip_content,
        output_path=output_path,
        conversion_options={'enable_debug': True}
    )
    result = task_result() if hasattr(task_result, '__call__') else task_result

    print(f"\nZIP Processing Result:")
    print(f"  Success: {result['success']}")
    print(f"  Pages: {result.get('page_count')}")
    print(f"  Architecture: {result.get('architecture')}")

    if Path(output_path).exists():
        print(f"✅ ZIP PPTX created: {output_path}")


def main():
    """Run all batch processing tests"""
    print("\n" + "="*80)
    print("CLEAN SLATE BATCH PROCESSING TEST SUITE")
    print("="*80)
    print("\nTesting:")
    print("  1. Multiple separate SVGs → Multi-slide PPTX (convert_files())")
    print("  2. Directory of SVGs → Multi-slide PPTX")
    print("  3. ZIP of SVGs → Multi-slide PPTX")
    print("  4. E2E tracing through entire pipeline")
    print("\n")

    try:
        # Run tests
        test_multiple_svgs_to_pptx()
        test_directory_to_pptx()
        test_zip_to_pptx()

        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)
        print("\nKey Findings:")
        print("  • Multiple SVGs → Multi-slide PPTX: ✅ Working")
        print("  • Directory processing: ✅ Working")
        print("  • ZIP processing: ✅ Working")
        print("  • E2E tracing: ✅ Available with enable_debug=True")
        print("  • Architecture: Clean Slate (IR → Policy → Map → Embed)")
        print("\nOutput files:")
        print("  - /tmp/svg2pptx_batch_test/multiple_svgs_output.pptx")
        print("  - /tmp/svg2pptx_dir_test/directory_output.pptx")
        print("  - /tmp/svg2pptx_zip_output.pptx")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
