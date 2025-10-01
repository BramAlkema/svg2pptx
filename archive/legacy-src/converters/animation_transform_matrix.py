#!/usr/bin/env python3
"""
Transform Matrix Handler for PowerPoint Animations

This module provides advanced matrix transformation capabilities for converting
SVG animations to PowerPoint DrawingML format, including proper matrix composition
and PowerPoint-specific coordinate system handling.

Key Features:
- Matrix composition for combined transforms
- SVG to PowerPoint coordinate system conversion
- Transform decomposition for PowerPoint animation
- EMU (English Metric Units) conversion
"""

import math
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class MatrixOperation(Enum):
    """Matrix operation types."""
    TRANSLATE = "translate"
    SCALE = "scale"
    ROTATE = "rotate"
    SKEW_X = "skewX"
    SKEW_Y = "skewY"
    MATRIX = "matrix"


@dataclass
class TransformMatrix:
    """2D transformation matrix representation."""
    a: float = 1.0  # Scale X / Rotation cos
    b: float = 0.0  # Rotation sin / Skew Y
    c: float = 0.0  # Rotation -sin / Skew X
    d: float = 1.0  # Scale Y / Rotation cos
    e: float = 0.0  # Translate X
    f: float = 0.0  # Translate Y

    def multiply(self, other: 'TransformMatrix') -> 'TransformMatrix':
        """
        Multiply this matrix by another matrix.

        Matrix multiplication: [this] × [other]
        """
        return TransformMatrix(
            a=self.a * other.a + self.b * other.c,
            b=self.a * other.b + self.b * other.d,
            c=self.c * other.a + self.d * other.c,
            d=self.c * other.b + self.d * other.d,
            e=self.e * other.a + self.f * other.c + other.e,
            f=self.e * other.b + self.f * other.d + other.f
        )

    def to_powerpoint_transform(self) -> Dict[str, Any]:
        """
        Convert matrix to PowerPoint transform attributes.

        Returns:
            Dictionary with PowerPoint transform properties
        """
        # Decompose matrix into PowerPoint-compatible components
        decomposed = self.decompose()

        # Convert to PowerPoint units (EMU for position, 60000ths of degree for rotation)
        return {
            'translate_x': int(decomposed['translate'][0] * 914400),  # Convert to EMU
            'translate_y': int(decomposed['translate'][1] * 914400),
            'scale_x': decomposed['scale'][0],
            'scale_y': decomposed['scale'][1],
            'rotate': int(decomposed['rotate'] * 60000),  # Convert to 60000ths of degree
            'skew_x': int(decomposed['skew'][0] * 60000),
            'skew_y': int(decomposed['skew'][1] * 60000)
        }

    def decompose(self) -> Dict[str, Any]:
        """
        Decompose matrix into translate, scale, rotate, and skew components.

        Returns:
            Dictionary with decomposed transform components
        """
        # Translation
        translate = [self.e, self.f]

        # Scale and rotation
        scale_x = math.sqrt(self.a * self.a + self.b * self.b)
        scale_y = math.sqrt(self.c * self.c + self.d * self.d)

        # Normalize for rotation calculation
        if scale_x != 0:
            a_norm = self.a / scale_x
            b_norm = self.b / scale_x
        else:
            a_norm, b_norm = 1, 0

        # Rotation in degrees
        rotation = math.degrees(math.atan2(b_norm, a_norm))

        # Skew calculation (after removing rotation and scale)
        # This is simplified; full decomposition is complex
        skew_x = 0
        skew_y = 0

        # Check for skew by comparing with pure rotation/scale
        expected_c = -scale_y * math.sin(math.radians(rotation))
        expected_d = scale_y * math.cos(math.radians(rotation))

        if abs(self.c - expected_c) > 0.001 or abs(self.d - expected_d) > 0.001:
            # There's skew present
            determinant = self.a * self.d - self.b * self.c
            if determinant != 0 and scale_x != 0:
                skew_x = math.degrees(math.atan((self.c * scale_x + self.b * scale_y) / determinant))
                skew_y = math.degrees(math.atan((self.a * scale_y + self.d * scale_x) / determinant))

        return {
            'translate': translate,
            'scale': [scale_x, scale_y],
            'rotate': rotation,
            'skew': [skew_x, skew_y]
        }

    @classmethod
    def identity(cls) -> 'TransformMatrix':
        """Create identity matrix."""
        return cls()

    @classmethod
    def from_translate(cls, tx: float, ty: float = 0) -> 'TransformMatrix':
        """Create translation matrix."""
        return cls(e=tx, f=ty)

    @classmethod
    def from_scale(cls, sx: float, sy: Optional[float] = None) -> 'TransformMatrix':
        """Create scale matrix."""
        if sy is None:
            sy = sx
        return cls(a=sx, d=sy)

    @classmethod
    def from_rotate(cls, angle: float, cx: float = 0, cy: float = 0) -> 'TransformMatrix':
        """
        Create rotation matrix.

        Args:
            angle: Rotation angle in degrees
            cx, cy: Center of rotation
        """
        angle_rad = math.radians(angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        if cx == 0 and cy == 0:
            return cls(a=cos_a, b=sin_a, c=-sin_a, d=cos_a)

        # Rotation around a point: translate(-cx,-cy), rotate, translate(cx,cy)
        return (cls.from_translate(-cx, -cy)
                .multiply(cls(a=cos_a, b=sin_a, c=-sin_a, d=cos_a))
                .multiply(cls.from_translate(cx, cy)))

    @classmethod
    def from_skew_x(cls, angle: float) -> 'TransformMatrix':
        """Create skewX matrix."""
        angle_rad = math.radians(angle)
        return cls(c=math.tan(angle_rad))

    @classmethod
    def from_skew_y(cls, angle: float) -> 'TransformMatrix':
        """Create skewY matrix."""
        angle_rad = math.radians(angle)
        return cls(b=math.tan(angle_rad))

    @classmethod
    def from_matrix_values(cls, values: List[float]) -> 'TransformMatrix':
        """
        Create matrix from 6 values [a, b, c, d, e, f].
        """
        if len(values) != 6:
            raise ValueError(f"Matrix requires 6 values, got {len(values)}")
        return cls(a=values[0], b=values[1], c=values[2],
                  d=values[3], e=values[4], f=values[5])


class AnimationTransformProcessor:
    """Processes SVG animation transforms for PowerPoint conversion."""

    def __init__(self):
        """Initialize the transform processor."""
        self.emu_per_pixel = 9525  # Default EMU conversion factor

    def parse_transform_string(self, transform_str: str) -> List[Tuple[MatrixOperation, List[float]]]:
        """
        Parse SVG transform string into operations list using canonical TransformEngine.

        Args:
            transform_str: SVG transform string like "translate(10,20) rotate(45)"

        Returns:
            List of (operation, values) tuples
        """
        try:
            # Use the canonical high-performance TransformEngine for parsing
            from ...transforms import TransformEngine

            engine = services.transform_parser
            transforms = engine.parse(transform_str)

            # Convert to expected format for animation processing
            operations = []
            for t in transforms:
                op_name = t.get('type', '')
                values = t.get('values', [])

                # Map to operation enum
                try:
                    operation = MatrixOperation(op_name)
                    operations.append((operation, values))
                except ValueError:
                    # Skip unknown operations for animation compatibility
                    continue

            return operations

        except ImportError:
            # Fallback to legacy parsing if TransformEngine not available
            return self._legacy_parse_transform_string(transform_str)
        except Exception:
            # Fallback to legacy parsing on any error
            return self._legacy_parse_transform_string(transform_str)

    def _legacy_parse_transform_string(self, transform_str: str) -> List[Tuple[MatrixOperation, List[float]]]:
        """Legacy transform parsing - to be replaced once TransformEngine integration is complete."""
        import re

        operations = []
        pattern = r'(\w+)\(([^)]+)\)'

        for match in re.finditer(pattern, transform_str):
            op_name = match.group(1)
            values_str = match.group(2)

            # Parse values
            values = [float(v.strip()) for v in re.split(r'[,\s]+', values_str)]

            # Map to operation enum
            try:
                operation = MatrixOperation(op_name)
                operations.append((operation, values))
            except ValueError:
                # Unknown operation, skip
                pass

        return operations

    def operations_to_matrix(self, operations: List[Tuple[MatrixOperation, List[float]]]) -> TransformMatrix:
        """
        Convert list of transform operations to combined matrix.

        Args:
            operations: List of (operation, values) tuples

        Returns:
            Combined transformation matrix
        """
        result = TransformMatrix.identity()

        for operation, values in operations:
            if operation == MatrixOperation.TRANSLATE:
                tx = values[0] if len(values) > 0 else 0
                ty = values[1] if len(values) > 1 else 0
                result = result.multiply(TransformMatrix.from_translate(tx, ty))

            elif operation == MatrixOperation.SCALE:
                sx = values[0] if len(values) > 0 else 1
                sy = values[1] if len(values) > 1 else sx
                result = result.multiply(TransformMatrix.from_scale(sx, sy))

            elif operation == MatrixOperation.ROTATE:
                angle = values[0] if len(values) > 0 else 0
                cx = values[1] if len(values) > 2 else 0
                cy = values[2] if len(values) > 2 else 0
                result = result.multiply(TransformMatrix.from_rotate(angle, cx, cy))

            elif operation == MatrixOperation.SKEW_X:
                angle = values[0] if len(values) > 0 else 0
                result = result.multiply(TransformMatrix.from_skew_x(angle))

            elif operation == MatrixOperation.SKEW_Y:
                angle = values[0] if len(values) > 0 else 0
                result = result.multiply(TransformMatrix.from_skew_y(angle))

            elif operation == MatrixOperation.MATRIX:
                if len(values) == 6:
                    result = result.multiply(TransformMatrix.from_matrix_values(values))

        return result

    def interpolate_matrices(self, matrix1: TransformMatrix, matrix2: TransformMatrix,
                           t: float) -> TransformMatrix:
        """
        Interpolate between two matrices.

        Args:
            matrix1: Start matrix
            matrix2: End matrix
            t: Interpolation factor (0-1)

        Returns:
            Interpolated matrix
        """
        # Decompose both matrices
        decomp1 = matrix1.decompose()
        decomp2 = matrix2.decompose()

        # Interpolate components
        translate_x = decomp1['translate'][0] + (decomp2['translate'][0] - decomp1['translate'][0]) * t
        translate_y = decomp1['translate'][1] + (decomp2['translate'][1] - decomp1['translate'][1]) * t

        scale_x = decomp1['scale'][0] + (decomp2['scale'][0] - decomp1['scale'][0]) * t
        scale_y = decomp1['scale'][1] + (decomp2['scale'][1] - decomp1['scale'][1]) * t

        # Handle rotation interpolation (shortest path)
        rot1 = decomp1['rotate']
        rot2 = decomp2['rotate']

        # Normalize angles to -180 to 180
        while rot2 - rot1 > 180:
            rot2 -= 360
        while rot2 - rot1 < -180:
            rot2 += 360

        rotation = rot1 + (rot2 - rot1) * t

        # Reconstruct matrix from interpolated components
        result = (TransformMatrix.from_translate(translate_x, translate_y)
                 .multiply(TransformMatrix.from_rotate(rotation))
                 .multiply(TransformMatrix.from_scale(scale_x, scale_y)))

        return result

    def generate_powerpoint_transform_xml(self, matrix: TransformMatrix,
                                         element_id: str) -> str:
        """
        Generate PowerPoint transform XML from matrix.

        Args:
            matrix: Transformation matrix
            element_id: Target element ID

        Returns:
            PowerPoint transform XML string
        """
        transform = matrix.to_powerpoint_transform()

        # Build transform XML based on non-identity components
        xml_parts = []

        if abs(transform['translate_x']) > 1 or abs(transform['translate_y']) > 1:
            xml_parts.append(f'''<a:off x="{transform['translate_x']}" y="{transform['translate_y']}"/>''')

        if abs(transform['scale_x'] - 1.0) > 0.001 or abs(transform['scale_y'] - 1.0) > 0.001:
            # Convert to percentage (100000 = 100%)
            scale_x_pct = int(transform['scale_x'] * 100000)
            scale_y_pct = int(transform['scale_y'] * 100000)
            xml_parts.append(f'''<a:ext cx="{scale_x_pct}" cy="{scale_y_pct}"/>''')

        if abs(transform['rotate']) > 1:
            xml_parts.append(f'''<a:rot rot="{transform['rotate']}"/>''')

        if not xml_parts:
            return ""  # No transform needed

        # Wrap in transform group
        return f'''<a:xfrm>
  {chr(10).join(xml_parts)}
</a:xfrm>'''


class PowerPointTransformAnimationGenerator:
    """Generates PowerPoint transform animations from SVG transforms."""

    def __init__(self):
        """Initialize the generator."""
        self.processor = AnimationTransformProcessor()

    def generate_transform_animation(self, from_transform: str, to_transform: str,
                                   duration_ms: int, element_id: str) -> str:
        """
        Generate PowerPoint transform animation XML.

        Args:
            from_transform: Starting SVG transform string
            to_transform: Ending SVG transform string
            duration_ms: Animation duration in milliseconds
            element_id: Target element ID

        Returns:
            PowerPoint animation XML
        """
        # Parse transforms
        from_ops = self.processor.parse_transform_string(from_transform)
        to_ops = self.processor.parse_transform_string(to_transform)

        # Convert to matrices
        from_matrix = self.processor.operations_to_matrix(from_ops)
        to_matrix = self.processor.operations_to_matrix(to_ops)

        # Decompose for animation
        from_decomp = from_matrix.decompose()
        to_decomp = to_matrix.decompose()

        # Generate appropriate animation based on differences
        animations = []

        # Translation animation
        if (abs(to_decomp['translate'][0] - from_decomp['translate'][0]) > 0.1 or
            abs(to_decomp['translate'][1] - from_decomp['translate'][1]) > 0.1):

            from_x = int(from_decomp['translate'][0] * 914400)
            from_y = int(from_decomp['translate'][1] * 914400)
            to_x = int(to_decomp['translate'][0] * 914400)
            to_y = int(to_decomp['translate'][1] * 914400)

            animations.append(f'''<a:animMotion>
  <a:cBhvr>
    <a:cTn dur="{duration_ms}"/>
    <a:tgtEl>
      <a:spTgt spid="{element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:from>
    <a:pt x="{from_x}" y="{from_y}"/>
  </a:from>
  <a:to>
    <a:pt x="{to_x}" y="{to_y}"/>
  </a:to>
</a:animMotion>''')

        # Scale animation
        if (abs(to_decomp['scale'][0] - from_decomp['scale'][0]) > 0.01 or
            abs(to_decomp['scale'][1] - from_decomp['scale'][1]) > 0.01):

            animations.append(f'''<a:animScale>
  <a:cBhvr>
    <a:cTn dur="{duration_ms}"/>
    <a:tgtEl>
      <a:spTgt spid="{element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:from>
    <a:pt x="{from_decomp['scale'][0]}" y="{from_decomp['scale'][1]}"/>
  </a:from>
  <a:to>
    <a:pt x="{to_decomp['scale'][0]}" y="{to_decomp['scale'][1]}"/>
  </a:to>
</a:animScale>''')

        # Rotation animation
        if abs(to_decomp['rotate'] - from_decomp['rotate']) > 0.1:
            from_rot = int(from_decomp['rotate'] * 60000)
            to_rot = int(to_decomp['rotate'] * 60000)

            animations.append(f'''<a:animRot>
  <a:cBhvr>
    <a:cTn dur="{duration_ms}"/>
    <a:tgtEl>
      <a:spTgt spid="{element_id}"/>
    </a:tgtEl>
  </a:cBhvr>
  <a:from val="{from_rot}"/>
  <a:to val="{to_rot}"/>
</a:animRot>''')

        # Combine animations in parallel group if multiple
        if len(animations) > 1:
            return f'''<a:par>
  <a:cTn>
    <a:childTnLst>
      {chr(10).join(animations)}
    </a:childTnLst>
  </a:cTn>
</a:par>'''
        elif animations:
            return animations[0]
        else:
            return ""