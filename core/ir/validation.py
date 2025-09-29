#!/usr/bin/env python3
"""
IR validation and serialization

Validates IR data structures and provides serialization for golden tests.
Ensures IR is always in valid state for mappers.
"""

from typing import Any, Dict, List, Union
import json
# Use shared numpy compatibility
from .numpy_compat import np, NUMPY_AVAILABLE

from .scene import IRElement, Path, TextFrame, Group, Image
from .geometry import Point, Rect, Segment, LineSegment, BezierSegment
from .paint import Paint, SolidPaint, LinearGradientPaint, RadialGradientPaint
from .text import Run, TextAnchor


class IRValidationError(Exception):
    """Raised when IR validation fails"""
    pass


def validate_ir(elements: List[IRElement]) -> None:
    """
    Validate IR scene graph for correctness.

    Checks:
    - All required fields present
    - Numeric ranges valid
    - No circular references in groups
    - Paint types consistent

    Args:
        elements: List of IR elements to validate

    Raises:
        IRValidationError: If validation fails
    """
    if not isinstance(elements, list):
        raise IRValidationError("IR must be a list of elements")

    for i, element in enumerate(elements):
        try:
            _validate_element(element)
        except Exception as e:
            raise IRValidationError(f"Element {i} validation failed: {e}")


def _validate_element(element: IRElement) -> None:
    """Validate single IR element"""
    if isinstance(element, Path):
        _validate_path(element)
    elif isinstance(element, TextFrame):
        _validate_text_frame(element)
    elif isinstance(element, Group):
        _validate_group(element)
    elif isinstance(element, Image):
        _validate_image(element)
    else:
        raise IRValidationError(f"Unknown IR element type: {type(element)}")


def _validate_path(path: Path) -> None:
    """Validate Path element"""
    if not path.segments:
        raise IRValidationError("Path must have at least one segment")

    for i, segment in enumerate(path.segments):
        if not isinstance(segment, (LineSegment, BezierSegment)):
            raise IRValidationError(f"Segment {i} has invalid type: {type(segment)}")

    if not (0.0 <= path.opacity <= 1.0):
        raise IRValidationError(f"Path opacity out of range: {path.opacity}")

    if path.transform is not None and path.transform.shape != (3, 3):
        raise IRValidationError(f"Path transform must be 3x3 matrix, got {path.transform.shape}")


def _validate_text_frame(frame: TextFrame) -> None:
    """Validate TextFrame element"""
    if not frame.runs:
        raise IRValidationError("TextFrame must have at least one run")

    for i, run in enumerate(frame.runs):
        if not isinstance(run, Run):
            raise IRValidationError(f"Run {i} has invalid type: {type(run)}")
        if run.font_size_pt <= 0:
            raise IRValidationError(f"Run {i} has invalid font size: {run.font_size_pt}")

    if not isinstance(frame.anchor, TextAnchor):
        raise IRValidationError(f"TextFrame anchor has invalid type: {type(frame.anchor)}")


def _validate_group(group: Group) -> None:
    """Validate Group element"""
    if not (0.0 <= group.opacity <= 1.0):
        raise IRValidationError(f"Group opacity out of range: {group.opacity}")

    # Check for circular references (simplified)
    if group.total_element_count > 10000:
        raise IRValidationError("Group nesting too deep (possible circular reference)")

    for child in group.children:
        _validate_element(child)


def _validate_image(image: Image) -> None:
    """Validate Image element"""
    if not image.data:
        raise IRValidationError("Image data cannot be empty")

    if image.format not in ["png", "jpg", "gif", "svg"]:
        raise IRValidationError(f"Unsupported image format: {image.format}")

    if not (0.0 <= image.opacity <= 1.0):
        raise IRValidationError(f"Image opacity out of range: {image.opacity}")


def serialize_ir(elements: List[IRElement]) -> str:
    """
    Serialize IR to JSON for golden tests and debugging.

    Args:
        elements: IR elements to serialize

    Returns:
        JSON string representation
    """
    return json.dumps(_serialize_elements(elements), indent=2, sort_keys=True)


def deserialize_ir(json_str: str) -> List[IRElement]:
    """
    Deserialize IR from JSON.

    Args:
        json_str: JSON string to deserialize

    Returns:
        List of IR elements
    """
    data = json.loads(json_str)
    return _deserialize_elements(data)


def _serialize_elements(elements: List[IRElement]) -> List[Dict[str, Any]]:
    """Serialize elements to JSON-compatible format"""
    result = []
    for element in elements:
        if isinstance(element, Path):
            result.append(_serialize_path(element))
        elif isinstance(element, TextFrame):
            result.append(_serialize_text_frame(element))
        elif isinstance(element, Group):
            result.append(_serialize_group(element))
        elif isinstance(element, Image):
            result.append(_serialize_image(element))
        else:
            raise IRValidationError(f"Cannot serialize element type: {type(element)}")
    return result


