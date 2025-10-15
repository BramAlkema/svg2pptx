# ADR-018: SVG Marker System Migration to Clean Slate Architecture

**Status**: PROPOSED
**Date**: 2025-10-15
**Context**: 696-line marker implementation exists in archive but not migrated to Clean Slate pipeline
**Related**: ADR-015 (Clipping Pipeline), ADR-006 (Animation System), ADR-002 (Converter Architecture)

---

## Problem Statement

SVG markers (arrowheads, line decorations, symbols) are essential for technical diagrams, flowcharts, and professional graphics. A comprehensive 696-line marker implementation exists in the archive (`archive/legacy-src/converters/markers.py`, commit 8eab950) but was not migrated during the Clean Slate architecture refactor.

**Current State:**
- ✅ Full marker implementation exists (696 lines, production-tested)
- ❌ Not integrated with Clean Slate IR/Mapper architecture
- ❌ No marker support in current production pipeline
- ⚠️ W3C compliance gap: 10% pass rate on marker tests (would be 80-90% if migrated)

**Git History:**
```
commit 51cca1e: Created (646 lines)
commit e840985: Dependency injection migration
commit f787b27: Enhanced (+83/-46 lines)
commit 8eab950: MOVED TO ARCHIVE (legacy converter cleanup)
commit 50350b3: Tests deleted (pre-Clean Slate cleanup)
```

---

## Decision

**Migrate marker system to Clean Slate architecture** following established IR-Mapper-Policy patterns.

**Phased Approach:**
1. **Phase 1**: Core IR structures and parser integration (1 day)
2. **Phase 2**: Mapper implementation with policy decisions (1-2 days)
3. **Phase 3**: Symbol support and advanced features (1 day)
4. **Phase 4**: Testing and W3C compliance validation (1 day)

**Estimated Effort**: 4-5 days
**Expected W3C Improvement**: +10-15% overall compliance (from 70-80% to 75-85%)

---

## Detailed Design

### 1. IR Structures (`core/ir/marker.py`)

```python
#!/usr/bin/env python3
"""
Marker IR - Intermediate Representation for SVG Markers

Represents marker definitions and references in a policy-agnostic format.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .geometry import Point, Rect
from .paint import Paint


class MarkerPosition(Enum):
    """Position of marker on path."""
    START = "start"
    MID = "mid"
    END = "end"


class MarkerUnits(Enum):
    """Marker coordinate space."""
    STROKE_WIDTH = "strokeWidth"      # Scale with stroke width
    USER_SPACE_ON_USE = "userSpaceOnUse"  # User coordinate space


class MarkerOrient(Enum):
    """Marker orientation modes."""
    AUTO = "auto"                      # Follow path tangent
    AUTO_START_REVERSE = "auto-start-reverse"  # Reversed at start
    FIXED = "fixed"                    # Fixed angle


@dataclass(frozen=True)
class MarkerDef:
    """
    Marker definition from <marker> element.

    Attributes:
        id: Unique marker identifier
        ref_point: Reference point (refX, refY)
        size: Marker size (markerWidth, markerHeight)
        orient: Orientation mode or fixed angle in degrees
        units: Coordinate units for marker sizing
        viewbox: Optional viewBox for scaling
        overflow: Clipping behavior ('visible' or 'hidden')
        content: List of IRElement shapes that make up the marker
        preserve_aspect_ratio: ViewBox aspect ratio preservation
    """
    id: str
    ref_point: Point
    size: tuple[float, float]  # (width, height)
    orient: MarkerOrient | float  # MarkerOrient enum or angle in degrees
    units: MarkerUnits
    viewbox: Optional[Rect]
    overflow: str
    content: list['IRElement']  # Marker shapes
    preserve_aspect_ratio: str = "xMidYMid meet"


@dataclass(frozen=True)
class MarkerRef:
    """
    Reference to a marker for application on a path.

    Attributes:
        marker_id: ID of marker definition
        position: Where marker appears (start/mid/end)
        stroke_width: Stroke width for scaling (if markerUnits=strokeWidth)
        color: Optional color override for marker
    """
    marker_id: str
    position: MarkerPosition
    stroke_width: float = 1.0
    color: Optional[Paint] = None


@dataclass(frozen=True)
class MarkerInstance:
    """
    Instantiated marker at specific path location.

    Attributes:
        definition: Marker definition being instantiated
        position: Where on path (start/mid/end)
        point: Exact (x, y) position
        tangent_angle: Path tangent angle in degrees at this point
        stroke_width: Effective stroke width for scaling
        color: Resolved color for marker
    """
    definition: MarkerDef
    position: MarkerPosition
    point: Point
    tangent_angle: float
    stroke_width: float
    color: Optional[Paint]

    def get_orientation_angle(self) -> float:
        """Calculate final marker orientation angle."""
        orient = self.definition.orient

        if isinstance(orient, MarkerOrient):
            if orient == MarkerOrient.AUTO:
                return self.tangent_angle
            elif orient == MarkerOrient.AUTO_START_REVERSE:
                return self.tangent_angle + 180.0
            else:  # FIXED (should have explicit angle)
                return 0.0
        else:
            # Fixed angle in degrees
            return float(orient)


@dataclass(frozen=True)
class SymbolDef:
    """
    Symbol definition from <symbol> element.

    Similar to marker but for <use> element instantiation.

    Attributes:
        id: Unique symbol identifier
        viewbox: Optional viewBox for coordinate mapping
        preserve_aspect_ratio: ViewBox aspect ratio mode
        content: List of IRElement shapes
    """
    id: str
    viewbox: Optional[Rect]
    preserve_aspect_ratio: str
    content: list['IRElement']
```

