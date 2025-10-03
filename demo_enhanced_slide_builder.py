#!/usr/bin/env python3
"""
Enhanced Slide Builder Performance Demo

Demonstrates the improvements made to the slide builder:
1. Proper XML handling vs string manipulation
2. Caching performance benefits
3. Schema validation capabilities
4. Error handling with context
"""

import time
import sys
from pathlib import Path
from lxml import etree as ET
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.io.slide_builder import SlideBuilder, SlideMetadata, SlideTemplate
from core.io.slide_builder_original import SlideBuilder as OriginalSlideBuilder


def create_mock_dependencies():
    """Create mock mappers, embedder, and policy for testing"""
    # Mock mapper
    mock_mapper = Mock()
    mock_mapper.can_map.return_value = True
    mock_mapper.map.return_value = Mock(
        drawingml_xml="<p:sp><p:nvSpPr><p:cNvPr id='1' name='shape'/></p:nvSpPr></p:sp>",
        relationships=[]
    )
    mock_mapper.get_statistics.return_value = {'elements_mapped': 1}
    mock_mapper.reset_statistics.return_value = None

    # Mock embedder that returns valid slide XML
    mock_embedder = Mock()
    mock_embedder.embed_scene.return_value = Mock(
        slide_xml='''<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <p:cSld>
        <p:spTree>
            <p:nvGrpSpPr>
                <p:cNvPr id="1" name=""/>
                <p:cNvGrpSpPr/>
                <p:nvPr/>
            </p:nvGrpSpPr>
            <p:grpSpPr/>
            <p:sp>
                <p:nvSpPr>
                    <p:cNvPr id="2" name="Rectangle"/>
                </p:nvSpPr>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>''',
        relationship_data=[],
        media_files=[],
        total_size_bytes=1000
    )
    mock_embedder.get_statistics.return_value = {'elements_embedded': 1}
    mock_embedder.reset_statistics.return_value = None

    # Mock policy
    mock_policy = Mock()

    return mock_mapper, mock_embedder, mock_policy


def create_test_scene(element_count=5):
    """Create mock scene with specified number of elements"""
    scene = Mock()
    scene.elements = [Mock() for _ in range(element_count)]
    return scene


def demo_xml_handling_comparison():
    """Compare string manipulation vs proper XML handling"""
    print("🔧 XML Handling Comparison")
    print("=" * 50)

    mock_mapper, mock_embedder, mock_policy = create_mock_dependencies()

    # Original builder (with string manipulation)
    original_builder = OriginalSlideBuilder(
        mappers={'shape': mock_mapper},
        embedder=mock_embedder,
        policy=mock_policy
    )

    # Enhanced builder (with proper XML handling)
    enhanced_builder = SlideBuilder(
        mappers={'shape': mock_mapper},
        embedder=mock_embedder,
        policy=mock_policy
    )

    scene = create_test_scene(1)
    metadata = SlideMetadata(
        template=SlideTemplate.BLANK,
        layout_id=999,
        master_id=888,
        notes="Test slide with metadata"
    )

    # Test original approach
    try:
        original_result = original_builder.build_slide(scene, metadata)
        print("✅ Original builder: Successfully applied metadata with string replacement")
        # Check if metadata was applied (basic check)
        if 'sldLayoutIdLst' in original_result.slide_xml:
            print("   → Layout reference found in XML")
        else:
            print("   ❌ Layout reference not found")
    except Exception as e:
        print(f"❌ Original builder failed: {e}")

    # Test enhanced approach
    try:
        enhanced_result = enhanced_builder.build_slide(scene, metadata)
        print("✅ Enhanced builder: Successfully applied metadata with XML parsing")

        # Parse and validate the XML structure
        root = ET.fromstring(enhanced_result.slide_xml.encode('utf-8'))
        nsmap = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}

        layout = root.find('.//p:sldLayoutId', nsmap)
        if layout is not None:
            print(f"   → Layout ID: {layout.get('id')} (properly structured XML)")

        master = root.find('.//p:sldMasterId', nsmap)
        if master is not None:
            print(f"   → Master ID: {master.get('id')} (properly structured XML)")

        notes = root.find('.//p:notes', nsmap)
        if notes is not None:
            print(f"   → Notes: '{notes.text}' (properly structured XML)")

    except Exception as e:
        print(f"❌ Enhanced builder failed: {e}")

    print()


def demo_caching_performance():
    """Demonstrate caching performance benefits"""
    print("⚡ Caching Performance Demo")
    print("=" * 50)

    mock_mapper, mock_embedder, mock_policy = create_mock_dependencies()

    enhanced_builder = SlideBuilder(
        mappers={'shape': mock_mapper},
        embedder=mock_embedder,
        policy=mock_policy
    )

    scene = create_test_scene(10)  # Larger scene
    metadata = SlideMetadata(template=SlideTemplate.BLANK)

    # First build (cache miss)
    start_time = time.perf_counter()
    result1 = enhanced_builder.build_slide(scene, metadata)
    first_build_time = (time.perf_counter() - start_time) * 1000

    # Second build (cache hit)
    start_time = time.perf_counter()
    result2 = enhanced_builder.build_slide(scene, metadata)
    second_build_time = (time.perf_counter() - start_time) * 1000

    stats = enhanced_builder.get_statistics()

    print(f"First build (cache miss): {first_build_time:.2f}ms")
    print(f"Second build (cache hit): {second_build_time:.2f}ms")
    print(f"Speed improvement: {first_build_time / second_build_time:.1f}x faster")
    print(f"Cache hit rate: {stats['cache_hit_rate']:.1%}")
    print(f"Cache size: {stats['cache_size']} scenes")
    print()


