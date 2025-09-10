# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/2025-09-10-converter-extension/spec.md

> Created: 2025-09-10
> Version: 1.0.0

## Test Coverage Requirements

### 1. Shape Converter Extension Tests

#### LineConverter Enhancement Tests
```python
class TestLineConverterEnhancements(unittest.TestCase):
    """Test enhanced line converter functionality."""
    
    def test_basic_line_conversion(self):
        """Test basic line element conversion to connection shape."""
        svg = '<line x1="0" y1="0" x2="100" y2="100" stroke="black" stroke-width="2"/>'
        # Verify generates <p:cxnSp> with correct coordinates
        
    def test_line_with_transforms(self):
        """Test line conversion with transform attributes."""
        svg = '<line x1="0" y1="0" x2="50" y2="50" transform="rotate(45)" stroke="red"/>'
        # Verify transform integration with universal TransformParser
        
    def test_line_coordinate_systems(self):
        """Test line conversion in different coordinate systems."""
        # Test with different viewbox configurations
        # Verify EMU conversion accuracy
        
    def test_line_styling(self):
        """Test line with various stroke styles."""
        # Test stroke-width, stroke-opacity, stroke-dasharray
        # Verify integration with universal ColorParser
        
    def test_zero_length_lines(self):
        """Test handling of zero-length lines."""
        svg = '<line x1="50" y1="50" x2="50" y2="50"/>'
        # Should handle gracefully or provide meaningful comment
```

#### PolygonConverter/PolylineConverter Tests
```python
class TestPolygonConverterEnhancements(unittest.TestCase):
    """Test enhanced polygon/polyline converter functionality."""
    
    def test_complex_polygon_paths(self):
        """Test complex polygon with many points."""
        points = "0,0 100,0 100,100 50,150 0,100"
        svg = f'<polygon points="{points}" fill="blue" stroke="black"/>'
        # Verify custom geometry generation
        
    def test_polyline_conversion(self):
        """Test polyline conversion (no auto-close)."""
        points = "0,0 50,25 100,0 150,25 200,0"
        svg = f'<polyline points="{points}" fill="none" stroke="green"/>'
        # Verify path doesn't close automatically
        
    def test_points_parsing_edge_cases(self):
        """Test various points string formats."""
        # Test comma-separated, space-separated, mixed formats
        # Test malformed points strings
        
    def test_polygon_with_units(self):
        """Test polygon with various unit types."""
        # Test points with units (px, em, %, etc.)
        # Verify integration with UnitConverter
```

### 2. New Converter Tests

#### ImageConverter Tests
```python
class TestImageConverter(unittest.TestCase):
    """Test SVG image element conversion."""
    
    def setUp(self):
        self.converter = ImageConverter()
        self.context = ConversionContext()
        
    def test_can_convert(self):
        """Test image element detection."""
        image_element = ET.fromstring('<image href="test.png" x="0" y="0" width="100" height="100"/>')
        self.assertTrue(self.converter.can_convert(image_element))
        
    def test_external_image_reference(self):
        """Test conversion of external image reference."""
        svg = '<image href="https://example.com/image.png" x="10" y="20" width="200" height="150"/>'
        # Mock image loading, verify DrawingML output
        
    def test_base64_embedded_image(self):
        """Test conversion of base64 embedded image."""
        base64_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        svg = f'<image href="{base64_data}" x="0" y="0" width="50" height="50"/>'
        # Verify base64 decoding and embedding
        
    def test_image_with_transforms(self):
        """Test image conversion with transform attributes."""
        svg = '<image href="test.jpg" x="0" y="0" width="100" height="100" transform="scale(2) rotate(45)"/>'
        # Verify transform integration
        
    def test_image_positioning(self):
        """Test image positioning and sizing."""
        svg = '<image href="test.png" x="25px" y="50%" width="10em" height="200"/>'
        # Verify unit conversion integration
        
    def test_invalid_image_source(self):
        """Test handling of invalid image sources."""
        svg = '<image href="nonexistent.png" x="0" y="0" width="100" height="100"/>'
        # Should handle gracefully with fallback or error comment
        
    def test_image_caching(self):
        """Test image caching for duplicate references."""
        # Multiple images with same href should reuse cached data
```