### 2. Parser Integration (`core/parse_split/marker_parser.py`)

```python
#!/usr/bin/env python3
"""
Marker Parser - Extract marker definitions from SVG

Extracts <marker> and <symbol> definitions during parse phase.
"""

import logging
import re
from typing import Dict, Optional

from lxml import etree as ET

from ..ir.marker import MarkerDef, MarkerOrient, MarkerUnits, SymbolDef
from ..ir.geometry import Point, Rect
from .ir_converter import IRConverter

logger = logging.getLogger(__name__)


class MarkerExtractor:
    """Extract marker definitions from SVG <defs>."""

    def __init__(self, ir_converter: IRConverter):
        """
        Initialize marker extractor.

        Args:
            ir_converter: IRConverter for parsing marker content shapes
        """
        self.ir_converter = ir_converter
        self.logger = logging.getLogger(__name__)

    def collect(self, svg_root: ET.Element, children_iter) -> Dict[str, MarkerDef]:
        """
        Collect all marker definitions from SVG.

        Args:
            svg_root: SVG root element
            children_iter: Safe children iterator

        Returns:
            Dictionary mapping marker IDs to MarkerDef objects
        """
        markers = {}

        # Find all <marker> elements
        for marker_elem in svg_root.xpath('.//svg:marker',
                                          namespaces={'svg': 'http://www.w3.org/2000/svg'}):
            marker_def = self._parse_marker_definition(marker_elem, children_iter)
            if marker_def:
                markers[marker_def.id] = marker_def

        self.logger.info(f"Collected {len(markers)} marker definitions")
        return markers

    def collect_symbols(self, svg_root: ET.Element, children_iter) -> Dict[str, SymbolDef]:
        """Collect all symbol definitions from SVG."""
        symbols = {}

        for symbol_elem in svg_root.xpath('.//svg:symbol',
                                          namespaces={'svg': 'http://www.w3.org/2000/svg'}):
            symbol_def = self._parse_symbol_definition(symbol_elem, children_iter)
            if symbol_def:
                symbols[symbol_def.id] = symbol_def

        self.logger.info(f"Collected {len(symbols)} symbol definitions")
        return symbols

    def _parse_marker_definition(self, marker_elem: ET.Element,
                                children_iter) -> Optional[MarkerDef]:
        """Parse single <marker> element into MarkerDef."""
        marker_id = marker_elem.get('id')
        if not marker_id:
            self.logger.warning("Marker without id, skipping")
            return None

        # Parse reference point
        ref_x = float(marker_elem.get('refX', '0'))
        ref_y = float(marker_elem.get('refY', '0'))
        ref_point = Point(ref_x, ref_y)

        # Parse size
        marker_width = float(marker_elem.get('markerWidth', '3'))
        marker_height = float(marker_elem.get('markerHeight', '3'))
        size = (marker_width, marker_height)

        # Parse orient
        orient_str = marker_elem.get('orient', 'auto')
        if orient_str == 'auto':
            orient = MarkerOrient.AUTO
        elif orient_str == 'auto-start-reverse':
            orient = MarkerOrient.AUTO_START_REVERSE
        else:
            try:
                orient = float(orient_str)
            except ValueError:
                orient = MarkerOrient.AUTO

        # Parse units
        units_str = marker_elem.get('markerUnits', 'strokeWidth')
        units = (MarkerUnits.STROKE_WIDTH if units_str == 'strokeWidth'
                else MarkerUnits.USER_SPACE_ON_USE)

        # Parse viewBox
        viewbox = self._parse_viewbox(marker_elem.get('viewBox'))

        # Parse overflow
        overflow = marker_elem.get('overflow', 'hidden')

        # Parse preserve aspect ratio
        preserve_aspect = marker_elem.get('preserveAspectRatio', 'xMidYMid meet')

        # Convert marker content to IR
        content = []
        for child in children_iter(marker_elem):
            try:
                ir_element = self.ir_converter.convert_element(child)
                if ir_element:
                    content.append(ir_element)
            except Exception as e:
                self.logger.warning(f"Failed to convert marker child: {e}")

        return MarkerDef(
            id=marker_id,
            ref_point=ref_point,
            size=size,
            orient=orient,
            units=units,
            viewbox=viewbox,
            overflow=overflow,
            content=content,
            preserve_aspect_ratio=preserve_aspect
        )

    def _parse_symbol_definition(self, symbol_elem: ET.Element,
                                children_iter) -> Optional[SymbolDef]:
        """Parse single <symbol> element into SymbolDef."""
        symbol_id = symbol_elem.get('id')
        if not symbol_id:
            return None

        viewbox = self._parse_viewbox(symbol_elem.get('viewBox'))
        preserve_aspect = symbol_elem.get('preserveAspectRatio', 'xMidYMid meet')

        content = []
        for child in children_iter(symbol_elem):
            try:
                ir_element = self.ir_converter.convert_element(child)
                if ir_element:
                    content.append(ir_element)
            except Exception as e:
                self.logger.warning(f"Failed to convert symbol child: {e}")

        return SymbolDef(
            id=symbol_id,
            viewbox=viewbox,
            preserve_aspect_ratio=preserve_aspect,
            content=content
        )

    @staticmethod
    def _parse_viewbox(viewbox_str: Optional[str]) -> Optional[Rect]:
        """Parse viewBox attribute into Rect."""
        if not viewbox_str:
            return None

        try:
            parts = re.split(r'[,\s]+', viewbox_str.strip())
            if len(parts) == 4:
                x, y, width, height = map(float, parts)
                return Rect(x, y, width, height)
        except (ValueError, TypeError):
            pass

        return None
```

