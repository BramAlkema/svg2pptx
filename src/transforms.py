#!/usr/bin/env python3
"""
Universal Transform Matrix Engine for SVG2PPTX

This module provides centralized, robust SVG transform parsing with comprehensive
matrix operations and DrawingML integration. Handles all SVG transform types
with accurate matrix composition and coordinate transformation.

Key Features:
- Complete SVG transform parsing (translate, rotate, scale, skew, matrix)
- Matrix composition and decomposition
- Coordinate system transformations
- DrawingML transform XML generation
- Transform chain optimization
- Bounding box calculations with transforms
- Integration with Universal Unit Converter
- Viewport-aware coordinate mapping

SVG Transform Reference:
- translate(x [y]) - Translation transform
- rotate(angle [cx cy]) - Rotation around optional center
- scale(sx [sy]) - Scaling transform
- skewX(angle) / skewY(angle) - Skew transforms
- matrix(a b c d e f) - Direct matrix specification
"""

import re
import math
from typing import List, Tuple, Optional, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
from lxml import etree as ET

from .units import UnitConverter, ViewportContext, EMU_PER_INCH


class TransformType(Enum):
    """SVG transform types."""
    TRANSLATE = "translate"
    ROTATE = "rotate"
    SCALE = "scale"
    SKEW_X = "skewX"
    SKEW_Y = "skewY"
    MATRIX = "matrix"


@dataclass
class Transform:
    """Individual transform operation."""
    type: TransformType
    values: List[float]
    original: str
    
    def to_matrix(self) -> 'Matrix':
        """Convert this transform to a transformation matrix."""
        if self.type == TransformType.TRANSLATE:
            tx = self.values[0] if len(self.values) > 0 else 0
            ty = self.values[1] if len(self.values) > 1 else 0
            return Matrix.translate(tx, ty)
        
        elif self.type == TransformType.ROTATE:
            angle = self.values[0] if len(self.values) > 0 else 0
            if len(self.values) >= 3:
                # Rotate around center point
                cx, cy = self.values[1], self.values[2]
                return (Matrix.translate(cx, cy).
                       multiply(Matrix.rotate(angle)).
                       multiply(Matrix.translate(-cx, -cy)))
            else:
                return Matrix.rotate(angle)
        
        elif self.type == TransformType.SCALE:
            sx = self.values[0] if len(self.values) > 0 else 1
            sy = self.values[1] if len(self.values) > 1 else sx
            return Matrix.scale(sx, sy)
        
        elif self.type == TransformType.SKEW_X:
            angle = self.values[0] if len(self.values) > 0 else 0
            return Matrix.skew_x(angle)
        
        elif self.type == TransformType.SKEW_Y:
            angle = self.values[0] if len(self.values) > 0 else 0
            return Matrix.skew_y(angle)
        
        elif self.type == TransformType.MATRIX:
            if len(self.values) >= 6:
                return Matrix(self.values[0], self.values[1], self.values[2],
                            self.values[3], self.values[4], self.values[5])
        
        return Matrix()  # Identity fallback


