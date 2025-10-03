# Text Converter Critical Fixes

## Overview
The text converter has several critical bugs that cause misalignment, incorrect positioning, and loss of styling. These fixes address the core issues with horizontal alignment, coordinate transformation, baseline handling, and per-tspan styling.

## 1. Fix Horizontal Alignment Bug + Clean Anchor Handling

**Problem**: Double mapping of text anchor values causes wrong alignment.
- `_get_text_anchor()` returns already-mapped values (l|ctr|r)
- Later code maps again, yielding incorrect alignment

**Solution**: Return raw SVG values (start|middle|end), then map once where we build the shape.

```python
# BEFORE: Double mapping bug
TEXT_ANCHORS = {
    'start': 'l',    # left
    'middle': 'ctr', # center
    'end': 'r'       # right
}

def _get_text_anchor(self, element: ET.Element) -> str:
    text_anchor = element.get('text-anchor', 'start')
    return self.TEXT_ANCHORS.get(text_anchor, 'l')  # First mapping

# Later in code - SECOND mapping causes bug
align_map = {'start': 'l', 'middle': 'ctr', 'end': 'r'}
align = align_map.get(text_anchor, 'l')  # Double mapping!

# AFTER: Single mapping
TEXT_ANCHORS = {'start', 'middle', 'end'}  # Keep raw values

def _get_text_anchor(self, element: ET.Element) -> str:
    """Get raw SVG text-anchor: 'start' | 'middle' | 'end'"""
    return element.get('text-anchor', 'start')

# Map once in _convert_to_text_shape:
text_anchor = self._get_text_anchor(element)  # 'start'|'middle'|'end'
align = {'start': 'l', 'middle': 'ctr', 'end': 'r'}.get(text_anchor, 'l')
```

## 2. Use ConversionContext Consistently for Coordinates

**Problem**: Manual viewport math instead of using robust coordinate pipeline.
- Ad-hoc parsing and manual slide calculations
- Doesn't respect viewBox + transforms properly

**Solution**: Replace manual coordinate handling with context helpers.

```python
# BEFORE: Manual coordinate transformation
try:
    x_str = element.get('x', '0')
    y_str = element.get('y', '0')
    coord_result = self.services.coordinate_transformer.parse_coordinate_string(f"{x_str},{y_str}")
    if coord_result.coordinates:
        x, y = coord_result.coordinates[0]
    else:
        x = float(x_str) if x_str else 0.0
        y = float(y_str) if y_str else 0.0

    # Manual transform application
    transform_attr = element.get('transform', '')
    if transform_attr:
        x, y = self.apply_transform(transform_attr, x, y, context.viewport_context)
except Exception:
    x, y = 0.0, 0.0

# AFTER: Use context transformation pipeline
x_val = element.get('x', '0')
y_val = element.get('y', '0')
try:
    x = float(x_val) if x_val else 0.0
    y = float(y_val) if y_val else 0.0
except Exception:
    x, y = 0.0, 0.0

# Transform from SVG user units → EMU using context (honors CTM)
try:
    x_emu, y_emu = context.transform_point(x, y)
except Exception:
    if context.coordinate_system:
        x_emu, y_emu = context.coordinate_system.svg_to_emu(x, y)
    else:
        x_emu, y_emu = int(x * 9525), int(y * 9525)
```

## 3. Generate Paragraph Alignment Correctly

**Problem**: Misusing `bodyPr.anchor` for horizontal alignment.
- `a:bodyPr@anchor` is vertical anchoring ("t/mid/b/ctr"), not horizontal
- Horizontal alignment should be in `<a:pPr algn="...">`

**Solution**: Separate vertical and horizontal alignment properly.

```python
# BEFORE: Confused vertical/horizontal alignment
bodyPr = ET.SubElement(
    txBody, _q("a:bodyPr"),
    vertOverflow="ellipsis",
    wrap="square",
    rtlCol="0",
    anchor="ctr" if align == "ctr" else "t",  # WRONG: horizontal in vertical
    anchorCtr="1" if align == "ctr" else "0",
)

# AFTER: Correct separation
bodyPr = ET.SubElement(
    txBody, _q("a:bodyPr"),
    vertOverflow="ellipsis",
    wrap="square",
    rtlCol="0",
    anchor="t",     # Vertical: top by default
    anchorCtr="0",
)

# Horizontal alignment in paragraph properties
if align in ("ctr", "r", "l", "just"):
    ET.SubElement(p, _q("a:pPr"), algn=("ctr" if align == "ctr" else align))
```

