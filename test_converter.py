#!/usr/bin/env python3
"""
Test the SVG to DrawingML converter without PowerPoint dependencies.
"""

from src.svg2drawingml import SVGToDrawingMLConverter

def main():
    print("=== SVG to DrawingML Converter Test ===\n")
    
    # Test with example SVG
    converter = SVGToDrawingMLConverter()
    
    try:
        print("Converting examples/input.svg...")
        result = converter.convert_file('examples/input.svg')
        
        # Count shapes
        rectangles = result.count('<p:sp>')
        lines = result.count('<p:cxnSp>')
        paths = result.count('SVG Path:')
        
        print(f"✓ Conversion successful!")
        print(f"  - Found {rectangles} filled shapes")
        print(f"  - Found {lines} lines/connectors") 
        print(f"  - Found {paths} path elements")
        print(f"  - Generated {len(result)} characters of DrawingML")
        
        # Save DrawingML output for inspection
        with open('drawingml_output.xml', 'w') as f:
            f.write(result)
        print(f"  - Saved DrawingML to drawingml_output.xml")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test with simple shapes
    print("\n=== Testing Simple Shapes ===")
    
    simple_svg = '''<?xml version="1.0"?>
    <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="50" height="30" fill="red" stroke="black"/>
        <circle cx="100" cy="100" r="25" fill="green"/>
        <line x1="20" y1="150" x2="180" y2="150" stroke="blue" stroke-width="3"/>
    </svg>'''
    
    result = converter.convert(simple_svg)
    print(f"✓ Simple shapes converted: {len(result)} chars")
    
    print("\n=== DrawingML Output Sample ===")
    print(result[:800] + "..." if len(result) > 800 else result)

if __name__ == "__main__":
    main()