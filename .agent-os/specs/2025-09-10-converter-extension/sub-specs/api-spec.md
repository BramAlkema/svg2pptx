# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-09-10-converter-extension/spec.md

> Created: 2025-09-10
> Version: 1.0.0

## Converter API Interfaces

### Base Converter Interface (Existing)

All new converters must implement the BaseConverter interface:

```python
class BaseConverter(ABC):
    supported_elements: List[str] = []
    
    @abstractmethod
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the given element."""
        pass
    
    @abstractmethod
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """Convert SVG element to DrawingML XML string."""
        pass
```

### New Converter Classes

#### 1. ImageConverter

```python
class ImageConverter(BaseConverter):
    """Converter for SVG <image> elements."""
    
    supported_elements = ['image']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if element is an image."""
        return self.get_element_tag(element) == 'image'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Convert SVG image to DrawingML.
        
        Handles:
        - href/xlink:href image sources
        - Base64 embedded images (data: URLs)
        - External image file references
        - x, y, width, height positioning
        - Transforms and styling
        
        Returns:
            DrawingML XML for image shape with embedded image data
        """
        pass
    
    def _resolve_image_source(self, href: str) -> bytes:
        """Resolve image source to binary data."""
        pass
    
    def _embed_image_data(self, image_data: bytes, context: ConversionContext) -> str:
        """Embed image data in PowerPoint and return relationship ID."""
        pass
```

#### 2. UseConverter

```python
class UseConverter(BaseConverter):
    """Converter for SVG <use> elements."""
    
    supported_elements = ['use']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if element is a use reference."""
        return self.get_element_tag(element) == 'use'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Convert SVG use element to DrawingML.
        
        Handles:
        - href/xlink:href element references
        - x, y positioning offsets
        - Transform composition
        - Recursive element resolution
        - Circular reference detection
        
        Returns:
            DrawingML XML for referenced element with applied transforms
        """
        pass
    
    def _resolve_reference(self, href: str, context: ConversionContext) -> Optional[ET.Element]:
        """Resolve href to referenced element."""
        pass
    
    def _detect_circular_reference(self, href: str, context: ConversionContext) -> bool:
        """Detect circular references in use chain."""
        pass
```

#### 3. SymbolConverter

```python
class SymbolConverter(BaseConverter):
    """Converter for SVG <symbol> elements."""
    
    supported_elements = ['symbol']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if element is a symbol definition."""
        return self.get_element_tag(element) == 'symbol'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Process SVG symbol definition.
        
        Handles:
        - Symbol storage in ConversionContext
        - viewBox processing for symbol scaling
        - Nested element processing
        - ID registration for future references
        
        Returns:
            Empty string (symbols are definitions, not rendered directly)
        """
        pass
    
    def _store_symbol(self, element: ET.Element, context: ConversionContext):
        """Store symbol definition in context for later use."""
        pass
```

#### 4. DefsConverter

```python
class DefsConverter(BaseConverter):
    """Converter for SVG <defs> elements."""
    
    supported_elements = ['defs']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if element is a defs container."""
        return self.get_element_tag(element) == 'defs'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Process SVG defs container.
        
        Handles:
        - Processing all child definition elements
        - Dispatching to appropriate converters (gradients, patterns, symbols, etc.)
        - Definition storage in ConversionContext
        - Nested defs support
        
        Returns:
            Empty string (defs contain definitions, not rendered content)
        """
        pass
    
    def _process_child_definitions(self, element: ET.Element, context: ConversionContext):
        """Process all child elements as definitions."""
        pass
```

#### 5. PatternConverter

```python
class PatternConverter(BaseConverter):
    """Converter for SVG <pattern> elements."""
    
    supported_elements = ['pattern']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if element is a pattern definition."""
        return self.get_element_tag(element) == 'pattern'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Process SVG pattern definition.
        
        Handles:
        - Pattern storage in context.patterns
        - patternUnits and patternContentUnits
        - Pattern transforms
        - x, y, width, height attributes
        - Nested pattern content processing
        
        Returns:
            Empty string (patterns are definitions, stored for later use)
        """
        pass
    
    def generate_pattern_fill(self, pattern_def: Dict, opacity: str = '1') -> str:
        """
        Generate DrawingML pattern fill from pattern definition.
        
        Note: PowerPoint has limited pattern support, may fallback to solid colors.
        """
        pass
```

#### 6. ClipPathConverter

```python
class ClipPathConverter(BaseConverter):
    """Converter for SVG <clipPath> elements."""
    
    supported_elements = ['clipPath']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if element is a clipping path definition."""
        return self.get_element_tag(element) == 'clipPath'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Process SVG clipPath definition.
        
        Handles:
        - Clipping path storage in context.clips
        - clipPathUnits attribute
        - Path and shape-based clipping
        - Transform handling
        
        Returns:
            Empty string (clipPaths are definitions, applied during shape rendering)
        """
        pass
    
    def apply_clip_path(self, shape_xml: str, clip_def: Dict) -> str:
        """
        Apply clipping path to shape DrawingML.
        
        Note: PowerPoint has limited clipping support, may use fallback strategies.
        """
        pass
```

#### 7. FilterConverter

