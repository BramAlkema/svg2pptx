"""
SVG to DrawingML Converters Package

Modular architecture for high-fidelity SVG to DrawingML conversion.
Each converter handles specific SVG elements and attributes.
"""

from .base import BaseConverter, ConverterRegistry, CoordinateSystem, ConversionContext
from .shapes import RectangleConverter, CircleConverter, EllipseConverter, PolygonConverter, LineConverter
from .paths import PathConverter
from .text import TextConverter
from .gradients import GradientConverter
from .transforms import TransformConverter
from .styles import StyleProcessor
from .groups import GroupHandler

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
    'GradientConverter',
    'TransformConverter',
    'StyleProcessor',
    'GroupHandler'
]