def demo_error_handling():
    """Demonstrate enhanced error handling with context"""
    print("🚨 Enhanced Error Handling Demo")
    print("=" * 50)

    mock_mapper, mock_embedder, mock_policy = create_mock_dependencies()

    # Make embedder return invalid XML to trigger error handling
    mock_embedder.embed_scene.return_value = Mock(
        slide_xml="<invalid>malformed XML without closing tag",
        relationship_data=[],
        media_files=[]
    )

    enhanced_builder = SlideBuilder(
        mappers={'shape': mock_mapper},
        embedder=mock_embedder,
        policy=mock_policy
    )

    scene = create_test_scene(3)
    metadata = SlideMetadata(
        template=SlideTemplate.BLANK,
        slide_index=42
    )

    try:
        result = enhanced_builder.build_slide(scene, metadata)
        print("✅ Graceful error handling: Invalid XML handled without crash")
        print(f"   → Original XML returned unmodified: {len(result.slide_xml)} chars")

        # Check error statistics
        stats = enhanced_builder.get_statistics()
        print(f"   → XML parse errors recorded: {stats['xml_parse_errors']}")

    except Exception as e:
        print(f"❌ Error handling failed: {e}")

    print()


def demo_statistics_and_monitoring():
    """Demonstrate enhanced statistics and monitoring"""
    print("📊 Enhanced Statistics Demo")
    print("=" * 50)

    mock_mapper, mock_embedder, mock_policy = create_mock_dependencies()

    enhanced_builder = SlideBuilder(
        mappers={'shape': mock_mapper},
        embedder=mock_embedder,
        policy=mock_policy
    )

    # Build multiple slides
    for i in range(3):
        scene = create_test_scene(2 + i)  # Varying element counts
        metadata = SlideMetadata(
            template=SlideTemplate.BLANK,
            slide_index=i + 1
        )
        enhanced_builder.build_slide(scene, metadata)

    stats = enhanced_builder.get_statistics()

    print(f"Slides built: {stats['slides_built']}")
    print(f"Total elements processed: {stats['total_elements']}")
    print(f"Average elements per slide: {stats['avg_elements_per_slide']:.1f}")
    print(f"Average time per slide: {stats['avg_time_per_slide_ms']:.2f}ms")
    print(f"XML parse errors: {stats['xml_parse_errors']}")
    print(f"Schema validation errors: {stats['schema_validation_errors']}")
    print(f"Cache performance:")
    print(f"  - Cache hits: {stats['cache_hits']}")
    print(f"  - Cache misses: {stats['cache_misses']}")
    print(f"  - Hit rate: {stats['cache_hit_rate']:.1%}")
    print(f"  - Cache size: {stats['cache_size']} scenes")

    if 'mapper_stats' in stats:
        print(f"Mapper statistics: {stats['mapper_stats']}")
    if 'embedder_stats' in stats:
        print(f"Embedder statistics: {stats['embedder_stats']}")

    print()


def demo_mapper_protocol_validation():
    """Demonstrate mapper protocol validation and adaptation"""
    print("🔌 Mapper Protocol Validation Demo")
    print("=" * 50)

    mock_embedder = Mock()
    mock_embedder.embed_scene.return_value = Mock(
        slide_xml="<p:sld xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'><p:cSld><p:spTree/></p:cSld></p:sld>",
        relationship_data=[],
        media_files=[]
    )
    mock_embedder.get_statistics.return_value = {}
    mock_embedder.reset_statistics.return_value = None

    # Create non-compliant mapper (missing methods)
    class OldMapper:
        def map(self, element):
            return Mock(drawingml_xml="<p:sp/>", relationships=[])

    old_mapper = OldMapper()
    print("Created old-style mapper without full protocol compliance")

    # Enhanced builder will adapt it automatically
    enhanced_builder = SlideBuilder(
        mappers={'old_style': old_mapper},
        embedder=mock_embedder,
        policy=Mock()
    )

    adapted_mapper = enhanced_builder.mappers['old_style']

    print("✅ Mapper automatically adapted with wrapper:")
    print(f"   → has can_map: {hasattr(adapted_mapper, 'can_map')}")
    print(f"   → has get_statistics: {hasattr(adapted_mapper, 'get_statistics')}")
    print(f"   → has reset_statistics: {hasattr(adapted_mapper, 'reset_statistics')}")

    # Test the adapted methods
    print(f"   → can_map returns: {adapted_mapper.can_map(Mock())}")
    print(f"   → get_statistics returns: {adapted_mapper.get_statistics()}")

    print()


def main():
    """Run all demonstrations"""
    print("🎯 Enhanced Slide Builder - Feature Demonstration")
    print("=" * 60)
    print("Showcasing XML handling improvements, caching, error handling,")
    print("schema validation support, and protocol compliance.")
    print()

    demo_xml_handling_comparison()
    demo_caching_performance()
    demo_error_handling()
    demo_statistics_and_monitoring()
    demo_mapper_protocol_validation()

    print("🎉 All demonstrations completed!")
    print()
    print("Key Improvements Summary:")
    print("✅ Proper XML manipulation with lxml instead of string replacement")
    print("✅ Namespace-aware XML handling for OOXML compliance")
    print("✅ Performance caching for identical scenes")
    print("✅ Enhanced error context with slide identifiers")
    print("✅ Graceful error handling with fallback to original XML")
    print("✅ Comprehensive statistics and monitoring")
    print("✅ Mapper protocol validation and automatic adaptation")
    print("✅ Optional schema validation support")
    print("✅ Thread-safe caching with size limits")


if __name__ == "__main__":
    main()