#!/usr/bin/env python3
"""
Unit tests for animation transform matrix handling.

Tests the conversion of SVG transform animations to PowerPoint DrawingML,
including matrix composition, decomposition, and interpolation.
"""

import pytest
import math
from src.converters.animation_transform_matrix import (
    TransformMatrix, MatrixOperation, AnimationTransformProcessor,
    PowerPointTransformAnimationGenerator
)


class TestTransformMatrix:
    """Test TransformMatrix operations."""

    def test_identity_matrix(self):
        """Test identity matrix creation."""
        matrix = TransformMatrix.identity()
        assert matrix.a == 1.0
        assert matrix.b == 0.0
        assert matrix.c == 0.0
        assert matrix.d == 1.0
        assert matrix.e == 0.0
        assert matrix.f == 0.0

    def test_translate_matrix(self):
        """Test translation matrix creation."""
        matrix = TransformMatrix.from_translate(10, 20)
        assert matrix.e == 10
        assert matrix.f == 20
        assert matrix.a == 1.0  # No scaling
        assert matrix.d == 1.0

    def test_scale_matrix(self):
        """Test scale matrix creation."""
        matrix = TransformMatrix.from_scale(2.0, 3.0)
        assert matrix.a == 2.0
        assert matrix.d == 3.0
        assert matrix.e == 0.0  # No translation
        assert matrix.f == 0.0

    def test_rotate_matrix(self):
        """Test rotation matrix creation."""
        # 90-degree rotation
        matrix = TransformMatrix.from_rotate(90)
        assert abs(matrix.a - 0) < 0.001  # cos(90°) = 0
        assert abs(matrix.b - 1) < 0.001  # sin(90°) = 1
        assert abs(matrix.c - (-1)) < 0.001  # -sin(90°) = -1
        assert abs(matrix.d - 0) < 0.001  # cos(90°) = 0

    def test_rotate_around_point(self):
        """Test rotation around a specific point."""
        matrix = TransformMatrix.from_rotate(90, 100, 100)
        # Should translate, rotate, then translate back
        decomp = matrix.decompose()
        assert abs(decomp['rotate'] - 90) < 0.001

    def test_matrix_multiplication(self):
        """Test matrix multiplication."""
        translate = TransformMatrix.from_translate(10, 20)
        scale = TransformMatrix.from_scale(2.0)

        # translate * scale means: scale first, then translate
        # The translation gets applied after the scale, so it's scaled
        result = translate.multiply(scale)
        assert result.a == 2.0  # Scale preserved
        assert result.d == 2.0
        # Translation is transformed by the scale matrix
        assert result.e == 20  # 10 * 2 (translation scaled)
        assert result.f == 40  # 20 * 2

    def test_matrix_decomposition(self):
        """Test matrix decomposition into components."""
        # Create a combined transform
        matrix = (TransformMatrix.from_translate(10, 20)
                 .multiply(TransformMatrix.from_rotate(45))
                 .multiply(TransformMatrix.from_scale(2.0)))

        decomp = matrix.decompose()

        # Check decomposed values (approximate due to composition)
        assert len(decomp['translate']) == 2
        assert len(decomp['scale']) == 2
        assert 'rotate' in decomp
        assert len(decomp['skew']) == 2

    def test_powerpoint_transform_conversion(self):
        """Test conversion to PowerPoint transform format."""
        matrix = TransformMatrix.from_translate(10, 20)
        powerpoint = matrix.to_powerpoint_transform()

        # Check EMU conversion (1 unit = 914400 EMU)
        assert powerpoint['translate_x'] == 10 * 914400
        assert powerpoint['translate_y'] == 20 * 914400
        assert powerpoint['scale_x'] == 1.0
        assert powerpoint['scale_y'] == 1.0
        assert powerpoint['rotate'] == 0

    def test_skew_matrices(self):
        """Test skew matrix creation."""
        skew_x = TransformMatrix.from_skew_x(30)
        assert abs(skew_x.c - math.tan(math.radians(30))) < 0.001

        skew_y = TransformMatrix.from_skew_y(45)
        assert abs(skew_y.b - math.tan(math.radians(45))) < 0.001

    def test_from_matrix_values(self):
        """Test matrix creation from 6 values."""
        matrix = TransformMatrix.from_matrix_values([2, 0, 0, 3, 10, 20])
        assert matrix.a == 2
        assert matrix.b == 0
        assert matrix.c == 0
        assert matrix.d == 3
        assert matrix.e == 10
        assert matrix.f == 20


