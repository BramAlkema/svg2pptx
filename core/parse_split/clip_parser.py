"""Clip path extraction helpers for the sliced parser."""

from __future__ import annotations

from typing import Iterable

from lxml import etree as ET

from ..ir.geometry import BezierSegment, LineSegment, Point, Rect, SegmentType
from .constants import MAX_SIMPLE_PATH_SEGMENTS
from .models import ClipDefinition


class ClipPathExtractor:
    """Extracts clipPath definitions from an SVG document."""

    def __init__(self, transform_parser, path_parser) -> None:
        self._transform_parser = transform_parser
        self._parse_path_data = path_parser

    def collect(self, svg_root: ET.Element, children_iter) -> dict[str, ClipDefinition]:
        if svg_root is None:
            return {}

        namespaces = {k or 'svg': v for k, v in svg_root.nsmap.items() if v}
        if 'svg' not in namespaces:
            namespaces['svg'] = 'http://www.w3.org/2000/svg'

        try:
            clip_paths = svg_root.xpath('.//svg:clipPath', namespaces=namespaces)
        except Exception:
            clip_paths = []

        definitions: dict[str, ClipDefinition] = {}

        for clip_elem in clip_paths:
            clip_id = clip_elem.get('id')
            if not clip_id:
                continue

            clip_transform = self._parse_transform(clip_elem.get('transform'))

            segments: list[SegmentType] = []
            for child in children_iter(clip_elem):
                segments.extend(self._clip_child_to_segments(child, clip_transform))

            if not segments:
                continue

            bbox = self._compute_segments_bbox(segments)
            clip_rule = clip_elem.get('clip-rule') or self._extract_clip_rule(clip_elem.get('style'))

            definitions[clip_id] = ClipDefinition(
                clip_id=clip_id,
                segments=tuple(segments),
                bounding_box=bbox,
                clip_rule=clip_rule,
                transform=clip_transform,
            )

        return definitions

    def _clip_child_to_segments(self, element: ET.Element, parent_transform=None) -> list[SegmentType]:
        if element is None or not hasattr(element, 'tag'):
            return []

        tag = element.tag.split('}')[-1].lower()

        matrix = parent_transform
        local_transform = element.get('transform')
        if local_transform:
            child_matrix = self._parse_transform(local_transform)
            if child_matrix:
                matrix = child_matrix if matrix is None else matrix.multiply(child_matrix)

        if tag == 'path':
            d = element.get('d', '')
            segments = self._parse_path_data(d) if d else []
            return self._apply_transform_to_segments(segments, matrix)

        if tag == 'rect':
            x = float(element.get('x', 0))
            y = float(element.get('y', 0))
            width = float(element.get('width', 0))
            height = float(element.get('height', 0))
            if width <= 0 or height <= 0:
                return []
            segments = [
                LineSegment(Point(x, y), Point(x + width, y)),
                LineSegment(Point(x + width, y), Point(x + width, y + height)),
                LineSegment(Point(x + width, y + height), Point(x, y + height)),
                LineSegment(Point(x, y + height), Point(x, y)),
            ]
            return self._apply_transform_to_segments(segments, matrix)

        if tag == 'circle':
            cx = float(element.get('cx', 0))
            cy = float(element.get('cy', 0))
            r = float(element.get('r', 0))
            if r <= 0:
                return []
            segments = self._approximate_circle(cx, cy, r)
            return self._apply_transform_to_segments(segments, matrix)

        if tag == 'ellipse':
            cx = float(element.get('cx', 0))
            cy = float(element.get('cy', 0))
            rx = float(element.get('rx', 0))
            ry = float(element.get('ry', 0))
            if rx <= 0 or ry <= 0:
                return []
            segments = self._approximate_ellipse(cx, cy, rx, ry)
            return self._apply_transform_to_segments(segments, matrix)

        return []

    def _apply_transform_to_segments(self, segments: Iterable[SegmentType], matrix) -> list[SegmentType]:
        if matrix is None:
            return list(segments)

        transformed = []
        for segment in segments:
            if isinstance(segment, LineSegment):
                transformed.append(LineSegment(matrix.transform_point(segment.start), matrix.transform_point(segment.end)))
            elif isinstance(segment, BezierSegment):
                transformed.append(
                    BezierSegment(
                        matrix.transform_point(segment.start),
                        matrix.transform_point(segment.control1),
                        matrix.transform_point(segment.control2),
                        matrix.transform_point(segment.end),
                    )
                )
            else:
                transformed.append(segment)
        return transformed

    def _parse_transform(self, transform: str | None):
        if not transform:
            return None
        try:
            return self._transform_parser.parse_to_matrix(transform)
        except Exception:
            return None

    def _compute_segments_bbox(self, segments: Iterable[SegmentType]) -> Rect | None:
        xs = []
        ys = []
        for segment in segments:
            if isinstance(segment, LineSegment):
                xs.extend([segment.start.x, segment.end.x])
                ys.extend([segment.start.y, segment.end.y])
            elif isinstance(segment, BezierSegment):
                xs.extend([segment.start.x, segment.control1.x, segment.control2.x, segment.end.x])
                ys.extend([segment.start.y, segment.control1.y, segment.control2.y, segment.end.y])
        if not xs or not ys:
            return None
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return Rect(min_x, min_y, max_x - min_x, max_y - min_y)

    def _extract_clip_rule(self, style_attribute: str | None) -> str | None:
        if not style_attribute:
            return None
        for entry in style_attribute.split(';'):
            if ':' not in entry:
                continue
            name, value = entry.split(':', 1)
            if name.strip() == 'clip-rule':
                return value.strip()
        return None

    def _approximate_circle(self, cx: float, cy: float, r: float) -> list[SegmentType]:
        segments: list[SegmentType] = []
        steps = 4
        for i in range(steps):
            angle = (i / steps) * 360.0
            next_angle = ((i + 1) / steps) * 360.0
            segments.append(self._arc_segment(cx, cy, r, r, angle, next_angle))
        return segments

    def _approximate_ellipse(self, cx: float, cy: float, rx: float, ry: float) -> list[SegmentType]:
        segments: list[SegmentType] = []
        steps = 4
        for i in range(steps):
            angle = (i / steps) * 360.0
            next_angle = ((i + 1) / steps) * 360.0
            segments.append(self._arc_segment(cx, cy, rx, ry, angle, next_angle))
        return segments

    def _arc_segment(self, cx: float, cy: float, rx: float, ry: float, start_angle: float, end_angle: float) -> LineSegment:
        # Simple approximation: start/end points only
        import math

        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)
        start_point = Point(cx + rx * math.cos(start_rad), cy + ry * math.sin(start_rad))
        end_point = Point(cx + rx * math.cos(end_rad), cy + ry * math.sin(end_rad))
        return LineSegment(start_point, end_point)
