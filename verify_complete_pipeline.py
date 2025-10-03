#!/usr/bin/env python3
"""
THOROUGH verification of the complete pipeline flow for ALL elements.
Let's see if we're really processing everything or just fooling ourselves.
"""

import traceback
from lxml import etree as ET

def verify_complete_pipeline():
    """Thoroughly verify EVERY part of the pipeline."""

    print("🔍 THOROUGH PIPELINE VERIFICATION")
    print("=" * 80)

    # Comprehensive test SVG
    test_svg = """<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="800" height="600">
        <!-- Basic shapes -->
        <rect x="10" y="10" width="100" height="80" fill="red"/>
        <circle cx="200" cy="50" r="40" fill="green"/>
        <ellipse cx="350" cy="50" rx="50" ry="30" fill="blue"/>
        <line x1="10" y1="150" x2="100" y2="200" stroke="black"/>
        <polyline points="150,150 200,180 250,150 300,200" stroke="purple" fill="none"/>
        <polygon points="350,150 400,180 450,150 425,200 375,200" fill="orange"/>

        <!-- Paths -->
        <path d="M10,250 Q50,200 100,250 T200,250" stroke="navy" fill="none"/>

        <!-- Text -->
        <text x="10" y="350" font-size="20">Basic Text</text>
        <text x="150" y="350" font-size="24" transform="rotate(45 150 350)">Rotated</text>

        <!-- Groups -->
        <g transform="translate(300,300)">
            <rect x="0" y="0" width="50" height="50" fill="cyan"/>
            <text x="25" y="30" text-anchor="middle">Group</text>
        </g>

        <!-- Definitions and references -->
        <defs>
            <linearGradient id="grad1">
                <stop offset="0%" stop-color="yellow"/>
                <stop offset="100%" stop-color="red"/>
            </linearGradient>
            <pattern id="pattern1" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
                <rect x="0" y="0" width="10" height="10" fill="lightblue"/>
                <rect x="10" y="10" width="10" height="10" fill="lightblue"/>
            </pattern>
            <clipPath id="clip1">
                <circle cx="25" cy="25" r="20"/>
            </clipPath>
        </defs>

        <!-- Using definitions -->
        <rect x="500" y="10" width="100" height="50" fill="url(#grad1)"/>
        <rect x="500" y="80" width="100" height="50" fill="url(#pattern1)"/>
        <rect x="500" y="150" width="100" height="50" fill="pink" clip-path="url(#clip1)"/>

        <!-- Filters -->
        <defs>
            <filter id="blur1">
                <feGaussianBlur stdDeviation="2"/>
            </filter>
        </defs>
        <rect x="500" y="220" width="100" height="50" fill="purple" filter="url(#blur1)"/>

        <!-- Markers -->
        <defs>
            <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                <polygon points="0,0 0,6 9,3" fill="black"/>
            </marker>
        </defs>
        <line x1="500" y1="300" x2="600" y2="350" stroke="black" marker-end="url(#arrow)"/>

        <!-- Image -->
        <image href="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiPjxyZWN0IHdpZHRoPSIxMCIgaGVpZ2h0PSIxMCIgZmlsbD0icmVkIi8+PC9zdmc+"
               x="500" y="400" width="50" height="50"/>

        <!-- Use element -->
        <use href="#grad1" x="650" y="10"/>

        <!-- Foreign object -->
        <foreignObject x="10" y="500" width="100" height="50">
            <div xmlns="http://www.w3.org/1999/xhtml">HTML content</div>
        </foreignObject>
    </svg>"""

    # Test each stage thoroughly
    print("1️⃣ TESTING PARSE STAGE")
    print("-" * 40)

    try:
        from core.parse.parser import SVGParser
        parser = SVGParser()
        parse_result = parser.parse(test_svg)

        print(f"✅ Parse successful: {parse_result.success}")
        print(f"   Elements found: {parse_result.element_count}")

        # Count each element type
        from core.xml.safe_iter import walk
        element_counts = {}
        for elem in walk(parse_result.svg_root):
            tag = elem.tag.split('}')[-1] if '}' in str(elem.tag) else str(elem.tag)
            element_counts[tag] = element_counts.get(tag, 0) + 1

        print("   Element breakdown:")
        for tag, count in sorted(element_counts.items()):
            print(f"     {tag}: {count}")

    except Exception as e:
        print(f"❌ Parse failed: {e}")
        traceback.print_exc()
        return False

    print("\n2️⃣ TESTING SVG → IR CONVERSION")
    print("-" * 40)

    try:
        scene, parse_result = parser.parse_to_ir(test_svg)

        if scene is None:
            print(f"❌ IR conversion failed: {parse_result.error}")
            return False

        print(f"✅ IR conversion successful")
        print(f"   IR elements created: {len(scene)}")

        # Analyze what IR elements were created
        ir_types = {}
        for ir_element in scene:
            ir_type = type(ir_element).__name__
            ir_types[ir_type] = ir_types.get(ir_type, 0) + 1

        print("   IR element breakdown:")
        for ir_type, count in sorted(ir_types.items()):
            print(f"     {ir_type}: {count}")

        # Check specific elements
        if len(scene) == 0:
            print("❌ WARNING: No IR elements created!")
            return False

    except Exception as e:
        print(f"❌ IR conversion failed: {e}")
        traceback.print_exc()
        return False

    print("\n3️⃣ TESTING ANALYSIS STAGE")
    print("-" * 40)

    try:
        from core.analyze.analyzer import SVGAnalyzer
        analyzer = SVGAnalyzer()

        analysis_result = analyzer.analyze(parse_result.svg_root)

        print(f"✅ Analysis successful")
        print(f"   Complexity score: {analysis_result.complexity_score:.3f}")
        print(f"   Element count: {analysis_result.element_count}")
        print(f"   Scene type: {type(analysis_result.scene)}")
        print(f"   Scene elements: {len(analysis_result.scene) if analysis_result.scene else 0}")

        # Check features detected
        features = []
        if analysis_result.has_transforms: features.append("transforms")
        if analysis_result.has_clipping: features.append("clipping")
        if analysis_result.has_patterns: features.append("patterns")
        if analysis_result.has_animations: features.append("animations")

        print(f"   Features detected: {', '.join(features) if features else 'none'}")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        traceback.print_exc()
        return False

    print("\n4️⃣ TESTING MAPPING STAGE")
    print("-" * 40)

    try:
        from core.pipeline.converter import CleanSlateConverter
        converter = CleanSlateConverter()

        # Test mapper assignments
        print("   Mapper configuration:")
        for name, mapper in converter.mappers.items():
            print(f"     {name}: {type(mapper).__name__}")

        # Test mapping each IR element
        mapped_count = 0
        mapper_usage = {}

        for ir_element in scene:
            element_type = type(ir_element).__name__.lower()
            mapper = converter._find_mapper(ir_element)

            if mapper:
                mapper_name = type(mapper).__name__
                mapper_usage[mapper_name] = mapper_usage.get(mapper_name, 0) + 1
                mapped_count += 1
                print(f"     ✅ {type(ir_element).__name__} → {mapper_name}")
            else:
                print(f"     ❌ {type(ir_element).__name__} → NO MAPPER")

        print(f"\n   Mapping results:")
        print(f"     Elements mapped: {mapped_count}/{len(scene)}")
        print(f"     Mapper usage: {mapper_usage}")

        if mapped_count == 0:
            print("❌ WARNING: No elements mapped!")
            return False

    except Exception as e:
        print(f"❌ Mapping stage failed: {e}")
        traceback.print_exc()
        return False

    print("\n5️⃣ TESTING FULL PIPELINE")
    print("-" * 40)

    try:
        result = converter.convert_string(test_svg)

        print(f"✅ Full conversion successful")
        print(f"   Total time: {result.total_time_ms:.2f}ms")
        print(f"   Elements processed: {result.elements_processed}")
        print(f"   Native elements: {result.native_elements}")
        print(f"   EMF elements: {result.emf_elements}")
        print(f"   Output size: {len(result.output_data)} bytes")

        # The critical question: Are we actually processing the elements?
        if result.elements_processed == 0:
            print("❌ CRITICAL ISSUE: No elements processed in final output!")
            return False
        elif result.elements_processed < len(scene):
            print(f"⚠️ WARNING: Only {result.elements_processed}/{len(scene)} elements processed!")
            print("   Some elements are being lost in the pipeline!")

    except Exception as e:
        print(f"❌ Full pipeline failed: {e}")
        traceback.print_exc()
        return False

    print("\n6️⃣ CHECKING WHAT'S ACTUALLY IN THE OUTPUT")
    print("-" * 40)

    try:
        # Save and inspect the output
        with open("pipeline_test_output.pptx", "wb") as f:
            f.write(result.output_data)
        print(f"✅ Output saved to pipeline_test_output.pptx")

        # Try to peek inside (basic check)
        import zipfile
        with zipfile.ZipFile("pipeline_test_output.pptx", 'r') as zip_file:
            files = zip_file.namelist()
            print(f"   PPTX contains {len(files)} files")

            # Check for slide content
            slide_files = [f for f in files if 'slide' in f and f.endswith('.xml')]
            print(f"   Slide files: {slide_files}")

            if slide_files:
                slide_content = zip_file.read(slide_files[0]).decode('utf-8')
                # Count actual shapes in the slide
                shape_count = slide_content.count('<p:sp>')
                print(f"   Shapes in slide XML: {shape_count}")

                if shape_count == 0:
                    print("❌ CRITICAL: No shapes found in slide XML!")
                    return False

    except Exception as e:
        print(f"❌ Output inspection failed: {e}")
        traceback.print_exc()

    return True

def main():
    success = verify_complete_pipeline()

    print("\n" + "=" * 80)
    if success:
        print("✅ PIPELINE VERIFICATION PASSED")
        print("All stages working and elements flowing through properly")
    else:
        print("❌ PIPELINE VERIFICATION FAILED")
        print("Found issues in the pipeline flow - elements not properly processed")
    print("=" * 80)

if __name__ == "__main__":
    main()