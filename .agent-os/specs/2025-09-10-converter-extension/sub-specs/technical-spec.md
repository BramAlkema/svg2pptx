# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-09-10-converter-extension/spec.md

> Created: 2025-09-10
> Version: 1.0.0

## Technical Requirements

### 1. Shape Converter Extensions

**Current State Analysis:**
- `shapes.py` contains: RectangleConverter, CircleConverter, EllipseConverter, PolygonConverter, LineConverter
- LineConverter exists but needs enhancement for proper line handling
- PolylineConverter is combined with PolygonConverter but may need separation

**Requirements:**
- Enhance LineConverter with proper connection shape handling (`<p:cxnSp>` vs `<p:sp>`)
- Improve coordinate system handling for line elements
- Add support for line markers (arrow heads, etc.) if missing
- Ensure all shape converters use the universal unit conversion system consistently

### 2. Missing Element Converters

**2.1 ImageConverter (`<image>` elements)**
```python
class ImageConverter(BaseConverter):
    supported_elements = ['image']
    
    # Requirements:
    # - Handle href/xlink:href attributes for image sources
    # - Support embedded base64 images (data: URLs)
    # - Support external image references
    # - Integrate with PowerPoint image embedding
    # - Handle x, y, width, height positioning
    # - Support transforms and clipping
```

**2.2 UseConverter (`<use>` elements)**
```python
class UseConverter(BaseConverter):
    supported_elements = ['use']
    
    # Requirements:
    # - Resolve href/xlink:href references to other elements
    # - Handle x, y positioning offsets
    # - Support transforms on the use element
    # - Recursively convert referenced elements
    # - Handle circular reference detection
```

**2.3 SymbolConverter (`<symbol>` elements)**
```python
class SymbolConverter(BaseConverter):
    supported_elements = ['symbol']
    
    # Requirements:
    # - Process symbol definitions (usually in <defs>)
    # - Handle viewBox attributes for symbol scaling
    # - Store symbol definitions in ConversionContext
    # - Support nested elements within symbols
```

**2.4 DefsConverter (`<defs>` elements)**
```python
class DefsConverter(BaseConverter):
    supported_elements = ['defs']
    
    # Requirements:
    # - Process all child elements as definitions
    # - Store definitions in ConversionContext (gradients, patterns, symbols, etc.)
    # - Don't render defs content directly
    # - Support nested defs elements
```

**2.5 PatternConverter (`<pattern>` elements)**
```python
class PatternConverter(BaseConverter):
    supported_elements = ['pattern']
    
    # Requirements:
    # - Store pattern definitions in context.patterns
    # - Handle patternUnits, patternContentUnits
    # - Support pattern transforms
    # - Generate DrawingML pattern fills (or solid color fallbacks)
    # - Handle x, y, width, height attributes
```

**2.6 ClipPathConverter (`<clipPath>` elements)**
```python
class ClipPathConverter(BaseConverter):
    supported_elements = ['clipPath']
    
    # Requirements:
    # - Store clipping path definitions in context.clips
    # - Handle clipPathUnits attribute
    # - Support path-based and shape-based clipping
    # - Generate PowerPoint masking (limited support, fallback strategies)
```

**2.7 FilterConverter (`<filter>` elements)**
```python
class FilterConverter(BaseConverter):
    supported_elements = ['filter']
    
    # Requirements:
    # - Basic filter effects support (drop shadows, blur)
    # - Fallback strategies for unsupported effects
    # - Store filter definitions in ConversionContext
    # - Handle filterUnits, primitiveUnits
```

### 3. Universal Utility Integration

**All new converters must integrate with existing utilities:**

**UnitConverter Integration:**
```python
# Use context.batch_convert_to_emu() for multiple values
dimensions = context.batch_convert_to_emu({
    'x': element.get('x', '0'),
    'y': element.get('y', '0'),
    'width': element.get('width', '0'),
    'height': element.get('height', '0')
})
```

**ColorParser Integration:**
```python
# Use self.parse_color() from BaseConverter
color = self.parse_color(element.get('fill', 'black'))
```

**TransformParser Integration:**
```python
# Use self.get_element_transform_matrix()
transform_matrix = self.get_element_transform_matrix(element, context.viewport_context)
```

