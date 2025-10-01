#!/usr/bin/env python3
"""
Debug why standalone <path> elements return 0 elements processed.
"""

from core.parse.parser import SVGParser
from core.pipeline.converter import CleanSlateConverter

# Simple path that fails
failing_path = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <path d="M10,50 Q50,10 90,50 T90,90" stroke="navy" fill="none" stroke-width="2"/>
</svg>"""

# Working shape (converts to path)
working_rect = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect x="10" y="10" width="80" height="60" fill="blue"/>
</svg>"""

print("🔍 DEBUGGING STANDALONE PATH BUG")
print("=" * 70)

# Step 1: Parse both
parser = SVGParser()

print("1️⃣ Parsing standalone path...")
path_scene, path_parse = parser.parse_to_ir(failing_path)
print(f"   Parse success: {path_parse.success}")
print(f"   IR elements: {len(path_scene) if path_scene else 0}")
if path_scene:
    for i, elem in enumerate(path_scene):
        print(f"     [{i}] {type(elem).__name__}")
        if hasattr(elem, 'd'):
            print(f"         Path data: {elem.d[:50] if elem.d else 'None'}...")
        if hasattr(elem, 'segments'):
            print(f"         Segments: {len(elem.segments) if elem.segments else 0}")

print("\n2️⃣ Parsing rect (for comparison)...")
rect_scene, rect_parse = parser.parse_to_ir(working_rect)
print(f"   Parse success: {rect_parse.success}")
print(f"   IR elements: {len(rect_scene) if rect_scene else 0}")
if rect_scene:
    for i, elem in enumerate(rect_scene):
        print(f"     [{i}] {type(elem).__name__}")
        if hasattr(elem, 'segments'):
            print(f"         Segments: {len(elem.segments) if elem.segments else 0}")

# Step 2: Check mapping
print("\n3️⃣ Testing mapping stage...")
converter = CleanSlateConverter()

if path_scene:
    print("   Path scene mapping:")
    for i, elem in enumerate(path_scene):
        mapper = converter._find_mapper(elem)
        if mapper:
            print(f"     [{i}] {type(elem).__name__} → {type(mapper).__name__}")
            try:
                result = mapper.map(elem)
                print(f"         ✅ Mapped: {len(result.xml_content)} chars")
            except Exception as e:
                print(f"         ❌ Mapping failed: {e}")
        else:
            print(f"     [{i}] {type(elem).__name__} → NO MAPPER")

# Step 3: Full pipeline
print("\n4️⃣ Full pipeline test...")
print("   Standalone path:")
path_result = converter.convert_string(failing_path)
print(f"     Elements processed: {path_result.elements_processed}")
print(f"     Native elements: {path_result.native_elements}")

print("\n   Rect (for comparison):")
rect_result = converter.convert_string(working_rect)
print(f"     Elements processed: {rect_result.elements_processed}")
print(f"     Native elements: {rect_result.native_elements}")

# Step 4: Check what's different
print("\n5️⃣ Analyzing differences...")

if path_scene and len(path_scene) > 0:
    path_elem = path_scene[0]
    print(f"   Path element attributes:")
    for attr in dir(path_elem):
        if not attr.startswith('_'):
            val = getattr(path_elem, attr, None)
            if not callable(val):
                print(f"     {attr}: {val}")

print("\n" + "=" * 70)
print("ROOT CAUSE:")
if len(path_scene) > 0 and path_result.elements_processed == 0:
    print("❌ Path converts to IR but doesn't get embedded!")
    print("   Likely issue: Embedder or mapper result not being included")
elif len(path_scene) == 0:
    print("❌ Path doesn't convert to IR at all!")
    print("   Likely issue: Parser._extract_recursive_to_ir() not handling paths")
else:
    print("✅ No bug detected in this test")