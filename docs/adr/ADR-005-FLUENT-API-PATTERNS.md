# ADR-005: Fluent API Patterns

**Status**: PROPOSED
**Date**: 2025-01-20
**Context**: Enhance developer experience with fluent API patterns for complex operations

## Decision

Implement **fluent API patterns** across core systems to provide intuitive, chainable interfaces for complex operations while maintaining the clean module structure from ADR-001 and ADR-002.

## Fluent API Design Principles

### 1. Method Chaining
- Return `self` from configuration methods
- Return new instances from transformation methods
- Clear distinction between mutating and non-mutating operations

### 2. Progressive Configuration
- Start with simple cases, allow complex configuration
- Sensible defaults at each step
- Validation at final execution

### 3. Readable Intent
- Method names clearly express intent
- Natural language flow
- Self-documenting API patterns

## Core System Fluent APIs

### 1. Units System Fluent Interface

**File**: `src/units/core.py`
```python
class UnitConverter:
    """Unified unit converter with fluent API."""

    def __init__(self, context: Optional[ConversionContext] = None):
        self._context = context or ConversionContext()

    # Fluent configuration methods
    def with_dpi(self, dpi: float) -> 'UnitConverter':
        """Set DPI and return new converter instance."""
        new_context = self._context.with_dpi(dpi)
        return UnitConverter(new_context)

    def with_viewport(self, width: str, height: str) -> 'UnitConverter':
        """Set viewport dimensions and return new converter instance."""
        new_context = self._context.with_viewport(width, height)
        return UnitConverter(new_context)

    def for_axis(self, axis: str) -> 'AxisConverter':
        """Create axis-specific converter for chaining."""
        return AxisConverter(self, axis)

    # Conversion methods
    def to_emu(self, value: str, axis: str = 'x') -> int:
        """Convert value to EMU."""
        pass

    def batch_convert(self, values: List[str]) -> 'BatchConverter':
        """Create batch converter for chaining."""
        return BatchConverter(self, values)

class AxisConverter:
    """Axis-specific converter for fluent operations."""

    def __init__(self, converter: UnitConverter, axis: str):
        self._converter = converter
        self._axis = axis

    def convert(self, value: str) -> int:
        """Convert value using specified axis."""
        return self._converter.to_emu(value, self._axis)

    def batch(self, values: List[str]) -> List[int]:
        """Convert multiple values for this axis."""
        return [self.convert(v) for v in values]

class BatchConverter:
    """Batch conversion with fluent configuration."""

    def __init__(self, converter: UnitConverter, values: List[str]):
        self._converter = converter
        self._values = values
        self._axis = 'x'

    def for_axis(self, axis: str) -> 'BatchConverter':
        """Set axis for batch conversion."""
        self._axis = axis
        return self

    def to_emu(self) -> List[int]:
        """Execute batch conversion to EMU."""
        return [self._converter.to_emu(v, self._axis) for v in self._values]

    def to_pixels(self) -> List[float]:
        """Execute batch conversion to pixels."""
        return [self._converter.to_pixels(v) for v in self._values]
```

**Usage Examples**:
```python
# Modern ConversionServices pattern (recommended)
from src.services.conversion_services import ConversionServices
services = ConversionServices.create_default()
converter = services.unit_converter
emu_value = converter.to_emu("100px")

# Legacy pattern (still supported with service-aware fallback)
converter = UnitConverter()  # Will use ConversionServices internally
emu_value = converter.to_emu("100px")

# Fluent configuration (legacy)
converter = (UnitConverter()
    .with_dpi(96.0)
    .with_viewport("800px", "600px"))

# Axis-specific operations
x_converter = converter.for_axis('x')
x_values = x_converter.batch(["100px", "200px", "300px"])

# Batch operations
batch_emu = (converter
    .batch_convert(["100px", "200px", "50mm"])
    .for_axis('x')
    .to_emu())
```

### 2. Transform System Fluent Interface