```python
class FilterConverter(BaseConverter):
    """Converter for SVG <filter> elements."""
    
    supported_elements = ['filter']
    
    def can_convert(self, element: ET.Element) -> bool:
        """Check if element is a filter definition."""
        return self.get_element_tag(element) == 'filter'
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Process SVG filter definition.
        
        Handles:
        - Basic filter effects (drop shadows, blur, etc.)
        - Filter storage in context.filters
        - filterUnits and primitiveUnits
        - Fallback strategies for unsupported effects
        
        Returns:
            Empty string (filters are definitions, applied during shape rendering)
        """
        pass
    
    def apply_filter_effects(self, shape_xml: str, filter_def: Dict) -> str:
        """
        Apply filter effects to shape DrawingML.
        
        Limited PowerPoint support, uses fallbacks for complex effects.
        """
        pass
```

## ConversionContext API Extensions

### New Storage Properties

```python
class ConversionContext:
    """Extended context with support for new element types."""
    
    def __init__(self, svg_root: Optional[ET.Element] = None):
        # Existing properties...
        
        # New storage for additional elements
        self.images: Dict[str, Dict] = {}         # Image definitions and data
        self.symbols: Dict[str, ET.Element] = {}  # Symbol element definitions
        self.uses: Dict[str, Any] = {}            # Use element reference tracking
        self.filters: Dict[str, Dict] = {}        # Filter definitions
        # patterns and clips already exist
        
    # New helper methods
    def store_image(self, image_id: str, image_data: bytes, metadata: Dict):
        """Store image data and metadata."""
        pass
        
    def get_image(self, image_id: str) -> Optional[Dict]:
        """Retrieve stored image data."""
        pass
        
    def store_symbol(self, symbol_id: str, symbol_element: ET.Element):
        """Store symbol definition."""
        pass
        
    def resolve_symbol(self, symbol_id: str) -> Optional[ET.Element]:
        """Resolve symbol by ID."""
        pass
        
    def track_use_reference(self, use_id: str, href: str):
        """Track use element for circular reference detection."""
        pass
        
    def has_circular_reference(self, href: str) -> bool:
        """Check for circular references in use chain."""
        pass
```

## Registry Integration API

### Converter Registration

```python
# In __init__.py or main initialization
registry = ConverterRegistry()

# Register new converters
registry.register_class(ImageConverter)
registry.register_class(UseConverter)
registry.register_class(SymbolConverter)
registry.register_class(DefsConverter)
registry.register_class(PatternConverter)
registry.register_class(ClipPathConverter)
registry.register_class(FilterConverter)
```

### Element Mapping

```python
# Automatic element type mapping
ELEMENT_CONVERTER_MAP = {
    'image': ImageConverter,
    'use': UseConverter,
    'symbol': SymbolConverter,
    'defs': DefsConverter,
    'pattern': PatternConverter,
    'clipPath': ClipPathConverter,
    'filter': FilterConverter
}
```

## Universal Utility Integration API

### Standard Integration Patterns

All converters must use these utility integration patterns:

```python
class NewConverter(BaseConverter):
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        # 1. Batch unit conversion
        dimensions = context.batch_convert_to_emu({
            'x': element.get('x', '0'),
            'y': element.get('y', '0'),
            'width': element.get('width', '0'),
            'height': element.get('height', '0')
        })
        
        # 2. Color parsing
        fill_color = self.parse_color(self.get_attribute_with_style(element, 'fill'))
        stroke_color = self.parse_color(self.get_attribute_with_style(element, 'stroke'))
        
        # 3. Transform handling
        transform_matrix = self.get_element_transform_matrix(element, context.viewport_context)
        
        # 4. Standard fill and stroke generation
        fill_xml = self.generate_fill(fill_color, opacity, context)
        stroke_xml = self.generate_stroke(stroke_color, stroke_width, opacity, context)
        
        return f"<drawingml_output>{fill_xml}{stroke_xml}</drawingml_output>"
```

## Error Handling API

### Standard Error Patterns

```python
class ConverterWithErrorHandling(BaseConverter):
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        try:
            # Main conversion logic
            return self._do_conversion(element, context)
            
        except ValueError as e:
            # Handle parsing errors
            self.logger.warning(f"Parse error in {element.tag}: {e}")
            return f"<!-- Parse error: {e} -->"
            
        except Exception as e:
            # Handle unexpected errors
            self.logger.error(f"Error converting {element.tag}: {e}")
            return f"<!-- Conversion error: {e} -->"
    
    def _do_conversion(self, element: ET.Element, context: ConversionContext) -> str:
        """Internal conversion logic that may raise exceptions."""
        pass
```

## Testing API Requirements

### Required Test Methods

```python
class TestNewConverter(unittest.TestCase):
    def test_can_convert(self):
        """Test element type detection."""
        pass
        
    def test_basic_conversion(self):
        """Test basic element conversion."""
        pass
        
    def test_with_transforms(self):
        """Test conversion with transforms applied."""
        pass
        
    def test_with_styles(self):
        """Test conversion with style attributes."""
        pass
        
    def test_utility_integration(self):
        """Test integration with universal utilities."""
        pass
        
    def test_error_handling(self):
        """Test error handling and fallbacks."""
        pass
```

## Backward Compatibility

### Compatibility Requirements

1. **Existing Converter Interfaces**: No changes to existing BaseConverter methods
2. **ConversionContext**: New properties only, no modifications to existing ones
3. **Universal Utilities**: Only usage, no API changes
4. **Registry System**: New registrations only, existing converters unaffected

### Migration Path

No migration required - new converters extend existing functionality without breaking changes.