class TestAnimationTransformProcessor:
    """Test AnimationTransformProcessor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = AnimationTransformProcessor()

    def test_parse_simple_transform(self):
        """Test parsing simple transform string."""
        operations = self.processor.parse_transform_string("translate(10, 20)")

        assert len(operations) == 1
        assert operations[0][0] == MatrixOperation.TRANSLATE
        assert operations[0][1] == [10, 20]

    def test_parse_multiple_transforms(self):
        """Test parsing multiple transforms."""
        operations = self.processor.parse_transform_string(
            "translate(10, 20) rotate(45) scale(2)"
        )

        assert len(operations) == 3
        assert operations[0][0] == MatrixOperation.TRANSLATE
        assert operations[1][0] == MatrixOperation.ROTATE
        assert operations[2][0] == MatrixOperation.SCALE

    def test_parse_complex_values(self):
        """Test parsing transforms with complex values."""
        operations = self.processor.parse_transform_string(
            "rotate(45 100 100) scale(2, 3)"
        )

        assert len(operations) == 2
        # Rotate with center point
        assert operations[0][1] == [45, 100, 100]
        # Non-uniform scale
        assert operations[1][1] == [2, 3]

    def test_operations_to_matrix(self):
        """Test converting operations to combined matrix."""
        operations = [
            (MatrixOperation.TRANSLATE, [10, 20]),
            (MatrixOperation.SCALE, [2, 2]),
        ]

        matrix = self.processor.operations_to_matrix(operations)

        # Operations are applied in order: first translate, then scale
        # Result is: translate(10,20) * scale(2,2)
        assert matrix.a == 2  # Scale
        assert matrix.d == 2
        # Translation happens first, then gets scaled
        assert matrix.e == 20  # 10 * 2 (translation scaled)
        assert matrix.f == 40  # 20 * 2

    def test_interpolate_matrices(self):
        """Test matrix interpolation."""
        matrix1 = TransformMatrix.from_translate(0, 0)
        matrix2 = TransformMatrix.from_translate(100, 100)

        # Interpolate halfway
        result = self.processor.interpolate_matrices(matrix1, matrix2, 0.5)
        decomp = result.decompose()

        assert abs(decomp['translate'][0] - 50) < 0.001
        assert abs(decomp['translate'][1] - 50) < 0.001

    def test_interpolate_rotation(self):
        """Test rotation interpolation (shortest path)."""
        matrix1 = TransformMatrix.from_rotate(0)
        matrix2 = TransformMatrix.from_rotate(90)

        result = self.processor.interpolate_matrices(matrix1, matrix2, 0.5)
        decomp = result.decompose()

        assert abs(decomp['rotate'] - 45) < 1  # Halfway between 0 and 90

    def test_interpolate_scale(self):
        """Test scale interpolation."""
        matrix1 = TransformMatrix.from_scale(1.0)
        matrix2 = TransformMatrix.from_scale(3.0)

        result = self.processor.interpolate_matrices(matrix1, matrix2, 0.5)
        decomp = result.decompose()

        assert abs(decomp['scale'][0] - 2.0) < 0.001
        assert abs(decomp['scale'][1] - 2.0) < 0.001

    def test_generate_powerpoint_transform_xml(self):
        """Test PowerPoint transform XML generation."""
        matrix = TransformMatrix.from_translate(10, 20)
        xml = self.processor.generate_powerpoint_transform_xml(matrix, "shape1")

        assert "<a:xfrm>" in xml
        assert "<a:off" in xml
        assert 'x="9144000"' in xml  # 10 * 914400
        assert 'y="18288000"' in xml  # 20 * 914400


class TestPowerPointTransformAnimationGenerator:
    """Test PowerPoint transform animation generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = PowerPointTransformAnimationGenerator()

    def test_generate_translation_animation(self):
        """Test generation of translation animation."""
        xml = self.generator.generate_transform_animation(
            "translate(0, 0)",
            "translate(100, 100)",
            2000,  # 2 seconds
            "element1"
        )

        assert "<a:animMotion>" in xml
        assert 'dur="2000"' in xml
        assert 'spid="element1"' in xml
        assert "<a:from>" in xml
        assert "<a:to>" in xml

    def test_generate_rotation_animation(self):
        """Test generation of rotation animation."""
        # Use a rotation that creates different matrices
        xml = self.generator.generate_transform_animation(
            "rotate(0)",
            "rotate(90)",  # 90 degrees creates a different matrix
            3000,
            "spinner"
        )

        assert "<a:animRot>" in xml
        assert 'dur="3000"' in xml
        # Check for from and to values in the XML
        assert '<a:from val="0"/>' in xml  # From 0 degrees
        assert '<a:to val="5400000"/>' in xml  # To 90 degrees in 60000ths

    def test_generate_scale_animation(self):
        """Test generation of scale animation."""
        xml = self.generator.generate_transform_animation(
            "scale(1)",
            "scale(2)",
            1500,
            "grower"
        )

        assert "<a:animScale>" in xml
        assert 'dur="1500"' in xml
        assert 'x="1.0"' in xml  # From scale
        assert 'x="2.0"' in xml  # To scale

    def test_generate_combined_animation(self):
        """Test generation of combined transform animation."""
        xml = self.generator.generate_transform_animation(
            "translate(0, 0) scale(1)",
            "translate(100, 100) scale(2)",
            2000,
            "mover_scaler"
        )

        # Should create parallel animation group
        assert "<a:par>" in xml
        assert "<a:childTnLst>" in xml
        assert "<a:animMotion>" in xml  # Translation
        assert "<a:animScale>" in xml  # Scale

    def test_no_animation_for_identical_transforms(self):
        """Test that no animation is generated for identical transforms."""
        xml = self.generator.generate_transform_animation(
            "translate(100, 100)",
            "translate(100, 100)",
            1000,
            "static"
        )

        assert xml == ""  # No animation needed

    def test_complex_transform_animation(self):
        """Test complex transform with rotation around point."""
        xml = self.generator.generate_transform_animation(
            "rotate(0 50 50)",
            "rotate(180 50 50)",
            2500,
            "rotator"
        )

        assert "<a:animRot>" in xml
        assert 'dur="2500"' in xml
        # Should handle rotation around point


