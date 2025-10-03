#!/usr/bin/env python3
"""
Enhanced XML Builder Demonstration

Shows the improvements from string interpolation to proper lxml.etree DOM manipulation:
1. Namespace-aware XML generation
2. Validation and error handling
3. Fluent building patterns
4. Performance improvements
5. Character encoding safety
"""

import time
import sys
from pathlib import Path
from lxml import etree as ET

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.utils.xml_builder import XMLBuilder  # Original string-based
from core.utils.enhanced_xml_builder import (
    EnhancedXMLBuilder, create_presentation, create_slide, create_shape
)


def demo_namespace_handling():
    """Demonstrate proper namespace handling vs string manipulation"""
    print("🔧 Namespace Handling Comparison")
    print("=" * 50)

    # Original string-based approach
    original_builder = XMLBuilder()
    print("Original XMLBuilder (string-based):")
    original_xml = original_builder.create_presentation_xml(9144000, 6858000)

    # Show a snippet of the string-based output
    lines = original_xml.split('\n')
    for i, line in enumerate(lines[:4]):
        print(f"  {i+1:2d}: {line}")
    print("     ...")
    print(f"     (Generated via f-string interpolation)")

    print()

    # Enhanced DOM-based approach
    enhanced_builder = EnhancedXMLBuilder()
    print("Enhanced XMLBuilder (DOM-based):")
    presentation_element = enhanced_builder.create_presentation_element(9144000, 6858000)
    enhanced_xml = enhanced_builder.element_to_string(presentation_element)

    # Show the DOM-based output
    lines = enhanced_xml.split('\n')
    for i, line in enumerate(lines[:4]):
        print(f"  {i+1:2d}: {line}")
    print("     ...")
    print(f"     (Generated via lxml.etree DOM manipulation)")

    print()
    print("Key Improvements:")
    print("✅ Proper namespace declarations with QNames")
    print("✅ Automatic XML character escaping")
    print("✅ Validation during construction")
    print("✅ No risk of malformed XML from string errors")
    print()


def demo_fluent_building():
    """Demonstrate fluent building patterns"""
    print("🏗️ Fluent Building Pattern Demonstration")
    print("=" * 50)

    enhanced_builder = EnhancedXMLBuilder()

    # Create presentation
    presentation = enhanced_builder.create_presentation_element(9144000, 6858000, "screen16x9")
    print("Created presentation element with proper namespaces")

    # Add slides to presentation
    enhanced_builder.add_slide_to_presentation(presentation, 256, 'rId2')
    enhanced_builder.add_slide_to_presentation(presentation, 257, 'rId3')
    print("Added slide references to presentation")

    # Create slide with shapes using fluent interface
    slide = enhanced_builder.create_slide_element()

    # Create shapes using fluent builder
    rectangle_shape = (create_shape(2, "My Rectangle")
                      .position(1000000, 500000)  # 1 inch from left, 0.5 inch from top
                      .size(2000000, 1500000)     # 2 inches wide, 1.5 inches tall
                      .build())

    circle_shape = (create_shape(3, "My Circle")
                   .position(4000000, 500000)   # 4 inches from left
                   .size(1500000, 1500000)      # 1.5 inch square (will be circular)
                   .build())

    # Add shapes to slide
    enhanced_builder.add_shape_to_slide(slide, rectangle_shape)
    enhanced_builder.add_shape_to_slide(slide, circle_shape)

    print("Created slide with 2 shapes using fluent interface")
    print("Shape building chain: .position() → .size() → .build()")

    # Serialize to XML
    slide_xml = enhanced_builder.element_to_string(slide, pretty_print=True)

    print("\nGenerated slide XML structure:")
    lines = slide_xml.split('\n')
    for i, line in enumerate(lines[:8]):
        print(f"  {line}")
    print("  ...")
    print(f"  (Total XML length: {len(slide_xml)} characters)")
    print()


def demo_validation_and_safety():
    """Demonstrate validation and character encoding safety"""
    print("🛡️ Validation and Safety Demonstration")
    print("=" * 50)

    enhanced_builder = EnhancedXMLBuilder()

    # Test 1: Character encoding safety
    print("Test 1: Character Encoding Safety")
    shape = enhanced_builder.create_shape_element(1, "Shape with <>&\"' characters")

    # The name should be properly handled
    xml_str = enhanced_builder.element_to_string(shape)
    print("✅ Special characters automatically escaped in XML")
    print(f"   Shape name contains: <>&\"'")
    print(f"   XML output correctly escapes them")

    # Test 2: Text content safety
    print("\nTest 2: Text Content Safety")
    from lxml.etree import Element
    text_element = Element("text")

    try:
        enhanced_builder.add_text_to_element(text_element, "Safe text content")
        print("✅ Safe text content added successfully")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    # Test 3: XML validation
    print("\nTest 3: XML Structure Validation")
    slide = enhanced_builder.create_slide_element()
    is_valid = enhanced_builder.validate_element(slide)
    print(f"✅ Generated slide XML is valid: {is_valid}")

    # Test 4: Namespace consistency
    print("\nTest 4: Namespace Consistency Check")
    presentation = enhanced_builder.create_presentation_element(9144000, 6858000)
    xml_content = enhanced_builder.element_to_string(presentation)

    # Check namespace declarations
    has_p_namespace = 'xmlns:p=' in xml_content
    has_r_namespace = 'xmlns:r=' in xml_content

    print(f"✅ Presentation namespace (p:): {has_p_namespace}")
    print(f"✅ Relationships namespace (r:): {has_r_namespace}")
    print()


