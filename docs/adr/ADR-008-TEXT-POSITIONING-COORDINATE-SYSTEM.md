# ADR-008: Text Positioning Coordinate System

**Status**: PROPOSED
**Date**: 2025-09-24
**Context**: SVG baseline-anchored text positioning vs PowerPoint top-left textbox positioning

## Problem Statement

SVG text elements use baseline-anchored positioning with `text-anchor` alignment, while PowerPoint textboxes use top-left corner positioning. Current implementation treats SVG text coordinates as PowerPoint textbox coordinates, causing systematic positioning errors.

**Critical Issues Identified**:
1. SVG `(x,y)` represents baseline position; PowerPoint needs top-left corner
2. `text-anchor="middle|end"` shifts baseline position, not top-left corner
3. Font metrics (ascent/descent) required to convert baseline to top-left
4. Service dependencies not properly wired causing fallback to defaults

## Decision

Implement proper SVG-to-PowerPoint text coordinate transformation following ADR-002 (Converter Architecture) and ADR-004 (Import Plumbing) specifications.

## Architecture Integration

### 1. Service Enhancement (`src/services/`)

Extend `ConversionServices` per ADR-004 to include font and viewport services:

**File**: `src/services/conversion_services.py`
```python
@dataclass
class ConversionServices:
    """Central service container for dependency injection."""

    # Existing services
    unit_converter: UnitConverter = field(default_factory=UnitConverter)
    transform_parser: Transform = field(default_factory=Transform)
    color_parser: Color = field(default_factory=Color)
    path_engine: PathEngine = field(default_factory=PathEngine)

    # NEW: Text positioning services
    font_service: FontService = field(default_factory=FontService)
    viewport_service: ViewportService = field(default_factory=ViewportService)
    style_parser: StyleParser = field(default_factory=StyleParser)

    @classmethod
    def create_with_viewport(cls, svg_root: ET.Element,
                           slide_width_emu: int, slide_height_emu: int) -> 'ConversionServices':
        """Create services with proper viewport mapping."""
        viewport_service = ViewportService(svg_root, slide_width_emu, slide_height_emu)
        return cls(viewport_service=viewport_service)
```

### 2. Font Service Implementation (`src/services/font_service.py`)

**File**: `src/services/font_service.py`
```python
"""Font metrics and measurement service."""
from typing import Tuple, Optional, Dict
from dataclasses import dataclass

@dataclass
class FontMetrics:
    """Font metric ratios."""
    ascent: float   # Ratio of font size (0.0-1.0)
    descent: float  # Ratio of font size (0.0-1.0)

class FontService:
    """Font metrics and text measurement service."""

    # Font metrics table: family -> (ascent_ratio, descent_ratio)
    FONT_METRICS: Dict[str, FontMetrics] = {
        "Arial": FontMetrics(0.82, 0.18),
        "Helvetica": FontMetrics(0.82, 0.18),
        "Times New Roman": FontMetrics(0.83, 0.17),
        "Courier New": FontMetrics(0.80, 0.20),
        # Default fallback
        "default": FontMetrics(0.80, 0.20)
    }

    def get_metrics(self, font_family: str) -> FontMetrics:
        """Get font metrics for family."""
        return self.FONT_METRICS.get(font_family, self.FONT_METRICS["default"])

    def measure_text_width(self, text: str, font_family: str, font_size_pt: float) -> float:
        """Measure text width in points."""
        # Character width estimation (0.5em average for Latin text)
        char_count = len(text)
        average_char_width = 0.5  # em units
        return char_count * average_char_width * font_size_pt

    def map_svg_font_to_ppt(self, svg_font_family: str) -> str:
        """Map SVG font-family to PowerPoint typeface."""
        if not svg_font_family:
            return "Arial"

        font_map = {
            "Arial": "Arial",
            "Helvetica": "Arial",
            "Times": "Times New Roman",
            "sans-serif": "Arial",
            "serif": "Times New Roman",
            "monospace": "Courier New"
        }

        cleaned = svg_font_family.strip().strip('\'"').split(',')[0].strip()
        return font_map.get(cleaned, cleaned)
```

### 3. Viewport Service Implementation (`src/services/viewport_service.py`)