**File**: `src/transforms/core.py`
```python
class Transform:
    """Transform builder with fluent API."""

    def __init__(self, matrix: Optional[np.ndarray] = None):
        self._matrix = matrix if matrix is not None else np.eye(3)

    # Fluent transform operations
    def translate(self, x: float, y: float) -> 'Transform':
        """Add translation and return new transform."""
        translation_matrix = np.array([
            [1, 0, x],
            [0, 1, y],
            [0, 0, 1]
        ])
        return Transform(self._matrix @ translation_matrix)

    def scale(self, sx: float, sy: Optional[float] = None) -> 'Transform':
        """Add scaling and return new transform."""
        sy = sy or sx
        scale_matrix = np.array([
            [sx, 0, 0],
            [0, sy, 0],
            [0, 0, 1]
        ])
        return Transform(self._matrix @ scale_matrix)

    def rotate(self, angle: float, cx: float = 0, cy: float = 0) -> 'Transform':
        """Add rotation and return new transform."""
        rad = np.radians(angle)
        cos_a, sin_a = np.cos(rad), np.sin(rad)

        # Translate to origin, rotate, translate back
        return (self
            .translate(-cx, -cy)
            ._apply_rotation_matrix(cos_a, sin_a)
            .translate(cx, cy))

    def _apply_rotation_matrix(self, cos_a: float, sin_a: float) -> 'Transform':
        """Apply rotation matrix (internal method)."""
        rotation_matrix = np.array([
            [cos_a, -sin_a, 0],
            [sin_a, cos_a, 0],
            [0, 0, 1]
        ])
        return Transform(self._matrix @ rotation_matrix)

    # Configuration and validation
    def with_precision(self, decimal_places: int) -> 'Transform':
        """Set precision for final output."""
        # Return precision-configured transform
        pass

    def validate(self) -> 'Transform':
        """Validate transform matrix."""
        # Validation logic
        return self

    # Terminal operations
    def apply_to(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Apply transform to points."""
        pass

    def to_svg_string(self) -> str:
        """Convert to SVG transform string."""
        pass

    def to_matrix_string(self) -> str:
        """Convert to CSS matrix string."""
        pass

class TransformBuilder:
    """Fluent builder for complex transforms."""

    @staticmethod
    def create() -> Transform:
        """Create new identity transform."""
        return Transform()

    @staticmethod
    def from_svg(transform_string: str) -> Transform:
        """Parse SVG transform string."""
        pass

    @staticmethod
    def from_matrix(matrix: np.ndarray) -> Transform:
        """Create from matrix."""
        return Transform(matrix)
```

**Usage Examples**:
```python
# Simple transform chain
transform = (Transform()
    .translate(100, 50)
    .scale(1.5)
    .rotate(45, cx=100, cy=50))

# Complex transform with validation
transform = (TransformBuilder
    .from_svg("translate(50,100) scale(2)")
    .rotate(30)
    .with_precision(2)
    .validate())

# Apply to coordinates
transformed_points = transform.apply_to([(0, 0), (100, 100)])
```

### 3. Animation System Fluent Interface

