#!/usr/bin/env python3
"""
Unit tests for transforms module functionality.

Tests the Universal Transform Matrix Engine including SVG transform parsing,
matrix operations, coordinate transformations, and DrawingML conversion.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
import math

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from src.transforms import (
    TransformParser, Transform, TransformType, Matrix, BoundingBox,
    parse_transform, create_matrix, translate_matrix, rotate_matrix, scale_matrix
)
from src.units import ViewportContext


class TestTransformType:
    """Test TransformType enum."""
    
    def test_transform_type_values(self):
        """Test transform type enum values."""
        assert TransformType.TRANSLATE.value == "translate"
        assert TransformType.ROTATE.value == "rotate"
        assert TransformType.SCALE.value == "scale"
        assert TransformType.SKEW_X.value == "skewX"
        assert TransformType.SKEW_Y.value == "skewY"
        assert TransformType.MATRIX.value == "matrix"


class TestMatrix:
    """Test Matrix class functionality."""
    
    def test_matrix_creation_default(self):
        """Test default matrix creation (identity)."""
        matrix = Matrix()
        
        assert matrix.a == 1
        assert matrix.b == 0
        assert matrix.c == 0
        assert matrix.d == 1
        assert matrix.e == 0
        assert matrix.f == 0
    
    def test_matrix_creation_custom(self):
        """Test custom matrix creation."""
        matrix = Matrix(2, 1, 0.5, 3, 10, 20)
        
        assert matrix.a == 2
        assert matrix.b == 1
        assert matrix.c == 0.5
        assert matrix.d == 3
        assert matrix.e == 10
        assert matrix.f == 20
    
    def test_identity_matrix(self):
        """Test identity matrix creation."""
        matrix = Matrix.identity()
        
        assert matrix.a == 1
        assert matrix.b == 0
        assert matrix.c == 0
        assert matrix.d == 1
        assert matrix.e == 0
        assert matrix.f == 0
        assert matrix.is_identity() is True
    
    def test_translate_matrix(self):
        """Test translation matrix creation."""
        matrix = Matrix.translate(10, 20)
        
        assert matrix.a == 1
        assert matrix.b == 0
        assert matrix.c == 0
        assert matrix.d == 1
        assert matrix.e == 10
        assert matrix.f == 20
        
        # Single parameter (x-only)
        matrix = Matrix.translate(15)
        assert matrix.e == 15
        assert matrix.f == 0
    
    def test_scale_matrix(self):
        """Test scaling matrix creation."""
        matrix = Matrix.scale(2, 3)
        
        assert matrix.a == 2
        assert matrix.b == 0
        assert matrix.c == 0
        assert matrix.d == 3
        assert matrix.e == 0
        assert matrix.f == 0
        
        # Uniform scaling (single parameter)
        matrix = Matrix.scale(2)
        assert matrix.a == 2
        assert matrix.d == 2
    
    def test_rotate_matrix(self):
        """Test rotation matrix creation."""
        # 90 degree rotation
        matrix = Matrix.rotate(90)
        
        assert abs(matrix.a - 0) < 1e-10  # cos(90°) = 0
        assert abs(matrix.b - 1) < 1e-10  # sin(90°) = 1
        assert abs(matrix.c - (-1)) < 1e-10  # -sin(90°) = -1
        assert abs(matrix.d - 0) < 1e-10  # cos(90°) = 0
        
        # 45 degree rotation
        matrix = Matrix.rotate(45)
        sqrt2_half = math.sqrt(2) / 2
        assert abs(matrix.a - sqrt2_half) < 1e-10
        assert abs(matrix.b - sqrt2_half) < 1e-10
        assert abs(matrix.c - (-sqrt2_half)) < 1e-10
        assert abs(matrix.d - sqrt2_half) < 1e-10
    
    def test_skew_x_matrix(self):
        """Test X-axis skew matrix creation."""
        matrix = Matrix.skew_x(45)  # 45 degrees
        
        assert matrix.a == 1
        assert matrix.b == 0
        assert abs(matrix.c - 1) < 1e-10  # tan(45°) = 1
        assert matrix.d == 1
        assert matrix.e == 0
        assert matrix.f == 0
    
    def test_skew_y_matrix(self):
        """Test Y-axis skew matrix creation."""
        matrix = Matrix.skew_y(45)  # 45 degrees
        
        assert matrix.a == 1
        assert abs(matrix.b - 1) < 1e-10  # tan(45°) = 1
        assert matrix.c == 0
        assert matrix.d == 1
        assert matrix.e == 0
        assert matrix.f == 0
    
    def test_matrix_multiplication(self):
        """Test matrix multiplication."""
        m1 = Matrix.translate(10, 20)
        m2 = Matrix.scale(2, 3)
        
        # Multiply: scale then translate (matrix multiplication applies rightmost first)
        result = m1.multiply(m2)
        
        assert result.a == 2  # Scale X
        assert result.d == 3  # Scale Y
        assert result.e == 10  # Translation X (applied after scale)
        assert result.f == 20  # Translation Y (applied after scale)
        
        # Matrix multiplication is not commutative
        result2 = m2.multiply(m1)
        assert result.e != result2.e or result.f != result2.f
    
    def test_matrix_inverse(self):
        """Test matrix inverse calculation."""
        # Simple translation matrix
        matrix = Matrix.translate(10, 20)
        inverse = matrix.inverse()
        
        assert inverse is not None
        assert inverse.e == -10
        assert inverse.f == -20
        
        # Verify inverse property: M * M^-1 = I
        identity = matrix.multiply(inverse)
        assert identity.is_identity()
        
        # Non-invertible matrix (determinant = 0)
        non_invertible = Matrix(0, 0, 0, 0, 10, 20)
        assert non_invertible.inverse() is None
    
    def test_transform_point(self):
        """Test point transformation."""
        # Translation
        matrix = Matrix.translate(10, 20)
        x, y = matrix.transform_point(5, 15)
        assert x == 15  # 5 + 10
        assert y == 35  # 15 + 20
        
        # Scaling
        matrix = Matrix.scale(2, 3)
        x, y = matrix.transform_point(10, 20)
        assert x == 20  # 10 * 2
        assert y == 60  # 20 * 3
        
        # Rotation (90 degrees)
        matrix = Matrix.rotate(90)
        x, y = matrix.transform_point(10, 0)
        assert abs(x - 0) < 1e-10
        assert abs(y - 10) < 1e-10
    
    def test_transform_multiple_points(self):
        """Test transforming multiple points."""
        matrix = Matrix.translate(5, 10)
        points = [(0, 0), (10, 20), (5, 5)]
        
        transformed = matrix.transform_points(points)
        
        assert transformed[0] == (5, 10)
        assert transformed[1] == (15, 30)
        assert transformed[2] == (10, 15)
    
    def test_matrix_decomposition(self):
        """Test matrix decomposition into components."""
        # Translation only
        matrix = Matrix.translate(10, 20)
        components = matrix.decompose()
        
        assert components['translateX'] == 10
        assert components['translateY'] == 20
        assert abs(components['scaleX'] - 1) < 1e-6
        assert abs(components['scaleY'] - 1) < 1e-6
        assert abs(components['rotation']) < 1e-6
        
        # Scale only
        matrix = Matrix.scale(2, 3)
        components = matrix.decompose()
        
        assert abs(components['translateX']) < 1e-6
        assert abs(components['translateY']) < 1e-6
        assert abs(components['scaleX'] - 2) < 1e-6
        assert abs(components['scaleY'] - 3) < 1e-6
        
        # Rotation only (45 degrees)
        matrix = Matrix.rotate(45)
        components = matrix.decompose()
        
        assert abs(components['rotation'] - 45) < 1e-6
    
    def test_matrix_properties(self):
        """Test matrix property methods."""
        # Identity
        identity = Matrix.identity()
        assert identity.is_identity() is True
        assert identity.is_translation_only() is True
        assert identity.has_rotation() is False
        assert identity.has_scale() is False
        
        # Translation
        translate = Matrix.translate(10, 20)
        assert translate.is_identity() is False
        assert translate.is_translation_only() is True
        assert translate.has_rotation() is False
        assert translate.has_scale() is False
        
        # Rotation
        rotate = Matrix.rotate(45)
        assert rotate.is_identity() is False
        assert rotate.is_translation_only() is False
        assert rotate.has_rotation() is True
        assert rotate.has_scale() is False
        
        # Scale
        scale = Matrix.scale(2, 3)
        assert scale.is_identity() is False
        assert scale.is_translation_only() is False
        assert scale.has_rotation() is False
        assert scale.has_scale() is True
    
    def test_matrix_get_components(self):
        """Test matrix component getters."""
        matrix = Matrix.translate(10, 20)
        tx, ty = matrix.get_translation()
        assert tx == 10
        assert ty == 20
        
        matrix = Matrix.scale(2, 3)
        sx, sy = matrix.get_scale()
        assert abs(sx - 2) < 1e-6
        assert abs(sy - 3) < 1e-6
        
        matrix = Matrix.rotate(45)
        rotation = matrix.get_rotation()
        assert abs(rotation - 45) < 1e-6
    
    def test_matrix_string_representations(self):
        """Test matrix string conversions."""
        matrix = Matrix(1, 2, 3, 4, 5, 6)
        
        svg_str = matrix.to_svg_string()
        assert svg_str == "matrix(1, 2, 3, 4, 5, 6)"
        
        css_str = matrix.to_css_string()
        assert css_str == "matrix(1, 2, 3, 4, 5, 6)"
        
        str_repr = str(matrix)
        assert "matrix(1, 2, 3, 4, 5, 6)" in str_repr
        
        repr_str = repr(matrix)
        assert "Matrix(a=1, b=2, c=3, d=4, e=5, f=6)" in repr_str


class TestBoundingBox:
    """Test BoundingBox class functionality."""
    
    def test_bounding_box_creation(self):
        """Test bounding box creation."""
        bbox = BoundingBox(10, 20, 50, 80)
        
        assert bbox.min_x == 10
        assert bbox.min_y == 20
        assert bbox.max_x == 50
        assert bbox.max_y == 80
    
    def test_bounding_box_properties(self):
        """Test bounding box properties."""
        bbox = BoundingBox(10, 20, 50, 80)
        
        assert bbox.width == 40  # 50 - 10
        assert bbox.height == 60  # 80 - 20
        assert bbox.center == (30, 50)  # ((10+50)/2, (20+80)/2)
    
    def test_bounding_box_transform(self):
        """Test bounding box transformation."""
        bbox = BoundingBox(0, 0, 10, 10)
        
        # Translation
        translate_matrix = Matrix.translate(5, 10)
        transformed = bbox.transform(translate_matrix)
        
        assert transformed.min_x == 5
        assert transformed.min_y == 10
        assert transformed.max_x == 15
        assert transformed.max_y == 20
        
        # Scaling
        scale_matrix = Matrix.scale(2, 3)
        transformed = bbox.transform(scale_matrix)
        
        assert transformed.min_x == 0
        assert transformed.min_y == 0
        assert transformed.max_x == 20
        assert transformed.max_y == 30
        
        # Rotation (90 degrees) - should affect all corners
        rotate_matrix = Matrix.rotate(90)
        transformed = bbox.transform(rotate_matrix)
        
        # After 90° rotation, the bounding box changes
        assert transformed.width > 0
        assert transformed.height > 0


class TestTransform:
    """Test Transform class functionality."""
    
    def test_transform_creation(self):
        """Test Transform creation."""
        transform = Transform(
            type=TransformType.TRANSLATE,
            values=[10, 20],
            original="translate(10, 20)"
        )
        
        assert transform.type == TransformType.TRANSLATE
        assert transform.values == [10, 20]
        assert transform.original == "translate(10, 20)"
    
    def test_transform_to_matrix_translate(self):
        """Test converting translate transform to matrix."""
        transform = Transform(TransformType.TRANSLATE, [10, 20], "translate(10, 20)")
        matrix = transform.to_matrix()
        
        assert matrix.e == 10
        assert matrix.f == 20
        
        # Single value (y defaults to 0)
        transform = Transform(TransformType.TRANSLATE, [15], "translate(15)")
        matrix = transform.to_matrix()
        
        assert matrix.e == 15
        assert matrix.f == 0
    
    def test_transform_to_matrix_rotate(self):
        """Test converting rotate transform to matrix."""
        # Simple rotation
        transform = Transform(TransformType.ROTATE, [45], "rotate(45)")
        matrix = transform.to_matrix()
        
        assert matrix.has_rotation() is True
        assert abs(matrix.get_rotation() - 45) < 1e-6
        
        # Rotation around center point
        transform = Transform(TransformType.ROTATE, [90, 10, 20], "rotate(90, 10, 20)")
        matrix = transform.to_matrix()
        
        # This should be equivalent to translate(10,20) * rotate(90) * translate(-10,-20)
        assert matrix.has_rotation() is True
    
    def test_transform_to_matrix_scale(self):
        """Test converting scale transform to matrix."""
        # Non-uniform scaling
        transform = Transform(TransformType.SCALE, [2, 3], "scale(2, 3)")
        matrix = transform.to_matrix()
        
        sx, sy = matrix.get_scale()
        assert abs(sx - 2) < 1e-6
        assert abs(sy - 3) < 1e-6
        
        # Uniform scaling (single value)
        transform = Transform(TransformType.SCALE, [2], "scale(2)")
        matrix = transform.to_matrix()
        
        sx, sy = matrix.get_scale()
        assert abs(sx - 2) < 1e-6
        assert abs(sy - 2) < 1e-6
    
    def test_transform_to_matrix_skew(self):
        """Test converting skew transforms to matrix."""
        # Skew X
        transform = Transform(TransformType.SKEW_X, [45], "skewX(45)")
        matrix = transform.to_matrix()
        
        assert abs(matrix.c - 1) < 1e-6  # tan(45°) = 1
        
        # Skew Y
        transform = Transform(TransformType.SKEW_Y, [30], "skewY(30)")
        matrix = transform.to_matrix()
        
        tan_30 = math.tan(math.radians(30))
        assert abs(matrix.b - tan_30) < 1e-6
    
    def test_transform_to_matrix_direct_matrix(self):
        """Test converting direct matrix transform."""
        transform = Transform(
            TransformType.MATRIX, 
            [1, 2, 3, 4, 5, 6], 
            "matrix(1, 2, 3, 4, 5, 6)"
        )
        matrix = transform.to_matrix()
        
        assert matrix.a == 1
        assert matrix.b == 2
        assert matrix.c == 3
        assert matrix.d == 4
        assert matrix.e == 5
        assert matrix.f == 6
    
    def test_transform_to_matrix_empty_values(self):
        """Test converting transform with empty/insufficient values."""
        # Empty values should return identity
        transform = Transform(TransformType.TRANSLATE, [], "translate()")
        matrix = transform.to_matrix()
        
        assert matrix.is_identity() is True
        
        # Insufficient matrix values should return identity
        transform = Transform(TransformType.MATRIX, [1, 2, 3], "matrix(1, 2, 3)")
        matrix = transform.to_matrix()
        
        assert matrix.is_identity() is True


class TestTransformParser:
    """Test TransformParser functionality."""
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = TransformParser()
        
        assert parser.unit_converter is not None
        assert parser.transform_pattern is not None
        assert parser.number_pattern is not None
    
    def test_parse_single_transform(self):
        """Test parsing single transforms."""
        parser = TransformParser()
        
        # Translate
        transforms = parser.parse("translate(10, 20)")
        assert len(transforms) == 1
        assert transforms[0].type == TransformType.TRANSLATE
        assert transforms[0].values == [10.0, 20.0]
        
        # Rotate
        transforms = parser.parse("rotate(45)")
        assert len(transforms) == 1
        assert transforms[0].type == TransformType.ROTATE
        assert transforms[0].values == [45.0]
        
        # Scale
        transforms = parser.parse("scale(2, 3)")
        assert len(transforms) == 1
        assert transforms[0].type == TransformType.SCALE
        assert transforms[0].values == [2.0, 3.0]
    
    def test_parse_multiple_transforms(self):
        """Test parsing multiple transforms."""
        parser = TransformParser()
        
        transforms = parser.parse("translate(10, 20) rotate(45) scale(2)")
        
        assert len(transforms) == 3
        assert transforms[0].type == TransformType.TRANSLATE
        assert transforms[1].type == TransformType.ROTATE
        assert transforms[2].type == TransformType.SCALE
    
    def test_parse_complex_transform_chain(self):
        """Test parsing complex transform chain."""
        parser = TransformParser()
        
        transform_str = "translate(100, 50) rotate(45, 25, 25) scale(1.5) skewX(15)"
        transforms = parser.parse(transform_str)
        
        assert len(transforms) == 4
        assert transforms[0].type == TransformType.TRANSLATE
        assert transforms[0].values == [100.0, 50.0]
        
        assert transforms[1].type == TransformType.ROTATE
        assert transforms[1].values == [45.0, 25.0, 25.0]
        
        assert transforms[2].type == TransformType.SCALE
        assert transforms[2].values == [1.5]
        
        assert transforms[3].type == TransformType.SKEW_X
        assert transforms[3].values == [15.0]
    
    def test_parse_matrix_transform(self):
        """Test parsing matrix transform."""
        parser = TransformParser()
        
        transforms = parser.parse("matrix(1.5, 0, 0, 2, 100, 200)")
        
        assert len(transforms) == 1
        assert transforms[0].type == TransformType.MATRIX
        assert transforms[0].values == [1.5, 0.0, 0.0, 2.0, 100.0, 200.0]
    
    def test_parse_with_units(self):
        """Test parsing transforms with unit values."""
        parser = TransformParser()
        viewport_context = ViewportContext(dpi=96.0)
        
        # This should handle unit conversion internally
        transforms = parser.parse("translate(10px, 20px)", viewport_context)
        
        assert len(transforms) == 1
        assert transforms[0].type == TransformType.TRANSLATE
        # Values should be converted from units
        assert len(transforms[0].values) == 2
    
    def test_parse_whitespace_and_formatting(self):
        """Test parsing with various whitespace and formatting."""
        parser = TransformParser()
        
        # Various whitespace patterns
        test_strings = [
            "translate(10,20)",
            "translate( 10 , 20 )",
            "translate(10 20)",  # Space-separated
            " translate(10, 20) ",
            "translate(10,20)rotate(45)",
            "translate(10, 20) rotate(45)",
        ]
        
        for transform_str in test_strings:
            transforms = parser.parse(transform_str)
            assert len(transforms) >= 1
            assert transforms[0].type == TransformType.TRANSLATE
    
    def test_parse_empty_and_invalid(self):
        """Test parsing empty and invalid transforms."""
        parser = TransformParser()
        
        # Empty string
        transforms = parser.parse("")
        assert len(transforms) == 0
        
        # None
        transforms = parser.parse(None)
        assert len(transforms) == 0
        
        # Invalid function
        transforms = parser.parse("invalid(10, 20)")
        assert len(transforms) == 0
        
        # Malformed parameters
        transforms = parser.parse("translate(invalid, params)")
        assert len(transforms) == 1  # Should still create transform, but with empty values
    
    def test_parse_to_matrix_single(self):
        """Test parsing directly to combined matrix."""
        parser = TransformParser()
        
        matrix = parser.parse_to_matrix("translate(10, 20)")
        
        assert matrix.e == 10
        assert matrix.f == 20
        assert matrix.is_translation_only() is True
    
    def test_parse_to_matrix_combined(self):
        """Test parsing multiple transforms to combined matrix."""
        parser = TransformParser()
        
        # Translate then scale (SVG order)
        matrix = parser.parse_to_matrix("translate(10, 20) scale(2)")
        
        # The implementation applies transforms right-to-left (like matrix multiplication)
        # So "translate(10, 20) scale(2)" means scale first, then translate
        # Final transformation: (x,y) -> (2x)+10, (2y)+20 = (2x+10, 2y+20)
        # Matrix form: [2 0 10]  [0 2 20]
        assert matrix.a == 2   # Scale X
        assert matrix.d == 2   # Scale Y
        assert matrix.e == 10  # Translation X (applied after scale)
        assert matrix.f == 20  # Translation Y (applied after scale)
    
    def test_optimize_transform_chain(self):
        """Test transform chain optimization."""
        parser = TransformParser()
        
        # Create transforms with consecutive translations
        transforms = [
            Transform(TransformType.TRANSLATE, [10, 20], "translate(10, 20)"),
            Transform(TransformType.TRANSLATE, [5, 10], "translate(5, 10)")
        ]
        
        optimized = parser.optimize_transform_chain(transforms)
        
        # Should combine into single translation
        assert len(optimized) == 1
        assert optimized[0].type == TransformType.TRANSLATE
        assert optimized[0].values == [15, 30]  # Combined translations
    
    def test_to_drawingml_transform(self):
        """Test converting matrix to DrawingML transform."""
        parser = TransformParser()
        
        # Identity matrix should return empty string
        identity = Matrix.identity()
        xml = parser.to_drawingml_transform(identity)
        assert xml == ""
        
        # Translation
        translate_matrix = Matrix.translate(10, 20)
        xml = parser.to_drawingml_transform(translate_matrix)
        assert '<a:xfrm>' in xml
        assert '<a:off' in xml
        assert '</a:xfrm>' in xml
        
        # Rotation
        rotate_matrix = Matrix.rotate(45)
        xml = parser.to_drawingml_transform(rotate_matrix)
        assert '<a:rot' in xml
        assert 'angle="2699999"' in xml or 'angle="2700000"' in xml  # 45 * 60000 with precision tolerance
        
        # Scaling
        scale_matrix = Matrix.scale(1.5, 2.0)
        xml = parser.to_drawingml_transform(scale_matrix)
        assert '<a:ext' in xml
    
    def test_debug_transform_info(self):
        """Test debug transform information."""
        parser = TransformParser()
        
        debug = parser.debug_transform_info("translate(10, 20) rotate(45)")
        
        assert debug['input'] == "translate(10, 20) rotate(45)"
        assert debug['parsed_transforms'] == 2
        assert len(debug['transform_details']) == 2
        assert 'combined_matrix' in debug
        assert 'decomposed' in debug
        assert debug['is_identity'] is False
        assert 'svg_string' in debug


class TestConvenienceFunctions:
    """Test global convenience functions."""
    
    def test_parse_transform_function(self):
        """Test global parse_transform function."""
        matrix = parse_transform("translate(10, 20)")
        
        assert matrix.e == 10
        assert matrix.f == 20
    
    def test_create_matrix_function(self):
        """Test global create_matrix function."""
        matrix = create_matrix(1, 2, 3, 4, 5, 6)
        
        assert matrix.a == 1
        assert matrix.b == 2
        assert matrix.c == 3
        assert matrix.d == 4
        assert matrix.e == 5
        assert matrix.f == 6
    
    def test_specific_matrix_functions(self):
        """Test specific matrix creation functions."""
        # Translation
        matrix = translate_matrix(10, 20)
        assert matrix.e == 10
        assert matrix.f == 20
        
        # Rotation
        matrix = rotate_matrix(90)
        assert abs(matrix.get_rotation() - 90) < 1e-6
        
        # Scale
        matrix = scale_matrix(2, 3)
        sx, sy = matrix.get_scale()
        assert abs(sx - 2) < 1e-6
        assert abs(sy - 3) < 1e-6
        
        # Uniform scale
        matrix = scale_matrix(2)
        sx, sy = matrix.get_scale()
        assert abs(sx - 2) < 1e-6
        assert abs(sy - 2) < 1e-6


class TestRealWorldScenarios:
    """Test real-world transform scenarios."""
    
    def test_svg_element_positioning(self):
        """Test typical SVG element positioning scenario."""
        parser = TransformParser()
        
        # Element translated and scaled
        matrix = parser.parse_to_matrix("translate(100, 50) scale(1.5)")
        
        # Transform a point
        x, y = matrix.transform_point(10, 20)
        
        assert x == 115  # (10 * 1.5) + 100
        assert y == 80   # (20 * 1.5) + 50
    
    def test_rotation_around_center(self):
        """Test rotation around element center."""
        parser = TransformParser()
        
        # Rotate 90 degrees around point (50, 50)
        matrix = parser.parse_to_matrix("rotate(90, 50, 50)")
        
        # Point at center should not move
        x, y = matrix.transform_point(50, 50)
        assert abs(x - 50) < 1e-6
        assert abs(y - 50) < 1e-6
        
        # Point to the right of center should move above center (90° counter-clockwise)
        x, y = matrix.transform_point(60, 50)
        assert abs(x - 50) < 1e-6
        assert abs(y - 60) < 1e-6
    
    def test_complex_animation_transform(self):
        """Test complex animation-style transform."""
        parser = TransformParser()
        
        # Complex transform chain typical in animations
        transform_str = "translate(200, 100) rotate(30, 50, 50) scale(0.8) skewX(5)"
        matrix = parser.parse_to_matrix(transform_str)
        
        # Should handle all transforms in sequence
        assert not matrix.is_identity()
        
        # Decomposition should work
        components = matrix.decompose()
        assert 'translateX' in components
        assert 'translateY' in components
        assert 'rotation' in components
        assert 'scaleX' in components
        assert 'scaleY' in components
    
    def test_nested_group_transforms(self):
        """Test handling nested group transforms."""
        parser = TransformParser()
        
        # Parent group transform
        parent_matrix = parser.parse_to_matrix("translate(100, 50) scale(2)")
        
        # Child element transform
        child_matrix = parser.parse_to_matrix("rotate(45) translate(10, 10)")
        
        # Combined transform (parent applied to child)
        combined = parent_matrix.multiply(child_matrix)
        
        # Should have complex behavior from both transforms
        assert not combined.is_identity()
        assert combined.has_rotation()
        assert combined.has_scale()


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""
    
    def test_very_small_values(self):
        """Test handling of very small transform values."""
        parser = TransformParser()
        
        matrix = parser.parse_to_matrix("translate(0.001, 0.001)")
        
        assert abs(matrix.e - 0.001) < 1e-10
        assert abs(matrix.f - 0.001) < 1e-10
    
    def test_very_large_values(self):
        """Test handling of very large transform values."""
        parser = TransformParser()
        
        matrix = parser.parse_to_matrix("translate(1000000, 2000000)")
        
        assert matrix.e == 1000000
        assert matrix.f == 2000000
    
    def test_negative_values(self):
        """Test handling of negative values."""
        parser = TransformParser()
        
        matrix = parser.parse_to_matrix("translate(-10, -20) scale(-1, 1)")
        
        assert matrix.e < 0  # Negative translation
        # Scale should be applied properly
    
    def test_scientific_notation(self):
        """Test handling of scientific notation in transforms."""
        parser = TransformParser()
        
        transforms = parser.parse("translate(1e2, 2.5E1)")
        
        assert len(transforms) == 1
        assert transforms[0].values[0] == 100.0  # 1e2
        assert transforms[0].values[1] == 25.0   # 2.5E1
    
    def test_malformed_but_recoverable(self):
        """Test handling of malformed but partially recoverable input."""
        parser = TransformParser()
        
        # Missing closing parenthesis - should not crash
        transforms = parser.parse("translate(10, 20")
        # Parser should handle gracefully
        
        # Extra parameters - should use what it can
        transforms = parser.parse("rotate(45, 50, 50, extra, params)")
        assert len(transforms) == 1
        assert transforms[0].type == TransformType.ROTATE
        # Should use first 3 valid parameters
    
    def test_mixed_valid_invalid_transforms(self):
        """Test mixed valid and invalid transforms."""
        parser = TransformParser()
        
        transforms = parser.parse("translate(10, 20) invalid(1, 2) scale(2)")
        
        # Should parse the valid ones and skip invalid
        assert len(transforms) == 2
        assert transforms[0].type == TransformType.TRANSLATE
        assert transforms[1].type == TransformType.SCALE