"""
ARCHIVED: Path-only shape conversion methods
Date: 2025-10-05
Reason: Replaced by native PowerPoint shape support (ADR-002 compliance)

These methods converted all SVG shapes (rect, circle, ellipse) to Path IR with
line/Bezier segments. This violated ADR-002 which specifies separate converters
for different shape types and loses native PowerPoint shape fidelity.

Replacement: New Circle, Ellipse, Rectangle IR types with native prstGeom output
See: .agent-os/specs/2025-10-05-native-shape-support/spec.md
"""

from lxml import etree as ET

# NOTE: These are extracted methods from core/parse/parser.py
# Original location: lines 600-749
# Do NOT import or use - kept for reference only


def _convert_rect_to_ir_PATH_ONLY(self, element: ET.Element):
    """Convert SVG rect to IR Path"""
    from ..ir import LineSegment, Path, Point

    # Extract rectangle attributes
    x = float(element.get('x', 0))
    y = float(element.get('y', 0))
    width = float(element.get('width', 0))
    height = float(element.get('height', 0))

    if width <= 0 or height <= 0:
        return None

    # Create rectangle as closed path
    segments = [
        LineSegment(start=Point(x, y), end=Point(x + width, y)),
        LineSegment(start=Point(x + width, y), end=Point(x + width, y + height)),
        LineSegment(start=Point(x + width, y + height), end=Point(x, y + height)),
        LineSegment(start=Point(x, y + height), end=Point(x, y)),
    ]

    # Extract styling
    fill, stroke, opacity = self._extract_styling(element)

    # Get hyperlink from current context if any
    getattr(self, '_current_hyperlink', None)

    return Path(
        segments=segments,
        fill=fill,
        stroke=stroke,
        opacity=opacity,
    )


def _convert_circle_to_ir_PATH_ONLY(self, element: ET.Element):
    """Convert SVG circle to IR Path with Bezier curves"""
    from ..ir import BezierSegment, Path, Point

    # Extract circle attributes
    cx = float(element.get('cx', 0))
    cy = float(element.get('cy', 0))
    r = float(element.get('r', 0))

    if r <= 0:
        return None

    # Create circle using 4 Bezier curves (standard approach)
    # Magic constant for circle approximation with Bezier curves
    k = 0.552284749831

    segments = [
        # Top right quadrant
        BezierSegment(
            start=Point(cx + r, cy),
            control1=Point(cx + r, cy - k * r),
            control2=Point(cx + k * r, cy - r),
            end=Point(cx, cy - r),
        ),
        # Top left quadrant
        BezierSegment(
            start=Point(cx, cy - r),
            control1=Point(cx - k * r, cy - r),
            control2=Point(cx - r, cy - k * r),
            end=Point(cx - r, cy),
        ),
        # Bottom left quadrant
        BezierSegment(
            start=Point(cx - r, cy),
            control1=Point(cx - r, cy + k * r),
            control2=Point(cx - k * r, cy + r),
            end=Point(cx, cy + r),
        ),
        # Bottom right quadrant
        BezierSegment(
            start=Point(cx, cy + r),
            control1=Point(cx + k * r, cy + r),
            control2=Point(cx + r, cy + k * r),
            end=Point(cx + r, cy),
        ),
    ]

    # Extract styling
    fill, stroke, opacity = self._extract_styling(element)

    # Get hyperlink from current context if any
    getattr(self, '_current_hyperlink', None)

    return Path(
        segments=segments,
        fill=fill,
        stroke=stroke,
        opacity=opacity,
    )


def _convert_ellipse_to_ir_PATH_ONLY(self, element: ET.Element):
    """Convert SVG ellipse to IR Path"""
    from ..ir import BezierSegment, Path, Point

    # Extract ellipse attributes
    cx = float(element.get('cx', 0))
    cy = float(element.get('cy', 0))
    rx = float(element.get('rx', 0))
    ry = float(element.get('ry', 0))

    if rx <= 0 or ry <= 0:
        return None

    # Create ellipse using 4 Bezier curves
    kx = 0.552284749831 * rx
    ky = 0.552284749831 * ry

    segments = [
        BezierSegment(
            start=Point(cx + rx, cy),
            control1=Point(cx + rx, cy - ky),
            control2=Point(cx + kx, cy - ry),
            end=Point(cx, cy - ry),
        ),
        BezierSegment(
            start=Point(cx, cy - ry),
            control1=Point(cx - kx, cy - ry),
            control2=Point(cx - rx, cy - ky),
            end=Point(cx - rx, cy),
        ),
        BezierSegment(
            start=Point(cx - rx, cy),
            control1=Point(cx - rx, cy + ky),
            control2=Point(cx - kx, cy + ry),
            end=Point(cx, cy + ry),
        ),
        BezierSegment(
            start=Point(cx, cy + ry),
            control1=Point(cx + kx, cy + ry),
            control2=Point(cx + rx, cy + ky),
            end=Point(cx + rx, cy),
        ),
    ]

    # Extract styling
    fill, stroke, opacity = self._extract_styling(element)

    # Get hyperlink from current context if any
    getattr(self, '_current_hyperlink', None)

    return Path(
        segments=segments,
        fill=fill,
        stroke=stroke,
        opacity=opacity,
    )


# Key insights from this implementation:
# 1. Bezier constant k = 0.552284749831 is optimal for circle approximation
# 2. Circle uses 4 quadrants with symmetric control points
# 3. Ellipse scales control points: kx = k * rx, ky = k * ry
# 4. Rectangle uses simple line segments (no Bezier needed)
# 5. All shapes became Path IR - no native shape representation
# 6. Hyperlink handling was incomplete (getattr does nothing)
# 7. No complexity detection - always converted to paths
# 8. No corner radius support for rectangles