### 3. Marker Mapper (`core/map/marker_mapper.py`)

```python
#!/usr/bin/env python3
"""
Marker Mapper - Apply markers to paths

Maps marker instances to DrawingML output.
"""

import logging
import math
from typing import List, Optional, TYPE_CHECKING

from ..ir import IRElement, Path
from ..ir.marker import MarkerDef, MarkerInstance, MarkerPosition, MarkerRef, MarkerUnits
from ..ir.geometry import Point
from ..policy import Policy
from .base import Mapper, MapperResult, OutputFormat

if TYPE_CHECKING:
    from core.services.conversion_services import ConversionServices

logger = logging.getLogger(__name__)


class MarkerMapper(Mapper):
    """
    Maps marker references to instantiated marker shapes.

    Handles marker positioning, orientation, and scaling along paths.
    """

    def __init__(self, policy: Policy, marker_definitions: dict[str, MarkerDef]):
        """
        Initialize marker mapper.

        Args:
            policy: Policy engine for decision making
            marker_definitions: Available marker definitions by ID
        """
        super().__init__(policy)
        self.marker_defs = marker_definitions
        self.services: 'ConversionServices' = getattr(policy, 'services', None)

        if self.services is None:
            raise RuntimeError("MarkerMapper requires ConversionServices injection.")

    def apply_markers_to_path(self, path: Path) -> List[MarkerInstance]:
        """
        Generate marker instances for a path.

        Args:
            path: Path IR element with marker references

        Returns:
            List of MarkerInstance objects positioned along path
        """
        if not hasattr(path, 'markers') or not path.markers:
            return []

        instances = []

        for marker_ref in path.markers:
            marker_def = self.marker_defs.get(marker_ref.marker_id)
            if not marker_def:
                logger.warning(f"Marker definition not found: {marker_ref.marker_id}")
                continue

            # Generate instances based on position
            if marker_ref.position == MarkerPosition.START:
                instance = self._create_start_marker(path, marker_ref, marker_def)
                if instance:
                    instances.append(instance)

            elif marker_ref.position == MarkerPosition.END:
                instance = self._create_end_marker(path, marker_ref, marker_def)
                if instance:
                    instances.append(instance)

            elif marker_ref.position == MarkerPosition.MID:
                mid_instances = self._create_mid_markers(path, marker_ref, marker_def)
                instances.extend(mid_instances)

        return instances

    def _create_start_marker(self, path: Path, marker_ref: MarkerRef,
                            marker_def: MarkerDef) -> Optional[MarkerInstance]:
        """Create marker instance at path start."""
        if not path.segments:
            return None

        # Get first segment
        first_seg = path.segments[0]
        start_point = getattr(first_seg, 'start', None)
        if not start_point:
            return None

        # Calculate tangent angle at start
        tangent_angle = self._calculate_start_tangent(path)

        return MarkerInstance(
            definition=marker_def,
            position=MarkerPosition.START,
            point=start_point,
            tangent_angle=tangent_angle,
            stroke_width=marker_ref.stroke_width,
            color=marker_ref.color or path.stroke
        )

    def _create_end_marker(self, path: Path, marker_ref: MarkerRef,
                          marker_def: MarkerDef) -> Optional[MarkerInstance]:
        """Create marker instance at path end."""
        if not path.segments:
            return None

        # Get last segment
        last_seg = path.segments[-1]
        end_point = getattr(last_seg, 'end', None)
        if not end_point:
            return None

        # Calculate tangent angle at end
        tangent_angle = self._calculate_end_tangent(path)

        return MarkerInstance(
            definition=marker_def,
            position=MarkerPosition.END,
            point=end_point,
            tangent_angle=tangent_angle,
            stroke_width=marker_ref.stroke_width,
            color=marker_ref.color or path.stroke
        )

    def _create_mid_markers(self, path: Path, marker_ref: MarkerRef,
                           marker_def: MarkerDef) -> List[MarkerInstance]:
        """Create marker instances at path vertices (mid points)."""
        instances = []

        # Mid markers appear at vertices between segments
        for i in range(len(path.segments) - 1):
            seg = path.segments[i]
            next_seg = path.segments[i + 1]

            # Vertex point (end of current segment = start of next)
            vertex = getattr(seg, 'end', None)
            if not vertex:
                continue

            # Calculate average tangent angle at vertex
            tangent1 = self._calculate_segment_end_tangent(seg)
            tangent2 = self._calculate_segment_start_tangent(next_seg)
            avg_tangent = (tangent1 + tangent2) / 2.0

            instances.append(MarkerInstance(
                definition=marker_def,
                position=MarkerPosition.MID,
                point=vertex,
                tangent_angle=avg_tangent,
                stroke_width=marker_ref.stroke_width,
                color=marker_ref.color or path.stroke
            ))

        return instances

    def _calculate_start_tangent(self, path: Path) -> float:
        """Calculate tangent angle at path start in degrees."""
        if not path.segments:
            return 0.0

        first_seg = path.segments[0]
        return self._calculate_segment_start_tangent(first_seg)

    def _calculate_end_tangent(self, path: Path) -> float:
        """Calculate tangent angle at path end in degrees."""
        if not path.segments:
            return 0.0

        last_seg = path.segments[-1]
        return self._calculate_segment_end_tangent(last_seg)

    def _calculate_segment_start_tangent(self, segment) -> float:
        """Calculate tangent angle at segment start."""
        from ..ir.geometry import LineSegment, BezierSegment

        if isinstance(segment, LineSegment):
            # Line tangent: direction from start to end
            dx = segment.end.x - segment.start.x
            dy = segment.end.y - segment.start.y
            return math.degrees(math.atan2(dy, dx))

        elif isinstance(segment, BezierSegment):
            # Bézier tangent at t=0: direction to first control point
            dx = segment.control1.x - segment.start.x
            dy = segment.control1.y - segment.start.y
            if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                # Degenerate case: use direction to second control point
                dx = segment.control2.x - segment.start.x
                dy = segment.control2.y - segment.start.y
            return math.degrees(math.atan2(dy, dx))

        return 0.0

    def _calculate_segment_end_tangent(self, segment) -> float:
        """Calculate tangent angle at segment end."""
        from ..ir.geometry import LineSegment, BezierSegment

        if isinstance(segment, LineSegment):
            # Line tangent: direction from start to end
            dx = segment.end.x - segment.start.x
            dy = segment.end.y - segment.start.y
            return math.degrees(math.atan2(dy, dx))

        elif isinstance(segment, BezierSegment):
            # Bézier tangent at t=1: direction from second control point
            dx = segment.end.x - segment.control2.x
            dy = segment.end.y - segment.control2.y
            if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                # Degenerate case: use direction from first control point
                dx = segment.end.x - segment.control1.x
                dy = segment.end.y - segment.control1.y
            return math.degrees(math.atan2(dy, dx))

        return 0.0
```

