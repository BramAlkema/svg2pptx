#!/usr/bin/env python3
"""
Test gradient support in SVG to DrawingML converter.
"""

from src.svg2drawingml import SVGToDrawingMLConverter

def test_gradient_conversion():
    """Test that gradients are properly parsed and converted."""
    
    # Simple gradient test SVG
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
    
    converter = SVGToDrawingMLConverter()
    
    # Test gradient parsing
    from src.svg2drawingml import SVGParser
    parser = SVGParser(gradient_svg)
    gradients = parser.gradients
    
    print("=== Gradient Detection Test ===")
    print(f"Gradients found: {len(gradients)}")
    
    for grad_id, grad_data in gradients.items():
        print(f"  {grad_id}: {grad_data['type']} gradient with {len(grad_data['stops'])} stops")
        for i, stop in enumerate(grad_data['stops']):
            print(f"    Stop {i+1}: {stop['offset']} -> {stop['color']} (opacity: {stop['opacity']})")
    
    # Test full conversion
    print("\n=== Full DrawingML Conversion ===")
    drawingml = converter.convert(gradient_svg)
    
    # Check that gradients appear in the output
    has_gradient_fill = '<a:gradFill' in drawingml
    has_linear = '<a:lin ang=' in drawingml  
    has_radial = '<a:path path="circle">' in drawingml
    
    print(f"✓ Gradient fills generated: {has_gradient_fill}")
    print(f"✓ Linear gradient found: {has_linear}")
    print(f"✓ Radial gradient found: {has_radial}")
    
    if has_gradient_fill and has_linear and has_radial:
        print("\n🎨 Gradient support is working perfectly!")
        print("LibreOffice-killer gradients are now supported!")
        return True
    else:
        print("\n⚠️  Some gradient features missing")
        return False

def show_sample_output():
    """Show sample DrawingML gradient output."""
    gradient_svg = '''<?xml version="1.0"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:rgb(255,255,0);stop-opacity:1" />
            <stop offset="100%" style="stop-color:rgb(255,0,0);stop-opacity:1" />
        </linearGradient>
    </defs>
    <rect x="50" y="50" width="150" height="100" fill="url(#grad1)"/>
</svg>'''
    
    converter = SVGToDrawingMLConverter()
    drawingml = converter.convert(gradient_svg)
    
    print("\n=== Sample DrawingML Gradient Output ===")
    print(drawingml)

if __name__ == "__main__":
    success = test_gradient_conversion()
    
    if success:
        print("\n" + "="*50)
        show_sample_output()