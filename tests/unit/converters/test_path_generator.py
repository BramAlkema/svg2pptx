"""
Tests for PathGenerator

Comprehensive test suite for glyph-to-path conversion and DrawingML generation.
"""

import pytest
import math
from unittest.mock import Mock, patch, MagicMock

from src.converters.path_generator import PathGenerator, PathCommand, PathPoint
from src.converters.font_metrics import GlyphOutline


class TestPathPoint:
    """Test PathPoint namedtuple."""
    
    def test_creation(self):
        """Test PathPoint creation and access."""
        point = PathPoint(10.5, 20.5)
        assert point.x == 10.5
        assert point.y == 20.5
    
    def test_equality(self):
        """Test PathPoint equality."""
        point1 = PathPoint(10, 20)
        point2 = PathPoint(10, 20)
        point3 = PathPoint(10, 21)
        
        assert point1 == point2
        assert point1 != point3


class TestPathCommand:
    """Test PathCommand dataclass."""
    
    def test_creation(self):
        """Test PathCommand creation."""
        points = [PathPoint(0, 0), PathPoint(10, 10)]
        cmd = PathCommand('lineTo', points)
        
        assert cmd.command == 'lineTo'
        assert cmd.points == points
    
    def test_to_drawingml_moveto(self):
        """Test DrawingML conversion for moveTo command."""
        cmd = PathCommand('moveTo', [PathPoint(100, 200)])
        result = cmd.to_drawingml(scale=1.0)
        
        assert '<a:moveTo>' in result
        assert 'x="100"' in result
        assert 'y="200"' in result
    
    def test_to_drawingml_lineto(self):
        """Test DrawingML conversion for lineTo command."""
        cmd = PathCommand('lineTo', [PathPoint(100, 200)])
        result = cmd.to_drawingml(scale=2.0)
        
        assert '<a:lnTo>' in result
        assert 'x="200"' in result
        assert 'y="400"' in result
    
    def test_to_drawingml_curveto_cubic(self):
        """Test DrawingML conversion for cubic curveTo command."""
        points = [PathPoint(100, 100), PathPoint(150, 50), PathPoint(200, 100)]
        cmd = PathCommand('curveTo', points)
        result = cmd.to_drawingml(scale=1.0)
        
        assert '<a:cubicBezTo>' in result
        assert result.count('<a:pt') == 3
    
    def test_to_drawingml_curveto_quadratic(self):
        """Test DrawingML conversion for quadratic curveTo command."""
        points = [PathPoint(100, 100), PathPoint(200, 100)]
        cmd = PathCommand('curveTo', points)
        result = cmd.to_drawingml(scale=1.0)
        
        assert '<a:cubicBezTo>' in result
        # Quadratic converted to cubic should have 3 control points
        assert result.count('<a:pt') == 3
    
    def test_to_drawingml_close(self):
        """Test DrawingML conversion for closePath command."""
        cmd = PathCommand('closePath', [])
        result = cmd.to_drawingml(scale=1.0)
        
        assert result == '<a:close/>'
    
    def test_to_drawingml_empty_points(self):
        """Test DrawingML conversion with empty points."""
        cmd = PathCommand('moveTo', [])
        result = cmd.to_drawingml(scale=1.0)
        
        assert result == ''