### 4. Policy Integration (`core/policy/config.py` additions)

```python
@dataclass
class MarkerPolicy:
    """Policy for marker processing."""
    max_marker_instances: int = 1000  # Prevent marker bombs
    simplify_complex_markers: bool = True  # Convert complex to simple shapes
    standard_arrow_types: set = field(default_factory=lambda: {
        'arrow', 'circle', 'square', 'diamond'
    })
    enable_mid_markers: bool = True  # Allow marker-mid (can be expensive)
    marker_units_preference: str = "strokeWidth"  # Preferred scaling mode
```

### 5. Path IR Extension (`core/ir/__init__.py` modification)

```python
@dataclass(frozen=True)
class Path(IRElement):
    """Path element with segments."""
    segments: list[SegmentType]
    fill: Optional[Paint]
    stroke: Optional[Paint]
    stroke_width: float
    clip: Optional[ClipRef]
    opacity: float
    markers: list[MarkerRef] = field(default_factory=list)  # NEW
    # ... rest of existing fields
```

---

## Implementation Phases

### Phase 1: Core IR and Parser (1 day)
**Files to create:**
- `core/ir/marker.py` (IR structures)
- `core/parse_split/marker_parser.py` (extraction logic)

**Integration points:**
- Update `core/ir/__init__.py` to export marker types
- Add `MarkerExtractor` to `core/parse/parser.py`
- Extend `Path` IR with `markers` field

