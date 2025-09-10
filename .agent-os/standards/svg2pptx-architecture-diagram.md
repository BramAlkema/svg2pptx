# SVG2PPTX Architecture Diagram

## Complete System Architecture - Bottom Up

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 USER LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  FastAPI Endpoints  │  CLI Interface  │  Direct Library Usage                   │
│  /convert-svg        │  python main.py │  import svg2pptx                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            INTEGRATION LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│  svg2pptx.py         │  enhanced_text_converter.py  │  preprocessing/          │
│  (Main Entry Point)  │  (Three-Tier Font Strategy)  │  (SVG Optimization)     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CONVERTER REGISTRY                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                      ConverterRegistry.get_converter()                         │
│                   Maps SVG elements → Specialized Converters                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         SPECIALIZED CONVERTERS                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ TextConverter        │ PathConverter      │ ShapeConverter    │ GroupConverter   │
│ ┌─────────────────┐  │ ┌───────────────┐  │ ┌──────────────┐  │ ┌─────────────┐  │
│ │• Font Embedding │  │ │• Path Data    │  │ │• Rectangles  │  │ │• Transform  │  │
│ │• Font Metrics   │  │ │• Bezier Curves│  │ │• Circles     │  │ │• Grouping   │  │
│ │• Text-to-Path   │  │ │• Arc Commands │  │ │• Ellipses    │  │ │• Clipping   │  │
│ │• DrawingML Text │  │ │• Coordinate   │  │ │• Polygons    │  │ │• Masking    │  │
│ └─────────────────┘  │ │  Transforms   │  │ └──────────────┘  │ └─────────────┘  │
│                      │ └───────────────┘  │                  │                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │ ALL INHERIT FROM
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            BASE CONVERTER                                      │
│                         (FOUNDATION LAYER)                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  class BaseConverter(ABC):                                                     │
│      def __init__(self):                                                       │
│          self.unit_converter = UnitConverter()      # 🔧 EMU calculations     │
│          self.transform_parser = TransformParser()  # 🔧 SVG transforms       │
│          self.color_parser = ColorParser()         # 🔧 Color handling        │
│          self.viewport_resolver = ViewportResolver() # 🔧 Viewport logic      │
│                                                                                 │
│      @abstractmethod                                                           │
│      def convert(element, context) -> DrawingML                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           STANDARDIZED TOOLS                                   │
│                          (TOOL FOUNDATION)                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│ UnitConverter        │ ColorParser         │ TransformParser   │ ViewportResolver│
│ ┌─────────────────┐  │ ┌─────────────────┐ │ ┌──────────────┐  │ ┌─────────────┐ │
│ │• SVG → EMU      │  │ │• RGB/HSL/Named  │ │ │• Matrix Calc │  │ │• ViewBox    │ │
│ │• Points/Pixels  │  │ │• Hex/Alpha      │ │ │• Translate   │  │ │• Scaling    │ │
│ │• DPI Handling   │  │ │• DrawingML XML  │ │ │• Scale/Rotate│  │ │• Aspect     │ │
│ │• EMU_PER_INCH   │  │ │• Opacity        │ │ │• Skew/Matrix │  │ │  Ratio      │ │
│ │• EMU_PER_POINT  │  │ │• Color Spaces   │ │ │• Coordinate  │  │ │• Centering  │ │
│ └─────────────────┘  │ └─────────────────┘ │ │  Systems     │  │ └─────────────┘ │
│                      │                     │ └──────────────┘  │                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CONTEXT LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ConversionContext           │ CoordinateSystem                                  │
│ ┌─────────────────────────┐ │ ┌─────────────────────────────────────────────┐   │
│ │• Shape ID Generation    │ │ │• SVG → EMU coordinate conversion           │   │
│ │• Gradient/Pattern Cache │ │ │• Viewbox handling                          │   │
│ │• Font Registry          │ │ │• Aspect ratio preservation                 │   │
│ │• Group Stack            │ │ │• Scale factor calculation                  │   │
│ │• Style Inheritance      │ │ │• Centering/offset computation              │   │
│ │• Embedded Font Storage  │ │ └─────────────────────────────────────────────┘   │
│ └─────────────────────────┘ │                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                              DrawingML XML                                     │
│  ┌───────────────┐ ┌────────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │<a:txBody>     │ │<a:pathLst>     │ │<a:solidFill> │ │<a:xfrm>             │ │
│  │ <a:p>         │ │ <a:path>       │ │ <a:srgbClr>  │ │ <a:off x="" y=""/>  │ │
│  │  <a:r>        │ │  <a:moveTo/>   │ │  <a:alpha/>  │ │ <a:ext cx="" cy=""/>│ │
│  │   <a:rPr/>    │ │  <a:lnTo/>     │ │ </a:srgbClr> │ │</a:xfrm>            │ │
│  │   <a:t>text   │ │  <a:arcTo/>    │ │</a:solidFill>│ │                     │ │
│  │  </a:r>       │ │ </a:path>      │ │              │ │                     │ │
│  │ </a:p>        │ │</a:pathLst>    │ │              │ │                     │ │
│  │</a:txBody>    │ │                │ │              │ │                     │ │
│  └───────────────┘ └────────────────┘ └──────────────┘ └─────────────────────┘ │
│   Text Elements     Path Elements      Fill/Stroke      Transform Elements     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            PPTX INTEGRATION                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│  python-pptx Library        │  Font Embedding           │  Drawing Integration │
│  ┌─────────────────────────┐ │ ┌───────────────────────┐ │ ┌─────────────────┐  │
│  │• Slide Creation         │ │ │• PPTXFontEmbedder     │ │ │• Shape Creation │  │
│  │• Shape Management       │ │ │• Font Resource IDs    │ │ │• XML Integration│  │
│  │• XML Structure          │ │ │• Three-Tier Strategy  │ │ │• Positioning    │  │
│  │• File Generation        │ │ │• @font-face Parsing   │ │ │• Layering       │  │
│  └─────────────────────────┘ │ └───────────────────────┘ │ └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Test Architecture Mapping

