#!/usr/bin/env python3
"""
Debug which element is being lost: 20 IR elements → 19 processed
"""

from core.parse.parser import SVGParser
from core.pipeline.converter import CleanSlateConverter

# Complex test SVG with 37 elements
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

print("🔍 DEBUGGING MISSING ELEMENT")
print("=" * 70)

# Step 1: Parse and convert to IR
parser = SVGParser()
scene, parse_result = parser.parse_to_ir(test_svg)

print(f"1️⃣ IR Conversion:")
print(f"   Total IR elements: {len(scene)}")

# Catalog all IR elements
ir_catalog = {}
for i, element in enumerate(scene):
    element_type = type(element).__name__
    ir_catalog[i] = {
        'type': element_type,
        'element': element
    }
    print(f"   [{i:2d}] {element_type}")

# Step 2: Test mapping stage
converter = CleanSlateConverter()

print(f"\n2️⃣ Mapping Stage:")
mapped_count = 0
unmapped = []

for i, element in enumerate(scene):
    mapper = converter._find_mapper(element)
    if mapper:
        mapper_type = type(mapper).__name__
        print(f"   [{i:2d}] {type(element).__name__:12s} → {mapper_type}")
        mapped_count += 1
    else:
        print(f"   [{i:2d}] {type(element).__name__:12s} → ❌ NO MAPPER")
        unmapped.append(i)

print(f"\n   Mapped: {mapped_count}/{len(scene)}")
if unmapped:
    print(f"   Unmapped elements: {unmapped}")

# Step 3: Actually map them and see which fails
print(f"\n3️⃣ Actual Mapping Execution:")
mapper_results = []
failed = []

for i, element in enumerate(scene):
    try:
        mapper = converter._find_mapper(element)
        if mapper:
            result = mapper.map(element)
            mapper_results.append(result)
            print(f"   [{i:2d}] ✅ Mapped successfully")
        else:
            print(f"   [{i:2d}] ❌ No mapper found")
            failed.append((i, "No mapper"))
    except Exception as e:
        print(f"   [{i:2d}] ❌ Mapping failed: {e}")
        failed.append((i, str(e)))

print(f"\n   Successfully mapped: {len(mapper_results)}/{len(scene)}")

if failed:
    print(f"\n   Failed elements:")
    for idx, reason in failed:
        element_info = ir_catalog[idx]
        print(f"     [{idx}] {element_info['type']}: {reason}")

# Step 4: Check embedding
print(f"\n4️⃣ Embedding Stage:")
embedder_result = converter.embedder.embed_scene(scene, mapper_results)
print(f"   Elements embedded: {embedder_result.elements_embedded}")
print(f"   Expected: {len(mapper_results)}")

if embedder_result.elements_embedded != len(mapper_results):
    print(f"   ⚠️ Mismatch: {len(mapper_results) - embedder_result.elements_embedded} elements lost in embedding!")

# Step 5: Check final result
print(f"\n5️⃣ Final Conversion Result:")
result = converter.convert_string(test_svg)
print(f"   Elements processed: {result.elements_processed}")
print(f"   Expected: {len(scene)}")

if result.elements_processed != len(scene):
    print(f"   ⚠️ Lost elements: {len(scene) - result.elements_processed}")

print("\n" + "=" * 70)
print(f"SUMMARY:")
print(f"  IR elements created: {len(scene)}")
print(f"  Elements mapped: {len(mapper_results)}")
print(f"  Elements embedded: {embedder_result.elements_embedded}")
print(f"  Elements in output: {result.elements_processed}")

if len(scene) != result.elements_processed:
    print(f"\n❌ ELEMENT LOSS CONFIRMED: {len(scene) - result.elements_processed} element(s) lost")
else:
    print(f"\n✅ ALL ELEMENTS ACCOUNTED FOR")