**ViewportResolver Integration:**
```python
# Use context.viewport_context for viewport-aware calculations
viewport_context = context.viewport_context
```

### 4. ConversionContext Extensions

**Add new storage for additional element types:**
```python
class ConversionContext:
    def __init__(self, svg_root: Optional[ET.Element] = None):
        # Existing attributes...
        self.images: Dict[str, Dict] = {}         # Image definitions
        self.symbols: Dict[str, ET.Element] = {}  # Symbol definitions  
        self.uses: Dict[str, Any] = {}            # Use element tracking
        self.filters: Dict[str, Dict] = {}        # Filter definitions
        # patterns and clips already exist
```

### 5. Registry Integration

**All new converters must register properly:**
```python
# In __init__.py
from .images import ImageConverter
from .references import UseConverter, SymbolConverter, DefsConverter
from .effects import PatternConverter, ClipPathConverter, FilterConverter

# Registration should happen in main converter initialization
```

## Approach

### Phase 1: Foundation (Shape Extensions)
1. Enhance existing LineConverter implementation
2. Improve PolygonConverter/PolylineConverter integration
3. Add comprehensive test coverage for shape extensions

### Phase 2: Reference System (High Priority)
1. Implement DefsConverter first (foundation for other references)
2. Add SymbolConverter for symbol definitions
3. Implement UseConverter for element references
4. Create reference resolution system in ConversionContext

### Phase 3: Media Elements
1. Implement ImageConverter with PowerPoint image embedding
2. Handle base64 and external image references
3. Add image caching and optimization

### Phase 4: Advanced Features
1. Implement PatternConverter with fallback strategies
2. Add ClipPathConverter with limited PowerPoint masking
3. Create FilterConverter with basic effect support

### Implementation Strategy

**1. Converter Template:**
```python
class NewConverter(BaseConverter):
    """Converter for SVG <element> elements."""
    
    supported_elements = ['element']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        tag = self.get_element_tag(element)
        return tag == 'element'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG element to DrawingML."""
        # 1. Extract attributes using universal utilities
        # 2. Handle transforms and styles
        # 3. Generate DrawingML output
        # 4. Return properly formatted XML
```

**2. Error Handling Pattern:**
```python
try:
    # Conversion logic
    return drawingml_output
except Exception as e:
    self.logger.error(f"Error converting {element.tag}: {e}")
    return f"<!-- Error converting {element.tag}: {e} -->"
```

**3. Testing Pattern:**
```python
def test_converter_basic():
    """Test basic converter functionality."""
    # Setup
    # Conversion
    # Assertions
    
def test_converter_with_utilities():
    """Test converter integration with universal utilities."""
    # Test unit conversion, color parsing, transforms
    
def test_converter_edge_cases():
    """Test converter error handling and edge cases."""
```

## External Dependencies

### Existing Dependencies (No Changes)
- `lxml` for XML processing
- Universal utility system (UnitConverter, ColorParser, TransformParser, ViewportResolver)
- DrawingML generation framework

### New Dependencies (If Needed)
- Image processing libraries for ImageConverter (PIL/Pillow already in use)
- Base64 decoding utilities (Python standard library)

### PowerPoint Integration
- Leverage existing PowerPoint image embedding mechanisms
- Use established DrawingML shape generation patterns
- Maintain compatibility with PowerPoint version requirements

## Implementation Notes

### Design Principles
1. **Follow BaseConverter Pattern**: All new converters inherit from BaseConverter
2. **Use Universal Utilities**: Leverage existing ColorParser, UnitConverter, etc.
3. **Maintain Backward Compatibility**: Don't modify existing converter interfaces
4. **Graceful Degradation**: Provide fallbacks for unsupported features
5. **Comprehensive Testing**: Each converter needs full test coverage

### Code Organization
- One converter per file when possible
- Related converters can be grouped (e.g., references.py for Use/Symbol/Defs)
- Follow existing naming conventions
- Update `__init__.py` for proper exports

### Performance Considerations
- Cache expensive operations (image loading, transform calculations)
- Use batch operations when possible (batch_convert_to_emu)
- Minimize XML parsing overhead
- Implement lazy loading for optional features