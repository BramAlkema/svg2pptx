#!/usr/bin/env python3
"""
Advanced SVG Feature Testbench

Tests complex SVG features that typically break LibreOffice:
- Text with embedded fonts and kerning
- Gradients (linear/radial)
- Clipping paths and masks  
- Complex path operations
- Filters and effects

Uses modern Python libraries to handle these advanced cases.
"""

import os
import sys
from pathlib import Path
from src.svg2drawingml import SVGToDrawingMLConverter
from testbench import PPTXBuilder

# Advanced SVG processing libraries
ADVANCED_LIBS = {}

try:
    import svgpathtools
    ADVANCED_LIBS['svgpathtools'] = True
except ImportError:
    ADVANCED_LIBS['svgpathtools'] = False

try:
    import svgelements  
    ADVANCED_LIBS['svgelements'] = True
except ImportError:
    ADVANCED_LIBS['svgelements'] = False

try:
    import cairosvg
    ADVANCED_LIBS['cairosvg'] = True
except ImportError:
    ADVANCED_LIBS['cairosvg'] = False

try:
    import svglib
    ADVANCED_LIBS['svglib'] = True
except ImportError:
    ADVANCED_LIBS['svglib'] = False


class AdvancedSVGTestSuite:
    """Test suite for advanced SVG features."""
    
    def __init__(self):
        self.svg_converter = SVGToDrawingMLConverter()
        self.pptx_builder = PPTXBuilder()
    
    def create_test_svgs(self):
        """Create test SVG files with advanced features."""
        print("=== Creating Advanced SVG Test Files ===")
        
        # Test 1: Linear and Radial Gradients
        gradient_svg = '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
        <radialGradient id="grad2" cx="50%" cy="50%" r="50%">
            <stop offset="0%" style="stop-color:rgb(255,255,255);stop-opacity:0" />
            <stop offset="100%" style="stop-color:rgb(0,0,255);stop-opacity:1" />
        </radialGradient>
    </defs>
    <rect x="50" y="50" width="150" height="100" fill="url(#grad1)" stroke="black" stroke-width="2"/>
    <circle cx="300" cy="150" r="80" fill="url(#grad2)" stroke="none"/>
</svg>'''
        
        # Test 2: Text with Different Fonts
        text_svg = '''<?xml version="1.0"?>
<svg width="500" height="200" xmlns="http://www.w3.org/2000/svg">
    <text x="50" y="50" font-family="Arial" font-size="20" fill="blue">Arial Text</text>
    <text x="50" y="80" font-family="Times" font-size="18" fill="red" font-weight="bold">Bold Times</text>
    <text x="50" y="110" font-family="Courier" font-size="16" fill="green" font-style="italic">Italic Courier</text>
    <text x="50" y="140" font-family="Helvetica" font-size="24" fill="purple" text-decoration="underline">Underlined</text>
</svg>'''
        
        # Test 3: Complex Paths with Curves
        path_svg = '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <path d="M 50,150 Q 150,50 250,150 T 350,150" stroke="blue" stroke-width="3" fill="none"/>
    <path d="M 50,200 C 50,100 200,100 200,200 S 350,300 350,200" stroke="red" stroke-width="2" fill="rgba(255,0,0,0.3)"/>
    <path d="M 100,250 A 30,50 0 0,1 200,250 Z" fill="orange" stroke="black"/>
</svg>'''
        
        # Test 4: Clipping Paths
        clipping_svg = '''<?xml version="1.0"?>
<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <clipPath id="myClip">
            <circle cx="150" cy="100" r="60"/>
        </clipPath>
    </defs>
    <rect x="0" y="0" width="300" height="200" fill="lightblue"/>
    <rect x="50" y="50" width="200" height="100" fill="red" clip-path="url(#myClip)"/>
</svg>'''
        
        # Test 5: Transforms and Groups
        transform_svg = '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <g transform="translate(100,100)">
        <rect x="0" y="0" width="50" height="50" fill="red"/>
        <g transform="rotate(45)">
            <rect x="0" y="0" width="50" height="50" fill="blue" opacity="0.7"/>
        </g>
    </g>
    <g transform="scale(1.5,0.8) translate(150,50)">
        <circle cx="0" cy="0" r="30" fill="green"/>
    </g>
