"""
SVG Transform to DrawingML Converter

Handles SVG transform attributes with support for:
- Translate transformations
- Scale transformations  
- Rotate transformations
- Skew transformations
- Matrix transformations
- Transform combinations and matrix operations
"""

import re
import math
from typing import List, Tuple, Optional, Dict, Any
import xml.etree.ElementTree as ET
from .base import BaseConverter, ConversionContext


class Matrix:
    """2D transformation matrix [a b c d e f] representing:
    [a c e]   [x]
    [b d f] * [y]
    [0 0 1]   [1]
    """
    
    def __init__(self, a: float = 1, b: float = 0, c: float = 0, 
                 d: float = 1, e: float = 0, f: float = 0):
        self.a = a  # x-scale
        self.b = b  # y-shear
        self.c = c  # x-shear  
        self.d = d  # y-scale
        self.e = e  # x-translate
        self.f = f  # y-translate
    
    def multiply(self, other: 'Matrix') -> 'Matrix':
        """Multiply this matrix with another matrix"""
        return Matrix(
            self.a * other.a + self.c * other.b,
            self.b * other.a + self.d * other.b,
            self.a * other.c + self.c * other.d,
            self.b * other.c + self.d * other.d,
            self.a * other.e + self.c * other.f + self.e,
            self.b * other.e + self.d * other.f + self.f
        )
    
    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        """Transform a point using this matrix"""
        new_x = self.a * x + self.c * y + self.e
        new_y = self.b * x + self.d * y + self.f
        return (new_x, new_y)
    
    def get_translation(self) -> Tuple[float, float]:
        """Get translation components"""
        return (self.e, self.f)
    
    def get_scale(self) -> Tuple[float, float]:
        """Get scale components (approximate for non-uniform transforms)"""
        scale_x = math.sqrt(self.a * self.a + self.b * self.b)
        scale_y = math.sqrt(self.c * self.c + self.d * self.d)
        return (scale_x, scale_y)
    
    def get_rotation(self) -> float:
        """Get rotation angle in degrees"""
        return math.degrees(math.atan2(self.b, self.a))
    
    def is_identity(self) -> bool:
        """Check if this is an identity matrix"""
        return (abs(self.a - 1) < 1e-6 and abs(self.b) < 1e-6 and 
                abs(self.c) < 1e-6 and abs(self.d - 1) < 1e-6 and
                abs(self.e) < 1e-6 and abs(self.f) < 1e-6)
    
    def __str__(self) -> str:
        return f"matrix({self.a}, {self.b}, {self.c}, {self.d}, {self.e}, {self.f})"