**File**: `src/services/viewport_service.py`
```python
"""Viewport coordinate transformation service."""
from typing import Tuple
from lxml import etree as ET
from src.viewbox.core import ViewportEngine
from src.units import UnitConverter, EMU_PER_POINT

class ViewportService:
    """Centralized viewport coordinate transformation."""

    def __init__(self, svg_root: ET.Element, slide_width_emu: int, slide_height_emu: int):
        self.unit_converter = UnitConverter()

        # Create viewport mapping using existing ViewportEngine
        self.viewport_mapping = (ViewportEngine(self.unit_converter)
                               .for_svg(svg_root)
                               .with_slide_size(slide_width_emu, slide_height_emu)
                               .top_left()
                               .meet()
                               .resolve_single())

    def svg_to_emu(self, svg_x: float, svg_y: float) -> Tuple[int, int]:
        """Transform SVG coordinates to EMU."""
        emu_x = int(svg_x * self.viewport_mapping['scale_x'] + self.viewport_mapping['translate_x'])
        emu_y = int(svg_y * self.viewport_mapping['scale_y'] + self.viewport_mapping['translate_y'])
        return emu_x, emu_y

    def get_scale_factors(self) -> Tuple[float, float]:
        """Get viewport scale factors."""
        return self.viewport_mapping['scale_x'], self.viewport_mapping['scale_y']
```

### 4. Text Layout Engine (`src/services/text_layout.py`)

**File**: `src/services/text_layout.py`
```python
"""SVG to PowerPoint text layout conversion."""
from typing import Tuple
from src.units import EMU_PER_POINT

def svg_text_to_ppt_box(svg_x: float, svg_y: float, anchor: str, text: str,
                       font_family: str, font_size_pt: float,
                       services: 'ConversionServices') -> Tuple[int, int, int, int]:
    """
    Convert SVG baseline-anchored text to PowerPoint top-left textbox.

    Args:
        svg_x, svg_y: SVG baseline coordinates
        anchor: text-anchor value ('start'|'middle'|'end')
        text: Text content
        font_family: Font family name
        font_size_pt: Font size in points
        services: ConversionServices with font and viewport services

    Returns:
        Tuple[x_emu, y_emu, width_emu, height_emu]: PowerPoint textbox coordinates
    """
    # Transform SVG coordinates to EMU
    baseline_x_emu, baseline_y_emu = services.viewport_service.svg_to_emu(svg_x, svg_y)

    # Get font metrics
    metrics = services.font_service.get_metrics(font_family)

    # Calculate text dimensions
    width_pt = services.font_service.measure_text_width(text, font_family, font_size_pt)
    width_emu = int(width_pt * EMU_PER_POINT)

    # Line height (1.2x font size)
    line_height_pt = font_size_pt * 1.2
    height_emu = int(line_height_pt * EMU_PER_POINT)

    # Convert baseline to top-left (subtract ascent)
    ascent_emu = int(font_size_pt * metrics.ascent * EMU_PER_POINT)
    y_top_emu = baseline_y_emu - ascent_emu

    # Apply text-anchor adjustment
    if anchor == 'middle':
        x_left_emu = baseline_x_emu - (width_emu // 2)
    elif anchor == 'end':
        x_left_emu = baseline_x_emu - width_emu
    else:  # 'start' or None
        x_left_emu = baseline_x_emu

    return x_left_emu, y_top_emu, width_emu, height_emu
```

### 5. Text Converter Update (`src/converters/text/text.py`)

Following ADR-002 converter architecture:

