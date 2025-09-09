# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-09-09-text-to-path-fallback/spec.md

> Created: 2025-09-09
> Version: 1.0.0

## Endpoints

### Core Classes and Methods

#### FontMetricsAnalyzer Class

**Purpose**: Analyzes fonts and extracts metrics needed for text-to-path conversion.

```python
class FontMetricsAnalyzer:
    def __init__(self, font_cache_size: int = 100):
        """Initialize the font metrics analyzer with optional cache size."""
        
    def get_font_metrics(self, font_family: str, font_style: str = "normal", 
                        font_weight: str = "400") -> FontMetrics:
        """
        Get font metrics for the specified font.
        
        Args:
            font_family: Name of the font family
            font_style: Font style (normal, italic, oblique)
            font_weight: Font weight (100-900 or normal/bold)
            
        Returns:
            FontMetrics object containing font information
            
        Raises:
            FontNotFoundError: If font cannot be located or loaded
            FontLoadError: If font file is corrupted or invalid
        """
        
    def is_font_available(self, font_family: str) -> bool:
        """Check if a font is available on the system."""
        
    def get_glyph_outline(self, character: str, font_metrics: FontMetrics, 
                         font_size: float) -> GlyphOutline:
        """
        Extract glyph outline for a specific character.
        
        Args:
            character: The character to get outline for
            font_metrics: Font metrics object
            font_size: Font size in points
            
        Returns:
            GlyphOutline object with path data
        """
        
    def get_fallback_fonts(self, font_family: str) -> List[str]:
        """Get list of fallback fonts for the specified font family."""
        
    def clear_cache(self) -> None:
        """Clear the font metrics cache."""
```

#### PathGenerator Class

**Purpose**: Converts glyph outlines to PowerPoint-compatible path definitions.

```python
class PathGenerator:
    def __init__(self, optimization_level: int = 1):
        """
        Initialize path generator.
        
        Args:
            optimization_level: 0=none, 1=basic, 2=aggressive optimization
        """
        
    def glyph_to_svg_path(self, glyph_outline: GlyphOutline) -> str:
        """Convert glyph outline to SVG path string."""
        
    def svg_path_to_drawingml(self, svg_path: str, width: int, height: int) -> str:
        """
        Convert SVG path to PowerPoint DrawingML path definition.
        
        Args:
            svg_path: SVG path data string
            width: Shape width in EMUs
            height: Shape height in EMUs
            
        Returns:
            DrawingML path definition XML
        """
        
    def optimize_path(self, path_data: str, tolerance: float = 1.0) -> str:
        """Optimize path by reducing points while maintaining shape."""
        
    def generate_text_decoration_path(self, decoration_type: str, 
                                    text_bounds: Tuple[int, int, int, int],
                                    line_thickness: float) -> str:
        """Generate path for text decorations (underline, strikethrough)."""
```

#### TextToPathConverter Class

**Purpose**: High-level converter that orchestrates text-to-path conversion.

```python
class TextToPathConverter(BaseConverter):
    supported_elements = ['text', 'tspan']
    
    def __init__(self, font_analyzer: FontMetricsAnalyzer = None,
                 path_generator: PathGenerator = None):
        """Initialize with optional custom font analyzer and path generator."""
        
    def can_convert(self, element: ET.Element) -> bool:
        """Check if this converter can handle the element."""
        
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Convert SVG text element to PowerPoint path shape.
        
        Args:
            element: SVG text element
            context: Conversion context with settings and state
            
        Returns:
            DrawingML XML for path shape(s)
        """
        
    def should_use_path_conversion(self, element: ET.Element, 
                                 context: ConversionContext) -> bool:
        """Determine if text should be converted to path."""
        
    def create_text_layout(self, element: ET.Element, 
                          context: ConversionContext) -> TextLayout:
        """Analyze text element and create layout information."""
        
    def convert_to_paths(self, layout: TextLayout, 
                        context: ConversionContext) -> str:
        """Convert text layout to PowerPoint path shapes."""
```

#### Enhanced TextConverter Class

**Purpose**: Updated TextConverter with integrated fallback logic.

```python
class TextConverter(BaseConverter):
    def __init__(self, enable_path_fallback: bool = True,
                 path_converter: TextToPathConverter = None):
        """
        Initialize TextConverter with path fallback capability.
        
        Args:
            enable_path_fallback: Whether to enable automatic path fallback
            path_converter: Custom TextToPathConverter instance
        """
        
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """
        Convert SVG text element to PowerPoint text or path shape.
        
        Automatically falls back to path conversion when:
        - Font is not available on the system
        - Complex formatting requires exact reproduction
        - User configuration forces path conversion
        """
        
    def should_use_path_fallback(self, element: ET.Element, 
                                context: ConversionContext) -> bool:
        """Determine if path fallback should be used."""
        
    def convert_as_text(self, element: ET.Element, 
                       context: ConversionContext) -> str:
        """Convert using traditional text shape approach."""
        
    def convert_as_path(self, element: ET.Element, 
                       context: ConversionContext) -> str:
        """Convert using text-to-path approach."""
```

### Configuration API

#### TextToPathConfig Class

**Purpose**: Configuration settings for text-to-path conversion behavior.