class TransformConverter(BaseConverter):
    """Converts SVG transform attributes to DrawingML transformations"""
    
    supported_elements = []  # This converter is used for transform attributes, not elements
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """This converter doesn't convert elements directly"""
        return ""
    
    def parse_transform(self, transform_str: str) -> Matrix:
        """Parse SVG transform string and return combined transformation matrix"""
        if not transform_str:
            return Matrix()
        
        # Clean up the transform string
        transform_str = re.sub(r'\s+', ' ', transform_str.strip())
        
        # Find all transform functions
        pattern = r'(\w+)\s*\([^)]+\)'
        transforms = re.findall(pattern, transform_str)
        
        # Parse each transform function
        result_matrix = Matrix()  # Identity matrix
        
        for match in re.finditer(pattern, transform_str):
            func_call = match.group(0)
            func_name = match.group(1)
            
            # Extract parameters
            params_str = func_call[func_call.index('(') + 1:func_call.rindex(')')]
            params = [float(x.strip()) for x in re.split(r'[,\s]+', params_str) if x.strip()]
            
            # Create transformation matrix based on function
            if func_name == 'translate':
                matrix = self._create_translate_matrix(params)
            elif func_name == 'scale':
                matrix = self._create_scale_matrix(params)
            elif func_name == 'rotate':
                matrix = self._create_rotate_matrix(params)
            elif func_name == 'skewX':
                matrix = self._create_skew_x_matrix(params)
            elif func_name == 'skewY':
                matrix = self._create_skew_y_matrix(params)
            elif func_name == 'matrix':
                matrix = self._create_matrix(params)
            else:
                continue  # Skip unknown transforms
            
            # Combine with result matrix
            result_matrix = result_matrix.multiply(matrix)
        
        return result_matrix
    
    def _create_translate_matrix(self, params: List[float]) -> Matrix:
        """Create translation matrix"""
        tx = params[0] if len(params) > 0 else 0
        ty = params[1] if len(params) > 1 else 0
        return Matrix(1, 0, 0, 1, tx, ty)
    
    def _create_scale_matrix(self, params: List[float]) -> Matrix:
        """Create scale matrix"""
        sx = params[0] if len(params) > 0 else 1
        sy = params[1] if len(params) > 1 else sx  # Uniform scale if only one param
        return Matrix(sx, 0, 0, sy, 0, 0)
    
    def _create_rotate_matrix(self, params: List[float]) -> Matrix:
        """Create rotation matrix"""
        angle = params[0] if len(params) > 0 else 0
        cx = params[1] if len(params) > 1 else 0
        cy = params[2] if len(params) > 2 else 0
        
        # Convert degrees to radians
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        # If rotation center is specified, translate to center, rotate, translate back
        if cx != 0 or cy != 0:
            # Translate to origin
            t1 = Matrix(1, 0, 0, 1, -cx, -cy)
            # Rotate
            r = Matrix(cos_a, sin_a, -sin_a, cos_a, 0, 0)
            # Translate back
            t2 = Matrix(1, 0, 0, 1, cx, cy)
            # Combine: T2 * R * T1
            return t2.multiply(r.multiply(t1))
        else:
            return Matrix(cos_a, sin_a, -sin_a, cos_a, 0, 0)
    
    def _create_skew_x_matrix(self, params: List[float]) -> Matrix:
        """Create skewX matrix"""
        angle = params[0] if len(params) > 0 else 0
        skew = math.tan(math.radians(angle))
        return Matrix(1, 0, skew, 1, 0, 0)
    
    def _create_skew_y_matrix(self, params: List[float]) -> Matrix:
        """Create skewY matrix"""
        angle = params[0] if len(params) > 0 else 0
        skew = math.tan(math.radians(angle))
        return Matrix(1, skew, 0, 1, 0, 0)
    
    def _create_matrix(self, params: List[float]) -> Matrix:
        """Create matrix from parameters"""
        if len(params) >= 6:
            return Matrix(params[0], params[1], params[2], params[3], params[4], params[5])
        return Matrix()  # Identity if insufficient parameters
    
    def apply_transform_to_coordinates(self, matrix: Matrix, coordinates: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Apply transformation matrix to a list of coordinates"""
        return [matrix.transform_point(x, y) for x, y in coordinates]
    
    def get_drawingml_transform(self, matrix: Matrix, context: ConversionContext, 
                              base_x: float = 0, base_y: float = 0, 
                              base_width: float = 100, base_height: float = 100) -> str:
        """Convert transformation matrix to DrawingML xfrm element"""
        
        if matrix.is_identity():
            # No transformation needed
            x_emu = context.coord_system.svg_to_emu_x(base_x)
            y_emu = context.coord_system.svg_to_emu_y(base_y)
            width_emu = context.to_emu(f"{base_width}px", 'x')
            height_emu = context.to_emu(f"{base_height}px", 'y')
            
            return f"""<a:xfrm>
    <a:off x="{x_emu}" y="{y_emu}"/>
    <a:ext cx="{width_emu}" cy="{height_emu}"/>
</a:xfrm>"""
        
        # Extract transformation components
        translation = matrix.get_translation()
        scale = matrix.get_scale()
        rotation = matrix.get_rotation()
        
        # Apply base position and transformation
        final_x = base_x + translation[0]
        final_y = base_y + translation[1]
        final_width = base_width * scale[0]
        final_height = base_height * scale[1]
        
        # Convert to EMU
        x_emu = context.coord_system.svg_to_emu_x(final_x)
        y_emu = context.coord_system.svg_to_emu_y(final_y)
        width_emu = context.to_emu(f"{final_width}px", 'x')
        height_emu = context.to_emu(f"{final_height}px", 'y')
        
        # Convert rotation to DrawingML angle (0-21600000, where 21600000 = 360°)
        rotation_emu = int(rotation * 60000) % 21600000
        
        # For complex transforms that can't be represented with simple xfrm,
        # we might need to use custom geometry or approximate
        if abs(matrix.b) > 1e-6 or abs(matrix.c) > 1e-6:  # Has shear/skew
            # Complex transformation - use simpler approximation
            return f"""<a:xfrm rot="{rotation_emu}">
    <a:off x="{x_emu}" y="{y_emu}"/>
    <a:ext cx="{width_emu}" cy="{height_emu}"/>
</a:xfrm>"""
        else:
            # Simple transformation (translate, scale, rotate)
            return f"""<a:xfrm rot="{rotation_emu}">
    <a:off x="{x_emu}" y="{y_emu}"/>
    <a:ext cx="{width_emu}" cy="{height_emu}"/>
</a:xfrm>"""
    
    def get_element_transform(self, element: ET.Element) -> Matrix:
        """Get the transformation matrix for an SVG element"""
        transform_attr = element.get('transform', '')
        return self.parse_transform(transform_attr)
    
    def get_accumulated_transform(self, element: ET.Element) -> Matrix:
        """Get the accumulated transformation matrix from element and all its parents"""
        result = Matrix()  # Identity
        
        # Walk up the element tree to accumulate transforms
        current = element
        transforms = []
        
        while current is not None:
            transform_attr = current.get('transform', '')
            if transform_attr:
                transforms.append(self.parse_transform(transform_attr))
            current = current.getparent() if hasattr(current, 'getparent') else None
        
        # Apply transforms in reverse order (parent to child)
        for transform in reversed(transforms):
            result = result.multiply(transform)
        
        return result
    
    def transform_bounding_box(self, matrix: Matrix, x: float, y: float, 
                             width: float, height: float) -> Tuple[float, float, float, float]:
        """Transform a bounding box and return new bounding box coordinates"""
        # Transform all four corners
        corners = [
            matrix.transform_point(x, y),
            matrix.transform_point(x + width, y),
            matrix.transform_point(x, y + height),
            matrix.transform_point(x + width, y + height)
        ]
        
        # Find bounding box of transformed corners
        min_x = min(corner[0] for corner in corners)
        max_x = max(corner[0] for corner in corners)
        min_y = min(corner[1] for corner in corners)
        max_y = max(corner[1] for corner in corners)
        
        return (min_x, min_y, max_x - min_x, max_y - min_y)
    
    def decompose_transform(self, matrix: Matrix) -> Dict[str, Any]:
        """Decompose transformation matrix into translation, scale, rotation, and skew"""
        # This is a simplified decomposition
        # For more accurate decomposition, see: https://freddie.witherden.org/tools/svd/
        
        translation = matrix.get_translation()
        
        # Calculate scale
        scale_x = math.sqrt(matrix.a * matrix.a + matrix.b * matrix.b)
        scale_y = math.sqrt(matrix.c * matrix.c + matrix.d * matrix.d)
        
        # Calculate rotation (from x-axis transformation)
        rotation = math.degrees(math.atan2(matrix.b, matrix.a))
        
        # Calculate skew (simplified)
        skew_x = math.degrees(math.atan2(matrix.c, matrix.d)) - 90
        skew_y = 0  # Simplified - full decomposition is more complex
        
        return {
            'translate': translation,
            'scale': (scale_x, scale_y),
            'rotate': rotation,
            'skew': (skew_x, skew_y)
        }