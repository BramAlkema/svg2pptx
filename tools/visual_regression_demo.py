#!/usr/bin/env python3
"""
Visual regression testing demo and examples.

This script demonstrates the visual regression testing capabilities
and provides a simple way to test the system with sample files.
"""

import tempfile
import zipfile
from pathlib import Path
import json
import time

from visual_regression_tester import (
    VisualRegressionTester,
    ComparisonMethod,
    PILLOW_AVAILABLE
)


def create_sample_pptx(output_path: Path, content_variation: str = "default") -> Path:
    """Create a sample PPTX file for testing."""
    
    # Base content that creates a valid PPTX
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-presentationml.presentation.main+xml"/>
    <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-presentationml.slide+xml"/>
</Types>'''

    main_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''

    presentation = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:sldMasterIdLst>
        <p:sldMasterId id="2147483648" r:id="rId2"/>
    </p:sldMasterIdLst>
    <p:sldIdLst>
        <p:sldId id="256" r:id="rId3"/>
    </p:sldIdLst>
    <p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>
    <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''

    # Slide content varies based on variation parameter
    if content_variation == "reference":
        slide_color = "FF0000"  # Red
        slide_text = "Reference Slide"
    elif content_variation == "similar":
        slide_color = "FF0000"  # Same red
        slide_text = "Reference Slide"  # Same text
    elif content_variation == "different":
        slide_color = "00FF00"  # Green
        slide_text = "Different Slide"
    else:
        slide_color = "0080FF"  # Blue
        slide_text = "Default Slide"

    slide1 = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" 
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr>
                <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="0" cy="0"/>
                    <a:chOff x="0" y="0"/>
                    <a:chExt cx="0" cy="0"/>
                </a:xfrm>
            </p:grpSpPr>
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="2" name="Rectangle 1"/>
                    <p:cNvSpPr/>
                    <p:nvPr/>
                </p:nvSpPr>
                <p:spPr>
                    <a:xfrm>
                        <a:off x="914400" y="914400"/>
                        <a:ext cx="2743200" cy="1371600"/>
                    </a:xfrm>
                    <a:prstGeom prst="rect">
                        <a:avLst/>
                    </a:prstGeom>
                    <a:solidFill>
                        <a:srgbClr val="{slide_color}"/>
                    </a:solidFill>
                    <a:ln w="19050">
                        <a:solidFill>
                            <a:srgbClr val="000000"/>
                        </a:solidFill>
                    </a:ln>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr rtlCol="0" anchor="ctr"/>
                    <a:lstStyle/>
                    <a:p>
                        <a:pPr algn="ctr"/>
                        <a:r>
                            <a:rPr lang="en-US" sz="2400" b="1"/>
                            <a:t>{slide_text}</a:t>
                        </a:r>
                    </a:p>
                </p:txBody>
            </p:sp>
        </p:spTree>
    </p:cSld>
    <p:clrMapOvr>
        <a:masterClrMapping/>
    </p:clrMapOvr>
</p:sld>'''

    # Create PPTX file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('[Content_Types].xml', content_types)
        zip_file.writestr('_rels/.rels', main_rels)
        zip_file.writestr('ppt/presentation.xml', presentation)
        zip_file.writestr('ppt/slides/slide1.xml', slide1)
    
    return output_path


