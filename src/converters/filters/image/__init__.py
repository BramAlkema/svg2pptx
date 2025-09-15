"""
Image processing filters.

This module contains filter implementations for image-based effects:
- blur: Gaussian blur, motion blur, and other blur effects
- color: Color matrix operations, flood effects, lighting
- convolve_matrix: Convolution matrix operations for edge detection and filtering
- distortion: Displacement maps, morphology operations
"""

from .blur import GaussianBlurFilter, MotionBlurFilter, BlurFilterException
from .color import ColorMatrixFilter, FloodFilter, LightingFilter, ColorFilterException
from .convolve_matrix import ConvolveMatrixFilter, ConvolveMatrixParameters, EdgeMode

__all__ = [
    "GaussianBlurFilter",
    "MotionBlurFilter",
    "BlurFilterException",
    "ColorMatrixFilter",
    "FloodFilter",
    "LightingFilter",
    "ColorFilterException",
    "ConvolveMatrixFilter",
    "ConvolveMatrixParameters",
    "EdgeMode",
]