## 4. Fix Baseline Handling

**Problem**: Over-adjusting baseline makes text "drift".
- Large ad-hoc offsets cause visible positioning errors
- Complex fallback calculations compound inaccuracies

**Solution**: Keep minimal, conservative baseline adjustment.

```python
# BEFORE: Complex baseline adjustment with large offsets
try:
    font_metrics = self._get_font_metrics_for_measurement(font_family, '400', 'normal')
    if font_metrics:
        baseline_offset = self._calculate_baseline_offset(font_size, font_metrics)
        adjusted_y += baseline_offset
    else:
        baseline_offset = self._calculate_enhanced_baseline_offset(font_family, font_size)
        adjusted_y += baseline_offset
except Exception:
    baseline_offset = int(font_size * 0.15 * 9525)  # Large 15% offset
    adjusted_y += baseline_offset

# AFTER: Conservative baseline correction
try:
    font_metrics = self._get_font_metrics_for_measurement(font_family, '400', 'normal')
    baseline_offset = self._calculate_baseline_offset(font_size, font_metrics) if font_metrics else 0
    adjusted_y += baseline_offset
except Exception:
    pass  # Trust PPTX text box positioning

# Make _calculate_baseline_offset conservative:
baseline_offset_ratio = ascender_ratio * 0.05  # 5% instead of 20%
```

## 5. Respect tspan → Multiple Runs (and Newlines)

**Problem**: All content collapsed into one run, losing inline styling and line breaks.
- No support for per-tspan styling
- Missing line break handling

**Solution**: Build runs per `<tspan>`, create newlines for positioned tspans.

```python
# BEFORE: Collapsed single run
def _extract_text_content(self, element: ET.Element) -> str:
    text_parts = []
    if element.text:
        text_parts.append(element.text.strip())
    for child in element:
        if child.tag.endswith('tspan'):
            if child.text:
                text_parts.append(child.text.strip())
        if child.tail:
            text_parts.append(child.tail.strip())
    return ' '.join(text_parts)

# AFTER: Preserve line breaks and structure
def _extract_text_content(self, element: ET.Element) -> str:
    parts: List[str] = []
    if element.text:
        parts.append(element.text.replace('\r', ''))
    for child in element:
        tag = child.tag.split('}')[-1]
        if tag == 'tspan':
            if child.get('x') or child.get('y'):
                parts.append('\n')  # New line for positioned tspan
            if child.text:
                parts.append(child.text.replace('\r', ''))
        if child.tail:
            parts.append(child.tail.replace('\r', ''))

    text = ''.join(parts)
    lines = [ln.strip() for ln in text.split('\n')]
    return '\n'.join([ln for ln in lines if ln != ''])

# Create multiple paragraphs (one <a:p> per line)
for idx, line in enumerate(text.split('\n')):
    p = ET.SubElement(txBody, _q("a:p"))
    if align in ("ctr", "r", "l", "just"):
        ET.SubElement(p, _q("a:pPr"), algn=("ctr" if align == "ctr" else align))
    # ... create run for each line
```

## 6. Make Min Readability Configurable

**Problem**: Forced 18pt minimum can override designer intent.

**Solution**: Gate behind config flag.

```python
# BEFORE: Forced readability boost
MIN_READABLE_FONT_SIZE = 18
if font_size < MIN_READABLE_FONT_SIZE:
    font_size = max(font_size * 1.8, MIN_READABLE_FONT_SIZE)

# AFTER: Configurable
def __init__(...):
    self.enforce_min_readable_pt = getattr(services, "config", {}).get("enforce_min_readable_pt", False)
    self.min_readable_pt = getattr(services, "config", {}).get("min_readable_pt", 18)

if self.enforce_min_readable_pt and font_size < self.min_readable_pt:
    font_size = max(font_size * 1.2, self.min_readable_pt)
```