#### UseConverter Tests
```python
class TestUseConverter(unittest.TestCase):
    """Test SVG use element conversion."""
    
    def setUp(self):
        self.converter = UseConverter()
        self.context = ConversionContext()
        
    def test_can_convert(self):
        """Test use element detection."""
        use_element = ET.fromstring('<use href="#rect1" x="50" y="100"/>')
        self.assertTrue(self.converter.can_convert(use_element))
        
    def test_reference_resolution(self):
        """Test resolving references to other elements."""
        # Create SVG with defs and use
        svg = '''<svg>
            <defs>
                <rect id="rect1" width="100" height="50" fill="blue"/>
            </defs>
            <use href="#rect1" x="25" y="75"/>
        </svg>'''
        # Verify referenced element is found and converted
        
    def test_use_positioning(self):
        """Test use element x,y offset positioning."""
        # Verify positioning offsets are applied correctly
        
    def test_use_transforms(self):
        """Test use element with transform attributes."""
        svg = '<use href="#circle1" x="50" y="50" transform="scale(1.5)"/>'
        # Verify transform composition (use transform + positioning)
        
    def test_circular_reference_detection(self):
        """Test detection of circular references."""
        # Create circular reference: use1 -> symbol1 -> use2 -> symbol2 -> use1
        # Should detect and handle gracefully
        
    def test_nested_use_elements(self):
        """Test use elements referencing other use elements."""
        # Test deep reference chains
        
    def test_invalid_reference(self):
        """Test handling of invalid href references."""
        svg = '<use href="#nonexistent" x="0" y="0"/>'
        # Should handle gracefully
```

#### SymbolConverter Tests
```python
class TestSymbolConverter(unittest.TestCase):
    """Test SVG symbol element processing."""
    
    def test_can_convert(self):
        """Test symbol element detection."""
        symbol_element = ET.fromstring('<symbol id="icon1" viewBox="0 0 100 100"><rect width="100" height="100"/></symbol>')
        self.assertTrue(self.converter.can_convert(symbol_element))
        
    def test_symbol_storage(self):
        """Test symbol definition storage in context."""
        # Verify symbol is stored in context.symbols
        
    def test_symbol_viewbox_handling(self):
        """Test symbol viewBox attribute processing."""
        # Verify viewBox is preserved for later scaling calculations
        
    def test_nested_symbol_content(self):
        """Test processing of nested elements within symbols."""
        svg = '''<symbol id="complex" viewBox="0 0 200 200">
            <rect width="100" height="100" fill="red"/>
            <circle cx="150" cy="50" r="25" fill="blue"/>
        </symbol>'''
        # Verify nested elements are preserved
        
    def test_symbol_without_viewbox(self):
        """Test symbol without viewBox attribute."""
        # Should handle gracefully with default viewport
```

#### DefsConverter Tests
```python
class TestDefsConverter(unittest.TestCase):
    """Test SVG defs container processing."""
    
    def test_can_convert(self):
        """Test defs element detection."""
        defs_element = ET.fromstring('<defs><linearGradient id="grad1"/></defs>')
        self.assertTrue(self.converter.can_convert(defs_element))
        
    def test_child_definition_processing(self):
        """Test processing of child definition elements."""
        svg = '''<defs>
            <linearGradient id="grad1"/>
            <pattern id="pat1"/>
            <symbol id="sym1"/>
            <clipPath id="clip1"/>
        </defs>'''
        # Verify all child elements are processed by appropriate converters
        
    def test_nested_defs(self):
        """Test nested defs elements."""
        # Should handle defs within defs
        
    def test_defs_conversion_output(self):
        """Test that defs conversion returns empty string."""
        # Defs should not generate visible output
```