class TestPathGenerator:
    """Test suite for PathGenerator functionality."""
    
    @pytest.fixture
    def generator(self):
        """Create PathGenerator instance for testing."""
        return PathGenerator(optimization_level=1)
    
    def test_initialization(self, generator):
        """Test proper initialization of PathGenerator."""
        assert generator.optimization_level == 1
        assert generator.EMU_PER_POINT == generator.EMU_PER_INCH / generator.POINTS_PER_INCH
    
    def test_constants(self, generator):
        """Test PathGenerator constants are reasonable."""
        assert generator.EMU_PER_INCH == 914400
        assert generator.POINTS_PER_INCH == 72
        assert generator.EMU_PER_POINT > 10000  # Should be around 12700
    
    def test_convert_glyph_to_commands_moveto(self, generator):
        """Test conversion of moveTo glyph data."""
        glyph_data = [('moveTo', [(100, 200)])]
        commands = generator._convert_glyph_to_commands(glyph_data)
        
        assert len(commands) == 1
        assert commands[0].command == 'moveTo'
        assert commands[0].points == [PathPoint(100, 200)]
    
    def test_convert_glyph_to_commands_lineto(self, generator):
        """Test conversion of lineTo glyph data."""
        glyph_data = [('lineTo', [(150, 250)])]
        commands = generator._convert_glyph_to_commands(glyph_data)
        
        assert len(commands) == 1
        assert commands[0].command == 'lineTo'
        assert commands[0].points == [PathPoint(150, 250)]
    
    def test_convert_glyph_to_commands_curveto(self, generator):
        """Test conversion of curveTo glyph data."""
        glyph_data = [('curveTo', [(100, 100), (150, 50), (200, 100)])]
        commands = generator._convert_glyph_to_commands(glyph_data)
        
        assert len(commands) == 1
        assert commands[0].command == 'curveTo'
        assert len(commands[0].points) == 3
    
    def test_convert_glyph_to_commands_qcurveto(self, generator):
        """Test conversion of qCurveTo glyph data."""
        glyph_data = [('qCurveTo', [(100, 100), (200, 100)])]
        commands = generator._convert_glyph_to_commands(glyph_data)
        
        assert len(commands) == 1
        assert commands[0].command == 'curveTo'  # Converted from qCurveTo
        assert len(commands[0].points) == 2
    
    def test_convert_glyph_to_commands_closepath(self, generator):
        """Test conversion of closePath glyph data."""
        glyph_data = [('closePath', [])]
        commands = generator._convert_glyph_to_commands(glyph_data)
        
        assert len(commands) == 1
        assert commands[0].command == 'closePath'
        assert commands[0].points == []
    
    def test_apply_transformations(self, generator):
        """Test coordinate transformations."""
        commands = [
            PathCommand('moveTo', [PathPoint(0, 0)]),
            PathCommand('lineTo', [PathPoint(100, 100)])
        ]
        
        transformed = generator._apply_transformations(commands, x_offset=10, y_offset=20, scale=2.0)
        
        assert len(transformed) == 2
        assert transformed[0].points[0] == PathPoint(10, 20)  # (0*2 + 10, 0*2 + 20)
        assert transformed[1].points[0] == PathPoint(210, 220)  # (100*2 + 10, 100*2 + 20)
    
    def test_apply_transformations_closepath(self, generator):
        """Test transformations preserve closePath commands."""
        commands = [PathCommand('closePath', [])]
        transformed = generator._apply_transformations(commands, x_offset=10, y_offset=20, scale=2.0)
        
        assert len(transformed) == 1
        assert transformed[0].command == 'closePath'
        assert transformed[0].points == []
    
    def test_optimize_path_commands_level_zero(self, generator):
        """Test optimization level 0 (no optimization)."""
        generator.optimization_level = 0
        commands = [
            PathCommand('moveTo', [PathPoint(0, 0)]),
            PathCommand('moveTo', [PathPoint(0, 0)])  # Duplicate
        ]
        
        optimized = generator._optimize_path_commands(commands)
        assert len(optimized) == 2  # No optimization should occur
    
    def test_optimize_path_commands_level_one(self, generator):
        """Test optimization level 1 (basic optimization)."""
        generator.optimization_level = 1
        commands = [
            PathCommand('moveTo', [PathPoint(0, 0)]),
            PathCommand('lineTo', [PathPoint(0, 0)])  # Same point
        ]
        
        optimized = generator._optimize_path_commands(commands)
        assert len(optimized) == 1  # Duplicate point should be removed
    
    def test_points_equal(self, generator):
        """Test point equality check with tolerance."""
        p1 = PathPoint(100.0, 200.0)
        p2 = PathPoint(100.05, 200.05)
        p3 = PathPoint(101.0, 201.0)
        
        assert generator._points_equal(p1, p2, tolerance=0.1) is True
        assert generator._points_equal(p1, p3, tolerance=0.1) is False
    
    def test_is_nearly_straight_curve(self, generator):
        """Test detection of nearly straight curves."""
        # Straight line
        p1 = PathPoint(0, 0)
        p2 = PathPoint(50, 50)  # On the line
        p3 = PathPoint(100, 100)
        assert generator._is_nearly_straight_curve(p1, p2, p3, tolerance=1.0) is True
        
        # Curved line
        p1 = PathPoint(0, 0)
        p2 = PathPoint(50, 100)  # Off the line
        p3 = PathPoint(100, 0)
        assert generator._is_nearly_straight_curve(p1, p2, p3, tolerance=1.0) is False
    
    def test_calculate_path_bounds(self, generator):
        """Test path bounding box calculation."""
        commands = [
            PathCommand('moveTo', [PathPoint(10, 20)]),
            PathCommand('lineTo', [PathPoint(100, 200)]),
            PathCommand('curveTo', [PathPoint(150, 50), PathPoint(200, 100), PathPoint(250, 150)])
        ]
        
        min_x, min_y, max_x, max_y = generator._calculate_path_bounds(commands)
        
        assert min_x == 10
        assert min_y == 20
        assert max_x == 250
        assert max_y == 200
    
    def test_calculate_path_bounds_empty(self, generator):
        """Test path bounds calculation with empty commands."""
        min_x, min_y, max_x, max_y = generator._calculate_path_bounds([])
        
        assert min_x == 0
        assert min_y == 0
        assert max_x == 100
        assert max_y == 100
    
    def test_generate_path_from_glyph_valid(self, generator):
        """Test path generation from valid glyph outline."""
        glyph_outline = GlyphOutline(
            unicode_char='A',
            glyph_name='A',
            advance_width=500,
            bbox=(0, 0, 500, 700),
            path_data=[
                ('moveTo', [(100, 0)]),
                ('lineTo', [(400, 700)]),
                ('lineTo', [(300, 700)]),
                ('closePath', [])
            ]
        )
        
        result = generator.generate_path_from_glyph(glyph_outline, x_offset=0, y_offset=0, scale=1.0)
        
        assert result is not None
        assert '<a:sp>' in result
        assert '<a:pathLst>' in result
        assert '<a:moveTo>' in result
        assert '<a:lnTo>' in result
        assert '<a:close/>' in result
    
    def test_generate_path_from_glyph_empty(self, generator):
        """Test path generation from empty glyph outline."""
        glyph_outline = GlyphOutline(
            unicode_char='',
            glyph_name='',
            advance_width=0,
            bbox=(0, 0, 0, 0),
            path_data=[]
        )
        
        result = generator.generate_path_from_glyph(glyph_outline)
        assert result is None
    
    def test_generate_path_from_glyph_none(self, generator):
        """Test path generation from None glyph outline."""
        result = generator.generate_path_from_glyph(None)
        assert result is None
    
    def test_generate_drawingml_path(self, generator):
        """Test complete DrawingML path generation."""
        commands = [
            PathCommand('moveTo', [PathPoint(0, 0)]),
            PathCommand('lineTo', [PathPoint(100, 100)]),
            PathCommand('closePath', [])
        ]
        
        result = generator._generate_drawingml_path(commands)
        
        assert '<a:sp>' in result
        assert '<a:nvSpPr>' in result
        assert '<a:spPr>' in result
        assert '<a:custGeom>' in result
        assert '<a:pathLst>' in result
        assert '<a:path' in result
        assert '{shape_id}' in result
        assert '{fill_style}' in result
    
    def test_create_text_group_shape(self, generator):
        """Test text group shape creation."""
        char_paths = [
            '<a:sp><a:nvSpPr><a:cNvPr id="{shape_id}" name="A"/></a:nvSpPr></a:sp>',
            '<a:sp><a:nvSpPr><a:cNvPr id="{shape_id}" name="B"/></a:nvSpPr></a:sp>'
        ]
        
        result = generator._create_text_group_shape(char_paths, x=100, y=200, width=300, height=50)
        
        assert '<a:grpSp>' in result
        assert '<a:nvGrpSpPr>' in result
        assert '<a:grpSpPr>' in result
        assert result.count('<a:sp>') == 2  # Two character shapes
    
    def test_generate_text_path_with_mock(self, generator):
        """Test text path generation with mocked analyzer."""
        mock_analyzer = Mock()
        
        # Mock font metrics
        mock_metrics = Mock()
        mock_metrics.ascender = 800
        mock_metrics.units_per_em = 1000
        mock_analyzer.get_font_metrics.return_value = mock_metrics
        
        # Mock glyph outline
        mock_glyph = GlyphOutline(
            unicode_char='A',
            glyph_name='A',
            advance_width=500,
            bbox=(0, 0, 500, 700),
            path_data=[('moveTo', [(100, 0)]), ('lineTo', [(400, 700)])]
        )
        mock_analyzer.get_glyph_outline.return_value = mock_glyph
        
        result = generator.generate_text_path(
            text='A',
            font_metrics_analyzer=mock_analyzer,
            font_family='Arial',
            font_size=12,
            x=0,
            y=0
        )
        
        assert result is not None
        assert '{shape_id}' in result
    
    def test_generate_text_path_empty_text(self, generator):
        """Test text path generation with empty text."""
        mock_analyzer = Mock()
        result = generator.generate_text_path('', mock_analyzer, 'Arial', 12)
        assert result is None
    
    def test_generate_text_path_no_metrics(self, generator):
        """Test text path generation when metrics unavailable."""
        mock_analyzer = Mock()
        mock_analyzer.get_font_metrics.return_value = None
        
        result = generator.generate_text_path('A', mock_analyzer, 'UnknownFont', 12)
        assert result is None
    
    def test_generate_text_path_with_spaces(self, generator):
        """Test text path generation with spaces."""
        mock_analyzer = Mock()
        
        # Mock font metrics
        mock_metrics = Mock()
        mock_metrics.ascender = 800
        mock_metrics.units_per_em = 1000
        mock_analyzer.get_font_metrics.return_value = mock_metrics
        
        # Mock glyph outline for 'A' only (spaces are handled specially)
        mock_glyph = GlyphOutline(
            unicode_char='A',
            glyph_name='A',
            advance_width=500,
            bbox=(0, 0, 500, 700),
            path_data=[('moveTo', [(100, 0)])]
        )
        mock_analyzer.get_glyph_outline.return_value = mock_glyph
        
        result = generator.generate_text_path('A A', mock_analyzer, 'Arial', 12)
        
        # Should handle text with spaces
        mock_analyzer.get_glyph_outline.assert_called()  # Called for 'A' characters
        assert result is not None
    
    def test_get_optimization_stats(self, generator):
        """Test optimization statistics reporting."""
        stats = generator.get_optimization_stats()
        
        assert 'optimization_level' in stats
        assert 'emu_per_point' in stats
        assert 'points_per_inch' in stats
        assert 'emu_per_inch' in stats
        
        assert stats['optimization_level'] == generator.optimization_level
        assert stats['emu_per_point'] == generator.EMU_PER_POINT


@pytest.mark.parametrize("optimization_level", [0, 1, 2])
def test_optimization_levels(optimization_level):
    """Test different optimization levels."""
    generator = PathGenerator(optimization_level=optimization_level)
    assert generator.optimization_level == optimization_level


@pytest.mark.parametrize("scale_factor", [0.5, 1.0, 2.0, 10.0])
def test_scaling_factors(scale_factor):
    """Test various scaling factors."""
    generator = PathGenerator()
    cmd = PathCommand('moveTo', [PathPoint(100, 200)])
    result = cmd.to_drawingml(scale=scale_factor)
    
    expected_x = int(100 * scale_factor)
    expected_y = int(200 * scale_factor)
    
    assert f'x="{expected_x}"' in result
    assert f'y="{expected_y}"' in result