## 7. Default Color Should Be Black

**Problem**: Default red color is unexpected.

**Solution**: Use black as default.

```python
# BEFORE
if not fill_color:
    return 'FF0000'  # Default red

# AFTER
if not fill_color:
    return '000000'  # Default black
```

## 8. Per-tspan Run Styling

**Major Enhancement**: Support individual styling per `<tspan>` element.

### New Multi-Run Architecture

```python
def make_text_shape(
    *,
    shape_id: int,
    name: str,
    x_emu: int,
    y_emu: int,
    w_emu: int,
    h_emu: int,
    lines: list,  # List[List[run_dict]]
    align: str = "l",
):
    """
    lines: List[List[{
        "text": str,
        "font_size_pt": float,
        "rgb": "RRGGBB",
        "bold": bool,
        "italic": bool,
        "underline": bool,
        "strike": bool,
        "font_family": Optional[str]
    }]]
    """
```

### Style Collection from tspans

```python
def _collect_text_runs(self, element: ET.Element) -> list:
    """
    Build structured lines with per-run styling from <text> and nested <tspan>.
    Rules:
      - A <tspan> with explicit x/y starts a new paragraph line
      - Styles cascade: parent <text>/<tspan> → child <tspan>
    """
    base_style = self._read_text_style(element)
    lines = [[]]  # Start with one empty line

    def push(text: str, style: dict):
        if not text:
            return
        lines[-1].append({
            "text": text,
            "font_family": style["font_family"],
            "font_size_pt": style["font_size_pt"],
            "bold": style["bold"],
            "italic": style["italic"],
            "underline": style["underline"],
            "strike": style["strike"],
            "rgb": style["rgb"],
        })

    # Process text nodes and tspans with style inheritance
    # ...
```

### Run Generation

```python
for idx, runs in enumerate(lines):
    p = ET.SubElement(txBody, _q("a:p"))
    if align in ("ctr", "r", "l", "just"):
        ET.SubElement(p, _q("a:pPr"), algn=("ctr" if align == "ctr" else align))

    for run in runs:
        r = ET.SubElement(p, _q("a:r"))
        rPr = ET.SubElement(
            r, _q("a:rPr"),
            lang="en-US",
            sz=str(int(round(run.get("font_size_pt", 24.0) * 100))),
            b="1" if run.get("bold") else "0",
            i="1" if run.get("italic") else "0",
            dirty="0",
        )

        # Underline/strikethrough
        if run.get("underline"):
            rPr.set("u", "sng")
        if run.get("strike"):
            rPr.set("strike", "sngStrike")

        # Color and font
        rgb = (run.get("rgb") or "000000").upper()
        solidFill = ET.SubElement(rPr, _q("a:solidFill"))
        ET.SubElement(solidFill, _q("a:srgbClr"), val=rgb)

        latin = ET.SubElement(rPr, _q("a:latin"))
        latin.set("typeface", run.get("font_family") or "+mn-lt")

        t_el = ET.SubElement(r, _q("a:t"))
        t_el.text = run.get("text", "")

    ET.SubElement(p, _q("a:endParaRPr"))
```

## Benefits

1. **Correct Alignment**: Horizontal and vertical alignment work as expected
2. **Accurate Positioning**: Coordinates respect viewBox and transforms
3. **Preserved Styling**: Per-tspan fonts, colors, weights maintained
4. **Line Breaks**: Positioned tspans create proper paragraph breaks
5. **Configurable**: Min font size boost can be disabled
6. **Robust Baseline**: Minimal, metrics-based positioning adjustments
7. **Standard Colors**: Black default instead of red

## Implementation Impact

- **Fixes critical text positioning bugs** in W3C test suite
- **Enables rich text support** with inline styling
- **Maintains backward compatibility** through configuration flags
- **Reduces text positioning drift** under complex transforms
- **Improves PowerPoint rendering fidelity** significantly

These fixes address the major text conversion issues that cause failures in comprehensive testing scenarios.