```python
@dataclass
class TextToPathConfig:
    # Fallback behavior
    enable_automatic_fallback: bool = True
    force_path_conversion: bool = False
    fallback_on_missing_fonts: bool = True
    fallback_on_complex_layouts: bool = True
    
    # Font handling
    font_cache_size: int = 100
    font_search_paths: List[str] = None
    default_fallback_font: str = "Arial"
    
    # Path generation
    path_optimization_level: int = 1
    curve_tolerance: float = 1.0
    max_points_per_path: int = 1000
    
    # Performance
    max_text_length_for_paths: int = 1000
    enable_glyph_caching: bool = True
    cache_size_limit_mb: int = 50
    
    # Debugging
    debug_mode: bool = False
    log_font_substitutions: bool = True
    save_intermediate_paths: bool = False
```

### Error Handling

#### Custom Exceptions

```python
class FontNotFoundError(Exception):
    """Raised when a specified font cannot be found."""
    def __init__(self, font_family: str, searched_paths: List[str] = None):
        self.font_family = font_family
        self.searched_paths = searched_paths or []
        super().__init__(f"Font '{font_family}' not found")

class FontLoadError(Exception):
    """Raised when a font file cannot be loaded or parsed."""
    def __init__(self, font_path: str, reason: str):
        self.font_path = font_path
        self.reason = reason
        super().__init__(f"Cannot load font '{font_path}': {reason}")

class GlyphNotFoundError(Exception):
    """Raised when a character glyph is not available in the font."""
    def __init__(self, character: str, font_family: str):
        self.character = character
        self.font_family = font_family
        super().__init__(f"Glyph for '{character}' not found in font '{font_family}'")

class PathGenerationError(Exception):
    """Raised when path generation fails."""
    def __init__(self, reason: str, glyph_data: str = None):
        self.reason = reason
        self.glyph_data = glyph_data
        super().__init__(f"Path generation failed: {reason}")
```

### Usage Examples

#### Basic Usage

```python
from svg2pptx.converters.text import TextConverter
from svg2pptx.converters.text_to_path import TextToPathConfig

# Configure text-to-path behavior
config = TextToPathConfig(
    enable_automatic_fallback=True,
    fallback_on_missing_fonts=True,
    path_optimization_level=2
)

# Create converter with configuration
converter = TextConverter(enable_path_fallback=True)
converter.config = config

# Convert SVG text element
result = converter.convert(text_element, context)
```

#### Advanced Configuration

```python
from svg2pptx.converters.text_to_path import (
    FontMetricsAnalyzer, PathGenerator, TextToPathConverter
)

# Custom font analyzer with extended cache
font_analyzer = FontMetricsAnalyzer(font_cache_size=200)
font_analyzer.add_font_search_path("/custom/fonts/path")

# Custom path generator with aggressive optimization
path_generator = PathGenerator(optimization_level=2)

# Create custom text-to-path converter
path_converter = TextToPathConverter(
    font_analyzer=font_analyzer,
    path_generator=path_generator
)

# Use with enhanced text converter
text_converter = TextConverter(path_converter=path_converter)
```

#### Force Path Conversion

```python
# Force all text to be converted to paths
config = TextToPathConfig(
    force_path_conversion=True,
    path_optimization_level=1
)

converter = TextConverter()
converter.config = config

# All text elements will be converted to paths regardless of font availability
```

## Controllers

### ConversionContext Extensions

The existing `ConversionContext` class will be extended with text-to-path specific functionality:

```python
class ConversionContext:
    # Existing properties...
    
    # Text-to-path extensions
    text_to_path_config: TextToPathConfig = None
    font_analyzer: FontMetricsAnalyzer = None
    path_generator: PathGenerator = None
    
    def get_font_analyzer(self) -> FontMetricsAnalyzer:
        """Get or create font analyzer instance."""
        
    def get_path_generator(self) -> PathGenerator:
        """Get or create path generator instance."""
        
    def should_force_path_conversion(self, element: ET.Element) -> bool:
        """Check if element should be forced to path conversion."""
        
    def log_font_substitution(self, original: str, substituted: str) -> None:
        """Log font substitution for debugging."""
```

### Integration with SVG2PPTX Main Pipeline

The text-to-path system integrates seamlessly with the existing converter registration system:

```python
# In the main converter registry
def register_converters():
    # Existing converters...
    
    # Enhanced text converter with path fallback
    registry.register(TextConverter(enable_path_fallback=True))
    
    # Optional: Direct path converter for specific use cases
    registry.register(TextToPathConverter(), priority=5)
```

### Performance Monitoring

```python
class TextConversionMetrics:
    """Track text conversion performance and fallback usage."""
    
    def __init__(self):
        self.text_conversions = 0
        self.path_conversions = 0
        self.font_cache_hits = 0
        self.font_cache_misses = 0
        self.conversion_times = []
        
    def record_text_conversion(self, duration: float) -> None:
        """Record successful text conversion."""
        
    def record_path_conversion(self, duration: float, reason: str) -> None:
        """Record path conversion with reason."""
        
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
```

This API specification provides a comprehensive interface for the text-to-path fallback system while maintaining compatibility with the existing SVG2PPTX converter architecture.