```
TEST LAYER                              PRODUCTION LAYER
─────────────                           ──────────────────

┌─────────────────────────────┐         ┌─────────────────────────────┐
│  Integration Tests          │ ◄────── │  svg2pptx.py               │
│  • test_end_to_end_*.py     │         │  • convert_svg_to_pptx()    │
│  • Full SVG → PPTX          │         │  • Main entry points       │
└─────────────────────────────┘         └─────────────────────────────┘
                │                                       │
                ▼                                       ▼
┌─────────────────────────────┐         ┌─────────────────────────────┐
│  Converter Unit Tests       │ ◄────── │  Specialized Converters     │
│  • test_text.py             │         │  • TextConverter            │
│  • test_shapes.py           │         │  • PathConverter            │
│  • test_paths.py            │         │  • ShapeConverter           │
│  • Uses UnitConverter       │         │  • All inherit from Base   │
│  • Uses ColorParser         │         │                             │
└─────────────────────────────┘         └─────────────────────────────┘
                │                                       │
                ▼                                       ▼
┌─────────────────────────────┐         ┌─────────────────────────────┐
│  Base Converter Tests       │ ◄────── │  BaseConverter              │
│  • test_base.py             │         │  • Tool initialization      │
│  • Mock inherits from Base  │         │  • Abstract methods         │
│  • Tool method validation   │         │  • Shared functionality     │
└─────────────────────────────┘         └─────────────────────────────┘
                │                                       │
                ▼                                       ▼
┌─────────────────────────────┐         ┌─────────────────────────────┐
│  Tool Unit Tests            │ ◄────── │  Standardized Tools         │
│  • test_units.py            │         │  • UnitConverter            │
│  • test_colors.py           │         │  • ColorParser              │
│  • test_transforms.py       │         │  • TransformParser          │
│  • Direct tool testing      │         │  • ViewportResolver         │
└─────────────────────────────┘         └─────────────────────────────┘
```

## Key Architectural Principles

### 1. **Bottom-Up Inheritance**
```
Tools (Foundation) → BaseConverter → Specialized Converters → Integration Layer
```

### 2. **Standardized Tool Access**
```python
# ❌ Wrong: Hardcoded values
assert '<a:ln w="25400">' in result

# ✅ Correct: Tool-based calculation  
expected_emu = converter.unit_converter.to_emu('2px')
assert f'<a:ln w="{expected_emu}">' in result
```

### 3. **Consistent Testing Pattern**
```python
# Every test inherits tools through BaseConverter
class MockConverter(BaseConverter):
    # Gets all 4 tools automatically
    pass

converter = MockConverter()
# Tests use same tools as production
```

### 4. **Three-Tier Font Strategy**
```
1. @font-face embedded fonts (highest priority)
2. System fonts (fallback)
3. Text-to-path conversion (last resort)
```

This architecture ensures that every layer uses standardized tools, maintains consistency from bottom to top, and provides a robust foundation for SVG to PowerPoint conversion with proper font handling, accurate unit conversions, and reliable color processing.