# Core Functions

Complete API reference for SVG2PPTX core functions and classes.

## Main Conversion Functions

### `convert_svg_to_pptx()`

Convert a single SVG file to PowerPoint presentation.

```python
def convert_svg_to_pptx(
    input_file: Union[str, Path, ET.Element],
    output_file: Union[str, Path],
    title: Optional[str] = None,
    author: Optional[str] = None,
    subject: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]
```

**Parameters:**
- `input_file`: SVG file path, file-like object, or parsed Element
- `output_file`: Output PPTX file path
- `title`: Presentation title
- `author`: Presentation author  
- `subject`: Presentation subject
- `**kwargs`: Additional conversion options

**Returns:**
Dictionary with conversion results:
```python
{
    'success': True,
    'output_path': '/path/to/output.pptx',
    'slide_count': 1,
    'conversion_time': 2.34,
    'warnings': []
}
```

### `convert_multiple_svgs_to_pptx()`

Combine multiple SVG files into one presentation.

```python 
def convert_multiple_svgs_to_pptx(
    svg_paths: List[Union[str, Path]],
    output_path: Union[str, Path],
    title: str = "SVG Presentation",
    slide_titles: Optional[Dict[str, str]] = None,
    **kwargs
) -> Dict[str, Any]
```

## Multi-slide Classes

### `MultiSlideConverter`

Advanced converter with multi-slide detection capabilities.

```python
class MultiSlideConverter:
    def __init__(
        self,
        enable_multislide_detection: bool = True,
        animation_threshold: int = 3,
        template_path: Optional[Path] = None
    )
    
    def convert_svg_to_pptx(
        self,
        svg_input: Union[str, Path, ET.Element, List[Path]],
        output_path: Path,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]
```

**Methods:**
- `convert_svg_to_pptx()`: Main conversion method
- `detect_slide_boundaries()`: Analyze SVG for slide boundaries  
- `generate_slide_plan()`: Create conversion plan

### `SlideDetector`

Analyzes SVG documents for slide boundaries.

```python
class SlideDetector:
    def detect_boundaries(self, svg_root: ET.Element) -> List[SlideBoundary]
    def recommend_conversion_strategy(self, boundaries: List[SlideBoundary]) -> Dict[str, Any]
    def generate_slide_plan(self, svg_root: ET.Element) -> Dict[str, Any]
```

## Preprocessing Functions

### `create_optimizer()`

Create SVG optimization pipeline.

```python
def create_optimizer(
    precision: int = 3,
    remove_empty: bool = True,
    optimize_paths: bool = True,
    merge_paths: bool = False,
    **plugin_options
) -> SVGOptimizer
```

### `SVGOptimizer`

Main preprocessing class.

```python
class SVGOptimizer:
    def optimize_svg_file(self, input_file: str, output_file: str) -> None
    def optimize_svg_string(self, svg_content: str) -> str  
    def optimize_svg_element(self, element: ET.Element) -> ET.Element
```

## Configuration Classes

### `SVGConfig`

Global configuration settings.

```python
@dataclass
class SVGConfig:
    default_font_family: str = 'Arial'
    default_font_size: int = 12
    preserve_aspect_ratio: bool = True
    max_image_resolution: int = 300
    enable_text_to_path_fallback: bool = True
```

## Exception Classes

### `SVGConversionError`

Base exception for SVG conversion errors.

```python
class SVGConversionError(Exception):
    def __init__(self, message: str, element_info: Optional[Dict] = None)
```

### `PPTXGenerationError`  

Exception for PowerPoint generation errors.

```python
class PPTXGenerationError(Exception):
    pass
```

## Validation Functions

### `validate_svg()`

Validate SVG file before conversion.

```python
def validate_svg(svg_path: Union[str, Path]) -> ValidationResult
```

### `validate_pptx()`

Validate generated PowerPoint file.

```python
def validate_pptx(pptx_path: Union[str, Path]) -> ValidationResult
```

## Utility Functions

### `detect_slide_boundaries()`

Standalone boundary detection.

```python
def detect_slide_boundaries(svg_path: Union[str, Path]) -> List[Dict[str, Any]]
```

### `get_svg_info()`

Extract information from SVG file.

```python
def get_svg_info(svg_path: Union[str, Path]) -> Dict[str, Any]
```

Returns SVG metadata, dimensions, and element counts.