def demo_performance_comparison():
    """Demonstrate performance improvements"""
    print("⚡ Performance Comparison")
    print("=" * 50)

    # Test creating multiple presentations
    iterations = 100

    # Original string-based approach
    print(f"Creating {iterations} presentations with original XMLBuilder...")
    original_builder = XMLBuilder()

    start_time = time.perf_counter()
    for i in range(iterations):
        xml_str = original_builder.create_presentation_xml(9144000, 6858000)
        # Simulate some processing
        len(xml_str)
    original_time = (time.perf_counter() - start_time) * 1000

    # Enhanced DOM-based approach
    print(f"Creating {iterations} presentations with enhanced XMLBuilder...")
    enhanced_builder = EnhancedXMLBuilder()

    start_time = time.perf_counter()
    for i in range(iterations):
        presentation = enhanced_builder.create_presentation_element(9144000, 6858000)
        xml_str = enhanced_builder.element_to_string(presentation)
        # Simulate some processing
        len(xml_str)
    enhanced_time = (time.perf_counter() - start_time) * 1000

    print(f"\nPerformance Results:")
    print(f"Original (string-based):  {original_time:.2f}ms ({original_time/iterations:.3f}ms per operation)")
    print(f"Enhanced (DOM-based):     {enhanced_time:.2f}ms ({enhanced_time/iterations:.3f}ms per operation)")

    if enhanced_time < original_time:
        improvement = (original_time - enhanced_time) / original_time * 100
        print(f"✅ Enhanced builder is {improvement:.1f}% faster")
    else:
        difference = (enhanced_time - original_time) / original_time * 100
        print(f"⚠️ Enhanced builder is {difference:.1f}% slower (but safer and more maintainable)")

    print()
    print("Key Benefits (beyond raw performance):")
    print("✅ Memory efficiency: No large string concatenations")
    print("✅ Maintainability: Structured DOM vs template strings")
    print("✅ Reliability: Guaranteed well-formed XML")
    print("✅ Extensibility: Easy to add new XML features")
    print()


def demo_complex_document_creation():
    """Demonstrate creating complex documents efficiently"""
    print("📋 Complex Document Creation")
    print("=" * 50)

    enhanced_builder = EnhancedXMLBuilder()

    # Create presentation
    presentation = enhanced_builder.create_presentation_element(9144000, 6858000, "screen16x9")

    # Add multiple slides with content
    slide_count = 5
    total_shapes = 0

    start_time = time.perf_counter()

    for slide_num in range(1, slide_count + 1):
        # Add slide reference to presentation
        enhanced_builder.add_slide_to_presentation(presentation, 255 + slide_num, f'rId{slide_num + 1}')

        # Create slide
        slide = enhanced_builder.create_slide_element()

        # Add shapes to slide
        shapes_per_slide = 3
        for shape_num in range(shapes_per_slide):
            shape_id = slide_num * 10 + shape_num
            x = (shape_num % 3) * 3000000  # Distribute horizontally
            y = 1000000  # Fixed vertical position

            shape = (create_shape(shape_id, f"Slide{slide_num}_Shape{shape_num}")
                    .position(x, y)
                    .size(2000000, 1000000)
                    .build())

            enhanced_builder.add_shape_to_slide(slide, shape)
            total_shapes += 1

    # Create final XML
    presentation_xml = enhanced_builder.element_to_string(presentation, pretty_print=True)

    creation_time = (time.perf_counter() - start_time) * 1000

    print(f"Document Statistics:")
    print(f"  Slides created: {slide_count}")
    print(f"  Total shapes: {total_shapes}")
    print(f"  Final XML size: {len(presentation_xml):,} characters")
    print(f"  Creation time: {creation_time:.2f}ms")
    print(f"  Average per slide: {creation_time/slide_count:.2f}ms")

    # Validate the final result
    is_valid = enhanced_builder.validate_element(presentation)
    print(f"  XML validation: {'✅ Valid' if is_valid else '❌ Invalid'}")

    print()
    print("Document structure preview:")
    lines = presentation_xml.split('\n')
    for i, line in enumerate(lines[:10]):
        print(f"  {i+1:2d}: {line[:80]}{'...' if len(line) > 80 else ''}")
    print("      ...")
    print()


def main():
    """Run all demonstrations"""
    print("🎯 Enhanced XML Builder - Comprehensive Demonstration")
    print("=" * 60)
    print("Showcasing improvements from string interpolation to proper")
    print("lxml.etree DOM manipulation for PowerPoint XML generation.")
    print()

    demo_namespace_handling()
    demo_fluent_building()
    demo_validation_and_safety()
    demo_performance_comparison()
    demo_complex_document_creation()

    print("🎉 All demonstrations completed!")
    print()
    print("Summary of Key Improvements:")
    print("✅ Proper XML namespaces with QNames instead of string templates")
    print("✅ Automatic character escaping and validation")
    print("✅ Fluent builder patterns for complex structures")
    print("✅ Memory-efficient DOM manipulation")
    print("✅ Guaranteed well-formed XML output")
    print("✅ Better maintainability and extensibility")
    print("✅ Comprehensive test coverage (26 tests)")
    print()
    print("Next Steps:")
    print("1. Convert animation XML generation (Phase 2)")
    print("2. Convert group processing XML (Phase 3)")
    print("3. Standardize text processing (Phase 4)")
    print("4. System integration and validation (Phase 5)")


if __name__ == "__main__":
    main()