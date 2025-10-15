"""DOM to IR conversion helpers for the sliced SVG parser."""

from __future__ import annotations

import logging
import re
from typing import Callable, Iterable

from lxml import etree as ET

from ..css import StyleContext, StyleResolver, parse_color
from ..ir.geometry import (
    BezierSegment,
    LineSegment,
    Point,
    Rect,
    SegmentType,
)
from ..pipeline.navigation import NavigationSpec
from ..transforms.coordinate_space import CoordinateSpace
from ..transforms.parser import TransformParser

from .constants import (
    FONT_WEIGHT_BOLD_THRESHOLD,
    MAX_SIMPLE_PATH_SEGMENTS,
    MIN_PATH_COORDS_FOR_ARC,
    MIN_PATH_COORDS_FOR_CURVE,
    MIN_PATH_COORDS_FOR_CUBIC,
    MIN_PATH_COORDS_FOR_LINE,
)
from .element_traversal import ElementTraversal
from .hyperlink_processor import HyperlinkProcessor
from .models import ClipDefinition
from .style_context import StyleContextBuilder


ChildrenIterator = Callable[[ET.Element], Iterable[ET.Element]]


class IRConverter:
    """Converts SVG DOM nodes into Clean Slate IR objects."""

    def __init__(
        self,
        style_resolver: StyleResolver,
        style_context_builder: StyleContextBuilder,
        hyperlink_processor: HyperlinkProcessor,
        children_iter: ChildrenIterator,
        logger: logging.Logger,
    ) -> None:
        self.style_resolver = style_resolver
        self._style_context_builder = style_context_builder
        self._hyperlinks = hyperlink_processor
        self._children = children_iter
        self.logger = logger

        self._transform_parser = TransformParser()

        self._style_context: StyleContext | None = None
        self._clip_definitions: dict[str, ClipDefinition] = {}
        self._filter_service = None

        self.coord_space: CoordinateSpace | None = None
        self._current_navigation: NavigationSpec | None = None

        self._path_command_pattern = re.compile(r"[MmLlHhVvCcSsQqTtAaZz][^MmLlHhVvCcSsQqTtAaZz]*")

    def register_filter_service(self, filter_service) -> None:
        """Inject optional filter resolution service."""
        self._filter_service = filter_service

    def parse_path_data(self, path_data: str) -> list[SegmentType]:
        """Expose path parsing for consumers like clip extraction."""
        return self._parse_path_data(path_data)

    def convert(self, svg_root: ET.Element, clip_definitions: dict[str, ClipDefinition] | None = None) -> list:
        """Convert an SVG DOM tree into IR elements."""
        self._style_context = self._style_context_builder.build(svg_root)
        self._clip_definitions = clip_definitions or {}

        traversal = ElementTraversal(
            ir_converter=self,
            hyperlink_processor=self._hyperlinks,
            transform_parser=self._transform_parser,
            children_iter=self._children,
            logger=self.logger,
        )
        return traversal.extract(svg_root)

    # Element dispatch -----------------------------------------------------------------

    def convert_element(
        self,
        tag: str,
        element: ET.Element,
        coord_space: CoordinateSpace,
        current_navigation: NavigationSpec | None,
        traverse_callback: Callable[[ET.Element, NavigationSpec | None], list],
    ):
        """Dispatch SVG element conversion based on tag name."""
        self.coord_space = coord_space
        self._current_navigation = current_navigation

        if tag == "rect":
            return self._convert_rect_to_ir(element)
        if tag == "circle":
            return self._convert_circle_to_ir(element)
        if tag == "ellipse":
            return self._convert_ellipse_to_ir(element)
        if tag == "line":
            return self._convert_line_to_ir(element)
        if tag == "path":
            return self._convert_path_to_ir(element)
        if tag in ("polygon", "polyline"):
            return self._convert_polygon_to_ir(element, closed=(tag == "polygon"))
        if tag == "text":
            return self._convert_text_to_ir(element)
        if tag == "image":
            return self._convert_image_to_ir(element)
        if tag == "foreignObject":
            return self._convert_foreignobject_to_ir(element, traverse_callback)

        return None

    def convert_group(self, element: ET.Element, child_nodes: list):
        """Create IR group element from converted children."""
        from ..ir import Group

        if not child_nodes:
            return None

        transform_matrix = None
        transform_attr = element.get("transform")
        if transform_attr:
            try:
                tm = self._transform_parser.parse_to_matrix(transform_attr)
                if hasattr(tm, "to_numpy"):
                    tm = tm.to_numpy()
                transform_matrix = tm
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger.warning(f"Failed to parse group transform '{transform_attr}': {exc}")

        clip_ref = self._extract_clip_reference(element)

        return Group(
            children=child_nodes,
            opacity=float(element.get("opacity", 1.0)),
            transform=transform_matrix,
            clip=clip_ref,
        )

    def attach_metadata(self, ir_element, source_element: ET.Element, navigation: NavigationSpec | None) -> None:
        """Attach original SVG metadata to converted IR element."""
        if ir_element is None or source_element is None:
            return

        try:
            source_id = source_element.get("id")
            if source_id:
                setattr(ir_element, "source_id", source_id)
            if navigation:
                setattr(ir_element, "navigation", navigation)
        except Exception:
            pass

    # Conversion helpers ----------------------------------------------------------------

    def _convert_rect_to_ir(self, element: ET.Element):
        from ..ir import Path, Rectangle

        x_svg = float(element.get("x", 0))
        y_svg = float(element.get("y", 0))
        width_svg = float(element.get("width", 0))
        height_svg = float(element.get("height", 0))

        if width_svg <= 0 or height_svg <= 0:
            return None

        if self.coord_space is not None:
            x, y = self.coord_space.apply_ctm(x_svg, y_svg)
            x2, y2 = self.coord_space.apply_ctm(x_svg + width_svg, y_svg + height_svg)
            width = abs(x2 - x)
            height = abs(y2 - y)
            x = min(x, x2)
            y = min(y, y2)
        else:
            x, y, width, height = x_svg, y_svg, width_svg, height_svg

        rx = float(element.get("rx", 0))
        ry = float(element.get("ry", 0))
        corner_radius = max(rx, ry)

        fill, stroke, opacity, effects = self._extract_styling(element)

        has_filter_attr = element.get("filter") is not None
        has_clip_path = element.get("clip-path") is not None
        has_mask = element.get("mask") is not None

        clip_ref = self._extract_clip_reference(element)

        if effects or not (has_filter_attr or has_clip_path or has_mask):
            return Rectangle(
                bounds=Rect(x=x, y=y, width=width, height=height),
                corner_radius=corner_radius,
                fill=fill,
                stroke=stroke,
                opacity=opacity,
            )

        segments = [
            LineSegment(Point(x, y), Point(x + width, y)),
            LineSegment(Point(x + width, y), Point(x + width, y + height)),
            LineSegment(Point(x + width, y + height), Point(x, y + height)),
            LineSegment(Point(x, y + height), Point(x, y)),
        ]

        return Path(
            segments=segments,
            fill=fill,
            stroke=stroke,
            opacity=opacity,
            clip=clip_ref,
        )

    def _convert_circle_to_ir(self, element: ET.Element):
        from ..ir import Circle, Ellipse, Path

        cx_svg = float(element.get("cx", 0))
        cy_svg = float(element.get("cy", 0))
        r_svg = float(element.get("r", 0))

        if r_svg <= 0:
            return None

        if self.coord_space is not None:
            cx, cy = self.coord_space.apply_ctm(cx_svg, cy_svg)
            rx = ry = r_svg
            ctm = self.coord_space.current_ctm
            scale_x = (ctm.a**2 + ctm.c**2) ** 0.5
            scale_y = (ctm.b**2 + ctm.d**2) ** 0.5
            rx *= scale_x
            ry *= scale_y
        else:
            cx, cy = cx_svg, cy_svg
            rx = ry = r_svg

        fill, stroke, opacity, effects = self._extract_styling(element)
        has_filter = element.get("filter") is not None
        has_clip_path = element.get("clip-path") is not None
        has_mask = element.get("mask") is not None
        clip_ref = self._extract_clip_reference(element)

        if not (effects or has_filter or has_clip_path or has_mask) and abs(rx - ry) < 1e-6:
            return Circle(
                center=Point(cx, cy),
                radius=rx,
                fill=fill,
                stroke=stroke,
                opacity=opacity,
            )

        k = 0.552284749831 * rx

        segments = [
            BezierSegment(Point(cx + rx, cy), Point(cx + rx, cy - k), Point(cx + k, cy - ry), Point(cx, cy - ry)),
            BezierSegment(Point(cx, cy - ry), Point(cx - k, cy - ry), Point(cx - rx, cy - k), Point(cx - rx, cy)),
            BezierSegment(Point(cx - rx, cy), Point(cx - rx, cy + k), Point(cx - k, cy + ry), Point(cx, cy + ry)),
            BezierSegment(Point(cx, cy + ry), Point(cx + k, cy + ry), Point(cx + rx, cy + k), Point(cx + rx, cy)),
        ]

        return (
            Ellipse(
                center=Point(cx, cy),
                radius_x=rx,
                radius_y=ry,
                fill=fill,
                stroke=stroke,
                opacity=opacity,
                clip=clip_ref,
            )
            if not (effects or has_filter or has_clip_path or has_mask)
            else Path(
                segments=segments,
                fill=fill,
                stroke=stroke,
                opacity=opacity,
                clip=clip_ref,
            )
        )

    def _convert_ellipse_to_ir(self, element: ET.Element):
        from ..ir import Ellipse, Path

        cx_svg = float(element.get("cx", 0))
        cy_svg = float(element.get("cy", 0))
        rx_svg = float(element.get("rx", 0))
        ry_svg = float(element.get("ry", 0))

        if rx_svg <= 0 or ry_svg <= 0:
            return None

        if self.coord_space is not None:
            cx, cy = self.coord_space.apply_ctm(cx_svg, cy_svg)
            ctm = self.coord_space.current_ctm
            scale_x = (ctm.a**2 + ctm.c**2) ** 0.5
            scale_y = (ctm.b**2 + ctm.d**2) ** 0.5
            rx = rx_svg * scale_x
            ry = ry_svg * scale_y
        else:
            cx, cy, rx, ry = cx_svg, cy_svg, rx_svg, ry_svg

        fill, stroke, opacity, effects = self._extract_styling(element)
        has_filter = element.get("filter") is not None
        has_clip_path = element.get("clip-path") is not None
        has_mask = element.get("mask") is not None
        clip_ref = self._extract_clip_reference(element)

        if not (effects or has_filter or has_clip_path or has_mask):
            return Ellipse(
                center=Point(cx, cy),
                radius_x=rx,
                radius_y=ry,
                fill=fill,
                stroke=stroke,
                opacity=opacity,
            )

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

        return Path(
            segments=segments,
            fill=fill,
            stroke=stroke,
            opacity=opacity,
            clip=clip_ref,
        )

    def _convert_line_to_ir(self, element: ET.Element):
        from ..ir import Path

        x1_svg = float(element.get("x1", 0))
        y1_svg = float(element.get("y1", 0))
        x2_svg = float(element.get("x2", 0))
        y2_svg = float(element.get("y2", 0))

        if self.coord_space is not None:
            x1, y1 = self.coord_space.apply_ctm(x1_svg, y1_svg)
            x2, y2 = self.coord_space.apply_ctm(x2_svg, y2_svg)
        else:
            x1, y1, x2, y2 = x1_svg, y1_svg, x2_svg, y2_svg

        segments = [LineSegment(start=Point(x1, y1), end=Point(x2, y2))]
        fill, stroke, opacity, _effects = self._extract_styling(element)
        clip_ref = self._extract_clip_reference(element)

        return Path(
            segments=segments,
            fill=None,
            stroke=stroke,
            opacity=opacity,
            clip=clip_ref,
        )

    def _convert_path_to_ir(self, element: ET.Element):
        from ..ir import Path

        d = element.get("d", "")
        if not d:
            return None

        segments = self._parse_path_data(d)
        if not segments:
            return None

        fill, stroke, opacity, _effects = self._extract_styling(element)
        clip_ref = self._extract_clip_reference(element)

        return Path(
            segments=segments[:MAX_SIMPLE_PATH_SEGMENTS],
            fill=fill,
            stroke=stroke,
            opacity=opacity,
            clip=clip_ref,
        )

    def _convert_polygon_to_ir(self, element: ET.Element, closed: bool = True):
        from ..ir import Path

        points_str = element.get("points", "")
        if not points_str:
            return None

        coords = [float(v) for v in points_str.replace(",", " ").split() if v.strip()]
        if len(coords) < 4:
            return None

        points = [Point(coords[i], coords[i + 1]) for i in range(0, len(coords) - 1, 2)]
        segments: list[SegmentType] = []
        for idx in range(len(points) - 1):
            segments.append(LineSegment(points[idx], points[idx + 1]))
        if closed and len(points) > 2:
            segments.append(LineSegment(points[-1], points[0]))

        if self.coord_space is not None:
            transformed = []
            for segment in segments:
                start = self.coord_space.apply_ctm(segment.start.x, segment.start.y)
                end = self.coord_space.apply_ctm(segment.end.x, segment.end.y)
                transformed.append(LineSegment(Point(*start), Point(*end)))
            segments = transformed

        fill, stroke, opacity, _effects = self._extract_styling(element)
        clip_ref = self._extract_clip_reference(element)

        return Path(
            segments=segments,
            fill=fill,
            stroke=stroke,
            opacity=opacity,
            clip=clip_ref,
        )

    def _convert_text_to_ir(self, element: ET.Element):
        from ..ir import Point, Rect, RichTextFrame, TextFrame

        x = float(element.get("x", 0))
        y = float(element.get("y", 0))
        position = Point(x, y)

        lines = self._extract_text_lines(element)
        if not lines:
            return None

        needs_rich_frame = (
            len(lines) > 1
            or any(len(line.runs) > 1 for line in lines)
            or any(line.anchor != lines[0].anchor for line in lines[1:])
        )

        if needs_rich_frame:
            total_height = sum(line.primary_font_size * 1.2 for line in lines)
            max_width = max(sum(len(run.text) * run.font_size_pt * 0.6 for run in line.runs) for line in lines)
            bounds = Rect(x, y, max_width, total_height)

            return RichTextFrame(
                lines=lines,
                position=position,
                bounds=bounds,
                transform=element.get("transform"),
            )

        line = lines[0]
        estimated_width = sum(len(run.text) * run.font_size_pt * 0.6 for run in line.runs)
        estimated_height = line.primary_font_size * 1.2

        return TextFrame(
            origin=position,
            runs=line.runs,
            bbox=Rect(x, y, estimated_width, estimated_height),
            anchor=line.anchor,
        )

    def _convert_image_to_ir(self, element: ET.Element):
        from ..ir import Image, Point, Rect

        x = float(element.get("x", 0))
        y = float(element.get("y", 0))
        width = float(element.get("width", 0))
        height = float(element.get("height", 0))

        if width <= 0 or height <= 0:
            return None

        href = element.get("href") or element.get("{http://www.w3.org/1999/xlink}href")
        if not href:
            return None

        data = b""
        format = "png"
        if href.endswith(".jpg") or href.endswith(".jpeg"):
            format = "jpg"
        elif href.endswith(".gif"):
            format = "gif"
        elif href.endswith(".svg"):
            format = "svg"

        return Image(
            origin=Point(x, y),
            size=Rect(0, 0, width, height),
            data=data,
            format=format,
            href=href,
            opacity=float(element.get("opacity", 1.0)),
        )

    def _convert_foreignobject_to_ir(
        self,
        element: ET.Element,
        traverse_callback: Callable[[ET.Element, NavigationSpec | None], list],
    ):
        from ..ir import ClipRef, Group, Image, Point, Rect, Run, TextAnchor, TextFrame

        try:
            x = float(element.get("x", 0))
            y = float(element.get("y", 0))
            width = float(element.get("width", 0))
            height = float(element.get("height", 0))

            if width <= 0 or height <= 0:
                self.logger.warning(f"ForeignObject has invalid dimensions: {width}x{height}")
                return None

            transform_attr = element.get("transform")
            bbox = Rect(x, y, width, height)
            payload_element = self._get_first_payload_child(element)
            if payload_element is None:
                self.logger.warning("ForeignObject has no content")
                return None

            payload_type = self._classify_payload_type(payload_element)
            complexity_score = self._calculate_payload_complexity(payload_element, payload_type)
            self.logger.debug(f"ForeignObject payload type: {payload_type}, complexity: {complexity_score}")

            if payload_type == "nested_svg":
                child_elements = traverse_callback(payload_element, self._current_navigation)

                transform_matrix = None
                if transform_attr:
                    try:
                        transform_matrix = self._transform_parser.parse_to_matrix(transform_attr)
                        if hasattr(transform_matrix, "to_numpy"):
                            transform_matrix = transform_matrix.to_numpy()
                    except Exception as exc:
                        self.logger.warning(f"Failed to parse transform '{transform_attr}': {exc}")

                return Group(
                    children=child_elements,
                    clip=ClipRef(self._create_bbox_clip_id(bbox), bounding_box=bbox),
                    transform=transform_matrix,
                )

            if payload_type == "image":
                href = (
                    payload_element.get("src")
                    or payload_element.get("href")
                    or payload_element.get("xlink:href")
                    or payload_element.get("{http://www.w3.org/1999/xlink}href")
                )
                if not href:
                    self.logger.warning("Image element in foreignObject has no source")
                    return None

                transform_matrix = None
                if transform_attr:
                    try:
                        transform_matrix = self._transform_parser.parse_to_matrix(transform_attr)
                        if hasattr(transform_matrix, "to_numpy"):
                            transform_matrix = transform_matrix.to_numpy()
                    except Exception as exc:
                        self.logger.warning(f"Failed to parse transform '{transform_attr}': {exc}")

                return Image(
                    origin=Point(bbox.x, bbox.y),
                    size=bbox,
                    data=b"",
                    format="png",
                    href=href,
                    clip=ClipRef(self._create_bbox_clip_id(bbox), bounding_box=bbox),
                    opacity=1.0,
                    transform=transform_matrix,
                )

            if payload_type == "xhtml":
                text_content = self._extract_xhtml_text_content(payload_element)
                if not text_content.strip():
                    return None

                run = Run(
                    text=text_content,
                    font_family="Arial",
                    font_size_pt=12.0,
                    bold=False,
                    italic=False,
                )

                return TextFrame(
                    origin=Point(bbox.x, bbox.y),
                    bbox=bbox,
                    runs=[run],
                    anchor=TextAnchor.START,
                )

            return self._create_foreignobject_placeholder(bbox, transform_attr, payload_type)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error(f"Failed to convert foreignObject to IR: {exc}")
            return None

    # Styling helpers -------------------------------------------------------------------

    def _extract_styling(self, element: ET.Element):
        from ..ir import SolidPaint, Stroke, StrokeCap, StrokeJoin

        paint_style = self.style_resolver.compute_paint_style(element, context=self._style_context)

        fill = None
        fill_color = paint_style.get("fill")
        if fill_color:
            fill = SolidPaint(
                rgb=fill_color,
                opacity=float(paint_style.get("fill_opacity", 1.0)),
            )

        stroke = None
        stroke_color = paint_style.get("stroke")
        if stroke_color:
            stroke_join = StrokeJoin.MITER
            join_attr = element.get("stroke-linejoin", "miter")
            if join_attr == "round":
                stroke_join = StrokeJoin.ROUND
            elif join_attr == "bevel":
                stroke_join = StrokeJoin.BEVEL

            stroke_cap = StrokeCap.BUTT
            cap_attr = element.get("stroke-linecap", "butt")
            if cap_attr == "round":
                stroke_cap = StrokeCap.ROUND
            elif cap_attr == "square":
                stroke_cap = StrokeCap.SQUARE

            stroke = Stroke(
                paint=SolidPaint(
                    rgb=stroke_color,
                    opacity=float(paint_style.get("stroke_opacity", 1.0)),
                ),
                width=float(paint_style.get("stroke_width_px", 1.0)),
                join=stroke_join,
                cap=stroke_cap,
            )

        opacity = float(paint_style.get("opacity", 1.0))

        effects = []
        filter_attr = element.get("filter")
        if filter_attr and self._filter_service:
            try:
                effects = self._filter_service.resolve_effects(filter_attr, self._style_context)
            except Exception as filter_err:  # pragma: no cover - defensive logging
                self.logger.debug(f"Filter resolution failed for {filter_attr}: {filter_err}")
                effects = []

        return fill, stroke, opacity, effects

    def _extract_text_content(self, element: ET.Element) -> str:
        text_parts = []

        if element.text:
            text_parts.append(element.text)

        for child in self._children(element):
            if self._local_name(child.tag) == "tspan":
                if child.text:
                    text_parts.append(child.text)
                if child.tail:
                    text_parts.append(child.tail)
            elif child.text:
                text_parts.append(child.text)

        if element.tail:
            text_parts.append(element.tail)

        return "".join(text_parts).strip()

    def _extract_text_lines(self, element: ET.Element) -> list:
        from ..ir import TextAnchor, TextLine

        base_style = self._read_text_style(element)

        text_anchor_str = element.get("text-anchor", "start")
        default_anchor = {
            "start": TextAnchor.START,
            "middle": TextAnchor.MIDDLE,
            "end": TextAnchor.END,
        }.get(text_anchor_str, TextAnchor.START)

        lines: list[TextLine] = []
        current_runs: list = []

        if element.text and element.text.strip():
            run = self._create_text_run(element.text.strip(), base_style)
            if run:
                current_runs.append(run)

        for child in self._children(element):
            current_runs = self._process_text_child_node(
                child,
                parent_style=base_style,
                default_anchor=default_anchor,
                current_runs=current_runs,
                lines=lines,
            )

        if current_runs:
            lines.append(TextLine(runs=current_runs, anchor=default_anchor))

        if not lines and element.text:
            run = self._create_text_run(element.text.strip(), base_style)
            if run:
                lines.append(TextLine(runs=[run], anchor=default_anchor))

        return lines

    def _process_text_child_node(
        self,
        node: ET.Element,
        parent_style: dict,
        default_anchor,
        current_runs: list,
        lines: list,
    ) -> list:
        from ..ir import TextLine

        tag = self._local_name(node.tag)

        if tag == "tspan":
            if node.get("x") is not None or node.get("y") is not None:
                if current_runs:
                    lines.append(TextLine(runs=current_runs, anchor=default_anchor))
                current_runs = []

            tspan_style = self._read_text_style(node, parent_style=parent_style)

            if node.text and node.text.strip():
                run = self._create_text_run(node.text.strip(), tspan_style)
                if run:
                    current_runs.append(run)

            for child in self._children(node):
                current_runs = self._process_text_child_node(
                    child,
                    parent_style=tspan_style,
                    default_anchor=default_anchor,
                    current_runs=current_runs,
                    lines=lines,
                )

            if node.tail and node.tail.strip():
                run = self._create_text_run(node.tail.strip(), parent_style)
                if run:
                    current_runs.append(run)

            return current_runs

        if tag == "a":
            navigation_spec = self._parse_inline_navigation(node)
            anchor_style = self._read_text_style(node, parent_style=parent_style)

            old_navigation = self._current_navigation
            if navigation_spec:
                self._current_navigation = navigation_spec

            try:
                if node.text and node.text.strip():
                    run = self._create_text_run(node.text.strip(), anchor_style)
                    if run:
                        current_runs.append(run)

                for child in self._children(node):
                    current_runs = self._process_text_child_node(
                        child,
                        parent_style=anchor_style,
                        default_anchor=default_anchor,
                        current_runs=current_runs,
                        lines=lines,
                    )
            finally:
                self._current_navigation = old_navigation

            if node.tail and node.tail.strip():
                run = self._create_text_run(node.tail.strip(), parent_style)
                if run:
                    current_runs.append(run)

            return current_runs

        child_style = self._read_text_style(node, parent_style=parent_style)

        if node.text and node.text.strip():
            run = self._create_text_run(node.text.strip(), child_style)
            if run:
                current_runs.append(run)

        for child in self._children(node):
            current_runs = self._process_text_child_node(
                child,
                parent_style=child_style,
                default_anchor=default_anchor,
                current_runs=current_runs,
                lines=lines,
            )

        if node.tail and node.tail.strip():
            run = self._create_text_run(node.tail.strip(), parent_style)
            if run:
                current_runs.append(run)

        return current_runs

    def _parse_inline_navigation(self, anchor_element: ET.Element):
        return self._hyperlinks.resolve_inline_navigation(anchor_element)

    def _read_text_style(self, element: ET.Element, parent_style: dict | None = None) -> dict:
        return self.style_resolver.compute_text_style(element, parent_style=parent_style)

    def _create_text_run(self, text: str, style: dict):
        from ..ir import Run

        if not text or not text.strip():
            return None

        rgb = parse_color(style.get("fill", "000000"))

        font_weight = style.get("font_weight", "normal")
        is_bold = (
            font_weight == "bold"
            or font_weight == "bolder"
            or (font_weight.isdigit() and int(font_weight) >= FONT_WEIGHT_BOLD_THRESHOLD)
        )

        text_decoration = style.get("text_decoration", "none")
        is_underline = "underline" in text_decoration
        is_strike = "line-through" in text_decoration

        try:
            return Run(
                text=text,
                font_family=style.get("font_family", "Arial"),
                font_size_pt=style.get("font_size_pt", 12.0),
                bold=is_bold,
                italic=style.get("font_style") == "italic",
                underline=is_underline,
                strike=is_strike,
                rgb=rgb,
                navigation=self._current_navigation,
                font_weight=style.get("font_weight", "normal"),
                font_style=style.get("font_style", "normal"),
            )
        except ValueError as exc:  # pragma: no cover - defensive logging
            self.logger.warning(f"Error creating text run: {exc}")
            return None

    def _parse_path_data(self, d: str):
        segments = []
        commands = self._path_command_pattern.findall(d)

        current_point = Point(0, 0)
        start_point = Point(0, 0)

        for command in commands:
            cmd_type = command[0]
            params = command[1:].strip()
            values = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", params)]

            is_relative = cmd_type.islower()
            cmd_type = cmd_type.upper()

            if cmd_type == "M":
                if len(values) >= 2:
                    current_point = Point(values[0], values[1])
                    start_point = current_point
            elif cmd_type == "L":
                for i in range(0, len(values), 2):
                    x = values[i]
                    y = values[i + 1]
                    point = Point(x, y)
                    if is_relative:
                        point = Point(current_point.x + x, current_point.y + y)
                    segments.append(LineSegment(start=current_point, end=point))
                    current_point = point
            elif cmd_type == "H":
                for value in values:
                    x = value
                    point = Point(x, current_point.y)
                    if is_relative:
                        point = Point(current_point.x + x, current_point.y)
                    segments.append(LineSegment(start=current_point, end=point))
                    current_point = point
            elif cmd_type == "V":
                for value in values:
                    y = value
                    point = Point(current_point.x, y)
                    if is_relative:
                        point = Point(current_point.x, current_point.y + y)
                    segments.append(LineSegment(start=current_point, end=point))
                    current_point = point
            elif cmd_type == "C":
                for i in range(0, len(values), 6):
                    control1 = Point(values[i], values[i + 1])
                    control2 = Point(values[i + 2], values[i + 3])
                    end_point = Point(values[i + 4], values[i + 5])
                    if is_relative:
                        control1 = Point(current_point.x + control1.x, current_point.y + control1.y)
                        control2 = Point(current_point.x + control2.x, current_point.y + control2.y)
                        end_point = Point(current_point.x + end_point.x, current_point.y + end_point.y)
                    segments.append(
                        BezierSegment(
                            start=current_point,
                            control1=control1,
                            control2=control2,
                            end=end_point,
                        )
                    )
                    current_point = end_point
            elif cmd_type == "Z":
                segments.append(LineSegment(start=current_point, end=start_point))
                current_point = start_point

        if self.coord_space is None:
            return segments

        transformed_segments = []
        for segment in segments[:MAX_SIMPLE_PATH_SEGMENTS]:
            if isinstance(segment, LineSegment):
                start = self.coord_space.apply_ctm(segment.start.x, segment.start.y)
                end = self.coord_space.apply_ctm(segment.end.x, segment.end.y)
                transformed_segments.append(LineSegment(Point(*start), Point(*end)))
            elif isinstance(segment, BezierSegment):
                start = self.coord_space.apply_ctm(segment.start.x, segment.start.y)
                control1 = self.coord_space.apply_ctm(segment.control1.x, segment.control1.y)
                control2 = self.coord_space.apply_ctm(segment.control2.x, segment.control2.y)
                end = self.coord_space.apply_ctm(segment.end.x, segment.end.y)
                transformed_segments.append(
                    BezierSegment(
                        start=Point(*start),
                        control1=Point(*control1),
                        control2=Point(*control2),
                        end=Point(*end),
                    )
                )

        return transformed_segments

    # ForeignObject helpers -------------------------------------------------------------

    def _get_first_payload_child(self, foreignobject_element: ET.Element):
        for child in self._children(foreignobject_element):
            if child.tag and not child.tag.startswith("{"):
                return child
            tag = self._local_name(child.tag)
            if tag and tag not in ["defs", "metadata", "title", "desc"]:
                return child
        return None

    def _classify_payload_type(self, payload_element: ET.Element) -> str:
        if not payload_element.tag:
            return "unknown"

        tag_str = str(payload_element.tag)
        if "}" in tag_str:
            namespace, tag = tag_str.split("}", 1)
            namespace = namespace[1:]
        else:
            namespace = ""
            tag = tag_str

        if tag == "svg" and "svg" in namespace.lower():
            return "nested_svg"

        image_tags = ["img", "image", "object", "picture"]
        if tag in image_tags:
            if (
                payload_element.get("src")
                or payload_element.get("href")
                or payload_element.get("xlink:href")
                or payload_element.get("{http://www.w3.org/1999/xlink}href")
            ):
                return "image"

        xhtml_tags = [
            "p",
            "div",
            "span",
            "table",
            "tbody",
            "tr",
            "td",
            "th",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "ul",
            "ol",
            "li",
            "dl",
            "dt",
            "dd",
            "a",
            "em",
            "strong",
            "b",
            "i",
            "u",
            "br",
            "hr",
            "pre",
            "code",
            "blockquote",
        ]
        if tag in xhtml_tags or "xhtml" in namespace.lower() or "html" in namespace.lower():
            return "xhtml"

        return "unknown"

    def _create_bbox_clip_id(self, bbox: Rect) -> str:
        return f"bbox:{bbox.x},{bbox.y},{bbox.width},{bbox.height}"

    def _extract_xhtml_text_content(self, element: ET.Element) -> str:
        text_parts = []

        if element.text:
            text_parts.append(element.text.strip())

        for child in self._children(element):
            child_text = self._extract_text_content(child)
            if child_text:
                text_parts.append(child_text)
            if child.tail:
                text_parts.append(child.tail.strip())

        return " ".join(text_parts)

    def _create_foreignobject_placeholder(self, bbox: Rect, transform_attr: str | None, payload_type: str):
        from ..ir import ClipRef, Group, LineSegment, Path, Point, SolidPaint, Stroke

        x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height

        segments = [
            LineSegment(Point(x, y), Point(x + w, y)),
            LineSegment(Point(x + w, y), Point(x + w, y + h)),
            LineSegment(Point(x + w, y + h), Point(x, y + h)),
            LineSegment(Point(x, y + h), Point(x, y)),
        ]

        placeholder_path = Path(
            segments=segments,
            fill=SolidPaint(rgb="F0F0F0"),
            stroke=Stroke(paint=SolidPaint(rgb="999999"), width=1.0),
            opacity=0.5,
        )

        transform_matrix = None
        if transform_attr:
            try:
                transform_matrix = self._transform_parser.parse_to_matrix(transform_attr)
                if hasattr(transform_matrix, "to_numpy"):
                    transform_matrix = transform_matrix.to_numpy()
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger.warning(f"Failed to parse transform '{transform_attr}': {exc}")

        return Group(
            children=[placeholder_path],
            clip=ClipRef(self._create_bbox_clip_id(bbox), bounding_box=bbox),
            transform=transform_matrix,
        )

    def _calculate_payload_complexity(self, payload_element: ET.Element, payload_type: str) -> int:
        complexity = 0
        for _ in self._children(payload_element):
            complexity += 1
        if payload_type == "xhtml":
            complexity += 10
        elif payload_type == "nested_svg":
            complexity += 25
        return complexity

    # Clip helpers ----------------------------------------------------------------------

    def _extract_clip_reference(self, element: ET.Element):
        from ..ir.scene import ClipRef

        clip_attr = element.get("clip-path")
        if not clip_attr:
            return None

        clip_key = self._extract_clip_id(clip_attr)
        if not clip_key:
            return None

        normalized = self._normalize_clip_attribute(clip_attr, clip_key)
        clip_def = self._clip_definitions.get(clip_key)

        if clip_def:
            return ClipRef(
                clip_id=normalized,
                path_segments=clip_def.segments,
                bounding_box=clip_def.bounding_box,
                clip_rule=clip_def.clip_rule,
            )

        return ClipRef(clip_id=normalized)

    @staticmethod
    def _normalize_clip_attribute(raw_value: str, clip_key: str) -> str:
        value = raw_value.strip()
        if value.startswith("url("):
            return value
        if value.startswith("#"):
            return f"url({value})"
        return f"url(#{clip_key})"

    @staticmethod
    def _extract_clip_id(raw_value: str) -> str | None:
        if not raw_value:
            return None
        value = raw_value.strip()
        if value.startswith("url(") and value.endswith(")"):
            inner = value[4:-1].strip().strip('"\'"')
            if inner.startswith("#"):
                inner = inner[1:]
            return inner or None
        if value.startswith("#"):
            return value[1:] or None
        return None

    # Utility ---------------------------------------------------------------------------

    @staticmethod
    def _local_name(tag: str | None) -> str:
        if not tag:
            return ""
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag


__all__ = ["IRConverter"]