#### PatternConverter Tests
```python
class TestPatternConverter(unittest.TestCase):
    """Test SVG pattern element processing."""
    
    def test_can_convert(self):
        """Test pattern element detection."""
        pattern_element = ET.fromstring('<pattern id="dots" x="0" y="0" width="20" height="20"/>')
        self.assertTrue(self.converter.can_convert(pattern_element))
        
    def test_pattern_storage(self):
        """Test pattern definition storage."""
        # Verify pattern is stored in context.patterns
        
    def test_pattern_units_handling(self):
        """Test patternUnits and patternContentUnits."""
        # Test userSpaceOnUse vs objectBoundingBox
        
    def test_pattern_transforms(self):
        """Test pattern with patternTransform."""
        # Verify transform integration
        
    def test_pattern_fill_generation(self):
        """Test DrawingML pattern fill generation."""
        # Test conversion to PowerPoint pattern fills (with fallbacks)
        
    def test_complex_pattern_content(self):
        """Test pattern with complex nested content."""
        svg = '''<pattern id="complex" width="50" height="50">
            <rect width="25" height="25" fill="red"/>
            <circle cx="35" cy="35" r="10" fill="blue"/>
        </pattern>'''
```

#### ClipPathConverter Tests
```python
class TestClipPathConverter(unittest.TestCase):
    """Test SVG clipPath element processing."""
    
    def test_can_convert(self):
        """Test clipPath element detection."""
        clip_element = ET.fromstring('<clipPath id="clip1"><rect width="100" height="100"/></clipPath>')
        self.assertTrue(self.converter.can_convert(clip_element))
        
    def test_clip_path_storage(self):
        """Test clip path definition storage."""
        # Verify stored in context.clips
        
    def test_clip_path_units(self):
        """Test clipPathUnits attribute handling."""
        # Test userSpaceOnUse vs objectBoundingBox
        
    def test_clip_path_application(self):
        """Test applying clip paths to shapes."""
        # Test apply_clip_path method
        
    def test_complex_clip_paths(self):
        """Test complex clipping paths with multiple shapes."""
        svg = '''<clipPath id="complex">
            <rect width="100" height="100"/>
            <circle cx="50" cy="50" r="25"/>
        </clipPath>'''
        
    def test_clip_path_fallbacks(self):
        """Test fallback strategies for unsupported clipping."""
        # PowerPoint has limited clipping support
```

#### FilterConverter Tests
```python
class TestFilterConverter(unittest.TestCase):
    """Test SVG filter element processing."""
    
    def test_can_convert(self):
        """Test filter element detection."""
        filter_element = ET.fromstring('<filter id="blur"><feGaussianBlur stdDeviation="3"/></filter>')
        self.assertTrue(self.converter.can_convert(filter_element))
        
    def test_basic_filter_effects(self):
        """Test basic filter effects (blur, drop shadow)."""
        # Test supported effects that can map to PowerPoint
        
    def test_filter_fallbacks(self):
        """Test fallback strategies for unsupported filters."""
        # Most SVG filters don't have PowerPoint equivalents
        
    def test_filter_units_handling(self):
        """Test filterUnits and primitiveUnits."""
        
    def test_complex_filter_chains(self):
        """Test filters with multiple effect primitives."""
        svg = '''<filter id="complex">
            <feGaussianBlur stdDeviation="2"/>
            <feOffset dx="5" dy="5"/>
            <feColorMatrix type="matrix" values="0.3 0.3 0.3 0 0 0.3 0.3 0.3 0 0 0.3 0.3 0.3 0 0 0 0 0 1 0"/>
        </filter>'''
```

### 3. Integration Tests

#### Universal Utility Integration Tests
```python
class TestUtilityIntegration(unittest.TestCase):
    """Test converter integration with universal utilities."""
    
    def test_unit_converter_integration(self):
        """Test all converters use UnitConverter correctly."""
        # Test batch_convert_to_emu usage
        # Test various unit types (px, em, %, pt, etc.)
        
    def test_color_parser_integration(self):
        """Test all converters use ColorParser correctly."""
        # Test named colors, hex, rgb, hsl
        # Test color parsing in fill and stroke attributes
        
    def test_transform_parser_integration(self):
        """Test all converters use TransformParser correctly."""
        # Test matrix transforms, composite transforms
        # Test integration with element positioning
        
    def test_viewport_resolver_integration(self):
        """Test all converters handle viewport contexts correctly."""
        # Test different viewport configurations
        # Test percentage calculations
```

