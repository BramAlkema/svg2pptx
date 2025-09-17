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
import importlib.util
from typing import List, Tuple, Optional, Dict, Any
from lxml import etree as ET
from .base import BaseConverter, ConversionContext

# Import unified Matrix class from core transforms module
from src.transforms import Matrix


class TransformConverter(BaseConverter):
    """Converts SVG transform attributes to DrawingML transformations"""
    
    supported_elements = []  # This converter is used for transform attributes, not elements
    
    def can_convert(self, element: ET.Element) -> bool:
        """This converter is used as a utility, not for direct element conversion"""
        return False
    
    def convert(self, element: ET.Element, context: ConversionContext) -> str:
        """This converter doesn't convert elements directly"""
        return ""
    
    def parse_transform(self, transform_str: str) -> Matrix:
        """Parse SVG transform string and return combined transformation matrix"""
        if not transform_str or transform_str is None:
            return Matrix()
        
        # Use the standardized TransformParser to parse the transform string
        standardized_matrix = self.transform_parser.parse_to_matrix(transform_str)
        
        # Convert from standardized Matrix to local Matrix format
        # Both Matrix classes have the same structure (a, b, c, d, e, f)
        return Matrix(
            standardized_matrix.a, standardized_matrix.b, standardized_matrix.c,
            standardized_matrix.d, standardized_matrix.e, standardized_matrix.f
        )
    
    def convert_transform_to_emu(self, transform_str: str, element: ET.Element) -> Matrix:
        """
        Convert SVG transform to EMU units using standardized tools.
        
        This method demonstrates integration with all standardized tools:
        - TransformParser: Parse transform strings
        - UnitConverter: Convert units to EMU
        - ColorParser: Parse color values if needed
        - ViewportResolver: Resolve viewport coordinates
        """
        # Parse the transform using standardized parser
        matrix = self.parse_transform(transform_str)
        
        # Use UnitConverter for any unit conversions in transform values
        # (transforms can contain unit values in translate operations)
        if hasattr(element, 'attrib'):
            # Use ViewportResolver for coordinate system context
            viewport_info = self.viewport_resolver.get_viewport_info()
            
            # Use ColorParser if transform affects color contexts
            # (useful for gradients with transforms)
            if 'fill' in element.attrib:
                self.color_parser.parse_color(element.attrib['fill'])
        
        return matrix
    
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