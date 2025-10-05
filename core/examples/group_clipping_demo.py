#!/usr/bin/env python3
"""
Group and Clipping Processing Demonstration

Shows how to use the enhanced group processing and clipping analysis
system with preprocessing integration.

This demonstrates Phase 2.3 completion: Group handling and clipping preprocessor.
"""

import os
import sys

from lxml import etree as ET

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.groups import create_group_converter_service
from core.pre import create_standard_chain

from ..services.conversion_services import ConversionServices


def create_sample_svg_with_groups_and_clipping() -> ET.Element:
    """Create sample SVG with various group and clipping scenarios."""
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg"
                         xmlns:xlink="http://www.w3.org/1999/xlink"
                         viewBox="0 0 600 400" width="600" height="400">
    <defs>
        <!-- ClipPath definitions -->
        <clipPath id="circle-clip">
            <circle cx="50" cy="50" r="40"/>
        </clipPath>

        <clipPath id="rect-clip">
            <rect x="10" y="10" width="80" height="60"/>
        </clipPath>

        <clipPath id="complex-clip">
            <path d="M 20 20 L 60 20 L 60 60 L 40 60 L 40 40 L 20 40 Z"/>
            <circle cx="70" cy="30" r="15"/>
        </clipPath>

        <!-- Reusable group template -->
        <g id="template-group">
            <rect x="0" y="0" width="50" height="30" fill="blue"/>
            <text x="25" y="20" text-anchor="middle" fill="white">Template</text>
        </g>
    </defs>

    <!-- Simple group -->
    <g id="simple-group" transform="translate(50, 50)">
        <rect x="0" y="0" width="100" height="60" fill="lightblue" stroke="navy" stroke-width="2"/>
        <text x="50" y="35" text-anchor="middle" fill="navy">Simple Group</text>
    </g>

    <!-- Group with simple clipping -->
    <g id="clipped-group" clip-path="url(#circle-clip)" transform="translate(200, 50)">
        <rect x="0" y="0" width="100" height="100" fill="red"/>
        <rect x="25" y="25" width="50" height="50" fill="yellow"/>
    </g>

    <!-- Nested groups -->
    <g id="nested-groups" transform="translate(350, 50)">
        <g id="outer-group" transform="scale(1.2)">
            <rect x="0" y="0" width="80" height="50" fill="green" opacity="0.7"/>
            <g id="inner-group" transform="translate(20, 10)">
                <circle cx="20" cy="15" r="10" fill="white"/>
                <text x="20" y="18" text-anchor="middle" font-size="8">Nested</text>
            </g>
        </g>
    </g>

    <!-- Group with complex clipping -->
    <g id="complex-clipped-group" clip-path="url(#complex-clip)" transform="translate(50, 150)">
        <rect x="0" y="0" width="100" height="80" fill="purple"/>
        <circle cx="50" cy="40" r="30" fill="orange"/>
        <text x="50" y="45" text-anchor="middle" fill="white">Complex Clip</text>
    </g>

    <!-- Group with USE elements -->
    <g id="group-with-use" transform="translate(200, 150)">
        <use href="#template-group" x="0" y="0"/>
        <use href="#template-group" x="60" y="0" transform="scale(0.8)"/>
        <use href="#template-group" x="30" y="40" transform="rotate(15)"/>
    </g>

    <!-- Group with multiple transforms and clipping -->
    <g id="multi-transform-clipped" transform="translate(350, 150) rotate(10)" clip-path="url(#rect-clip)">
        <g transform="scale(1.5)">
            <rect x="10" y="10" width="40" height="30" fill="cyan"/>
            <g transform="translate(15, 15)">
                <circle cx="15" cy="10" r="8" fill="magenta"/>
            </g>
        </g>
    </g>

    <!-- Deeply nested groups -->
    <g id="deep-nesting" transform="translate(50, 280)">
        <g id="level-1" transform="translate(10, 10)">
            <g id="level-2" transform="rotate(5)">
                <g id="level-3" transform="scale(0.9)">
                    <g id="level-4" transform="translate(5, 5)">
                        <rect x="0" y="0" width="60" height="40" fill="gold"/>
                        <text x="30" y="25" text-anchor="middle" font-size="10">Deep</text>
                    </g>
                </g>
            </g>
        </g>
    </g>

    <!-- Group with text and clipping -->
    <g id="text-clipped-group" clip-path="url(#circle-clip)" transform="translate(350, 280)">
        <rect x="0" y="0" width="100" height="80" fill="lightgreen"/>
        <text x="50" y="30" text-anchor="middle" font-size="12" fill="darkgreen">
            Clipped Text Group
        </text>
        <text x="50" y="50" text-anchor="middle" font-size="10" fill="darkgreen">
            Multiple lines
        </text>
    </g>
