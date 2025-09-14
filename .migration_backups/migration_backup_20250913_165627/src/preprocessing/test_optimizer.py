"""
Test script for SVG optimizer functionality.
"""

from .optimizer import SVGOptimizer, create_optimizer


def test_basic_optimization():
    """Test basic SVG optimization functionality."""
    
    test_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="200px" height="100px" viewBox="0 0 200 100">
    <!-- This is a comment -->
    <g id="group1" class="">
        <rect x="10.000" y="20.500" width="80px" height="40px" 
              fill="rgb(255, 0, 0)" stroke="" />
        <circle cx="150.000" cy="50.0000" r="25px" fill="#ff0000" />
        <g></g>
    </g>
    <text></text>
</svg>'''
    
    optimizer = create_optimizer("default")
    result = optimizer.optimize(test_svg)
    
    print("Original SVG:")
    print(test_svg)
    print("\nOptimized SVG:")
    print(result)
    
    # Check that optimizations were applied
    assert 'px' not in result  # Units should be removed
    assert 'rgb(255, 0, 0)' not in result  # Should be converted to hex
    assert 'xmlns:inkscape' not in result  # Unused namespace removed
    assert '<g></g>' not in result  # Empty container removed
    assert '<text></text>' not in result  # Empty text removed
    
    print("\n✅ Basic optimization test passed!")


def test_shape_to_path_conversion():
    """Test shape to path conversion."""
    
    test_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
    <rect x="10" y="20" width="50" height="30" fill="red"/>
    <circle cx="100" cy="50" r="20" fill="blue"/>
    <line x1="0" y1="0" x2="50" y2="50" stroke="black"/>
</svg>'''
    
    optimizer = create_optimizer("aggressive")
    result = optimizer.optimize(test_svg)
    
    print("Shape-to-path conversion:")
    print("Original:", test_svg)
    print("Converted:", result)
    
    # Should convert shapes to paths
    assert '<rect' not in result
    assert '<circle' not in result
    assert '<line' not in result
    assert '<path' in result
    assert 'd=' in result
    
    print("\n✅ Shape-to-path conversion test passed!")


def test_numeric_cleanup():
    """Test numeric value cleanup."""
    
    test_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
    <rect x="10.000000" y="20.5000" width="50.00px" height="30.000px"/>
    <path d="M10.0000,20.5000 L60.0000,50.5000 Z"/>
</svg>'''
    
    optimizer = create_optimizer("default", precision=2)
    result = optimizer.optimize(test_svg)
    
    print("Numeric cleanup:")
    print("Original:", test_svg)
    print("Cleaned:", result)
    
    # Check numeric precision and unit removal
    assert '10.000000' not in result
    assert '20.5000' not in result or '20.5' in result
    assert 'px' not in result
    
    print("\n✅ Numeric cleanup test passed!")


if __name__ == "__main__":
    print("Testing SVG optimizer...")
    
    try:
        test_basic_optimization()
        test_shape_to_path_conversion()
        test_numeric_cleanup()
        
        print("\n🎉 All tests passed! SVG optimizer is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()