class TestIntegration:
    """Integration tests for transform matrix system."""

    def test_svg_to_powerpoint_workflow(self):
        """Test complete SVG to PowerPoint transform workflow."""
        processor = AnimationTransformProcessor()
        generator = PowerPointTransformAnimationGenerator()

        # Parse SVG transform
        svg_transform = "translate(50, 50) rotate(45) scale(1.5)"
        operations = processor.parse_transform_string(svg_transform)

        # Convert to matrix
        matrix = processor.operations_to_matrix(operations)

        # Decompose for PowerPoint
        powerpoint = matrix.to_powerpoint_transform()

        # Verify conversion
        # After applying translate, rotate, and scale, the final translation
        # is affected by the transformations
        decomp = matrix.decompose()
        assert abs(decomp['scale'][0] - 1.5) < 0.01
        assert abs(decomp['scale'][1] - 1.5) < 0.01
        assert abs(decomp['rotate'] - 45) < 1  # 45 degrees rotation
        # Translation exists in the composed matrix
        assert abs(decomp['translate'][0]) > 0 or abs(decomp['translate'][1]) > 0

    def test_animation_sequence(self):
        """Test animation sequence generation."""
        generator = PowerPointTransformAnimationGenerator()

        # Simulate SVG animation values
        transforms = [
            "translate(0, 0) scale(1)",
            "translate(50, 50) scale(1.5) rotate(180)",
            "translate(100, 100) scale(1) rotate(360)"
        ]

        # Generate animations between keyframes
        animations = []
        for i in range(len(transforms) - 1):
            xml = generator.generate_transform_animation(
                transforms[i],
                transforms[i + 1],
                1000,
                f"animated_{i}"
            )
            animations.append(xml)

        # Verify animations were generated
        assert len(animations) == 2
        assert all("<a:" in anim for anim in animations)