#!/usr/bin/env python3
"""
Debug optimization issues to understand performance regression.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.multislide.detection import SlideDetector
from src.multislide.config import DetectionConfig
from tests.support.multislide.performance_helpers import generate_test_svg

def debug_detection_results():
    """Debug why detection results differ."""
    print("=== Debugging Detection Logic ===\n")

    config = DetectionConfig(
        enable_animation_detection=True,
        enable_nested_svg_detection=True,
        enable_layer_detection=True,
        enable_section_marker_detection=True,
        enable_input_validation=False,
        enable_performance_optimizations=False
    )

    detector = SlideDetector(config)
    test_svg = generate_test_svg(100)

    print("1. Testing Legacy Detection Methods")
    print("-" * 35)

    # Test each method individually
    explicit = detector._detect_explicit_markers(test_svg)
    animation = detector._detect_animation_keyframes(test_svg)
    nested = detector._detect_nested_svgs(test_svg)
    layer = detector._detect_layer_groups(test_svg)
    section = detector._detect_section_markers(test_svg)

    print(f"Explicit markers: {len(explicit)} boundaries")
    print(f"Animation keyframes: {len(animation)} boundaries")
    print(f"Nested SVGs: {len(nested)} boundaries")
    print(f"Layer groups: {len(layer)} boundaries")
    print(f"Section markers: {len(section)} boundaries")
    print(f"Total legacy: {len(explicit + animation + nested + layer + section)} boundaries")

    print("\n2. Testing Element Index")
    print("-" * 25)

    # Test element index
    element_index = detector._build_element_index(test_svg)
    print(f"Groups indexed: {len(element_index['groups'])}")
    print(f"Text elements: {len(element_index['text_elements'])}")
    print(f"Animation elements: {len(element_index['animation_elements'])}")
    print(f"Nested SVGs: {len(element_index['nested_svgs'])}")
    print(f"Explicit markers: {len(element_index['explicit_markers'])}")

    print("\n3. Testing Optimized Detection Methods")
    print("-" * 38)

    # Test optimized methods
    explicit_opt = detector._detect_explicit_markers_optimized(element_index)
    animation_opt = detector._detect_animation_keyframes_optimized(element_index)
    nested_opt = detector._detect_nested_svgs_optimized(element_index)
    layer_opt = detector._detect_layer_groups_optimized(element_index)
    section_opt = detector._detect_section_markers_optimized(element_index)

    print(f"Explicit markers (opt): {len(explicit_opt)} boundaries")
    print(f"Animation keyframes (opt): {len(animation_opt)} boundaries")
    print(f"Nested SVGs (opt): {len(nested_opt)} boundaries")
    print(f"Layer groups (opt): {len(layer_opt)} boundaries")
    print(f"Section markers (opt): {len(section_opt)} boundaries")
    print(f"Total optimized: {len(explicit_opt + animation_opt + nested_opt + layer_opt + section_opt)} boundaries")

    print("\n4. Analyzing Differences")
    print("-" * 24)

    print("\nElement counts in generated SVG:")
    all_elements = list(test_svg.iter())
    print(f"Total elements: {len(all_elements)}")

    # Count by tag
    from collections import Counter
    tag_counts = Counter(elem.tag.split('}')[-1] for elem in all_elements)
    for tag, count in tag_counts.most_common():
        print(f"  {tag}: {count}")

    # Check layer group detection specifically
    print(f"\nLayer group analysis:")
    groups = test_svg.xpath('//g')
    print(f"Total groups found by XPath: {len(groups)}")

    layer_groups = []
    for group in groups:
        group_id = (group.get('id') or '').lower()
        group_class = (group.get('class') or '').lower()
        has_layer_keyword = any(keyword in group_id + group_class
                              for keyword in ['layer', 'slide', 'page', 'step', 'frame'])

        if has_layer_keyword:
            content_count = len(group.xpath('.//rect | .//circle | .//path | .//text'))
            print(f"  Group '{group_id}' class='{group_class}': {content_count} content elements")
            if content_count >= 3:
                layer_groups.append(group)

    print(f"Groups that should be detected as layers: {len(layer_groups)}")

if __name__ == "__main__":
    debug_detection_results()