@dataclass
class BoundingBox:
    """Axis-aligned bounding box."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    @property
    def width(self) -> float:
        return self.max_x - self.min_x
    
    @property
    def height(self) -> float:
        return self.max_y - self.min_y
    
    @property
    def center(self) -> Tuple[float, float]:
        return ((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)
    
    def transform(self, matrix: 'Matrix') -> 'BoundingBox':
        """Transform bounding box by matrix."""
        # Transform all four corners
        corners = [
            (self.min_x, self.min_y),
            (self.max_x, self.min_y),
            (self.max_x, self.max_y),
            (self.min_x, self.max_y)
        ]
        
        transformed = [matrix.transform_point(x, y) for x, y in corners]
        
        xs = [p[0] for p in transformed]
        ys = [p[1] for p in transformed]
        
        return BoundingBox(min(xs), min(ys), max(xs), max(ys))


class Matrix:
    """
    2D transformation matrix [a b c d e f] representing:
    [a c e]   [x]   [a*x + c*y + e]
    [b d f] * [y] = [b*x + d*y + f]
    [0 0 1]   [1]   [1]
    
    Where:
    - a, d: scaling
    - b, c: shearing/rotation
    - e, f: translation
    """
    
    def __init__(self, a: float = 1, b: float = 0, c: float = 0, 
                 d: float = 1, e: float = 0, f: float = 0):
        self.a = a  # x-scale component
        self.b = b  # y-shear component
        self.c = c  # x-shear component
        self.d = d  # y-scale component
        self.e = e  # x-translate
        self.f = f  # y-translate
    
    @classmethod
    def identity(cls) -> 'Matrix':
        """Create identity matrix."""
        return cls()
    
    @classmethod
    def translate(cls, tx: float, ty: float = 0) -> 'Matrix':
        """Create translation matrix."""
        return cls(1, 0, 0, 1, tx, ty)
    
    @classmethod
    def scale(cls, sx: float, sy: Optional[float] = None) -> 'Matrix':
        """Create scale matrix."""
        if sy is None:
            sy = sx
        return cls(sx, 0, 0, sy, 0, 0)
    
    @classmethod
    def rotate(cls, angle_deg: float) -> 'Matrix':
        """Create rotation matrix (angle in degrees)."""
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        return cls(cos_a, sin_a, -sin_a, cos_a, 0, 0)
    
    @classmethod
    def skew_x(cls, angle_deg: float) -> 'Matrix':
        """Create X-axis skew matrix (angle in degrees)."""
        angle_rad = math.radians(angle_deg)
        return cls(1, 0, math.tan(angle_rad), 1, 0, 0)
    
    @classmethod
    def skew_y(cls, angle_deg: float) -> 'Matrix':
        """Create Y-axis skew matrix (angle in degrees)."""
        angle_rad = math.radians(angle_deg)
        return cls(1, math.tan(angle_rad), 0, 1, 0, 0)
    
    def multiply(self, other: 'Matrix') -> 'Matrix':
        """Multiply this matrix with another (this * other)."""
        return Matrix(
            self.a * other.a + self.c * other.b,
            self.b * other.a + self.d * other.b,
            self.a * other.c + self.c * other.d,
            self.b * other.c + self.d * other.d,
            self.a * other.e + self.c * other.f + self.e,
            self.b * other.e + self.d * other.f + self.f
        )
    
    def inverse(self) -> Optional['Matrix']:
        """Calculate matrix inverse."""
        det = self.a * self.d - self.b * self.c
        if abs(det) < 1e-10:
            return None  # Non-invertible
        
        inv_det = 1.0 / det
        return Matrix(
            self.d * inv_det,
            -self.b * inv_det,
            -self.c * inv_det,
            self.a * inv_det,
            (self.c * self.f - self.d * self.e) * inv_det,
            (self.b * self.e - self.a * self.f) * inv_det
        )
    
    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        """Transform a point using this matrix."""
        new_x = self.a * x + self.c * y + self.e
        new_y = self.b * x + self.d * y + self.f
        return (new_x, new_y)
    
    def transform_points(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Transform multiple points."""
        return [self.transform_point(x, y) for x, y in points]
    
    def decompose(self) -> Dict[str, float]:
        """
        Decompose matrix into transform components.
        
        Returns:
            Dictionary with translateX, translateY, scaleX, scaleY, rotation, skewX
        """
        # Translation is straightforward
        translate_x = self.e
        translate_y = self.f
        
        # Calculate scale and rotation
        scale_x = math.sqrt(self.a * self.a + self.b * self.b)
        scale_y = math.sqrt(self.c * self.c + self.d * self.d)
        
        # Check if determinant is negative (indicates reflection)
        det = self.a * self.d - self.b * self.c
        if det < 0:
            scale_x = -scale_x
        
        # Calculate rotation (in degrees)
        rotation = math.degrees(math.atan2(self.b, self.a))
        
        # Calculate skew
        skew_x = math.degrees(math.atan2(self.a * self.c + self.b * self.d, 
                                       scale_x * scale_x))
        
        return {
            'translateX': translate_x,
            'translateY': translate_y,
            'scaleX': scale_x,
            'scaleY': scale_y,
            'rotation': rotation,
            'skewX': skew_x
        }
    
    def get_translation(self) -> Tuple[float, float]:
        """Get translation components."""
        return (self.e, self.f)
    
    def get_scale(self) -> Tuple[float, float]:
        """Get scale components."""
        scale_x = math.sqrt(self.a * self.a + self.b * self.b)
        scale_y = math.sqrt(self.c * self.c + self.d * self.d)
        return (scale_x, scale_y)
    
    def get_rotation(self) -> float:
        """Get rotation angle in degrees."""
        return math.degrees(math.atan2(self.b, self.a))
    
    def is_identity(self, tolerance: float = 1e-6) -> bool:
        """Check if this is an identity matrix."""
        return (abs(self.a - 1) < tolerance and abs(self.b) < tolerance and 
                abs(self.c) < tolerance and abs(self.d - 1) < tolerance and
                abs(self.e) < tolerance and abs(self.f) < tolerance)
    
    def is_translation_only(self, tolerance: float = 1e-6) -> bool:
        """Check if this is a pure translation matrix."""
        return (abs(self.a - 1) < tolerance and abs(self.b) < tolerance and 
                abs(self.c) < tolerance and abs(self.d - 1) < tolerance)
    
    def has_rotation(self, tolerance: float = 1e-6) -> bool:
        """Check if matrix contains rotation."""
        return abs(self.b) > tolerance or abs(self.c) > tolerance
    
    def has_scale(self, tolerance: float = 1e-6) -> bool:
        """Check if matrix contains scaling."""
        # Calculate the determinant of the linear part (excluding translation)
        det = abs(self.a * self.d - self.b * self.c)
        # For pure rotation/reflection, determinant should be ±1
        # For scaling, determinant will be different from 1
        return abs(det - 1) > tolerance
    
    def to_svg_string(self) -> str:
        """Convert to SVG matrix string."""
        return f"matrix({self.a}, {self.b}, {self.c}, {self.d}, {self.e}, {self.f})"
    
    def to_css_string(self) -> str:
        """Convert to CSS matrix string."""
        return f"matrix({self.a}, {self.b}, {self.c}, {self.d}, {self.e}, {self.f})"
    
    def __str__(self) -> str:
        return self.to_svg_string()
    
    def __repr__(self) -> str:
        return f"Matrix(a={self.a}, b={self.b}, c={self.c}, d={self.d}, e={self.e}, f={self.f})"