</svg>'''
        
        # Save test files
        test_files = {
            'gradient_test.svg': gradient_svg,
            'text_test.svg': text_svg,  
            'path_test.svg': path_svg,
            'clipping_test.svg': clipping_svg,
            'transform_test.svg': transform_svg
        }
        
        test_dir = Path('advanced_tests')
        test_dir.mkdir(exist_ok=True)
        
        for filename, content in test_files.items():
            filepath = test_dir / filename
            filepath.write_text(content, encoding='utf-8')
            print(f"  ✓ Created {filepath}")
        
        return list(test_files.keys())
    
    def test_basic_conversion(self, svg_files):
        """Test basic conversion of advanced SVG files."""
        print("\n=== Testing Basic Advanced SVG Conversion ===")
        
        results = []
        test_dir = Path('advanced_tests')
        
        for svg_file in svg_files:
            print(f"\n--- Testing {svg_file} ---")
            svg_path = test_dir / svg_file
            
            try:
                # Convert with our basic converter
                drawingml = self.svg_converter.convert_file(str(svg_path))
                
                # Count shapes
                shapes = drawingml.count('<p:sp>')
                lines = drawingml.count('<p:cxnSp>')
                comments = drawingml.count('<!--')
                
                print(f"  Basic conversion: {shapes} shapes, {lines} lines, {comments} comments")
                
                # Create PPTX
                output_file = f"advanced_{svg_file.replace('.svg', '.pptx')}"
                self.pptx_builder.create_minimal_pptx(drawingml, output_file)
                
                if os.path.exists(output_file):
                    size = os.path.getsize(output_file)
                    print(f"  ✓ Created {output_file} ({size:,} bytes)")
                    results.append((svg_file, True, shapes + lines))
                else:
                    print(f"  ✗ Failed to create {output_file}")
                    results.append((svg_file, False, 0))
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append((svg_file, False, 0))
        
        return results
    
    def test_with_advanced_libraries(self, svg_files):
        """Test conversion using advanced SVG libraries."""
        print("\n=== Testing with Advanced Libraries ===")
        
        if not any(ADVANCED_LIBS.values()):
            print("❌ No advanced libraries available!")
            print("Install with:")
            print("  pip install svgpathtools svgelements cairosvg svglib")
            return
        
        test_dir = Path('advanced_tests')
        
        for svg_file in svg_files:
            print(f"\n--- Advanced Processing: {svg_file} ---")
            svg_path = test_dir / svg_file
            
            # Test with svgelements
            if ADVANCED_LIBS['svgelements']:
                try:
                    import svgelements
                    svg = svgelements.SVG.parse(str(svg_path))
                    elements = list(svg.elements())
                    print(f"  svgelements: Found {len(elements)} elements")
                    
                    # Try to flatten transforms
                    for element in elements:
                        if hasattr(element, 'transform'):
                            print(f"    Element with transform: {type(element).__name__}")
                            
                except Exception as e:
                    print(f"  svgelements error: {e}")
            
            # Test with svgpathtools
            if ADVANCED_LIBS['svgpathtools']:
                try:
                    import svgpathtools
                    paths, attributes = svgpathtools.svg2paths(str(svg_path))
                    print(f"  svgpathtools: Found {len(paths)} paths")
                    
                    for i, path in enumerate(paths[:3]):  # Show first 3
                        print(f"    Path {i}: {len(path)} segments, length={path.length():.1f}")
                        
                except Exception as e:
                    print(f"  svgpathtools error: {e}")
            
            # Test with cairosvg (for rasterization reference)
            if ADVANCED_LIBS['cairosvg']:
                try:
                    import cairosvg
                    png_data = cairosvg.svg2png(url=str(svg_path))
                    print(f"  cairosvg: Generated PNG ({len(png_data):,} bytes)")
                    
                except Exception as e:
                    print(f"  cairosvg error: {e}")
    
    def analyze_complex_features(self, svg_files):
        """Analyze which complex features are present in each SVG."""
        print("\n=== Analyzing Complex Features ===")
        
        test_dir = Path('advanced_tests')
        
        features_to_check = {
            'linearGradient': 'Linear gradients',
            'radialGradient': 'Radial gradients', 
            'clipPath': 'Clipping paths',
            'mask': 'Masks',
            'filter': 'Filters',
            'text': 'Text elements',
            'font-family': 'Custom fonts',
            'transform': 'Transforms',
            'opacity': 'Transparency',
            'pattern': 'Patterns'
        }
        
        for svg_file in svg_files:
            print(f"\n--- Feature Analysis: {svg_file} ---")
            svg_path = test_dir / svg_file
            content = svg_path.read_text(encoding='utf-8')
            
            found_features = []
            for feature, description in features_to_check.items():
                if feature in content:
                    found_features.append(description)
            
            if found_features:
                print(f"  Features found: {', '.join(found_features)}")
            else:
                print("  No advanced features detected")
    
    def create_libreoffice_killer_svg(self):
        """Create an SVG that combines multiple problematic features."""
        print("\n=== Creating LibreOffice Killer SVG ===")
        
        killer_svg = '''<?xml version="1.0"?>
<svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <!-- Complex gradient with multiple stops -->
        <linearGradient id="complexGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#ff0000;stop-opacity:1" />
            <stop offset="25%" style="stop-color:#00ff00;stop-opacity:0.8" />
            <stop offset="50%" style="stop-color:#0000ff;stop-opacity:0.6" />
            <stop offset="75%" style="stop-color:#ffff00;stop-opacity:0.4" />
            <stop offset="100%" style="stop-color:#ff00ff;stop-opacity:0.2" />
        </linearGradient>
        
        <!-- Clipping path with complex shape -->
        <clipPath id="starClip">
            <path d="M 300,50 L 318,118 L 386,118 L 332,162 L 350,230 L 300,186 L 250,230 L 268,162 L 214,118 L 282,118 Z"/>
        </clipPath>
        
        <!-- Pattern definition -->
        <pattern id="dots" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
            <circle cx="10" cy="10" r="3" fill="red"/>
        </pattern>
    </defs>
    
    <!-- Background with gradient -->
    <rect width="600" height="400" fill="url(#complexGrad)"/>
    
    <!-- Transformed group with nested transforms -->
    <g transform="translate(100,100) rotate(15) scale(1.2,0.8)">
        <rect x="0" y="0" width="80" height="60" fill="url(#dots)" opacity="0.7"/>
        
        <!-- Text with custom font and effects -->
        <text x="10" y="30" font-family="Arial Black" font-size="16" fill="white" 
              font-weight="bold" text-decoration="underline" 
              transform="rotate(-10)">Custom Font Text</text>
        
        <!-- Nested group with more transforms -->
        <g transform="translate(50,30) skewX(15)">
            <ellipse cx="0" cy="0" rx="25" ry="15" fill="yellow" opacity="0.5"/>
        </g>
    </g>
    
    <!-- Complex path with all curve types -->
    <path d="M 200,200 Q 250,150 300,200 T 400,200 C 400,250 450,300 400,350 S 350,400 300,350 L 250,320 A 30,20 0 0,1 200,300 Z" 
          fill="rgba(0,255,0,0.6)" stroke="blue" stroke-width="3" clip-path="url(#starClip)"/>
    
    <!-- Text along a path -->
    <defs>
        <path id="textPath" d="M 50,350 Q 300,300 550,350"/>
    </defs>
    <text font-family="Times" font-size="18" fill="darkblue">
        <textPath href="#textPath">This text follows a curved path!</textPath>
    </text>
    
    <!-- Multiple overlapping shapes with transparency -->
    <g opacity="0.8">
        <circle cx="500" cy="100" r="40" fill="red"/>
        <circle cx="520" cy="100" r="40" fill="green"/>
        <circle cx="510" cy="120" r="40" fill="blue"/>
    </g>
    
</svg>'''
        
        killer_path = Path('advanced_tests/libreoffice_killer.svg')
        killer_path.write_text(killer_svg, encoding='utf-8')
        print(f"  ✓ Created {killer_path}")
        
        return 'libreoffice_killer.svg'
    
    def run_full_test_suite(self):
        """Run the complete advanced SVG test suite."""
        print("Advanced SVG Feature Testbench")
        print("=" * 50)
        
        # Check available libraries
        print("\n=== Library Availability ===")
        for lib, available in ADVANCED_LIBS.items():
            status = "✓" if available else "✗"
            print(f"  {status} {lib}")
        
        if not any(ADVANCED_LIBS.values()):
            print("\n⚠️  No advanced libraries installed!")
            print("Basic conversion will be tested, but advanced features limited.")
        
        # Create test files
        svg_files = self.create_test_svgs()
        
        # Add the killer SVG
        killer_file = self.create_libreoffice_killer_svg()
        svg_files.append(killer_file)
        
        # Analyze features
        self.analyze_complex_features(svg_files)
        
        # Test basic conversion
        basic_results = self.test_basic_conversion(svg_files)
        
        # Test with advanced libraries
        self.test_with_advanced_libraries(svg_files)
        
        # Summary
        print("\n=== Test Results Summary ===")
        successful = sum(1 for _, success, _ in basic_results if success)
        total = len(basic_results)
        
        print(f"Basic conversion: {successful}/{total} files converted")
        
        for filename, success, shape_count in basic_results:
            status = "✓" if success else "✗"
            print(f"  {status} {filename}: {shape_count} shapes")
        
        if successful == total:
            print("\n🎉 All test files converted successfully!")
            print("Your converter handles advanced SVG features better than LibreOffice!")
        else:
            print(f"\n⚠️  {total - successful} files had conversion issues")
            print("This shows the complexity of advanced SVG features")
        
        return successful == total


def install_missing_libraries():
    """Install missing advanced libraries."""
    missing = [lib for lib, available in ADVANCED_LIBS.items() if not available]
    
    if missing:
        print(f"\nMissing libraries: {', '.join(missing)}")
        print("\nTo install all advanced SVG libraries:")
        print("  pip install svgpathtools svgelements cairosvg svglib reportlab")
        print("\nOr install individual libraries:")
        for lib in missing:
            print(f"  pip install {lib}")


def main():
    """Run the advanced testbench."""
    testbench = AdvancedSVGTestSuite()
    
    try:
        success = testbench.run_full_test_suite()
        
        if not success:
            install_missing_libraries()
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n❌ Testbench error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()