**Validation:**
- Parse SVGs with `<marker>` definitions
- Extract marker references from path elements
- Verify marker definitions are collected

### Phase 2: Mapper Implementation (1-2 days)
**Files to create:**
- `core/map/marker_mapper.py` (instantiation logic)

**Integration points:**
- Register `MarkerMapper` in mapper registry
- Integrate with `PathMapper` for marker application
- Handle marker transformations and scaling

**Validation:**
- Generate marker instances at path endpoints
- Calculate correct tangent angles
- Apply marker-start/marker-end/marker-mid

### Phase 3: Symbol Support (1 day)
**Extensions:**
- Symbol parsing in `marker_parser.py`
- `<use>` element handling
- Symbol instantiation with transforms

**Validation:**
- Parse `<symbol>` definitions
- Instantiate symbols with `<use>`
- Apply transforms to symbol instances

### Phase 4: Testing and W3C Compliance (1 day)
**Testing:**
- Unit tests for marker parser
- Unit tests for marker mapper
- Integration tests with path conversion
- W3C marker test suite validation

**Expected results:**
- 80-90% pass rate on W3C marker tests
- Arrows, decorations, technical diagram support
- Symbol reuse with proper transforms

---

## Benefits

### 1. W3C Compliance
- **Before**: 10% marker test pass rate (ignored)
- **After**: 80-90% marker test pass rate
- **Overall**: +10-15% total W3C compliance (70-80% → 75-85%)