**File**: `src/animations/core.py`
```python
class AnimationBuilder:
    """Fluent builder for animation definitions."""

    def __init__(self):
        self._element_id = None
        self._animation_type = None
        self._target_attribute = None
        self._values = []
        self._timing = None
        self._easing = None

    # Element targeting
    def target(self, element_id: str) -> 'AnimationBuilder':
        """Set target element ID."""
        self._element_id = element_id
        return self

    def animate(self, attribute: str) -> 'AnimationBuilder':
        """Set animation type to animate and target attribute."""
        self._animation_type = AnimationType.ANIMATE
        self._target_attribute = attribute
        return self

    def animate_transform(self, transform_type: str) -> 'AnimationBuilder':
        """Set animation type to animateTransform."""
        self._animation_type = AnimationType.ANIMATE_TRANSFORM
        self._target_attribute = transform_type
        return self

    def animate_motion(self) -> 'AnimationBuilder':
        """Set animation type to animateMotion."""
        self._animation_type = AnimationType.ANIMATE_MOTION
        return self

    # Value configuration
    def from_to(self, from_val: str, to_val: str) -> 'AnimationBuilder':
        """Set from and to values."""
        self._values = [from_val, to_val]
        return self

    def values(self, *values: str) -> 'AnimationBuilder':
        """Set multiple values."""
        self._values = list(values)
        return self

    def along_path(self, path_data: str) -> 'AnimationBuilder':
        """Set motion path data."""
        self._values = [path_data]
        return self

    # Timing configuration
    def duration(self, dur: str) -> 'TimingBuilder':
        """Configure timing (returns timing builder)."""
        return TimingBuilder(self).duration(dur)

    def with_timing(self, timing: AnimationTiming) -> 'AnimationBuilder':
        """Set pre-configured timing."""
        self._timing = timing
        return self

    # Easing configuration
    def with_easing(self, easing_type: str) -> 'AnimationBuilder':
        """Set easing type."""
        self._easing = easing_type
        return self

    def with_bezier_easing(self, x1: float, y1: float, x2: float, y2: float) -> 'AnimationBuilder':
        """Set cubic Bezier easing."""
        self._easing = f"cubic-bezier({x1},{y1},{x2},{y2})"
        return self

    # Terminal operations
    def build(self) -> AnimationDefinition:
        """Build final animation definition."""
        if not self._element_id:
            raise ValueError("Element ID is required")
        if not self._animation_type:
            raise ValueError("Animation type is required")

        return AnimationDefinition(
            element_id=self._element_id,
            animation_type=self._animation_type,
            target_attribute=self._target_attribute,
            values=self._values,
            timing=self._timing,
            # ... other properties
        )

    def to_powerpoint(self) -> str:
        """Build and convert to PowerPoint XML."""
        animation_def = self.build()
        # Convert to PowerPoint
        pass

class TimingBuilder:
    """Fluent builder for animation timing."""

    def __init__(self, parent: AnimationBuilder):
        self._parent = parent
        self._duration = 1.0
        self._begin = 0.0
        self._repeat_count = 1
        self._fill_mode = FillMode.REMOVE

    def duration(self, dur: str) -> 'TimingBuilder':
        """Set duration."""
        self._duration = self._parse_duration(dur)
        return self

    def begin_at(self, begin: str) -> 'TimingBuilder':
        """Set begin time."""
        self._begin = self._parse_time(begin)
        return self

    def repeat(self, count: Union[int, str]) -> 'TimingBuilder':
        """Set repeat count."""
        if count == "indefinite":
            self._repeat_count = "indefinite"
        else:
            self._repeat_count = int(count)
        return self

    def fill_mode(self, mode: str) -> 'TimingBuilder':
        """Set fill mode."""
        self._fill_mode = FillMode(mode)
        return self

    def and_then(self) -> AnimationBuilder:
        """Return to animation builder with timing configured."""
        timing = AnimationTiming(
            begin=self._begin,
            duration=self._duration,
            repeat_count=self._repeat_count,
            fill_mode=self._fill_mode
        )
        return self._parent.with_timing(timing)

    def _parse_duration(self, dur: str) -> float:
        """Parse duration string."""
        pass

    def _parse_time(self, time: str) -> float:
        """Parse time string."""
        pass

class AnimationSequence:
    """Fluent builder for animation sequences."""

    def __init__(self):
        self._animations = []

    def add(self, animation: AnimationDefinition) -> 'AnimationSequence':
        """Add animation to sequence."""
        self._animations.append(animation)
        return self

    def then(self, builder: AnimationBuilder) -> 'AnimationSequence':
        """Add animation from builder to sequence."""
        return self.add(builder.build())

    def parallel(self, *builders: AnimationBuilder) -> 'AnimationSequence':
        """Add parallel animations."""
        for builder in builders:
            self.add(builder.build())
        return self

    def with_stagger(self, delay: str) -> 'AnimationSequence':
        """Set stagger delay between animations."""
        # Apply stagger delay
        return self

    def to_powerpoint(self) -> str:
        """Convert sequence to PowerPoint XML."""
        pass
```

**Usage Examples**:
```python
# Simple fade animation
animation = (AnimationBuilder()
    .target("rect1")
    .animate("opacity")
    .from_to("0", "1")
    .duration("2s")
    .and_then()
    .with_easing("ease-in-out")
    .build())

# Complex transform animation
animation = (AnimationBuilder()
    .target("circle1")
    .animate_transform("rotate")
    .values("0", "180", "360")
    .duration("3s")
    .begin_at("1s")
    .repeat("indefinite")
    .fill_mode("freeze")
    .and_then()
    .with_bezier_easing(0.25, 0.1, 0.25, 1.0)
    .to_powerpoint())

# Motion path animation
animation = (AnimationBuilder()
    .target("moving-element")
    .animate_motion()
    .along_path("M 0,0 Q 50,25 100,0")
    .duration("5s")
    .and_then()
    .to_powerpoint())

# Animation sequence
sequence = (AnimationSequence()
    .then(AnimationBuilder()
        .target("rect1")
        .animate("opacity")
        .from_to("0", "1")
        .duration("1s"))
    .then(AnimationBuilder()
        .target("rect2")
        .animate("opacity")
        .from_to("0", "1")
        .duration("1s"))
    .with_stagger("0.5s")
    .to_powerpoint())

# Parallel animations
sequence = (AnimationSequence()
    .parallel(
        AnimationBuilder().target("rect1").animate("opacity").from_to("0", "1").duration("2s"),
        AnimationBuilder().target("rect1").animate_transform("scale").from_to("1", "1.5").duration("2s")
    )
    .to_powerpoint())
```

### 4. Path System Fluent Interface

