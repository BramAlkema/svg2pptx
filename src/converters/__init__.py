"""
SVG to DrawingML Converters Package

Modular architecture for high-fidelity SVG to DrawingML conversion.
Each converter handles specific SVG elements and attributes.
"""

from .base import BaseConverter, ConverterRegistry, CoordinateSystem, ConversionContext
# Import shape converters - will be available after shapes/__init__.py is fixed
from .shapes import RectangleConverter, CircleConverter, EllipseConverter, PolygonConverter, LineConverter
# PathConverter removed - use src.paths.PathEngine directly
from .text import TextConverter
from .text_path_engine import TextPathEngine
from .font_metrics import FontMetricsAnalyzer
from .path_generator import PathGenerator
from .font_embedding import FontEmbeddingAnalyzer, EmbeddedFontFace, FontEmbedResult
try:
    from .gradients import GradientConverter
except ImportError:
    # Use core gradient engine as fallback
    from .gradients import GradientEngine as GradientConverter
# TransformConverter removed - using consolidated transform engine directly
from .style_engine import StyleEngine
from .groups import GroupHandler
from .image import ImageConverter
from .style import StyleConverter

__all__ = [
    'BaseConverter',
    'ConverterRegistry',
    'CoordinateSystem',
    'ConversionContext',
    'RectangleConverter',
    'CircleConverter',
    'EllipseConverter',
    'PolygonConverter',
    'LineConverter',
    # 'PathConverter', # Removed - use src.paths.PathEngine
    'TextConverter',
    'TextPathEngine',
    'FontMetricsAnalyzer',
    'PathGenerator',
    'FontEmbeddingAnalyzer',
    'EmbeddedFontFace',
    'FontEmbedResult',
    'GradientConverter',
    # 'TransformConverter', # Removed - using consolidated transform engine
    'StyleEngine',
    'GroupHandler',
    'ImageConverter',
    'StyleConverter'
]