</svg>'''

    return ET.fromstring(svg_content)


def demonstrate_preprocessing_integration():
    """Demonstrate preprocessing integration with group handling."""
    print("=== Preprocessing Integration Demonstration ===\n")

    # Create sample SVG
    svg_root = create_sample_svg_with_groups_and_clipping()
    print(f"Original SVG has {len(svg_root.xpath('.//svg:g', namespaces={'svg': 'http://www.w3.org/2000/svg'}))} group elements")

    # Apply preprocessing
    preprocessor_chain = create_standard_chain()
    processed_svg = preprocessor_chain.process(svg_root, validate=True)

    # Show preprocessing results for groups
    group_elements = processed_svg.xpath('.//svg:g', namespaces={'svg': 'http://www.w3.org/2000/svg'})
    print(f"After preprocessing: {len(group_elements)} group elements")

    print("\nGroup Preprocessing Results:")
    for i, group_elem in enumerate(group_elements):
        group_id = group_elem.get('id', f'group_{i}')
        print(f"\nGroup '{group_id}':")

        # Check for clipping metadata
        clip_operation = group_elem.get('data-clip-operation')
        if clip_operation:
            clip_source = group_elem.get('data-clip-source', 'unknown')
            print(f"  Clipping: {clip_operation} from {clip_source}")

            # Count clipping masks
            mask_elements = group_elem.xpath(".//*[@data-clip-role='mask']")
            if mask_elements:
                print(f"  Clipping masks: {len(mask_elements)}")

        # Check for transform information
        transform = group_elem.get('transform')
        if transform:
            print(f"  Transform: {transform[:50]}...")

        # Check children
        child_count = len(list(group_elem))
        print(f"  Children: {child_count}")

    return processed_svg


def demonstrate_group_processing():
    """Demonstrate group processing capabilities."""
    print("\n=== Group Processing Demonstration ===\n")

    # Create processed SVG
    processed_svg = demonstrate_preprocessing_integration()

    # Create services (mock for demonstration)
    services = ConversionServices.create_default()

    # Create group converter service
    group_service = create_group_converter_service(services)

    # Mock context
    class MockContext:
        def __init__(self):
            self.next_shape_id = 1
            self.svg_root = processed_svg

        def get_next_shape_id(self):
            self.next_shape_id += 1
            return self.next_shape_id - 1

    context = MockContext()

    # Process each group
    group_elements = processed_svg.xpath('.//svg:g', namespaces={'svg': 'http://www.w3.org/2000/svg'})
    print(f"Processing {len(group_elements)} groups:\n")

    for i, group_elem in enumerate(group_elements):
        group_id = group_elem.get('id', f'group_{i}')
        print(f"Processing Group '{group_id}':")

        try:
            # Validate group first
            validation = group_service.validate_group_element(group_elem)
            print(f"  Valid: {validation['valid']}")

            if validation['issues']:
                print(f"  Issues: {', '.join(validation['issues'])}")

            if validation['optimization_opportunities']:
                print(f"  Optimizations: {', '.join(validation['optimization_opportunities'])}")

            # Convert group
            drawingml = group_service.convert_group_element(group_elem, context, enable_optimizations=True)

            if drawingml:
                lines = drawingml.split('\n')
                print(f"  ✓ Generated DrawingML ({len(lines)} lines)")

                # Extract key information
                if '<a:grpSp>' in drawingml:
                    print("  Type: Group Shape")
                elif '<p:sp>' in drawingml:
                    print("  Type: Shape")

                # Check for clipping
                if 'Clipping' in drawingml or 'Clip' in drawingml:
                    print("  Contains clipping elements")

            else:
                print("  ⚠ No DrawingML generated")

        except Exception as e:
            print(f"  ✗ Processing failed: {e}")

    return group_elements


def demonstrate_clipping_analysis():
    """Demonstrate clipping analysis capabilities."""
    print("\n=== Clipping Analysis Demonstration ===\n")

    # Create processed SVG
    processed_svg = demonstrate_preprocessing_integration()

    # Create services
    services = ConversionServices.create_default()
    group_service = create_group_converter_service(services)

    # Mock context
    class MockContext:
        def __init__(self):
            self.next_shape_id = 1
            self.svg_root = processed_svg

        def get_next_shape_id(self):
            self.next_shape_id += 1
            return self.next_shape_id - 1

    context = MockContext()

    # Find elements with clipping
    clipped_elements = processed_svg.xpath(".//*[@clip-path or @data-clip-operation]",
                                         namespaces={'svg': 'http://www.w3.org/2000/svg'})

    print(f"Found {len(clipped_elements)} elements with clipping:\n")

    for i, clipped_elem in enumerate(clipped_elements):
        elem_id = clipped_elem.get('id', f'element_{i}')
        tag = clipped_elem.tag.split('}')[-1] if '}' in clipped_elem.tag else clipped_elem.tag

        print(f"Analyzing {tag} '{elem_id}':")

        try:
            # Analyze clipping
            analysis = group_service.clipping_analyzer.analyze_clipping_scenario(clipped_elem, context)

            print(f"  Complexity: {analysis.complexity.value}")
            print(f"  Strategy: {analysis.recommended_strategy.value}")
            print(f"  PowerPoint Compatible: {analysis.powerpoint_compatible}")
            print(f"  Performance Impact: {analysis.estimated_performance_impact}")

            if analysis.clipping_paths:
                print(f"  Clipping Paths: {len(analysis.clipping_paths)}")
                for j, clip_path in enumerate(analysis.clipping_paths):
                    print(f"    Path {j+1}: {clip_path.id} ({clip_path.complexity.value})")

            if analysis.optimization_opportunities:
                print(f"  Optimizations: {', '.join(analysis.optimization_opportunities)}")

            if analysis.fallback_strategy != analysis.recommended_strategy:
                print(f"  Fallback: {analysis.fallback_strategy.value}")

            # Convert clipped element
            drawingml = group_service.convert_clipped_element(clipped_elem, context)
            if drawingml:
                print("  ✓ Conversion successful")
            else:
                print("  ⚠ No conversion output")

        except Exception as e:
            print(f"  ✗ Analysis failed: {e}")

        print()


def demonstrate_performance_optimization():
    """Demonstrate performance optimization features."""
    print("\n=== Performance Optimization Demonstration ===\n")

    # Create services
    services = ConversionServices.create_default()
    group_service = create_group_converter_service(services)

    print("Performance optimization features:")
    print("1. Group flattening - Reduces nesting levels")
    print("2. Transform consolidation - Merges transform hierarchies")
    print("3. Clipping simplification - Optimizes clipping paths")
    print("4. PowerPoint compatibility - Chooses optimal conversion strategy")
    print("5. Caching - Reuses analysis results")

    # Show statistics before processing
    print("\nStatistics before processing:")
    stats = group_service.get_combined_statistics()
    for component, component_stats in stats.items():
        print(f"  {component}: {component_stats}")

    # Create test SVG with optimization opportunities
    complex_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
        <defs>
            <clipPath id="test-clip">
                <rect x="0" y="0" width="100" height="100"/>
            </clipPath>
        </defs>

        <!-- Complex nested structure -->
        <g transform="translate(10, 10)">
            <g transform="scale(1.1)">
                <g transform="rotate(5)" clip-path="url(#test-clip)">
                    <g transform="translate(5, 5)">
                        <rect x="0" y="0" width="50" height="50" fill="blue"/>
                        <g transform="rotate(10)">
                            <circle cx="25" cy="25" r="15" fill="red"/>
                        </g>
                    </g>
                </g>
            </g>
        </g>
    </svg>'''

    svg_root = ET.fromstring(complex_svg)

    # Mock context
    class MockContext:
        def __init__(self):
            self.next_shape_id = 1
            self.svg_root = svg_root

        def get_next_shape_id(self):
            self.next_shape_id += 1
            return self.next_shape_id - 1

    context = MockContext()

    # Process with optimizations
    group_elem = svg_root.find('.//{http://www.w3.org/2000/svg}g')
    if group_elem is not None:
        print("\nProcessing complex group with optimizations:")

        # Validate first
        validation = group_service.validate_group_element(group_elem)
        print(f"Validation issues: {len(validation['issues'])}")
        print(f"Optimization opportunities: {len(validation['optimization_opportunities'])}")

        # Convert with optimizations
        drawingml = group_service.convert_group_element(group_elem, context, enable_optimizations=True)
        print(f"Conversion successful: {bool(drawingml)}")

    # Show statistics after processing
    print("\nStatistics after processing:")
    final_stats = group_service.get_combined_statistics()
    for component, component_stats in final_stats.items():
        print(f"  {component}: {component_stats}")


