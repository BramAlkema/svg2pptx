#!/usr/bin/env python3
"""
Test script to verify which of the 20 critical bugs are still active.
"""

def test_unit_imports():
    """Test that unit/units functions can be imported."""
    try:
        from core.units import unit, units
        print("✅ unit/units import: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ unit/units import: FAILED - {e}")
        return False

def test_conversion_services():
    """Test ConversionServices creation."""
    try:
        from core.services.conversion_services import ConversionServices
        services = ConversionServices.create_default()
        print("✅ ConversionServices.create_default(): SUCCESS")
        return True
    except Exception as e:
        print(f"❌ ConversionServices.create_default(): FAILED - {e}")
        return False

def test_symbol_converter_import():
    """Test SymbolConverter imports and creation."""
    try:
        from src.converters.symbols import SymbolConverter
        from core.services.conversion_services import ConversionServices
        services = ConversionServices.create_default()
        converter = SymbolConverter(services)
        print("✅ SymbolConverter creation: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ SymbolConverter creation: FAILED - {e}")
        return False

def test_path_converter():
    """Test PathConverter creation."""
    try:
        from src.converters.paths import PathConverter
        from core.services.conversion_services import ConversionServices
        services = ConversionServices.create_default()
        converter = PathConverter(services)
        print("✅ PathConverter creation: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ PathConverter creation: FAILED - {e}")
        return False

def test_text_converter():
    """Test TextConverter creation."""
    try:
        from src.converters.text import TextConverter
        from core.services.conversion_services import ConversionServices
        services = ConversionServices.create_default()
        converter = TextConverter(services)
        print("✅ TextConverter creation: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ TextConverter creation: FAILED - {e}")
        return False

def test_enhanced_shape_converter():
    """Test EnhancedShapeConverter creation."""
    try:
        from src.converters.shapes.enhanced_converter import EnhancedShapeConverter
        from core.services.conversion_services import ConversionServices
        services = ConversionServices.create_default()
        converter = EnhancedShapeConverter(services)
        print("✅ EnhancedShapeConverter creation: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ EnhancedShapeConverter creation: FAILED - {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing Critical Converter Bugs...")
    print("=" * 50)

    tests = [
        test_unit_imports,
        test_conversion_services,
        test_symbol_converter_import,
        test_path_converter,
        test_text_converter,
        test_enhanced_shape_converter
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("=" * 50)
    print(f"🎯 Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All critical converter creation tests PASSED!")
    else:
        print(f"❌ {total - passed} tests FAILED - need immediate fixes")