def demo_basic_functionality():
    """Demonstrate basic visual regression testing functionality."""
    print("\n🚀 Visual Regression Testing Demo")
    print("=" * 50)
    
    try:
        tester = VisualRegressionTester()
        print(f"✅ LibreOffice found: {tester.renderer.libreoffice_path}")
        print(f"🖼️  Pillow available: {PILLOW_AVAILABLE}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            print(f"📁 Working directory: {temp_path}")
            
            # Create sample PPTX files
            ref_pptx = temp_path / "reference.pptx"
            similar_pptx = temp_path / "similar.pptx" 
            different_pptx = temp_path / "different.pptx"
            
            print("\n📋 Creating sample PPTX files...")
            create_sample_pptx(ref_pptx, "reference")
            create_sample_pptx(similar_pptx, "similar") 
            create_sample_pptx(different_pptx, "different")
            print(f"   Reference: {ref_pptx.name} ({ref_pptx.stat().st_size} bytes)")
            print(f"   Similar:   {similar_pptx.name} ({similar_pptx.stat().st_size} bytes)")
            print(f"   Different: {different_pptx.name} ({different_pptx.stat().st_size} bytes)")
            
            # Test 1: Similar files (should pass)
            print("\n🔍 Test 1: Comparing similar files...")
            start_time = time.time()
            
            result1 = tester.run_regression_test(
                ref_pptx, similar_pptx, 
                test_name="similar_test",
                similarity_threshold=0.90,
                comparison_methods=[ComparisonMethod.STRUCTURAL_SIMILARITY]
            )
            
            duration1 = time.time() - start_time
            print(f"   Result: {'✅ PASSED' if result1.passed else '❌ FAILED'}")
            print(f"   Similarity: {result1.actual_similarity:.3f} (threshold: {result1.similarity_threshold:.3f})")
            print(f"   Duration: {duration1:.2f}s")
            if result1.error_message:
                print(f"   Error: {result1.error_message}")
            
            # Test 2: Different files (should fail)
            print("\n🔍 Test 2: Comparing different files...")
            start_time = time.time()
            
            result2 = tester.run_regression_test(
                ref_pptx, different_pptx,
                test_name="different_test", 
                similarity_threshold=0.90,
                comparison_methods=[ComparisonMethod.STRUCTURAL_SIMILARITY]
            )
            
            duration2 = time.time() - start_time
            print(f"   Result: {'✅ PASSED' if result2.passed else '❌ FAILED'}")
            print(f"   Similarity: {result2.actual_similarity:.3f} (threshold: {result2.similarity_threshold:.3f})")
            print(f"   Duration: {duration2:.2f}s")
            if result2.error_message:
                print(f"   Error: {result2.error_message}")
            
            # Test 3: Multiple comparison methods
            print("\n🔍 Test 3: Multiple comparison methods...")
            start_time = time.time()
            
            methods = [
                ComparisonMethod.STRUCTURAL_SIMILARITY,
                ComparisonMethod.PIXEL_PERFECT,
                ComparisonMethod.PERCEPTUAL_HASH
            ]
            
            result3 = tester.run_regression_test(
                ref_pptx, similar_pptx,
                test_name="multi_method_test",
                similarity_threshold=0.85,
                comparison_methods=methods
            )
            
            duration3 = time.time() - start_time
            print(f"   Result: {'✅ PASSED' if result3.passed else '❌ FAILED'}")
            print(f"   Primary similarity: {result3.actual_similarity:.3f}")
            print(f"   Duration: {duration3:.2f}s")
            
            for method_name, comp_result in result3.comparison_results.items():
                print(f"     {method_name}: {comp_result.similarity_score:.3f}")
            
            # Test 4: Test suite execution
            print("\n🔍 Test 4: Running test suite...")
            
            test_configs = [
                {
                    "name": "suite_similar",
                    "reference": str(ref_pptx),
                    "output": str(similar_pptx),
                    "similarity_threshold": 0.90,
                    "comparison_methods": ["structural_similarity"]
                },
                {
                    "name": "suite_different", 
                    "reference": str(ref_pptx),
                    "output": str(different_pptx),
                    "similarity_threshold": 0.90,
                    "comparison_methods": ["structural_similarity"]
                }
            ]
            
            results_dir = temp_path / "results"
            suite_results = tester.run_test_suite(test_configs, results_dir)
            
            print(f"   Suite completed: {len(suite_results)} tests")
            
            passed_count = sum(1 for r in suite_results.values() if r.passed)
            failed_count = len(suite_results) - passed_count
            
            print(f"   Results: {passed_count} passed, {failed_count} failed")
            
            for test_name, result in suite_results.items():
                status = "✅ PASSED" if result.passed else "❌ FAILED"
                print(f"     {test_name}: {status} ({result.actual_similarity:.3f})")
            
            # Show generated files
            if results_dir.exists():
                result_files = list(results_dir.glob("*.json"))
                print(f"   Generated {len(result_files)} result files in {results_dir}")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"💡 Visual regression testing system is working with LibreOffice")
        
        if not PILLOW_AVAILABLE:
            print(f"⚠️  Note: Pillow not available - using mock image comparison")
            print(f"   Install Pillow for full image analysis: pip install Pillow")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print(f"💡 Make sure LibreOffice is installed and accessible")
        raise


def demo_image_comparison_methods():
    """Demonstrate different image comparison methods."""
    if not PILLOW_AVAILABLE:
        print("\n⚠️  Skipping image comparison demo - Pillow not available")
        return
    
    print("\n🖼️  Image Comparison Methods Demo")
    print("=" * 40)
    
    from visual_regression_tester import ImageComparator
    
    comparator = ImageComparator()
    
    print("Available comparison methods:")
    for method in ComparisonMethod:
        print(f"   • {method.value}")
    
    print(f"\nComparator initialized (mock mode: {getattr(comparator, 'mock_mode', False)})")


if __name__ == '__main__':
    try:
        demo_basic_functionality()
        demo_image_comparison_methods()
        
        print(f"\n📖 Integration Information:")
        print(f"   • Use VisualRegressionTester for end-to-end testing")
        print(f"   • LibreOffice converts PPTX to images automatically") 
        print(f"   • Multiple comparison algorithms available")
        print(f"   • Configurable similarity thresholds")
        print(f"   • Comprehensive test suite execution")
        print(f"   • JSON result reporting and archival")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Demo error: {e}")
        import traceback
        traceback.print_exc()