#!/usr/bin/env python3
"""
Local Python Testbench for SVG to PPTX Direct Integration

Creates actual PPTX files by manually building the ZIP structure
and injecting DrawingML shapes directly into slide XML.
"""

import os
import zipfile
from pathlib import Path

from src.core.pptx_builder import PPTXBuilder
from src.svg2drawingml import SVGToDrawingMLConverter


# PPTXBuilder is now provided by ``src.core.pptx_builder`` for broader reuse.


class SVGToPPTXTestbench:
    """Complete testbench for SVG to PPTX conversion."""
    
    def __init__(self):
        self.svg_converter = SVGToDrawingMLConverter()
        self.pptx_builder = PPTXBuilder()
    
    def test_simple_conversion(self):
        """Test conversion with simple SVG shapes."""
        print("=== Testing Simple SVG to PPTX Conversion ===")
        
        simple_svg = '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <rect x="50" y="50" width="100" height="80" fill="#ff0000" stroke="#000000" stroke-width="2"/>
    <circle cx="250" cy="100" r="40" fill="#00ff00" stroke="#0000ff" stroke-width="3"/>
    <ellipse cx="150" cy="200" rx="60" ry="30" fill="#0000ff"/>
    <line x1="50" y1="250" x2="350" y2="250" stroke="#ff00ff" stroke-width="4"/>
</svg>'''
        
        # Convert SVG to DrawingML
        print("1. Converting SVG to DrawingML...")
        drawingml = self.svg_converter.convert(simple_svg)
        
        # Count shapes
        rectangles = drawingml.count('<p:sp>')
        lines = drawingml.count('<p:cxnSp>')
        print(f"   Generated {rectangles} shapes and {lines} lines")
        
        # Create PPTX
        print("2. Creating PPTX file...")
        output_file = "test_simple.pptx"
        self.pptx_builder.create_minimal_pptx(drawingml, output_file)
        
        # Verify file
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"   ✓ Created {output_file} ({size:,} bytes)")
            return True
        else:
            print(f"   ✗ Failed to create {output_file}")
            return False
    
    def test_file_conversion(self, svg_file: str):
        """Test conversion with an actual SVG file."""
        print(f"\n=== Testing File Conversion: {svg_file} ===")
        
        if not os.path.exists(svg_file):
            print(f"   ✗ SVG file not found: {svg_file}")
            return False
        
        try:
            # Convert SVG to DrawingML  
            print("1. Converting SVG file to DrawingML...")
            drawingml = self.svg_converter.convert_file(svg_file)
            
            # Count elements
            shapes = drawingml.count('<p:sp>')
            lines = drawingml.count('<p:cxnSp>')
            paths = drawingml.count('SVG Path:')
            print(f"   Found {shapes} shapes, {lines} lines, {paths} paths")
            
            # Create PPTX
            print("2. Creating PPTX file...")
            svg_name = Path(svg_file).stem
            output_file = f"test_{svg_name}.pptx"
            self.pptx_builder.create_minimal_pptx(drawingml, output_file)
            
            # Verify file
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"   ✓ Created {output_file} ({size:,} bytes)")
                return True
            else:
                print(f"   ✗ Failed to create {output_file}")
                return False
                
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False
    
    def validate_pptx_structure(self, pptx_file: str):
        """Validate the internal structure of generated PPTX."""
        print(f"\n=== Validating PPTX Structure: {pptx_file} ===")
        
        try:
            with zipfile.ZipFile(pptx_file, 'r') as zipf:
                files = zipf.namelist()
                
                # Check required files
                required_files = [
                    '[Content_Types].xml',
                    '_rels/.rels',
                    'ppt/presentation.xml',
                    'ppt/slides/slide1.xml'
                ]
                
                missing_files = []
                for req_file in required_files:
                    if req_file not in files:
                        missing_files.append(req_file)
                
                if missing_files:
                    print(f"   ✗ Missing required files: {missing_files}")
                    return False
                
                # Check slide content
                slide_content = zipf.read('ppt/slides/slide1.xml').decode('utf-8')
                if '<p:spTree>' in slide_content and '<p:sp>' in slide_content:
                    shape_count = slide_content.count('<p:sp>')
                    print(f"   ✓ Valid PPTX structure with {shape_count} shapes")
                    
                    # Show a sample of the slide XML
                    print("   Sample slide XML:")
                    lines = slide_content.split('\n')[:15]
                    for line in lines:
                        if line.strip():
                            print(f"     {line.strip()}")
                    print("     ...")
                    
                    return True
                else:
                    print("   ✗ Invalid slide structure - missing shapes")
                    return False
                    
        except Exception as e:
            print(f"   ✗ Error validating PPTX: {e}")
            return False
    
    def run_all_tests(self):
        """Run complete test suite."""
        print("SVG to PPTX Direct Integration Testbench")
        print("=" * 50)
        
        results = []
        
        # Test 1: Simple shapes
        results.append(self.test_simple_conversion())
        
        # Test 2: Example SVG file
        if os.path.exists('examples/input.svg'):
            results.append(self.test_file_conversion('examples/input.svg'))
        
        # Validation tests
        if os.path.exists('test_simple.pptx'):
            results.append(self.validate_pptx_structure('test_simple.pptx'))
        
        # Summary
        print(f"\n=== Test Results ===")
        passed = sum(results)
        total = len(results)
        print(f"Passed: {passed}/{total} tests")
        
        if passed == total:
            print("🎉 All tests passed! SVG to PPTX conversion is working!")
        else:
            print("❌ Some tests failed. Check the output above.")
        
        return passed == total


def main():
    """Run the testbench."""
    testbench = SVGToPPTXTestbench()
    success = testbench.run_all_tests()
    
    if success:
        print("\n✅ Testbench completed successfully!")
        print("You can now open the generated .pptx files in PowerPoint!")
    else:
        print("\n❌ Testbench had failures.")


if __name__ == "__main__":
    main()