**File**: `src/paths/engine.py`
```python
class PathBuilder:
    """Fluent builder for SVG paths."""

    def __init__(self):
        self._commands = []

    # Movement commands
    def move_to(self, x: float, y: float) -> 'PathBuilder':
        """Add moveTo command."""
        self._commands.append(f"M {x},{y}")
        return self

    def line_to(self, x: float, y: float) -> 'PathBuilder':
        """Add lineTo command."""
        self._commands.append(f"L {x},{y}")
        return self

    def horizontal_to(self, x: float) -> 'PathBuilder':
        """Add horizontal line command."""
        self._commands.append(f"H {x}")
        return self

    def vertical_to(self, y: float) -> 'PathBuilder':
        """Add vertical line command."""
        self._commands.append(f"V {y}")
        return self

    # Curve commands
    def cubic_to(self, x1: float, y1: float, x2: float, y2: float, x: float, y: float) -> 'PathBuilder':
        """Add cubic Bézier curve."""
        self._commands.append(f"C {x1},{y1} {x2},{y2} {x},{y}")
        return self

    def quadratic_to(self, x1: float, y1: float, x: float, y: float) -> 'PathBuilder':
        """Add quadratic Bézier curve."""
        self._commands.append(f"Q {x1},{y1} {x},{y}")
        return self

    def arc_to(self, rx: float, ry: float, angle: float, large_arc: bool, sweep: bool, x: float, y: float) -> 'PathBuilder':
        """Add elliptical arc."""
        large = 1 if large_arc else 0
        sweep_flag = 1 if sweep else 0
        self._commands.append(f"A {rx},{ry} {angle} {large},{sweep_flag} {x},{y}")
        return self

    # Path operations
    def close(self) -> 'PathBuilder':
        """Close current subpath."""
        self._commands.append("Z")
        return self

    # Shape builders
    def rectangle(self, x: float, y: float, width: float, height: float) -> 'PathBuilder':
        """Add rectangle as path commands."""
        return (self
            .move_to(x, y)
            .horizontal_to(x + width)
            .vertical_to(y + height)
            .horizontal_to(x)
            .close())

    def circle(self, cx: float, cy: float, r: float) -> 'PathBuilder':
        """Add circle as path commands."""
        return (self
            .move_to(cx + r, cy)
            .arc_to(r, r, 0, False, True, cx - r, cy)
            .arc_to(r, r, 0, False, True, cx + r, cy)
            .close())

    # Terminal operations
    def to_string(self) -> str:
        """Build path string."""
        return " ".join(self._commands)

    def to_path_data(self) -> PathData:
        """Build PathData object."""
        return PathData.from_string(self.to_string())

    def optimize(self) -> 'PathBuilder':
        """Optimize path commands."""
        # Apply optimization
        return self
```

**Usage Examples**:
```python
# Simple rectangle path
path = (PathBuilder()
    .rectangle(10, 10, 100, 50)
    .to_string())

# Complex curved path
path = (PathBuilder()
    .move_to(50, 50)
    .cubic_to(75, 25, 125, 25, 150, 50)
    .line_to(150, 100)
    .quadratic_to(125, 125, 100, 100)
    .close()
    .optimize()
    .to_path_data())

# Circle with custom radius
circle_path = (PathBuilder()
    .circle(100, 100, 50)
    .to_string())
```

## Integration with Existing ADR Patterns

### 1. Service Integration
Fluent APIs integrate with dependency injection from ADR-002:

```python
class AnimationConverter(BaseConverter):
    def __init__(self, services: ConversionServices):
        super().__init__(services)
        self.animation_builder = AnimationBuilder(services)

    def convert_with_fluent_api(self, element: ET.Element) -> str:
        return (self.animation_builder
            .target(element.get('id'))
            .animate(element.get('attributeName'))
            .from_to(element.get('from'), element.get('to'))
            .duration(element.get('dur'))
            .and_then()
            .to_powerpoint())
```

### 2. Module Structure
Fluent builders live within their respective modules following ADR-001:

```
src/
├── units/
│   ├── core.py                 # UnitConverter + fluent methods
│   └── builders.py             # AxisConverter, BatchConverter
├── transforms/
│   ├── core.py                 # Transform + fluent methods
│   └── builders.py             # TransformBuilder
├── animations/
│   ├── core.py                 # AnimationDefinition
│   └── builders.py             # AnimationBuilder, TimingBuilder
└── paths/
    ├── engine.py               # PathEngine
    └── builders.py             # PathBuilder
```

## Benefits

1. **Developer Experience**: Intuitive, self-documenting APIs
2. **Type Safety**: Full TypeScript-like type inference in modern IDEs
3. **Discoverability**: Method chaining reveals available options
4. **Validation**: Progressive validation at each step
5. **Flexibility**: Start simple, add complexity as needed

## Implementation Guidelines

1. **Return Types**: Always return `self` for configuration, new instances for transformations
2. **Validation**: Validate incrementally, fail fast with clear messages
3. **Defaults**: Provide sensible defaults at each step
4. **Documentation**: Each fluent method should have clear docstrings
5. **Testing**: Test fluent chains as complete scenarios

This ADR establishes fluent API patterns that enhance the developer experience while maintaining the clean architecture established in previous ADRs.