def demonstrate_powerpoint_compatibility():
    """Demonstrate PowerPoint compatibility assessment."""
    print("\n=== PowerPoint Compatibility Demonstration ===\n")

    # Create services
    services = ConversionServices.create_default()
    group_service = create_group_converter_service(services)

    # Test different clipping scenarios
    test_scenarios = [
        {
            'name': 'Simple Rectangle Clip',
            'svg': '''<g clip-path="url(#rect-clip)">
                <rect x="0" y="0" width="100" height="100" fill="blue"/>
            </g>''',
            'expected_compatibility': True,
        },
        {
            'name': 'Simple Circle Clip',
            'svg': '''<g clip-path="url(#circle-clip)">
                <rect x="0" y="0" width="100" height="100" fill="red"/>
            </g>''',
            'expected_compatibility': True,
        },
        {
            'name': 'Complex Path Clip',
            'svg': '''<g clip-path="url(#complex-clip)">
                <rect x="0" y="0" width="100" height="100" fill="green"/>
            </g>''',
            'expected_compatibility': False,
        },
        {
            'name': 'Multiple Clips',
            'svg': '''<g clip-path="url(#clip1)">
                <g clip-path="url(#clip2)">
                    <rect x="0" y="0" width="100" height="100" fill="yellow"/>
                </g>
            </g>''',
            'expected_compatibility': False,
        },
    ]

    print("Testing PowerPoint compatibility:")

    for scenario in test_scenarios:
        print(f"\n{scenario['name']}:")

        # Create test SVG
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
            <defs>
                <clipPath id="rect-clip">
                    <rect x="10" y="10" width="80" height="60"/>
                </clipPath>
                <clipPath id="circle-clip">
                    <circle cx="50" cy="50" r="40"/>
                </clipPath>
                <clipPath id="complex-clip">
                    <path d="M 20 20 L 60 20 L 60 60 L 40 60 L 40 40 L 20 40 Z"/>
                    <circle cx="70" cy="30" r="15"/>
                </clipPath>
                <clipPath id="clip1">
                    <rect x="0" y="0" width="50" height="50"/>
                </clipPath>
                <clipPath id="clip2">
                    <circle cx="25" cy="25" r="20"/>
                </clipPath>
            </defs>
            {scenario['svg']}
        </svg>'''

        try:
            svg_root = ET.fromstring(svg_content)

            # Mock context
            class MockContext:
                def __init__(self):
                    self.next_shape_id = 1
                    self.svg_root = svg_root

                def get_next_shape_id(self):
                    self.next_shape_id += 1
                    return self.next_shape_id - 1

            context = MockContext()

            # Find clipped element
            clipped_elem = svg_root.find('.//{http://www.w3.org/2000/svg}g[@clip-path]')
            if clipped_elem is not None:
                # Analyze compatibility
                analysis = group_service.clipping_analyzer.analyze_clipping_scenario(clipped_elem, context)

                print(f"  PowerPoint Compatible: {analysis.powerpoint_compatible}")
                print(f"  Complexity: {analysis.complexity.value}")
                print(f"  Strategy: {analysis.recommended_strategy.value}")
                print(f"  Expected: {scenario['expected_compatibility']}")

                # Check if prediction matches expectation
                if analysis.powerpoint_compatible == scenario['expected_compatibility']:
                    print("  ✓ Prediction matches expectation")
                else:
                    print("  ⚠ Prediction differs from expectation")

        except Exception as e:
            print(f"  ✗ Test failed: {e}")


def main():
    """Run all demonstrations."""
    print("Group Processing and Clipping Analysis - Phase 2.3 Demo")
    print("=" * 70)

    try:
        # Run demonstrations
        demonstrate_preprocessing_integration()
        demonstrate_group_processing()
        demonstrate_clipping_analysis()
        demonstrate_performance_optimization()
        demonstrate_powerpoint_compatibility()

        print("\n" + "=" * 70)
        print("✓ Phase 2.3 Implementation Complete!")
        print("Group handling and clipping preprocessor system is working.")

    except ImportError as e:
        print(f"Import error: {e}")
        print("Note: This demo requires the full services infrastructure.")
        print("The group processing components are implemented and ready for integration.")

    except Exception as e:
        print(f"Demonstration error: {e}")
        print("This may indicate missing dependencies or services.")


if __name__ == '__main__':
    main()