class TransformParser:
    """Universal SVG transform parser."""
    
    def __init__(self, unit_converter: Optional[UnitConverter] = None):
        """
        Initialize transform parser.
        
        Args:
            unit_converter: Unit converter for dimension parsing
        """
        self.unit_converter = unit_converter or UnitConverter()
        
        # Compile regex patterns for performance
        self.transform_pattern = re.compile(r'(\w+)\s*\(\s*([^)]*)\s*\)')
        self.number_pattern = re.compile(r'[-+]?(?:\d*\.?\d+(?:[eE][-+]?\d+)?)')
    
    def parse(self, transform_str: str, 
              viewport_context: Optional[ViewportContext] = None) -> List[Transform]:
        """
        Parse SVG transform string into list of Transform objects.
        
        Args:
            transform_str: SVG transform attribute value
            viewport_context: Context for unit conversion
            
        Returns:
            List of Transform objects
            
        Examples:
            >>> parser.parse("translate(10, 20) rotate(45)")
            [Transform(TRANSLATE, [10.0, 20.0]), Transform(ROTATE, [45.0])]
        """
        if not transform_str or not isinstance(transform_str, str):
            return []
        
        transforms = []
        
        # Find all transform functions
        matches = self.transform_pattern.findall(transform_str)
        
        for func_name, params_str in matches:
            transform_type = self._get_transform_type(func_name)
            if not transform_type:
                continue
            
            # Parse parameters
            params = self._parse_parameters(params_str, transform_type, viewport_context)
            
            transforms.append(Transform(
                type=transform_type,
                values=params,
                original=f"{func_name}({params_str})"
            ))
        
        return transforms
    
    def _get_transform_type(self, func_name: str) -> Optional[TransformType]:
        """Map function name to TransformType."""
        name_map = {
            'translate': TransformType.TRANSLATE,
            'rotate': TransformType.ROTATE,
            'scale': TransformType.SCALE,
            'skewx': TransformType.SKEW_X,
            'skewy': TransformType.SKEW_Y,
            'matrix': TransformType.MATRIX
        }
        return name_map.get(func_name.lower())
    
    def _parse_parameters(self, params_str: str, transform_type: TransformType,
                         viewport_context: Optional[ViewportContext]) -> List[float]:
        """Parse parameter string into float values."""
        if not params_str.strip():
            return []
        
        # Extract all numeric values
        matches = self.number_pattern.findall(params_str)
        
        values = []
        for match in matches:
            try:
                # Check if it's a unit value (for translate operations)
                if (transform_type == TransformType.TRANSLATE and 
                    any(match.endswith(unit) for unit in ['px', 'pt', 'mm', 'in', 'cm', 'em', 'ex', '%'])):
                    # Convert using unit converter
                    if viewport_context:
                        emu_value = self.unit_converter.to_emu(match, viewport_context)
                        # Convert EMU back to user units (typically pixels at 96 DPI)
                        pixel_value = emu_value / (EMU_PER_INCH / 96)
                        values.append(pixel_value)
                    else:
                        values.append(float(match.rstrip('pxPXptPTmMinIncmCMemExEx%')))
                else:
                    values.append(float(match))
            except ValueError:
                continue
        
        return values
    
    def parse_to_matrix(self, transform_str: str, 
                       viewport_context: Optional[ViewportContext] = None) -> Matrix:
        """
        Parse SVG transform string directly to combined matrix.
        
        Args:
            transform_str: SVG transform attribute value
            viewport_context: Context for unit conversion
            
        Returns:
            Combined transformation matrix
        """
        transforms = self.parse(transform_str, viewport_context)
        
        result_matrix = Matrix.identity()
        for transform in transforms:
            result_matrix = result_matrix.multiply(transform.to_matrix())
        
        return result_matrix
    
    def optimize_transform_chain(self, transforms: List[Transform]) -> List[Transform]:
        """Optimize transform chain by combining compatible operations."""
        if not transforms:
            return []
        
        # Simple optimization: combine consecutive translations
        optimized = []
        i = 0
        
        while i < len(transforms):
            current = transforms[i]
            
            # Look for consecutive translations
            if (current.type == TransformType.TRANSLATE and 
                i + 1 < len(transforms) and 
                transforms[i + 1].type == TransformType.TRANSLATE):
                
                # Combine translations
                tx1 = current.values[0] if len(current.values) > 0 else 0
                ty1 = current.values[1] if len(current.values) > 1 else 0
                
                next_transform = transforms[i + 1]
                tx2 = next_transform.values[0] if len(next_transform.values) > 0 else 0
                ty2 = next_transform.values[1] if len(next_transform.values) > 1 else 0
                
                combined = Transform(
                    type=TransformType.TRANSLATE,
                    values=[tx1 + tx2, ty1 + ty2],
                    original=f"translate({tx1 + tx2}, {ty1 + ty2})"
                )
                optimized.append(combined)
                i += 2  # Skip both transforms
            else:
                optimized.append(current)
                i += 1
        
        return optimized
    
    def to_drawingml_transform(self, matrix: Matrix, context_emu: Dict[str, int] = None) -> str:
        """
        Convert matrix to DrawingML transform XML.
        
        Args:
            matrix: Transformation matrix
            context_emu: Context dimensions in EMU for relative calculations
            
        Returns:
            DrawingML transform XML string
        """
        if matrix.is_identity():
            return ""
        
        # Decompose matrix for DrawingML
        components = matrix.decompose()
        
        transform_parts = []
        
        # Translation (in EMU)
        if abs(components['translateX']) > 1e-6 or abs(components['translateY']) > 1e-6:
            tx_emu = self.unit_converter.to_emu(f"{components['translateX']}px")
            ty_emu = self.unit_converter.to_emu(f"{components['translateY']}px")
            transform_parts.append(f'<a:off x="{tx_emu}" y="{ty_emu}"/>')
        
        # Rotation
        if abs(components['rotation']) > 1e-6:
            # DrawingML uses 1/60000 degree units
            angle_units = int(components['rotation'] * 60000)
            transform_parts.append(f'<a:rot angle="{angle_units}"/>')
        
        # Scaling
        if abs(components['scaleX'] - 1.0) > 1e-6 or abs(components['scaleY'] - 1.0) > 1e-6:
            # DrawingML uses percentage (100000 = 100%)
            sx_pct = int(components['scaleX'] * 100000)
            sy_pct = int(components['scaleY'] * 100000)
            transform_parts.append(f'<a:ext cx="{sx_pct}" cy="{sy_pct}"/>')
        
        if not transform_parts:
            return ""
        
        return f'<a:xfrm>{"".join(transform_parts)}</a:xfrm>'
    
    def debug_transform_info(self, transform_str: str) -> Dict[str, Any]:
        """Get comprehensive transform analysis for debugging."""
        transforms = self.parse(transform_str)
        combined_matrix = self.parse_to_matrix(transform_str)
        
        return {
            'input': transform_str,
            'parsed_transforms': len(transforms),
            'transform_details': [
                {
                    'type': t.type.value,
                    'values': t.values,
                    'original': t.original
                } for t in transforms
            ],
            'combined_matrix': {
                'a': combined_matrix.a, 'b': combined_matrix.b, 'c': combined_matrix.c,
                'd': combined_matrix.d, 'e': combined_matrix.e, 'f': combined_matrix.f
            },
            'decomposed': combined_matrix.decompose(),
            'is_identity': combined_matrix.is_identity(),
            'has_rotation': combined_matrix.has_rotation(),
            'has_scale': combined_matrix.has_scale(),
            'svg_string': combined_matrix.to_svg_string()
        }


# Global parser instance for convenient access
default_parser = TransformParser()

# Convenience functions for direct usage
def parse_transform(transform_str: str, 
                   viewport_context: Optional[ViewportContext] = None) -> Matrix:
    """Parse transform string using default parser."""
    return default_parser.parse_to_matrix(transform_str, viewport_context)

def create_matrix(a: float = 1, b: float = 0, c: float = 0, 
                 d: float = 1, e: float = 0, f: float = 0) -> Matrix:
    """Create transformation matrix."""
    return Matrix(a, b, c, d, e, f)

def translate_matrix(tx: float, ty: float = 0) -> Matrix:
    """Create translation matrix."""
    return Matrix.translate(tx, ty)

def rotate_matrix(angle_deg: float) -> Matrix:
    """Create rotation matrix."""
    return Matrix.rotate(angle_deg)

def scale_matrix(sx: float, sy: Optional[float] = None) -> Matrix:
    """Create scale matrix."""
    return Matrix.scale(sx, sy)