"""
SVG to DrawingML Converters Package

Modular architecture for high-fidelity SVG to DrawingML conversion.
Each converter handles specific SVG elements and attributes.
"""

from .base import BaseConverter, ConverterRegistry, CoordinateSystem, ConversionContext
from .shapes import RectangleConverter, CircleConverter, EllipseConverter, PolygonConverter, LineConverter
from .paths import PathConverter
from .text import TextConverter
from .text_to_path import TextToPathConverter
from .font_metrics import FontMetricsAnalyzer
from .path_generator import PathGenerator
from .font_embedding import FontEmbeddingAnalyzer, EmbeddedFontFace, FontEmbedResult
from .gradients import GradientConverter
from .transforms import TransformConverter
from .styles import StyleProcessor
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
    'PathConverter',
    'TextConverter',
    'TextToPathConverter',
    'FontMetricsAnalyzer',
    'PathGenerator',
    'FontEmbeddingAnalyzer',
    'EmbeddedFontFace',
    'FontEmbedResult',
    'GradientConverter',
    'TransformConverter',
    'StyleProcessor',
    'GroupHandler',
    'ImageConverter',
    'StyleConverter'
]