#!/usr/bin/env python3
"""
Debug the embedder to find where mapped elements disappear.
"""

import traceback

def debug_embedder():
    """Debug the embedding stage to find where elements are lost."""

    print("🔍 DEBUGGING EMBEDDER - Finding the Black Hole")
    print("=" * 60)

    # Test SVG
    test_svg = """<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
        <rect x="10" y="10" width="100" height="80" fill="red"/>
        <circle cx="200" cy="50" r="40" fill="green"/>
        <text x="50" y="150" font-size="20">Test Text</text>
    </svg>"""

    try:
        # Step 1: Get mapper results
        from core.parse.parser import SVGParser
        from core.pipeline.converter import CleanSlateConverter

        parser = SVGParser()
        scene, parse_result = parser.parse_to_ir(test_svg)

        converter = CleanSlateConverter()
        mapper_results = converter._map_scene_elements(scene)

        print(f"✅ Mapper Results: {len(mapper_results)} results")
        for i, result in enumerate(mapper_results):
            print(f"   [{i}] {type(result.element).__name__} → {result.output_format.value}")
            print(f"       XML length: {len(result.xml_content)} chars")
            print(f"       First 100 chars: {result.xml_content[:100]}...")

        # Step 2: Test embedder directly
        print(f"\n🔧 Testing Embedder Directly...")

        embedder_result = converter.embedder.embed_scene(scene, mapper_results)

        print(f"   Embedder result type: {type(embedder_result)}")
        print(f"   Elements embedded: {embedder_result.elements_embedded}")
        print(f"   Native elements: {embedder_result.native_elements}")
        print(f"   EMF elements: {embedder_result.emf_elements}")
        print(f"   Slide XML length: {len(embedder_result.slide_xml) if embedder_result.slide_xml else 0}")

        if embedder_result.slide_xml:
            print(f"   Slide XML preview:")
            print(f"   {embedder_result.slide_xml[:500]}...")
        else:
            print(f"   ❌ No slide XML generated!")

        # Step 3: Check ConversionResult creation
        print(f"\n📊 Checking ConversionResult Creation...")

        result = converter.convert_string(test_svg)
        print(f"   Final result elements_processed: {result.elements_processed}")
        print(f"   How is elements_processed calculated?")

        # Look at the ConversionResult creation
        print(f"   len(mapper_results): {len(mapper_results)}")
        print(f"   embedder_result.elements_embedded: {embedder_result.elements_embedded}")

        return True

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        traceback.print_exc()
        return False

def investigate_embedder_code():
    """Look at the embedder source to understand the issue."""

    print("\n🔍 INVESTIGATING EMBEDDER SOURCE")
    print("=" * 60)

    try:
        # Check what method is being called
        from core.io.embedder import DrawingMLEmbedder
        embedder = DrawingMLEmbedder(9144000, 6858000)

        # Check available methods
        methods = [m for m in dir(embedder) if not m.startswith('_') and callable(getattr(embedder, m))]
        print(f"Available embedder methods: {methods}")

        # Check if embed_scene exists
        if hasattr(embedder, 'embed_scene'):
            print("✅ embed_scene method exists")
        else:
            print("❌ embed_scene method missing!")

        # Check for other embed methods
        embed_methods = [m for m in methods if 'embed' in m.lower()]
        print(f"Embed methods found: {embed_methods}")

    except Exception as e:
        print(f"❌ Embedder investigation failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_embedder()
    investigate_embedder_code()