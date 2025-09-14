# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-09-14-advanced-svg-ooxml-precision/spec.md

## Technical Requirements

### 1. Subpixel Precision System Enhancement

**Current State**: EMU conversion uses integer coordinates limiting precision to ~1/914,400 inch
**Enhancement**: Implement fractional EMU coordinates within DrawingML's 21,600 coordinate space

- Extend `UnitConverter` class with `fractional_emu_mode` parameter
- Implement `to_fractional_emu()` method with configurable precision factor (1x to 1000x)
- Update all path coordinate conversion to support fractional values
- Add precision validation to ensure PowerPoint compatibility (max 3 decimal places recommended)

### 2. Advanced Gradient Engine

**Per-mille Precision Enhancement**:
- Extend current gradient system from integer per-mille (0-1000) to fractional positioning (0.0-1000.0)
- Implement gradient stop interpolation with floating-point precision
- Add support for alpha channel precision using 100,000-unit scale

**Mesh Gradient Implementation**:
- Create mesh gradients using overlapping radial gradients with precise positioning
- Implement 4-corner color interpolation using PowerPoint's native gradient blending
- Use custom geometry paths to create mesh-like regions with individual gradient fills

### 3. Filter Effects Pipeline

**OOXML Effect Mapping Strategy**:
- Map `feGaussianBlur` → PowerPoint's `<a:blur>` with radius precision
- Implement `feDropShadow` → PowerPoint's `<a:outerShdw>` with OOXML precision
- Chain effects using PowerPoint's effect groups: `<a:effectLst>` containers
- Create composite effects using PowerPoint's blending modes

**Filter Primitive Implementation**:
- `feImage`: Map to PowerPoint's `<a:blipFill>` with image effects
- `feMerge`: Use PowerPoint's grouped shapes with blend modes
- `feComponentTransfer`: Map to PowerPoint's color adjustment effects

### 4. Pattern Fill System

**Advanced Pattern Support**:
- Implement nested patterns using PowerPoint's texture fills with transforms
- Support pattern `viewBox` using custom coordinate space scaling
- Handle pattern inheritance through PowerPoint's style system
- Map SVG pattern units to PowerPoint's pattern scaling modes

**OOXML Pattern Implementation**:
- Use `<a:pattFill>` for simple patterns with `prst` attribute
- Implement complex patterns using `<a:grpSpPr>` with repeated shapes
- Apply pattern transforms using PowerPoint's shape transformation matrix

### 5. Text-on-Path Enhancement

**Precise Path Following**:
- Implement text positioning using PowerPoint's `<a:pathLst>` custom geometry
- Calculate character positioning with subpixel precision along curve segments
- Handle font metrics with EMU-level accuracy for proper character spacing
- Support text baseline adjustments using PowerPoint's text effects

**Typography Integration**:
- Map SVG `textPath` attributes to PowerPoint's text wrapping properties
- Implement letter spacing and word spacing with EMU precision
- Handle text direction and orientation using PowerPoint's text rotation

### 6. Precision Coordinate System

**Fractional Coordinate Implementation**:
```python
class AdvancedCoordinateSystem:
    def __init__(self, precision_mode: str = "subpixel"):
        self.precision_factor = {"standard": 1, "subpixel": 100, "ultra": 1000}[precision_mode]

    def to_precise_drawingml_coords(self, svg_x: float, svg_y: float) -> tuple[float, float]:
        # Convert with fractional precision within 21,600 coordinate space
        base_x = (svg_x / self.svg_width) * 21600
        base_y = (svg_y / self.svg_height) * 21600
        return (base_x * self.precision_factor, base_y * self.precision_factor)
```

**PowerPoint Compatibility Requirements**:
- Maintain coordinate values within PowerPoint's acceptable ranges
- Ensure generated OOXML validates against PowerPoint's schema
- Test compatibility across PowerPoint 2016, 2019, 2021, and Office 365
- Implement fallback modes for older PowerPoint versions

### 7. Performance Optimization

**Precision vs Performance Balance**:
- Implement adaptive precision scaling based on shape complexity
- Cache fractional coordinate calculations for repeated operations
- Optimize OOXML output size by truncating unnecessary decimal places
- Use precision only where visually significant (>0.1px difference)

**Memory Management**:
- Stream OOXML generation for large documents with precision coordinates
- Implement coordinate precision garbage collection for intermediate calculations
- Optimize gradient stop storage for high-precision gradients

## External Dependencies

### New Libraries Required

- **`lxml`** version >= 4.9.0 - Enhanced XML generation with decimal precision support
  - **Justification**: Current XML generation may not handle floating-point coordinates with sufficient precision for advanced OOXML features

- **`spectra`** version >= 0.0.11 - Advanced color space operations and interpolation for mesh gradients
  - **Justification**: Mesh gradient interpolation requires precise color blending, HSL/RGB conversions, and color space calculations. Spectra provides a clean API for color manipulation and interpolation that's more focused than NumPy for color operations
  - **GitHub**: https://github.com/jsvine/spectra

### Optional Performance Enhancement

- **`numba`** version >= 0.56.0 - JIT compilation for coordinate transformation hot paths
  - **Justification**: Fractional coordinate calculations may become performance bottlenecks for complex SVGs; JIT compilation could provide significant speedup