def _serialize_path(path: Path) -> Dict[str, Any]:
    """Serialize Path to dict"""
    return {
        "type": "Path",
        "segments": [_serialize_segment(seg) for seg in path.segments],
        "fill": _serialize_paint(path.fill),
        "stroke": _serialize_stroke(path.stroke),
        "clip": _serialize_clip(path.clip),
        "opacity": path.opacity,
        "transform": path.transform.tolist() if path.transform is not None else None,
        "bbox": _serialize_rect(path.bbox),
        "complexity_score": path.complexity_score
    }


def _serialize_segment(segment: Segment) -> Dict[str, Any]:
    """Serialize segment to dict"""
    if isinstance(segment, LineSegment):
        return {
            "type": "LineSegment",
            "start": _serialize_point(segment.start),
            "end": _serialize_point(segment.end)
        }
    elif isinstance(segment, BezierSegment):
        return {
            "type": "BezierSegment",
            "start": _serialize_point(segment.start),
            "control1": _serialize_point(segment.control1),
            "control2": _serialize_point(segment.control2),
            "end": _serialize_point(segment.end)
        }
    else:
        raise IRValidationError(f"Cannot serialize segment type: {type(segment)}")


def _serialize_point(point: Point) -> List[float]:
    """Serialize Point to [x, y]"""
    return [point.x, point.y]


def _serialize_rect(rect: Rect) -> List[float]:
    """Serialize Rect to [x, y, width, height]"""
    return [rect.x, rect.y, rect.width, rect.height]


def _serialize_paint(paint: Paint) -> Union[Dict[str, Any], None]:
    """Serialize Paint to dict"""
    if paint is None:
        return None
    elif isinstance(paint, SolidPaint):
        return {
            "type": "SolidPaint",
            "rgb": paint.rgb,
            "opacity": paint.opacity
        }
    elif isinstance(paint, LinearGradientPaint):
        return {
            "type": "LinearGradientPaint",
            "stops": [{"offset": s.offset, "rgb": s.rgb, "opacity": s.opacity} for s in paint.stops],
            "start": _serialize_point(paint.start),
            "end": _serialize_point(paint.end),
            "transform": paint.transform.tolist() if paint.transform is not None else None
        }
    else:
        return {"type": "UnknownPaint", "class": type(paint).__name__}


def _serialize_stroke(stroke) -> Union[Dict[str, Any], None]:
    """Serialize Stroke to dict"""
    if stroke is None:
        return None
    return {
        "paint": _serialize_paint(stroke.paint),
        "width": stroke.width,
        "join": stroke.join.value,
        "cap": stroke.cap.value,
        "opacity": stroke.opacity,
        "is_dashed": stroke.is_dashed
    }


def _serialize_clip(clip) -> Union[Dict[str, Any], None]:
    """Serialize ClipRef to dict"""
    if clip is None:
        return None
    return {
        "clip_id": clip.clip_id,
        "strategy": clip.strategy.value
    }


def _serialize_text_frame(frame: TextFrame) -> Dict[str, Any]:
    """Serialize TextFrame to dict"""
    return {
        "type": "TextFrame",
        "origin": _serialize_point(frame.origin),
        "runs": [_serialize_run(run) for run in frame.runs],
        "anchor": frame.anchor.value,
        "bbox": _serialize_rect(frame.bbox),
        "text_content": frame.text_content,
        "complexity_score": frame.complexity_score
    }


def _serialize_run(run: Run) -> Dict[str, Any]:
    """Serialize Run to dict"""
    return {
        "text": run.text,
        "font_family": run.font_family,
        "font_size_pt": run.font_size_pt,
        "bold": run.bold,
        "italic": run.italic,
        "underline": run.underline,
        "strike": run.strike,
        "rgb": run.rgb
    }


def _serialize_group(group: Group) -> Dict[str, Any]:
    """Serialize Group to dict"""
    return {
        "type": "Group",
        "children": _serialize_elements(group.children),
        "clip": _serialize_clip(group.clip),
        "opacity": group.opacity,
        "transform": group.transform.tolist() if group.transform is not None else None,
        "bbox": _serialize_rect(group.bbox),
        "total_element_count": group.total_element_count
    }


def _serialize_image(image: Image) -> Dict[str, Any]:
    """Serialize Image to dict"""
    return {
        "type": "Image",
        "origin": _serialize_point(image.origin),
        "size": _serialize_rect(image.size),
        "format": image.format,
        "data_size": len(image.data),
        "clip": _serialize_clip(image.clip),
        "opacity": image.opacity,
        "transform": image.transform.tolist() if image.transform is not None else None
    }


# Deserialization methods (simplified for now)
def _deserialize_elements(data: List[Dict[str, Any]]) -> List[IRElement]:
    """Deserialize elements from JSON data"""
    # TODO: Implement full deserialization when needed for golden tests
    raise NotImplementedError("Full deserialization not yet implemented")