**File**: `src/converters/text/text.py`
```python
"""Text converter implementation."""
from lxml import etree as ET
from ..base import BaseConverter, ConversionContext, ConversionResult
from ..result_types import BoundingBox
from src.services.text_layout import svg_text_to_ppt_box

class TextConverter(BaseConverter):
    """Converts SVG <text> elements to PowerPoint textboxes."""

    def can_convert(self, element: ET.Element) -> bool:
        """Check if element is text."""
        return element.tag.endswith('text')

    def convert(self, element: ET.Element, context: ConversionContext) -> ConversionResult:
        """Convert text element with proper coordinate transformation."""

        # Extract SVG text properties
        svg_x = float(element.get('x', '0'))
        svg_y = float(element.get('y', '0'))
        text_content = element.text or ''

        # Extract font properties
        svg_font_family = element.get('font-family', 'Arial')
        font_size_str = element.get('font-size', '12')
        font_size_pt = float(font_size_str.replace('px', '').replace('pt', ''))

        # Apply readability boost (minimum 18pt for presentations)
        if font_size_pt < 18:
            font_size_pt = max(font_size_pt * 1.8, 18)

        anchor = element.get('text-anchor', 'start')

        # Map SVG font to PowerPoint typeface
        ppt_font_family = self.services.font_service.map_svg_font_to_ppt(svg_font_family)

        # Convert SVG text to PowerPoint textbox coordinates
        x_emu, y_emu, width_emu, height_emu = svg_text_to_ppt_box(
            svg_x, svg_y, anchor, text_content,
            ppt_font_family, font_size_pt, self.services
        )

        # Create bounding box
        bounds = BoundingBox(x_emu, y_emu, width_emu, height_emu)

        # Generate PowerPoint textbox XML
        xml = self._create_textbox_xml(bounds, text_content, ppt_font_family, font_size_pt, element)

        return ConversionResult(
            xml=xml,
            bounds=bounds,
            element_type='text'
        )

    def _create_textbox_xml(self, bounds: BoundingBox, text: str,
                          font_family: str, font_size_pt: float, element: ET.Element) -> str:
        """Generate PowerPoint textbox XML."""
        # Font weight and style
        font_weight = element.get('font-weight', 'normal')
        is_bold = font_weight in ['bold', '700']

        font_style = element.get('font-style', 'normal')
        is_italic = font_style == 'italic'

        # Font size in PowerPoint units (1/100 points)
        size_units = int(font_size_pt * 100)

        return f'''
        <p:sp>
            <p:nvSpPr>
                <p:cNvPr id="{{shape_id}}" name="Text {{shape_id}}"/>
                <p:cNvSpPr/>
                <p:nvPr/>
            </p:nvSpPr>
            <p:spPr>
                <a:xfrm>
                    <a:off x="{bounds.x}" y="{bounds.y}"/>
                    <a:ext cx="{bounds.width}" cy="{bounds.height}"/>
                </a:xfrm>
                <a:prstGeom prst="rect">
                    <a:avLst/>
                </a:prstGeom>
                <a:ln>
                    <a:noFill/>
                </a:ln>
            </p:spPr>
            <p:txBody>
                <a:bodyPr wrap="square" rtlCol="0" anchor="t"/>
                <a:lstStyle/>
                <a:p>
                    <a:r>
                        <a:rPr lang="en-US" sz="{size_units}"
                               b="{'1' if is_bold else '0'}"
                               i="{'1' if is_italic else '0'}">
                            <a:latin typeface="{font_family}"/>
                        </a:rPr>
                        <a:t>{text}</a:t>
                    </a:r>
                </a:p>
            </p:txBody>
        </p:sp>'''
```

### 6. Integration Point (`src/svg2drawingml.py`)

Update main converter to use proper service initialization:

```python
def convert(self, svg_content: str) -> str:
    """Convert SVG to DrawingML with proper service wiring."""

    # Parse SVG
    self.parser = SVGParser(svg_content)

    # Initialize services with viewport mapping
    STANDARD_SLIDE_WIDTH_EMU = 9144000   # 10 inches
    STANDARD_SLIDE_HEIGHT_EMU = 6858000  # 7.5 inches

    self.services = ConversionServices.create_with_viewport(
        self.parser.root, STANDARD_SLIDE_WIDTH_EMU, STANDARD_SLIDE_HEIGHT_EMU
    )

    # Create converter registry with properly wired services
    registry = ConverterRegistry(self.services)
    registry.register_all_standard_converters()

    # Rest of conversion process...
```

## Implementation Plan

### Phase 1: Service Infrastructure
1. ✅ Create `FontService` in `src/services/font_service.py`
2. ✅ Create `ViewportService` in `src/services/viewport_service.py`
3. ✅ Update `ConversionServices` to include new services
4. ✅ Create `text_layout.py` with coordinate transformation logic

### Phase 2: Converter Integration
1. ✅ Update `TextConverter` to use `svg_text_to_ppt_box`
2. ✅ Ensure service dependency injection follows ADR-002 patterns
3. ✅ Update service initialization in main converter

### Phase 3: Testing & Validation
1. ⏳ Add unit tests for text coordinate transformation
2. ⏳ Test with W3C compliance SVG
3. ⏳ Validate text positioning accuracy improvements

## Benefits

1. **Architectural Compliance**: Follows ADR-002 and ADR-004 specifications
2. **Proper Coordinate System**: SVG baseline → PowerPoint top-left conversion
3. **Service Injection**: Font and viewport services properly wired
4. **Text Anchor Support**: Correct `text-anchor="middle|end"` positioning
5. **Font Metrics**: Proper ascent/descent calculations
6. **Testable Design**: Services can be mocked for unit testing

## Acceptance Criteria

- [ ] Text positioning accuracy > 90% for W3C test elements
- [ ] `text-anchor="middle"` centers text on baseline X coordinate
- [ ] `text-anchor="end"` right-aligns text to baseline X coordinate
- [ ] Font baseline correctly converted to textbox top-left
- [ ] Service dependencies properly injected per ADR-002
- [ ] No hardcoded slide dimensions or font fallbacks
- [ ] All text elements use mapped PowerPoint typefaces

## Validation Command

```bash
source venv/bin/activate && PYTHONPATH=. python comprehensive_debug_system.py
# Expected: "Text Position Accuracy: >90%" in output
```