### 2. Feature Completeness
- ✅ Technical diagrams (flowcharts, network diagrams)
- ✅ Arrowheads for paths (all orientations)
- ✅ Custom marker shapes
- ✅ Symbol libraries with reuse
- ✅ Professional graphics rendering

### 3. Code Quality
- Clean IR-Mapper separation
- Policy-driven complexity decisions
- Reuses existing infrastructure (clipping, transforms, paths)
- Comprehensive test coverage

### 4. User Value
- Diagram tools (draw.io, Lucidchart) export markers heavily
- CAD/engineering graphics require precise arrow placement
- Professional presentations need decorated paths

---

## Risks and Mitigations

### Risk 1: Complex Marker Content
**Issue**: Markers can contain arbitrary SVG content (filters, gradients, nested groups)

**Mitigation**:
- Reuse existing IR conversion pipeline for marker content
- Apply same policy decisions (EMF fallback for complex markers)
- Limit marker complexity via policy (simplify_complex_markers)

### Risk 2: Performance
**Issue**: Thousands of mid-markers on long paths could impact performance

**Mitigation**:
- Policy limit: `max_marker_instances = 1000`
- Optional: `enable_mid_markers = False` for performance mode
- Path simplification before marker application
- Cache marker DrawingML for reuse

### Risk 3: Edge Cases
**Issue**: Degenerate paths, zero-length segments, coincident points

**Mitigation**:
- Robust tangent angle calculation with fallbacks
- Skip markers on invalid geometry
- Comprehensive unit tests for edge cases
- Validation from archived 696-line implementation

---

## Alternatives Considered

### Alternative 1: Simplify to Standard Arrows Only
**Rejected**: Loses 80% of marker use cases. Custom markers are essential for technical diagrams.

### Alternative 2: Rasterize All Markers
**Rejected**: Defeats purpose of vector output. Markers are usually simple geometry.

### Alternative 3: Convert Markers to Path Decorations
**Rejected**: Doesn't preserve semantic structure. Loses editability in PowerPoint.

### Alternative 4: Keep in Archive, Don't Migrate
**Rejected**: Marker support is table stakes for professional graphics. Missing 15% of W3C tests.

---

## Success Metrics

### Quantitative
- ✅ 80-90% pass rate on W3C marker tests
- ✅ +10-15% overall W3C compliance
- ✅ <100ms overhead for marker processing
- ✅ Support for 1000+ marker instances per slide

### Qualitative
- ✅ Flowcharts render correctly (draw.io, Lucidchart)
- ✅ Network diagrams preserve arrow directions
- ✅ CAD exports maintain line decorations
- ✅ Symbol libraries work for icon reuse

### Technical
- ✅ Clean IR separation (marker definitions vs. instances)
- ✅ Policy-driven complexity decisions
- ✅ Reuses existing infrastructure (no duplication)
- ✅ Comprehensive test coverage (unit, integration, E2E)

---

## Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|-------------|
| **Phase 1** | 1 day | IR structures, parser integration |
| **Phase 2** | 1-2 days | Mapper implementation, path integration |
| **Phase 3** | 1 day | Symbol support, `<use>` elements |
| **Phase 4** | 1 day | Testing, W3C validation |
| **Total** | **4-5 days** | Production-ready marker system |

---

## References

- **Archived Implementation**: `archive/legacy-src/converters/markers.py` (commit 8eab950)
- **W3C SVG Marker Specification**: https://www.w3.org/TR/SVG2/painting.html#Markers
- **Related ADRs**:
  - ADR-015: Clipping Pipeline (similar pattern)
  - ADR-006: Animation System (IR-Mapper architecture)
  - ADR-002: Converter Architecture (Clean Slate principles)

---

## Approval

**Proposed by**: Analysis findings (2025-10-15)
**Reviewed by**: _Pending_
**Approved by**: _Pending_
**Implementation**: _Planned_