#### Context Storage Tests
```python
class TestContextExtensions(unittest.TestCase):
    """Test ConversionContext extensions."""
    
    def test_image_storage_and_retrieval(self):
        """Test image storage and retrieval in context."""
        
    def test_symbol_storage_and_resolution(self):
        """Test symbol storage and reference resolution."""
        
    def test_circular_reference_detection(self):
        """Test circular reference detection system."""
        
    def test_definition_cross_references(self):
        """Test cross-references between different definition types."""
        # Test patterns referencing symbols, etc.
```

#### Registry Integration Tests  
```python
class TestRegistryIntegration(unittest.TestCase):
    """Test converter registry integration."""
    
    def test_new_converter_registration(self):
        """Test registration of all new converters."""
        
    def test_converter_dispatch(self):
        """Test proper converter dispatch for new elements."""
        
    def test_converter_priority(self):
        """Test converter selection when multiple can handle element."""
        
    def test_fallback_behavior(self):
        """Test behavior when no converter found."""
```

### 4. Error Handling and Edge Case Tests

#### Error Handling Tests
```python
class TestErrorHandling(unittest.TestCase):
    """Test error handling across all converters."""
    
    def test_malformed_svg_handling(self):
        """Test handling of malformed SVG elements."""
        
    def test_missing_attributes(self):
        """Test handling of elements with missing required attributes."""
        
    def test_invalid_attribute_values(self):
        """Test handling of invalid attribute values."""
        
    def test_circular_reference_handling(self):
        """Test graceful handling of circular references."""
        
    def test_resource_loading_failures(self):
        """Test handling of failed external resource loading."""
```

#### Edge Case Tests
```python
class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def test_zero_dimension_elements(self):
        """Test elements with zero width/height."""
        
    def test_extremely_large_elements(self):
        """Test handling of very large coordinate values."""
        
    def test_negative_coordinates(self):
        """Test handling of negative coordinates."""
        
    def test_empty_elements(self):
        """Test handling of empty elements."""
        
    def test_deeply_nested_references(self):
        """Test very deep reference chains."""
```

### 5. Performance and Regression Tests

#### Performance Tests
```python
class TestPerformance(unittest.TestCase):
    """Test performance characteristics of new converters."""
    
    def test_large_svg_conversion(self):
        """Test conversion of large, complex SVG files."""
        
    def test_many_image_references(self):
        """Test performance with many image elements."""
        
    def test_deep_reference_chains(self):
        """Test performance with deep use/symbol references."""
        
    def test_memory_usage(self):
        """Test memory usage patterns."""
```

#### Regression Tests
```python
class TestRegression(unittest.TestCase):
    """Test that new converters don't break existing functionality."""
    
    def test_existing_converter_compatibility(self):
        """Test that existing converters still work correctly."""
        
    def test_backward_compatibility(self):
        """Test that existing SVG files still convert correctly."""
        
    def test_context_compatibility(self):
        """Test that ConversionContext extensions don't break existing usage."""
```

## Mocking Requirements

### External Dependencies
- **Image Loading**: Mock HTTP requests for external images
- **File System**: Mock file system access for local image files
- **Base64 Decoding**: Test both valid and invalid base64 data

### PowerPoint Integration
- **Image Embedding**: Mock PowerPoint image relationship creation
- **DrawingML Generation**: Validate XML structure without PowerPoint dependency

### Test Data Requirements
- Sample SVG files with various element combinations
- Test images in multiple formats (PNG, JPEG, SVG)
- Base64 encoded test images
- Malformed SVG samples for error testing

### Test Organization
```
tests/
├── unit/
│   ├── converters/
│   │   ├── test_image_converter.py
│   │   ├── test_use_converter.py
│   │   ├── test_symbol_converter.py
│   │   ├── test_defs_converter.py
│   │   ├── test_pattern_converter.py
│   │   ├── test_clippath_converter.py
│   │   └── test_filter_converter.py
│   ├── test_context_extensions.py
│   └── test_registry_integration.py
├── integration/
│   ├── test_utility_integration.py
│   └── test_converter_chains.py
├── performance/
│   └── test_converter_performance.py
└── fixtures/
    ├── svg/
    │   ├── images/
    │   ├── references/
    │   └── edge_cases/
    └── expected_outputs/
```

### Coverage Requirements
- **Minimum 90% code coverage** for all new converters
- **100% coverage** for error handling paths  
- **Integration test coverage** for all utility interactions
- **Edge case coverage** for malformed input handling